"""
Cache compartido de tablas Access para modelos diarios.

Este módulo implementa una capa de caché en archivos Parquet para las tablas
leídas desde archivos MS Access en la red. Como múltiples modelos
(NMD, LC, Prepago CMR, Inversiones) leen las mismas tablas del mismo
archivo Access (RF_Base_Carteras_Completa.accdb), este caché evita lecturas
redundantes durante el mismo día de ejecución.

Lectura Access:
    Se usa pyodbc directamente (sin SQLAlchemy) para evitar el cuello de
    botella de ``has_table()`` que itera todas las tablas del .accdb sobre
    rutas UNC de red, provocando cuelgues o tiempos excesivos.

Estructura de archivos:
    data/cache/
        RF_BD_Gestion_RL_20260218.parquet
        RF_BD_Gestion_RM_20260218.parquet
        RF_base_Completa_Hist_20260218.parquet
        ...

Uso básico:
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    # Primera ejecución del día: lee de Access, guarda parquet
    df = leer_tabla_con_cache(
        access_path='//vmdvorak/.../RF_Base_Carteras_Completa.accdb',
        nombre_tabla='RF_BD_Gestion_RL',
        fecha_proceso=20260218,
    )

    # Ejecuciones siguientes: lee de parquet (instantáneo)
    df = leer_tabla_con_cache(...)

Autor: Modelos & Metodologías
Fecha: 2026-02

TODOs futuros:
  - [ ] Caché compartido NMD/LC: Actualmente NMD cachea 'NMD_balance' y
    'NMD_dap_contractual', y LC cachea 'LC_balance', cada uno con su propia
    query SQL. Ambos leen de la misma tabla RF_BD_Gestion_RL. Se podría
    cachear un SELECT * FROM RF_BD_Gestion_RL WHERE Fec_Pro=#date# como
    tabla completa y que cada modelo aplique su GROUP BY / HAVING como
    operaciones pandas post-lectura. Esto eliminaría lecturas duplicadas
    al Access cuando se ejecuta segunda_vuelta.
  - [ ] Caché local para primera vuelta: Los modelos de primera vuelta
    (mr_prepago_consumo, mr_prepago_hipotecario, ml_mora_*) leen archivos
    CSV/Excel desde la ruta de red \\vmdvorak\...\RRFF-GCP\Cartera\input.
    Se podría implementar una descarga inicial a local (data/cache/) para
    que las re-ejecuciones del mismo día no dependan de la red.
"""

import os
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Union

import pandas as pd
import pyodbc


# =============================================================================
# CONSTANTES
# =============================================================================

# Directorio de caché por defecto (relativo a la raíz del proyecto)
_BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR_DEFAULT = _BASE_DIR / 'data' / 'cache'

# Tablas conocidas y el archivo Access donde viven
CATALOGO_TABLAS = {
    # RF_Base_Carteras_Completa.accdb
    'RF_BD_Gestion_RL': 'RF_Base_Carteras_Completa.accdb',
    'RF_BD_Gestion_RM': 'RF_Base_Carteras_Completa.accdb',
    'RF_base_Completa_Hist': 'RF_Base_Carteras_Completa.accdb',
    'RF_Cartera_RtaFija_Hist': 'RF_Base_Carteras_Completa.accdb',
    # RF_Base_PT_Puente.accdb
    'RF_Base_Diaria_Precios': 'RF_Base_PT_Puente.accdb',
}
"""Mapeo de nombre de tabla → archivo Access de origen."""

# Variable de entorno para forzar recarga global
ENV_FORZAR_RECARGA = 'CACHE_FORZAR_RECARGA'

# Reintentos de conexión
_MAX_REINTENTOS = 3
_ESPERA_BASE_SECS = 2.0


# =============================================================================
# CONEXIÓN ACCESS
# =============================================================================

def _conectar_access(
    access_path: Union[str, Path],
    timeout: int = 60,
    verbose: bool = True,
) -> pyodbc.Connection:
    """
    Conecta a un archivo Access con reintentos automáticos.

    Si la primera conexión falla (error intermitente de pyodbc con
    archivos grandes sobre rutas UNC), reintenta hasta ``_MAX_REINTENTOS``
    veces con espera exponencial.

    Args:
        access_path: Ruta al archivo .accdb
        timeout: Timeout de conexión en segundos
        verbose: Si True, imprime mensajes de progreso

    Returns:
        Conexión pyodbc activa

    Raises:
        pyodbc.Error: Si se agotan todos los reintentos
    """
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={access_path};"
    )

    last_err = None
    for intento in range(1, _MAX_REINTENTOS + 1):
        try:
            conn = pyodbc.connect(conn_str, timeout=timeout)
            return conn
        except Exception as e:
            last_err = e
            if intento < _MAX_REINTENTOS:
                espera = _ESPERA_BASE_SECS * intento
                if verbose:
                    print(f"    ⚠ Conexión fallida (intento {intento}/{_MAX_REINTENTOS}): {e}")
                    print(f"      Reintentando en {espera:.0f}s...")
                time.sleep(espera)

    raise last_err  # type: ignore[misc]


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================

def leer_tabla_con_cache(
    access_path: Union[str, Path],
    nombre_tabla: str,
    fecha_proceso: Union[int, str],
    query: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    forzar_recarga: bool = False,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Lee una tabla desde Access con caché transparente en Parquet.

    En la primera invocación del día, lee la tabla completa desde Access
    y la guarda como Parquet en el directorio de caché. Las invocaciones
    siguientes cargan directamente desde Parquet (~10-50x más rápido).

    IMPORTANTE: El caché almacena la tabla completa (SELECT * FROM tabla).
    Si el caller necesita un subconjunto, debe filtrar el DataFrame
    después de la lectura. Esto permite que múltiples modelos con queries
    distintas compartan el mismo archivo de caché.

    Args:
        access_path: Ruta al archivo .accdb
        nombre_tabla: Nombre de la tabla en Access
        fecha_proceso: Fecha de proceso (YYYYMMDD int o string)
        query: Query SQL personalizada (solo se usa si no hay caché).
               Si es None, usa 'SELECT * FROM [nombre_tabla]'.
        cache_dir: Directorio de caché. None = data/cache/
        forzar_recarga: Si True, ignora caché existente y lee de Access
        verbose: Si True, muestra mensajes de progreso

    Returns:
        DataFrame con los datos de la tabla
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    fecha_str = str(fecha_proceso)
    nombre_archivo = f"{nombre_tabla}_{fecha_str}.parquet"
    ruta_cache = cache_dir / nombre_archivo

    # Chequear env var para forzar recarga global
    forzar_recarga = forzar_recarga or os.environ.get(ENV_FORZAR_RECARGA, '') == '1'

    # --- Intentar leer de caché ---
    if ruta_cache.exists() and not forzar_recarga:
        if verbose:
            size_mb = ruta_cache.stat().st_size / (1024 * 1024)
            print(f"  ⚡ Cache: {nombre_tabla} ({size_mb:.1f} MB)")
        t0 = time.perf_counter()
        df = pd.read_parquet(ruta_cache)
        if verbose:
            dt = time.perf_counter() - t0
            print(f"     → {len(df):,} filas en {dt:.2f}s")
        return df

    # --- Leer desde Access (pyodbc directo, sin SQLAlchemy) ---
    access_path = Path(access_path)
    if not access_path.exists():
        raise FileNotFoundError(f"Archivo Access no encontrado: {access_path}")

    if query is None:
        query = f"SELECT * FROM [{nombre_tabla}]"

    if verbose:
        print(f"  📂 Access: {nombre_tabla} ← {access_path.name}")

    t0 = time.perf_counter()
    conn = _conectar_access(access_path, verbose=verbose)
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()
    dt_access = time.perf_counter() - t0

    if verbose:
        print(f"     → {len(df):,} filas en {dt_access:.1f}s")

    # --- Guardar caché ---
    try:
        t0 = time.perf_counter()
        df.to_parquet(ruta_cache, index=False, engine='pyarrow')
        dt_save = time.perf_counter() - t0
        size_mb = ruta_cache.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  💾 Guardado: {nombre_archivo} ({size_mb:.1f} MB, {dt_save:.1f}s)")
    except Exception as e:
        warnings.warn(f"No se pudo guardar caché {nombre_archivo}: {e}")

    return df


def leer_multiples_tablas_con_cache(
    access_path: Union[str, Path],
    tablas: List[Union[str, dict]],
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
    forzar_recarga: bool = False,
    verbose: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Lee múltiples tablas desde un mismo archivo Access con caché.

    Reutiliza una única conexión pyodbc para todas las tablas que
    necesitan leerse desde Access (las que no tienen caché).

    Args:
        access_path: Ruta al archivo .accdb
        tablas: Lista de nombres de tabla (str), o lista de dicts con
                {'nombre_fuente': str, 'nombre_destino': str, 'query': str}.
        fecha_proceso: Fecha de proceso (YYYYMMDD)
        cache_dir: Directorio de caché
        forzar_recarga: Si True, ignora caché existente
        verbose: Si True, muestra mensajes

    Returns:
        Dict[nombre_destino, DataFrame]

    Example:
        >>> tablas = leer_multiples_tablas_con_cache(
        ...     access_path='//server/RF_Base_Carteras_Completa.accdb',
        ...     tablas=[
        ...         'RF_BD_Gestion_RL',
        ...         {'nombre_fuente': 'RF_base_Completa_Hist',
        ...          'nombre_destino': 'RF_base_Completa_Hist_Input'},
        ...     ],
        ...     fecha_proceso=20260218,
        ... )
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    access_path = Path(access_path)
    fecha_str = str(fecha_proceso)
    forzar_recarga = forzar_recarga or os.environ.get(ENV_FORZAR_RECARGA, '') == '1'

    resultado: Dict[str, pd.DataFrame] = {}

    # --- Separar tablas con caché vs sin caché ---
    tablas_pendientes: list = []  # (nombre_fuente, nombre_destino, query)

    for tabla_spec in tablas:
        if isinstance(tabla_spec, str):
            nombre_fuente = tabla_spec
            nombre_destino = tabla_spec
            query = None
        else:
            nombre_fuente = tabla_spec['nombre_fuente']
            nombre_destino = tabla_spec.get('nombre_destino', nombre_fuente)
            query = tabla_spec.get('query')

        ruta_cache = cache_dir / f"{nombre_fuente}_{fecha_str}.parquet"

        if ruta_cache.exists() and not forzar_recarga:
            if verbose:
                size_mb = ruta_cache.stat().st_size / (1024 * 1024)
                print(f"  ⚡ Cache: {nombre_fuente} ({size_mb:.1f} MB)")
            t0 = time.perf_counter()
            df = pd.read_parquet(ruta_cache)
            if verbose:
                dt = time.perf_counter() - t0
                print(f"     → {len(df):,} filas en {dt:.2f}s")
            resultado[nombre_destino] = df
        else:
            tablas_pendientes.append((nombre_fuente, nombre_destino, query))

    # --- Leer pendientes con una sola conexión pyodbc ---
    if tablas_pendientes:
        if not access_path.exists():
            raise FileNotFoundError(f"Archivo Access no encontrado: {access_path}")

        if verbose:
            print(f"  🔌 Conectando a {access_path.name} "
                  f"({len(tablas_pendientes)} tabla(s) pendiente(s))...")

        t_conn = time.perf_counter()
        conn = _conectar_access(access_path, verbose=verbose)
        if verbose:
            print(f"     Conexión OK en {time.perf_counter() - t_conn:.1f}s")

        try:
            for nombre_fuente, nombre_destino, query in tablas_pendientes:
                sql = query if query else f"SELECT * FROM [{nombre_fuente}]"
                if verbose:
                    print(f"  📂 Access: {nombre_fuente}")

                t0 = time.perf_counter()
                try:
                    df = pd.read_sql(sql, conn)
                except Exception as e:
                    print(f"    ✗ Error leyendo {nombre_fuente}: {e}")
                    continue
                dt_access = time.perf_counter() - t0

                if verbose:
                    print(f"     → {len(df):,} filas en {dt_access:.1f}s")

                resultado[nombre_destino] = df

                # Guardar caché
                ruta_cache = cache_dir / f"{nombre_fuente}_{fecha_str}.parquet"
                try:
                    t0 = time.perf_counter()
                    df.to_parquet(ruta_cache, index=False, engine='pyarrow')
                    dt_save = time.perf_counter() - t0
                    size_mb = ruta_cache.stat().st_size / (1024 * 1024)
                    if verbose:
                        print(f"  💾 Guardado: {ruta_cache.name} "
                              f"({size_mb:.1f} MB, {dt_save:.1f}s)")
                except Exception as e:
                    warnings.warn(
                        f"No se pudo guardar caché {ruta_cache.name}: {e}"
                    )
        finally:
            conn.close()
            if verbose:
                print(f"  🔌 Conexión cerrada")

    return resultado


# =============================================================================
# UTILIDADES
# =============================================================================

def listar_cache(
    cache_dir: Optional[Path] = None,
    fecha_proceso: Optional[Union[int, str]] = None,
) -> List[dict]:
    """
    Lista los archivos de caché disponibles.

    Args:
        cache_dir: Directorio de caché. None = data/cache/
        fecha_proceso: Filtrar por fecha (opcional)

    Returns:
        Lista de dicts con info de cada archivo.
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT

    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return []

    patron = f"*_{fecha_proceso}.parquet" if fecha_proceso else "*.parquet"
    archivos = sorted(cache_dir.glob(patron))

    resultado = []
    for archivo in archivos:
        partes = archivo.stem.rsplit('_', 1)
        nombre_tabla = partes[0] if len(partes) == 2 else archivo.stem
        fecha = partes[1] if len(partes) == 2 else 'unknown'

        resultado.append({
            'archivo': archivo,
            'tabla': nombre_tabla,
            'fecha': fecha,
            'size_mb': archivo.stat().st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(archivo.stat().st_mtime),
        })

    return resultado


def limpiar_cache(
    cache_dir: Optional[Path] = None,
    fecha_proceso: Optional[Union[int, str]] = None,
    dias_antiguos: Optional[int] = None,
    verbose: bool = True,
) -> int:
    """
    Elimina archivos de caché.

    Args:
        cache_dir: Directorio de caché
        fecha_proceso: Si se indica, elimina solo los de esa fecha
        dias_antiguos: Si se indica, elimina los de más de N días
        verbose: Muestra mensajes

    Returns:
        Número de archivos eliminados
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT

    caches = listar_cache(cache_dir, fecha_proceso)
    eliminados = 0

    from datetime import timedelta
    fecha_limite = (
        datetime.now() - timedelta(days=dias_antiguos)
        if dias_antiguos is not None
        else None
    )

    for cache_info in caches:
        eliminar = False
        if fecha_proceso:
            eliminar = True  # Si se pidió una fecha, eliminar todo de esa fecha
        elif fecha_limite and cache_info['modified'] < fecha_limite:
            eliminar = True

        if eliminar:
            try:
                cache_info['archivo'].unlink()
                eliminados += 1
                if verbose:
                    print(f"  🗑 Eliminado: {cache_info['archivo'].name}")
            except Exception as e:
                if verbose:
                    print(f"  ⚠ Error eliminando {cache_info['archivo'].name}: {e}")

    if verbose and eliminados > 0:
        print(f"  Total eliminados: {eliminados} archivos")

    return eliminados


def invalidar_tabla(
    nombre_tabla: str,
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
    verbose: bool = True,
) -> bool:
    """
    Invalida (elimina) el caché de una tabla específica.

    Args:
        nombre_tabla: Nombre de la tabla a invalidar
        fecha_proceso: Fecha del caché a eliminar
        cache_dir: Directorio de caché

    Returns:
        True si se eliminó, False si no existía
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT

    ruta = Path(cache_dir) / f"{nombre_tabla}_{fecha_proceso}.parquet"
    if ruta.exists():
        ruta.unlink()
        if verbose:
            print(f"  🗑 Invalidado: {ruta.name}")
        return True
    return False
