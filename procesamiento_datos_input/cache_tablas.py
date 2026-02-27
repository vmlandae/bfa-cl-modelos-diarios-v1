r"""
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
import hashlib
import json
import shutil
import threading
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Union

import pandas as pd
import pyodbc

from core.logger import get_logger

logger = get_logger(__name__)


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

# Nombre del archivo de interfaz (PML = ProductosMercadoLiquidez)
INTERFAZ_PML_PATRON = "ProductosMercadoLiquidezGCP{fecha}.txt"

# Columnas y dtypes comunes a los 6 modelos de primera vuelta
INTERFAZ_PML_COLUMNAS = [
    "FECHA_PROCESO", "SISTEMA", "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO",
    "DESTINOCREDITO", "MONEDA_ORIGEN", "AMORTIZACION", "INTERES",
    "FECHA_VENCIMIENTO_CUOTA",
]
INTERFAZ_PML_DTYPES = {
    "FECHA_PROCESO": "str", "SISTEMA": "str", "CODIGO_PRODUCTO": "str",
    "CODIGO_SUBPRODUCTO": "str", "DESTINOCREDITO": "str",
    "MONEDA_ORIGEN": "str", "AMORTIZACION": "float",
    "INTERES": "float", "FECHA_VENCIMIENTO_CUOTA": "str",
}


# =============================================================================
# INTERFAZ PML — COPIA LOCAL + CACHÉ PARQUET  (F14)
# =============================================================================
#
# Arquitectura (post-fix race condition):
#
#   PRE-EJECUCIÓN  (orquestador, 1 sola vez, hilo principal):
#     copiar_interfaz_a_local()  — copia .txt de red → data/cache/raw/
#
#   DURANTE EJECUCIÓN  (N hilos en paralelo):
#     leer_interfaz_con_cache()  — lee SOLO desde local/parquet,
#                                  NUNCA toca la red
#
#   POST-EJECUCIÓN  (orquestador, 1 sola vez, hilo principal):
#     verificar_interfaz_post_ejecucion()  — compara checksum local vs red,
#                                            emite WARNING si el archivo cambió
#
# Lock de seguridad: si un modelo se ejecuta sin orquestador,
# copiar_interfaz_a_local() usa un threading.Lock para evitar copias
# paralelas del mismo archivo.
# =============================================================================

_lock_copia_interfaz = threading.Lock()


def _md5_archivo(ruta: Path, chunk_size: int = 8192) -> str:
    """Calcula hash MD5 de un archivo."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def _ruta_metadata(ruta_raw_local: Path) -> Path:
    """Ruta del archivo de metadata JSON asociado al raw."""
    return ruta_raw_local.with_suffix(".meta.json")


def _guardar_metadata(ruta_raw_local: Path, checksum: str) -> None:
    """Guarda metadata de la copia: timestamp + checksum."""
    meta = {
        "timestamp_copia": datetime.now().isoformat(timespec="seconds"),
        "checksum_md5": checksum,
        "archivo_origen": str(ruta_raw_local.name),
    }
    _ruta_metadata(ruta_raw_local).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _leer_metadata(ruta_raw_local: Path) -> Optional[dict]:
    """Lee metadata existente, o None si no existe."""
    ruta = _ruta_metadata(ruta_raw_local)
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolver_rutas_interfaz(
    ruta_red: Union[str, Path],
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
) -> tuple:
    """Resuelve rutas de origen (red), local (.txt) y parquet.

    Returns:
        (ruta_origen, ruta_local_txt, ruta_parquet, fecha_str)
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT
    cache_dir = Path(cache_dir)
    raw_dir = cache_dir / "raw"

    fecha_str = str(fecha_proceso)
    nombre_archivo = INTERFAZ_PML_PATRON.format(fecha=fecha_str)

    ruta_origen = Path(ruta_red) / nombre_archivo
    ruta_local = raw_dir / nombre_archivo
    ruta_parquet = cache_dir / f"interfaz_pml_{fecha_str}.parquet"

    return ruta_origen, ruta_local, ruta_parquet, fecha_str


def copiar_interfaz_a_local(
    ruta_red: Union[str, Path],
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
    forzar_recarga: bool = False,
) -> Path:
    """Copia el .txt de interfaz desde red a local (raw, sin modificar).

    Diseñado para ser llamado **una sola vez** desde el orquestador
    antes de lanzar los hilos de los modelos.  Usa un ``threading.Lock``
    como guardia adicional para el caso en que un modelo se ejecute
    individualmente sin orquestador.

    Si el archivo local ya existe y ``forzar_recarga=False``:
      - Verifica checksum de la **copia local** contra su metadata.
      - Si la metadata coincide → no recopia (rápido, sin tocar red).
      - Si no hay metadata → recalcula md5 local, guarda metadata.
      - NO accede a la red aquí; la verificación de red se hace en
        ``verificar_interfaz_post_ejecucion()`` al final.

    Args:
        ruta_red: Ruta de red a la carpeta que contiene el .txt.
        fecha_proceso: Fecha ``YYYYMMDD``.
        cache_dir: Directorio de caché. None = ``data/cache/``.
        forzar_recarga: Si True, siempre recopia desde red.

    Returns:
        Path al archivo .txt local.

    Raises:
        FileNotFoundError: Si el archivo no existe en red.
    """
    forzar_recarga = forzar_recarga or os.environ.get(ENV_FORZAR_RECARGA, '') == '1'

    ruta_origen, ruta_local, _, fecha_str = _resolver_rutas_interfaz(
        ruta_red, fecha_proceso, cache_dir,
    )

    with _lock_copia_interfaz:
        # Dentro del lock: verificar de nuevo (double-check locking)
        raw_dir = ruta_local.parent
        raw_dir.mkdir(parents=True, exist_ok=True)

        # --- Ya existe copia local ---
        if ruta_local.exists() and not forzar_recarga:
            meta = _leer_metadata(ruta_local)
            if meta and meta.get("checksum_md5"):
                logger.info(
                    f"  ✓ Interfaz local vigente: {ruta_local.name} "
                    f"(copiado {meta['timestamp_copia']}, md5={meta['checksum_md5'][:8]}...)"
                )
                return ruta_local
            # Sin metadata → calcular md5 del archivo existente y guardar
            checksum_local = _md5_archivo(ruta_local)
            _guardar_metadata(ruta_local, checksum_local)
            logger.info(
                f"  ✓ Interfaz local existente (metadata regenerada): "
                f"{ruta_local.name} (md5={checksum_local[:8]}...)"
            )
            return ruta_local

        # --- Copiar desde red ---
        if not ruta_origen.exists():
            raise FileNotFoundError(
                f"Archivo de interfaz no encontrado en red: {ruta_origen}"
            )

        t0 = time.perf_counter()
        shutil.copy2(ruta_origen, ruta_local)
        dt = time.perf_counter() - t0
        size_mb = ruta_local.stat().st_size / (1024 * 1024)
        checksum = _md5_archivo(ruta_local)
        _guardar_metadata(ruta_local, checksum)
        logger.info(
            f"  📥 Interfaz copiada: {ruta_local.name} "
            f"({size_mb:.1f} MB, {dt:.1f}s, md5={checksum[:8]}...)"
        )
        return ruta_local


def verificar_interfaz_post_ejecucion(
    ruta_red: Union[str, Path],
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
) -> bool:
    """Verifica que el archivo de red no haya cambiado durante la ejecución.

    Compara el checksum MD5 de la copia local contra el archivo actual
    en red.  Si difieren, emite un WARNING visible (el usuario deberá
    decidir si re-ejecutar).

    Diseñado para llamarse **una sola vez** desde el orquestador
    después de que todos los modelos de primera vuelta terminaron.

    Args:
        ruta_red: Ruta de red a la carpeta con el .txt.
        fecha_proceso: Fecha ``YYYYMMDD``.
        cache_dir: Directorio de caché.

    Returns:
        True si checksums coinciden (OK), False si difieren o hay error.
    """
    ruta_origen, ruta_local, ruta_parquet, _ = _resolver_rutas_interfaz(
        ruta_red, fecha_proceso, cache_dir,
    )

    if not ruta_local.exists():
        logger.warning("  ⚠ Verificación post-ejecución: copia local no existe")
        return False

    meta = _leer_metadata(ruta_local)
    checksum_local = meta["checksum_md5"] if meta else _md5_archivo(ruta_local)

    try:
        checksum_red = _md5_archivo(ruta_origen)
    except Exception as e:
        logger.warning(
            f"  ⚠ No se pudo verificar archivo en red post-ejecución: {e}"
        )
        return False

    if checksum_red == checksum_local:
        logger.info(
            f"  ✓ Verificación post-ejecución OK: archivo de red no cambió "
            f"(md5={checksum_local[:8]}...)"
        )
        return True

    logger.warning(
        f"  ⚠ ¡ARCHIVO CAMBIÓ EN RED DURANTE LA EJECUCIÓN!\n"
        f"    Archivo  : {ruta_origen.name}\n"
        f"    MD5 local: {checksum_local}\n"
        f"    MD5 red  : {checksum_red}\n"
        f"    → Los resultados podrían estar basados en datos desactualizados.\n"
        f"    → Considere re-ejecutar los modelos de primera vuelta."
    )
    # Invalidar parquet para que la próxima ejecución re-parsee
    if ruta_parquet.exists():
        ruta_parquet.unlink()
        logger.info(f"    → Parquet invalidado: {ruta_parquet.name}")

    return False


def leer_interfaz_con_cache(
    ruta_red: Union[str, Path],
    fecha_proceso: Union[int, str],
    cache_dir: Optional[Path] = None,
    forzar_recarga: bool = False,
) -> pd.DataFrame:
    """Lee la interfaz PML desde la **copia local** con caché parquet.

    **No accede a la red.**  Espera que ``copiar_interfaz_a_local()``
    haya sido llamado previamente (por el orquestador o manualmente).

    Flujo:
      1. Busca parquet cacheado ``data/cache/interfaz_pml_{fecha}.parquet``
      2. Si no hay parquet → lee el .txt local con ``pd.read_csv()``
      3. Aplica limpieza común (datetimes, strip de strings)
      4. Guarda parquet para próximas lecturas
      5. Retorna DataFrame completo (cada modelo filtra después)

    Si la copia local no existe, intenta copiar desde red como fallback
    (para el caso de ejecución individual sin orquestador).

    Args:
        ruta_red: Ruta de red (usada como fallback si no hay copia local).
        fecha_proceso: Fecha ``YYYYMMDD``.
        cache_dir: Directorio de caché. None = ``data/cache/``.
        forzar_recarga: Si True, re-parsea desde .txt local.

    Returns:
        DataFrame con las 9 columnas comunes, fechas como datetime,
        strings ya strip()eados.
    """
    forzar_recarga = forzar_recarga or os.environ.get(ENV_FORZAR_RECARGA, '') == '1'

    if cache_dir is None:
        cache_dir = CACHE_DIR_DEFAULT
    cache_dir = Path(cache_dir)

    _, ruta_local_txt, ruta_parquet, fecha_str = _resolver_rutas_interfaz(
        ruta_red, fecha_proceso, cache_dir,
    )

    # Paso 1: buscar parquet cacheado
    if ruta_parquet.exists() and not forzar_recarga:
        size_mb = ruta_parquet.stat().st_size / (1024 * 1024)
        logger.info(f"  ⚡ Cache interfaz: {ruta_parquet.name} ({size_mb:.1f} MB)")
        t0 = time.perf_counter()
        df = pd.read_parquet(ruta_parquet)
        dt = time.perf_counter() - t0
        logger.info(f"     → {len(df):,} filas en {dt:.2f}s")
        return df

    # Paso 2: verificar que existe copia local .txt
    if not ruta_local_txt.exists():
        # Fallback: copiar desde red (ejecución sin orquestador)
        logger.warning(
            f"  ⚠ Copia local no encontrada, copiando desde red (fallback)..."
        )
        copiar_interfaz_a_local(ruta_red, fecha_proceso, cache_dir, forzar_recarga)

    # Paso 3: leer .txt local → DataFrame
    logger.info(f"  📂 Leyendo interfaz local: {ruta_local_txt.name}")
    t0 = time.perf_counter()
    df = pd.read_csv(
        ruta_local_txt,
        sep=";",
        decimal=",",
        usecols=INTERFAZ_PML_COLUMNAS,
        dtype=INTERFAZ_PML_DTYPES,
    )
    dt_read = time.perf_counter() - t0
    logger.info(f"     → {len(df):,} filas en {dt_read:.1f}s")

    # Paso 4: limpieza común (misma que los 6 modelos hacían inline)
    df["FECHA_PROCESO"] = pd.to_datetime(df["FECHA_PROCESO"], format="%Y%m%d")
    df["FECHA_VENCIMIENTO_CUOTA"] = pd.to_datetime(
        df["FECHA_VENCIMIENTO_CUOTA"], format="%Y%m%d"
    )
    for col in ("CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO", "DESTINOCREDITO", "SISTEMA"):
        df[col] = df[col].str.strip()

    # Paso 5: guardar parquet
    try:
        t0 = time.perf_counter()
        df.to_parquet(ruta_parquet, index=False, engine="pyarrow")
        dt_save = time.perf_counter() - t0
        size_mb = ruta_parquet.stat().st_size / (1024 * 1024)
        logger.info(
            f"  💾 Guardado: {ruta_parquet.name} ({size_mb:.1f} MB, {dt_save:.1f}s)"
        )
    except Exception as e:
        warnings.warn(f"No se pudo guardar caché {ruta_parquet.name}: {e}")

    return df
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
                logger.warning(f"    ⚠ Conexión fallida (intento {intento}/{_MAX_REINTENTOS}): {e}")
                logger.warning(f"      Reintentando en {espera:.0f}s...")
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
            logger.info(f"  ⚡ Cache: {nombre_tabla} ({size_mb:.1f} MB)")
        t0 = time.perf_counter()
        df = pd.read_parquet(ruta_cache)
        if verbose:
            dt = time.perf_counter() - t0
            logger.info(f"     → {len(df):,} filas en {dt:.2f}s")
        return df

    # --- Leer desde Access (pyodbc directo, sin SQLAlchemy) ---
    access_path = Path(access_path)
    if not access_path.exists():
        raise FileNotFoundError(f"Archivo Access no encontrado: {access_path}")

    if query is None:
        query = f"SELECT * FROM [{nombre_tabla}]"

    if verbose:
        logger.info(f"  📂 Access: {nombre_tabla} ← {access_path.name}")

    t0 = time.perf_counter()
    conn = _conectar_access(access_path, verbose=verbose)
    try:
        df = pd.read_sql(query, conn)
    finally:
        conn.close()
    dt_access = time.perf_counter() - t0

    if verbose:
        logger.info(f"     → {len(df):,} filas en {dt_access:.1f}s")

    # --- Guardar caché ---
    try:
        t0 = time.perf_counter()
        df.to_parquet(ruta_cache, index=False, engine='pyarrow')
        dt_save = time.perf_counter() - t0
        size_mb = ruta_cache.stat().st_size / (1024 * 1024)
        if verbose:
            logger.info(f"  💾 Guardado: {nombre_archivo} ({size_mb:.1f} MB, {dt_save:.1f}s)")
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
                logger.info(f"  ⚡ Cache: {nombre_fuente} ({size_mb:.1f} MB)")
            t0 = time.perf_counter()
            df = pd.read_parquet(ruta_cache)
            if verbose:
                dt = time.perf_counter() - t0
                logger.info(f"     → {len(df):,} filas en {dt:.2f}s")
            resultado[nombre_destino] = df
        else:
            tablas_pendientes.append((nombre_fuente, nombre_destino, query))

    # --- Leer pendientes con una sola conexión pyodbc ---
    if tablas_pendientes:
        if not access_path.exists():
            raise FileNotFoundError(f"Archivo Access no encontrado: {access_path}")

        if verbose:
            logger.info(f"  🔌 Conectando a {access_path.name} "
                        f"({len(tablas_pendientes)} tabla(s) pendiente(s))...")

        t_conn = time.perf_counter()
        conn = _conectar_access(access_path, verbose=verbose)
        if verbose:
            logger.info(f"     Conexión OK en {time.perf_counter() - t_conn:.1f}s")

        try:
            for nombre_fuente, nombre_destino, query in tablas_pendientes:
                sql = query if query else f"SELECT * FROM [{nombre_fuente}]"
                if verbose:
                    logger.info(f"  📂 Access: {nombre_fuente}")

                t0 = time.perf_counter()
                try:
                    df = pd.read_sql(sql, conn)
                except Exception as e:
                    logger.error(f"    ✗ Error leyendo {nombre_fuente}: {e}")
                    continue
                dt_access = time.perf_counter() - t0

                if verbose:
                    logger.info(f"     → {len(df):,} filas en {dt_access:.1f}s")

                resultado[nombre_destino] = df

                # Guardar caché
                ruta_cache = cache_dir / f"{nombre_fuente}_{fecha_str}.parquet"
                try:
                    t0 = time.perf_counter()
                    df.to_parquet(ruta_cache, index=False, engine='pyarrow')
                    dt_save = time.perf_counter() - t0
                    size_mb = ruta_cache.stat().st_size / (1024 * 1024)
                    if verbose:
                        logger.info(f"  💾 Guardado: {ruta_cache.name} "
                                    f"({size_mb:.1f} MB, {dt_save:.1f}s)")
                except Exception as e:
                    warnings.warn(
                        f"No se pudo guardar caché {ruta_cache.name}: {e}"
                    )
        finally:
            conn.close()
            if verbose:
                logger.info(f"  🔌 Conexión cerrada")

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
                    logger.info(f"  🗑 Eliminado: {cache_info['archivo'].name}")
            except Exception as e:
                logger.warning(f"  ⚠ Error eliminando {cache_info['archivo'].name}: {e}")

    if verbose and eliminados > 0:
        logger.info(f"  Total eliminados: {eliminados} archivos")

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
            logger.info(f"  🗑 Invalidado: {ruta.name}")
        return True
    return False
