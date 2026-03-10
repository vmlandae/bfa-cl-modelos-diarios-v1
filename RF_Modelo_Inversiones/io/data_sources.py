"""
Abstracción de fuentes de datos para RF_Modelo_Inversiones.

Este módulo proporciona una capa de abstracción para cargar datos desde
múltiples fuentes (pickle, Access/Excel, BigQuery) con una interfaz unificada.

Soporta tres modos de operación:
- PICKLE: Carga desde archivos pickle cacheados (desarrollo)
- LIVE: Carga directa desde Access/Excel (producción actual)
- BIGQUERY: Carga desde BigQuery/GCS (producción futura)

Uso básico:
    from RF_Modelo_Inversiones.io.data_sources import cargar_tablas_ml_inversiones
    
    # Modo automático (usa variable de entorno o default PICKLE)
    tablas = cargar_tablas_ml_inversiones(fecha_proceso=20260131)
    
    # Modo explícito
    tablas = cargar_tablas_ml_inversiones(
        fecha_proceso=20260131, 
        modo=DataSourceMode.LIVE
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import os
import pandas as pd
import numpy as np
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Callable, Optional, Any, List, Union
from functools import wraps

# Importaciones condicionales para evitar errores si no están instaladas
try:
    import bfa_cl_utilidades as ut
    HAS_BFA_UTILS = True
except ImportError:
    HAS_BFA_UTILS = False

try:
    from google.cloud import bigquery
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False


# =============================================================================
# ENUMS Y CONFIGURACIÓN
# =============================================================================

class DataSourceMode(Enum):
    """Modos de carga de datos disponibles."""
    PICKLE = "pickle"      # Desde archivos pickle cacheados
    LIVE = "live"          # Desde Access/Excel directamente
    BIGQUERY = "bigquery"  # Desde BigQuery (futuro)


# Registro global de transformadores
_TRANSFORMADORES: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {}


# =============================================================================
# DECORADOR PARA REGISTRAR TRANSFORMACIONES
# =============================================================================

def registrar_transformacion(nombre_tabla: str):
    """
    Decorador para registrar funciones de transformación/limpieza por tabla.
    
    Args:
        nombre_tabla: Nombre de la tabla a la que aplica la transformación
        
    Example:
        @registrar_transformacion('FPL')
        def limpiar_fpl(df: pd.DataFrame) -> pd.DataFrame:
            return df[['Instrumento', 'Haircut']].dropna()
    """
    def decorator(func: Callable[[pd.DataFrame], pd.DataFrame]):
        _TRANSFORMADORES[nombre_tabla] = func
        @wraps(func)
        def wrapper(df: pd.DataFrame) -> pd.DataFrame:
            return func(df)
        return wrapper
    return decorator


def aplicar_transformacion(nombre_tabla: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la transformación registrada para una tabla, si existe.
    
    Args:
        nombre_tabla: Nombre de la tabla
        df: DataFrame a transformar
        
    Returns:
        DataFrame transformado (o el original si no hay transformación)
    """
    if nombre_tabla in _TRANSFORMADORES:
        return _TRANSFORMADORES[nombre_tabla](df)
    return df


# =============================================================================
# TRANSFORMACIONES ESPECÍFICAS
# =============================================================================

@registrar_transformacion('FPL')
def limpiar_fpl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia la tabla FPL eliminando columnas basura y filas NaN.
    
    La tabla FPL del Access viene con columnas extra vacías que generan
    problemas en el procesamiento.
    """
    columnas_requeridas = ['Instrumento', 'Haircut']
    columnas_disponibles = [c for c in columnas_requeridas if c in df.columns]
    
    if not columnas_disponibles:
        # Intentar con nombres en mayúscula
        columnas_disponibles = [c for c in ['INSTRUMENTO', 'HAIRCUT'] if c in df.columns]
    
    if columnas_disponibles:
        return df[columnas_disponibles].dropna()
    
    return df.dropna()


@registrar_transformacion('RF_MontosLiq')
def limpiar_montos_liq(df: pd.DataFrame) -> pd.DataFrame:
    """
    Re-estructura la tabla RF_MontosLiq.
    
    La tabla viene con headers en la fila 0 y columna 0 vacía,
    requiere re-estructuración para ser usable.
    """
    # Si ya está limpia (tiene las columnas correctas), retornar
    columnas_esperadas = ['Monto Mercado', '% participacion', 'Monto a Liquidar']
    if all(col in df.columns for col in columnas_esperadas):
        return df
    
    # Re-estructurar: headers en fila 0, col 0 vacía
    df_clean = df.iloc[1:, 1:].copy()  # Desde fila 1, desde col 1
    
    # Usar la primera fila como headers
    try:
        df_clean.columns = df.iloc[0, 1:].values
    except (IndexError, ValueError):
        # Si falla, retornar original
        return df
    
    df_clean = df_clean.reset_index(drop=True)
    
    # Convertir columnas numéricas
    for col in columnas_esperadas:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    return df_clean


# =============================================================================
# GENERACIÓN DE QUERIES CON WHERE (F22)
# =============================================================================

# Ventanas de fecha por tabla: cuántos días hacia atrás necesita cada tabla.
# Se usa un margen mayor al estrictamente necesario para evitar perder datos
# por diferencias de timezone o redondeo.
_VENTANAS_FECHA: Dict[str, dict] = {
    # RF_base_Completa_Hist: el modelo solo usa Fec_Pro == fecha_proceso
    # en todas las carteras y pasos. Filtro exacto.
    'RF_base_Completa_Hist': {
        'columna': 'Fec_Pro',
        'dias': 0,
        'operador': '=',
    },
    # RF_Base_Diaria_Precios: solo se necesita Fecha == fecha_proceso (paso 20).
    # Margen: 5 días.
    'RF_Base_Diaria_Precios': {
        'columna': 'Fecha',
        'dias': 5,
        'operador': '>=',
    },
    # RF_BD_Gestion_RM: cada modelo lo filtra por Fec_Pro == fecha exacta.
    # Margen: 1 día (solo fecha actual).
    'RF_BD_Gestion_RM': {
        'columna': 'Fec_Pro',
        'dias': 0,
        'operador': '=',
    },
}


def _generar_queries_where(
    tablas_spec: List[dict],
    fecha_proceso: int,
) -> List[dict]:
    """
    Enriquece las especificaciones de tablas con queries WHERE.

    Para las tablas que tienen una ventana de fecha definida en _VENTANAS_FECHA,
    genera un query ``SELECT * FROM [tabla] WHERE col >= #fecha#`` que filtra
    en origen en lugar de traer todos los registros.

    Las tablas sin ventana definida mantienen el comportamiento original
    (``SELECT * FROM [tabla]``).

    Args:
        tablas_spec: Lista de dicts con al menos 'nombre_fuente'.
        fecha_proceso: Fecha YYYYMMDD como int.

    Returns:
        Lista enriquecida (copias, no muta las originales).
    """
    from datetime import datetime as dt

    fecha = dt.strptime(str(fecha_proceso), '%Y%m%d')
    resultado = []

    for spec in tablas_spec:
        spec_copia = dict(spec)
        nombre = spec_copia['nombre_fuente']

        # Solo inyectar WHERE si no viene un query explícito
        if 'query' not in spec_copia and nombre in _VENTANAS_FECHA:
            ventana = _VENTANAS_FECHA[nombre]
            fecha_corte = fecha - timedelta(days=ventana['dias'])
            # Formato Access date literal: #YYYY-MM-DD#
            fecha_access = fecha_corte.strftime('%Y-%m-%d')

            if ventana['operador'] == '=':
                # Para operador igual, filtrar por fecha exacta
                fecha_access = fecha.strftime('%Y-%m-%d')

            spec_copia['query'] = (
                f"SELECT * FROM [{nombre}] "
                f"WHERE [{ventana['columna']}] {ventana['operador']} #{fecha_access}#"
            )

        resultado.append(spec_copia)

    return resultado


# =============================================================================
# FUNCIONES DE CARGA POR MODO
# =============================================================================

def _cargar_desde_pickle(
    data_path: Path,
    fecha_proceso: int,
    nombre_cache: str = 'tablas_linkeadas_ml_inversiones',
) -> Dict[str, pd.DataFrame]:
    """
    Carga tablas desde archivo pickle cacheado.
    
    Args:
        data_path: Ruta al directorio de datos
        fecha_proceso: Fecha de proceso (YYYYMMDD)
        nombre_cache: Nombre base del archivo de cache
        
    Returns:
        Diccionario con DataFrames por nombre de tabla
    """
    from .cache import cache_pickle
    
    # Buscar pickle existente
    patron = f"{nombre_cache}_{fecha_proceso}_*.pkl"
    archivos = list(data_path.glob(patron))
    
    if not archivos:
        raise FileNotFoundError(
            f"No se encontró cache pickle para {nombre_cache} "
            f"con fecha {fecha_proceso} en {data_path}"
        )
    
    # Cargar el más reciente
    archivo = sorted(archivos, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    
    import pickle
    with open(archivo, 'rb') as f:
        tablas = pickle.load(f)
    
    print(f"  ✓ Cargado desde pickle: {archivo.name}")
    return tablas


def _cargar_desde_live(
    rutas_config: Dict[str, Any],
    fecha_proceso: int,
    tablas_requeridas: Optional[list] = None,
    forzar_recarga: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Carga tablas directamente desde Access/Excel.
    
    Soporta dos formatos de configuración:
    
    1. **Multi-source** (ml_inversiones): múltiples archivos Access y Excel
       con renombrado de tablas.
       - 'ms_access_sources': lista de {path, tablas: [{nombre_fuente, nombre_destino?}]}
       - 'excel_files': lista de {path, sheets: [{nombre, sheet}]}
    
    2. **Single-source** (legacy): un solo archivo Access + Excel.
       - 'ms_access_path': ruta al archivo Access
       - 'tablas_access': lista de nombres de tablas
       - 'excel_files': lista de {path, sheets: [{nombre, sheet}]}
    
    Args:
        rutas_config: Diccionario con rutas a los archivos fuente
        fecha_proceso: Fecha de proceso (YYYYMMDD)
        tablas_requeridas: Lista de tablas a cargar (None = todas)
        
    Returns:
        Diccionario con DataFrames por nombre de tabla
    """
    if not HAS_BFA_UTILS:
        raise ImportError(
            "bfa_cl_utilidades no está instalado. "
            "Requerido para modo LIVE."
        )
    
    # Importar cache compartido
    from procesamiento_datos_input.cache_tablas import leer_multiples_tablas_con_cache
    
    tablas = {}
    
    # --- Formato multi-source (ml_inversiones) ---
    if 'ms_access_sources' in rutas_config:
        # F22: usar copias locales si el orquestador las preparó
        from procesamiento_datos_input.cache_tablas import obtener_mapa_access_local
        _mapa_local = obtener_mapa_access_local()

        for source in rutas_config['ms_access_sources']:
            access_path_red = Path(source['path'])
            # Usar copia local si existe, o la ruta original
            access_path = Path(_mapa_local.get(str(access_path_red), access_path_red))
            # Filtrar tablas si se solicitaron específicas
            tablas_spec = []
            for tabla_config in source.get('tablas', []):
                nombre_destino = tabla_config.get('nombre_destino', tabla_config['nombre_fuente'])
                if tablas_requeridas and nombre_destino not in tablas_requeridas:
                    continue
                tablas_spec.append(tabla_config)

            if not tablas_spec:
                continue

            # F22: inyectar WHERE clauses según ventanas de fecha
            tablas_spec = _generar_queries_where(tablas_spec, fecha_proceso)

            try:
                resultado = leer_multiples_tablas_con_cache(
                    access_path=access_path,
                    tablas=tablas_spec,
                    fecha_proceso=fecha_proceso,
                    forzar_recarga=forzar_recarga,
                )
                tablas.update(resultado)
            except Exception as e:
                print(f"    ✗ Error cargando desde {access_path.name}: {e}")
    
    # --- Formato single-source (legacy) ---
    elif 'ms_access_path' in rutas_config:
        access_path = Path(rutas_config['ms_access_path'])
        if access_path.exists():
            tablas_access = rutas_config.get('tablas_access', [])
            for tabla in tablas_access:
                if tablas_requeridas and tabla not in tablas_requeridas:
                    continue
                query = f"SELECT * FROM [{tabla}]"
                try:
                    df = ut.lectura_datos_ms_access(str(access_path), query)
                    tablas[tabla] = df
                    print(f"    ✓ {tabla}: {len(df):,} registros")
                except Exception as e:
                    print(f"    ✗ Error cargando {tabla}: {e}")
    
    # --- Cargar desde Excel ---
    if 'excel_files' in rutas_config:
        for excel_config in rutas_config['excel_files']:
            excel_path = Path(excel_config['path'])
            if not excel_path.exists():
                print(f"    ✗ No existe: {excel_path}")
                continue
            
            for sheet_config in excel_config.get('sheets', []):
                nombre = sheet_config['nombre']
                if tablas_requeridas and nombre not in tablas_requeridas:
                    continue
                try:
                    df = pd.read_excel(
                        excel_path,
                        sheet_name=sheet_config.get('sheet', nombre),
                        **sheet_config.get('kwargs', {})
                    )
                    tablas[nombre] = df
                    print(f"    ✓ {nombre}: {len(df):,} registros")
                except Exception as e:
                    print(f"    ✗ Error cargando {nombre}: {e}")
    
    return tablas


def _cargar_desde_bigquery(
    project_id: str,
    dataset: str,
    fecha_proceso: int,
    tablas_requeridas: Optional[list] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Carga tablas desde BigQuery.
    
    Args:
        project_id: ID del proyecto GCP
        dataset: Nombre del dataset
        fecha_proceso: Fecha de proceso (YYYYMMDD)
        tablas_requeridas: Lista de tablas a cargar (None = todas)
        
    Returns:
        Diccionario con DataFrames por nombre de tabla
    """
    if not HAS_BIGQUERY:
        raise ImportError(
            "google-cloud-bigquery no está instalado. "
            "Requerido para modo BIGQUERY."
        )
    
    client = bigquery.Client(project=project_id)
    tablas = {}
    
    # Mapeo de tablas a queries
    queries = {
        'RF_Cartera_Inv': f"""
            SELECT * FROM `{project_id}.{dataset}.RF_Cartera_Inv`
            WHERE fecha_proceso = {fecha_proceso}
        """,
        'RF_Cartera_Inv_Pacto': f"""
            SELECT * FROM `{project_id}.{dataset}.RF_Cartera_Inv_Pacto`
            WHERE fecha_proceso = {fecha_proceso}
        """,
        # TODO: Agregar más tablas según sea necesario
    }
    
    for nombre, query in queries.items():
        if tablas_requeridas and nombre not in tablas_requeridas:
            continue
        try:
            df = client.query(query).to_dataframe()
            tablas[nombre] = df
            print(f"    ✓ {nombre}: {len(df):,} registros")
        except Exception as e:
            print(f"    ✗ Error cargando {nombre}: {e}")
    
    return tablas


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def cargar_tablas_ml_inversiones(
    fecha_proceso: int,
    modo: Optional[DataSourceMode] = None,
    data_path: Optional[Path] = None,
    rutas_config: Optional[Dict[str, Any]] = None,
    tablas_requeridas: Optional[list] = None,
    aplicar_transformaciones: bool = True,
    forzar_recarga: bool = False,
    verbose: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Carga todas las tablas necesarias para ML Inversiones.
    
    Punto de entrada unificado que abstrae la fuente de datos.
    El modo se determina por:
    1. Parámetro `modo` si se especifica
    2. Variable de entorno `ML_INVERSIONES_DATA_MODE`
    3. Default: PICKLE (desarrollo)
    
    Args:
        fecha_proceso: Fecha de proceso como int (YYYYMMDD)
        modo: Modo de carga (PICKLE, LIVE, BIGQUERY). None = automático
        data_path: Ruta a datos (requerido para PICKLE)
        rutas_config: Config de rutas (requerido para LIVE)
        tablas_requeridas: Lista de tablas específicas a cargar (None = todas)
        aplicar_transformaciones: Si True, aplica limpiezas registradas
        forzar_recarga: Si True, ignora caché parquet y lee directamente de Access
        verbose: Si True, imprime mensajes de progreso
        
    Returns:
        Dict[str, pd.DataFrame]: Diccionario {nombre_tabla: DataFrame}
        
    Example:
        >>> tablas = cargar_tablas_ml_inversiones(20260131)
        >>> tablas['RF_Cartera_Inv'].head()
    """
    # Determinar modo
    if modo is None:
        modo_env = os.environ.get('ML_INVERSIONES_DATA_MODE', 'pickle').lower()
        modo = DataSourceMode(modo_env)
    
    if verbose:
        print(f"📊 Cargando tablas ML Inversiones (modo: {modo.value})")
    
    # Cargar según modo
    if modo == DataSourceMode.PICKLE:
        if data_path is None:
            # Default: RF_Modelo_Inversiones/data/
            data_path = Path(__file__).parent.parent / 'data'
        tablas = _cargar_desde_pickle(data_path, fecha_proceso)
        
    elif modo == DataSourceMode.LIVE:
        if rutas_config is None:
            rutas_config = crear_config_rutas_live_desde_yaml()
        tablas = _cargar_desde_live(rutas_config, fecha_proceso, tablas_requeridas, forzar_recarga)
        
    elif modo == DataSourceMode.BIGQUERY:
        project_id = os.environ.get('GCP_PROJECT_ID', 'bfa-cl-trade-price-report-dev')
        dataset = os.environ.get('ML_INVERSIONES_DATASET', 'rf_modelos')
        tablas = _cargar_desde_bigquery(project_id, dataset, fecha_proceso, tablas_requeridas)
    
    else:
        raise ValueError(f"Modo no soportado: {modo}")
    
    # Aplicar transformaciones/limpiezas
    if aplicar_transformaciones:
        for nombre in list(tablas.keys()):
            tablas[nombre] = aplicar_transformacion(nombre, tablas[nombre])
    
    if verbose:
        print(f"  ✓ {len(tablas)} tablas cargadas")
    
    return tablas


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def obtener_modo_actual() -> DataSourceMode:
    """Retorna el modo de carga actualmente configurado."""
    modo_env = os.environ.get('ML_INVERSIONES_DATA_MODE', 'pickle').lower()
    return DataSourceMode(modo_env)


def configurar_modo(modo: Union[DataSourceMode, str]) -> None:
    """
    Configura el modo de carga de datos.
    
    Args:
        modo: Modo a configurar (enum o string)
    """
    if isinstance(modo, DataSourceMode):
        modo = modo.value
    os.environ['ML_INVERSIONES_DATA_MODE'] = modo


def listar_transformaciones() -> Dict[str, str]:
    """
    Lista todas las transformaciones registradas.
    
    Returns:
        Dict con nombre de tabla y docstring de la transformación
    """
    return {
        nombre: func.__doc__ or "Sin documentación"
        for nombre, func in _TRANSFORMADORES.items()
    }


# =============================================================================
# CONFIGURACIÓN DE RUTAS LIVE (TEMPLATE)
# =============================================================================

def crear_config_rutas_live_desde_yaml() -> Dict[str, Any]:
    """
    Carga la configuración de rutas para ml_inversiones desde el YAML central.
    
    Lee `config/config_rutas_ext_y_archivos.yaml` y transforma la sección
    `ml_inversiones` al formato que espera `_cargar_desde_live()`.
    
    Returns:
        Dict con la configuración para _cargar_desde_live()
    """
    import yaml
    
    yaml_path = Path(__file__).resolve().parent.parent.parent / 'config' / 'config_rutas_ext_y_archivos.yaml'
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    cfg_inv = config['modelos']['ml_inversiones']
    
    rutas = {
        'ms_access_sources': cfg_inv['ms_access_sources'],
        'excel_files': [],
    }
    
    # Convertir excel_parametros_input + excel_hojas al formato excel_files
    if 'excel_parametros_input' in cfg_inv and 'excel_hojas' in cfg_inv:
        rutas['excel_files'].append({
            'path': cfg_inv['excel_parametros_input'],
            'sheets': [
                {'nombre': h['nombre'], 'sheet': h['hoja']}
                for h in cfg_inv['excel_hojas']
            ]
        })
    
    # Agregar rutas de output
    if 'excel_output' in cfg_inv:
        rutas['excel_output'] = cfg_inv['excel_output']
    if 'csv_output_dir' in cfg_inv:
        rutas['csv_output_dir'] = cfg_inv['csv_output_dir']
    
    return rutas


# =============================================================================
# FILTRO RF_base_Completa_Hist (ex dev/helpers.py)
# =============================================================================

def genera_tabla_RF_base_Completa_Hist(
    df: pd.DataFrame,
    fecha_proceso: int,
    delta: int = 10,
) -> pd.DataFrame:
    """
    Paso 01: Filtra RF_base_Completa_Hist_Input para generar RF_base_Completa_Hist.

    Replica la query Access RF_PLI_000_Gener_CarteraInv:
    - Fec_Pro > fecha_proceso - delta días
    - Excluye registros donde Cod_Pro contiene 'publico' AND Clasificacion_Contable = 'htm'

    Args:
        df: DataFrame con RF_base_Completa_Hist_Input
        fecha_proceso: Fecha de proceso en formato YYYYMMDD (int)
        delta: Días hacia atrás para el filtro de Fec_Pro (default: 10)

    Returns:
        DataFrame filtrado
    """
    fecha_corte = pd.to_datetime(str(fecha_proceso), format="%Y%m%d") - pd.Timedelta(days=delta)
    mask_fecha = df['Fec_Pro'] > fecha_corte
    mask_producto = (
        (~df['Cod_Pro'].str.contains('publico', case=False, na=False))
        | (~df['Clasificacion_Contable'].str.contains('htm', na=False))
    )
    return df[mask_fecha & mask_producto].copy()
