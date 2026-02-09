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
from enum import Enum
from pathlib import Path
from typing import Dict, Callable, Optional, Any, Union
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
) -> Dict[str, pd.DataFrame]:
    """
    Carga tablas directamente desde Access/Excel.
    
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
    
    tablas = {}
    
    # Cargar desde Access
    if 'ms_access_path' in rutas_config:
        access_path = Path(rutas_config['ms_access_path'])
        if access_path.exists():
            tablas_access = rutas_config.get('tablas_access', [])
            for tabla in tablas_access:
                if tablas_requeridas and tabla not in tablas_requeridas:
                    continue
                query = f"SELECT * FROM [{tabla}]"
                try:
                    df = ut.lectura_datos_ms_access(str(access_path), query)
                    df = ut.estandariza_nombre_columnas_dataframe(df)
                    tablas[tabla] = df
                    print(f"    ✓ {tabla}: {len(df):,} registros")
                except Exception as e:
                    print(f"    ✗ Error cargando {tabla}: {e}")
    
    # Cargar desde Excel
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
            raise ValueError("rutas_config es requerido para modo LIVE")
        tablas = _cargar_desde_live(rutas_config, fecha_proceso, tablas_requeridas)
        
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

def crear_config_rutas_live(
    access_path: str,
    excel_tcrc_path: str,
    excel_fpl_path: str,
) -> Dict[str, Any]:
    """
    Crea configuración de rutas para modo LIVE.
    
    Template de conveniencia para crear la configuración.
    
    Args:
        access_path: Ruta al archivo Access principal
        excel_tcrc_path: Ruta al Excel con datos TCRC
        excel_fpl_path: Ruta al Excel con FPL y MontosLiq
        
    Returns:
        Dict con la configuración completa
    """
    return {
        'ms_access_path': access_path,
        'tablas_access': [
            'RF_Cartera_Inv',
            'RF_Cartera_Inv_Pacto',
            'RF_Flujos_Bonos_DLY',
            'RF_Flujos_Papeles_DLY',
            'RF_Flujos_Papeles_Ext_DLY',
            'RF_Flujos_Bonos_Ext_DLY',
            'RF_Flujos_DAP_DLY',
            'RF_Flujos_FI_DLY',
            # Tablas de validación
            'P01_Cartera_Bonos',
            'P02_Cartera_Papeles',
            'P03_Cartera_Otros',
            'P04_Cartera_Bonos_Ext',
            'P05_Cartera_Papeles_Ext',
            'P06_Cartera_DAP',
            'P07_Cartera_FI',
            'P08_Cartera_Pactos',
        ],
        'excel_files': [
            {
                'path': excel_tcrc_path,
                'sheets': [
                    {'nombre': 'TCRC', 'sheet': 'TCRC'},
                ]
            },
            {
                'path': excel_fpl_path,
                'sheets': [
                    {'nombre': 'FPL', 'sheet': 'FPL'},
                    {'nombre': 'RF_MontosLiq', 'sheet': 'RF_MontosLiq'},
                ]
            },
        ]
    }
