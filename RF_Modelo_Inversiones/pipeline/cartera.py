"""
Módulo de generación de cartera para RF_Modelo_Inversiones.

Este módulo contiene funciones unificadas para generar las carteras de inversiones,
reemplazando las funciones duplicadas:
- genera_cartera_inv_001() → genera_cartera_inv(tipo='disponible')
- genera_cartera_inv_pacto() → genera_cartera_inv(tipo='pacto')

Uso:
    from RF_Modelo_Inversiones.pipeline.cartera import genera_cartera_inv
    
    df_disponible = genera_cartera_inv(df_base, df_fecha, tipo='disponible')
    df_pacto = genera_cartera_inv(df_base, df_fecha, tipo='pacto')

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
from typing import Literal, Dict, List, Any


# =============================================================================
# CONFIGURACIÓN DE FILTROS POR TIPO DE CARTERA
# =============================================================================

FILTROS_CARTERA: Dict[str, Dict[str, Any]] = {
    'disponible': {
        'descripcion': 'Cartera Inversiones Disponible (RF_PLI_001_CarteraInv)',
        'sufijos_cod_sub_pro': ['Disp', 'Disp_Liq', 'MUTUOS'],
        'longitudes_sufijo': [4, 8, 6],  # Para str[-N:]
        'excluir_lch': True,
        'excluir_htm': True,
        'columnas_extra': [],
    },
    'pacto': {
        'descripcion': 'Cartera Inversiones Pacto (RF_PLI_001d_CarteraInv_Pcto)',
        'sufijos_cod_sub_pro': ['Pcto', 'Pcto_Liq'],
        'longitudes_sufijo': [4, 8],
        'excluir_lch': False,
        'excluir_htm': False,
        'columnas_extra': ['Dias_Pacto'],
    },
}

# Productos que se transforman a 'Inversion Financiera Privado'
PRODUCTOS_FONDOS_MUTUOS: List[str] = [
    'INVERSIONES FINANCIERAS FONDOS MUTUOS',
    'INVERSIONES FINANCIERAS FONDOS MUTUOS DERIVADOS',
]

# Columnas base de salida (sin las columnas extra)
COLUMNAS_BASE_SALIDA: List[str] = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
    'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 'Dias_Vcto'
]


# =============================================================================
# FUNCIÓN PRINCIPAL UNIFICADA
# =============================================================================

def genera_cartera_inv(
    df_base: pd.DataFrame,
    df_fecha: pd.DataFrame,
    tipo: Literal['disponible', 'pacto'],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera cartera de inversiones filtrada según el tipo especificado.
    
    Esta función unifica la lógica de:
    - genera_cartera_inv_001() → tipo='disponible'
    - genera_cartera_inv_pacto() → tipo='pacto'
    
    Args:
        df_base: DataFrame RF_base_Completa_Hist
        df_fecha: DataFrame con columna 'Fecha' (fecha de proceso)
        tipo: 'disponible' para cartera disponible, 'pacto' para cartera en pacto
        verbose: Si True, muestra estadísticas de filtrado
    
    Returns:
        DataFrame con la cartera filtrada y transformada
        
    Raises:
        ValueError: Si el tipo no es 'disponible' o 'pacto'
    
    Example:
        >>> df_disp = genera_cartera_inv(df_base, df_fecha, 'disponible')
        >>> df_pacto = genera_cartera_inv(df_base, df_fecha, 'pacto')
    
    SQL de referencia (disponible):
        SELECT Fec_Pro, Cod_Emp, Moneda, 
               IIf(Cod_Pro='INVERSIONES FINANCIERAS FONDOS MUTUOS' Or ...,'Inversion Financiera Privado',Cod_Pro) AS Cod_Pro,
               Cod_Sub_Pro, Nemotecnico, Left(Nemotecnico,3) AS Instrumento, 
               VP_Cap_Amort, VP_Int_Total, Dias_Vcto
        FROM RF_Fecha_Proceso_Carteras 
        INNER JOIN RF_base_Completa_Hist ON Fecha = Fec_Pro
        WHERE Left(Nemotecnico,3)<>'LCH'                    -- Solo para 'disponible'
          And (Left(Cod_Pro,20)='Inversion Financiera' Or Left(Cod_Pro,23)='INVERSIONES FINANCIERAS')
          And (Right(Cod_Sub_Pro,4)='Disp' Or Right(Cod_Sub_Pro,8)='Disp_Liq' Or Right(Cod_Sub_Pro,6)='MUTUOS')
          And Clasificacion_Contable<>"HTM";               -- Solo para 'disponible'
    """
    # Validar tipo
    if tipo not in FILTROS_CARTERA:
        tipos_validos = list(FILTROS_CARTERA.keys())
        raise ValueError(f"tipo='{tipo}' inválido. Usar uno de: {tipos_validos}")
    
    config = FILTROS_CARTERA[tipo]
    
    # Construir lista de columnas de salida
    columnas_salida = COLUMNAS_BASE_SALIDA.copy()
    columnas_salida.extend(config['columnas_extra'])
    
    if verbose:
        print("\n" + "=" * 70)
        print(f"GENERANDO CARTERA: {config['descripcion']}")
        print("=" * 70)
        print(f"Registros entrada: {len(df_base):,}")
    
    # =========================================================================
    # PASO 1: JOIN por fecha de proceso
    # =========================================================================
    fecha_proceso = _obtener_fecha_proceso(df_fecha)
    df_base = _asegurar_datetime(df_base, 'Fec_Pro')
    
    mask_fecha = df_base['Fec_Pro'] == fecha_proceso
    
    if verbose:
        print(f"\n[JOIN] Filtro fecha proceso = {fecha_proceso.strftime('%Y-%m-%d')}")
        print(f"  Registros que cumplen: {mask_fecha.sum():,}")
    
    # =========================================================================
    # PASO 2: WHERE - Aplicar filtros
    # =========================================================================
    
    # FILTRO 2.1: Nemotecnico NO empieza con 'LCH' (solo para disponible)
    if config['excluir_lch']:
        mask_no_lch = ~df_base['Nemotecnico'].str[:3].eq('LCH')
        if verbose:
            print(f"\n[WHERE] Excluir LCH: Nemotecnico[:3] <> 'LCH'")
            print(f"  Registros que cumplen: {mask_no_lch.sum():,}")
    else:
        mask_no_lch = pd.Series(True, index=df_base.index)
    
    # FILTRO 2.2: Cod_Pro es inversión financiera
    mask_inversion = (
        df_base['Cod_Pro'].str[:20].eq('Inversion Financiera') |
        df_base['Cod_Pro'].str[:23].eq('INVERSIONES FINANCIERAS')
    )
    
    if verbose:
        print(f"\n[WHERE] Cod_Pro es inversión financiera")
        print(f"  Registros que cumplen: {mask_inversion.sum():,}")
    
    # FILTRO 2.3: Cod_Sub_Pro termina en sufijos configurados
    mask_subpro = _crear_mask_sufijos(
        df_base['Cod_Sub_Pro'],
        config['sufijos_cod_sub_pro'],
        config['longitudes_sufijo']
    )
    
    if verbose:
        sufijos_str = ', '.join(config['sufijos_cod_sub_pro'])
        print(f"\n[WHERE] Cod_Sub_Pro termina en: {sufijos_str}")
        print(f"  Registros que cumplen: {mask_subpro.sum():,}")
    
    # FILTRO 2.4: Clasificacion_Contable NO es 'HTM' (solo para disponible)
    if config['excluir_htm']:
        mask_no_htm = ~df_base['Clasificacion_Contable'].str.upper().eq('HTM')
        if verbose:
            print(f"\n[WHERE] Excluir HTM: Clasificacion_Contable <> 'HTM'")
            print(f"  Registros que cumplen: {mask_no_htm.sum():,}")
    else:
        mask_no_htm = pd.Series(True, index=df_base.index)
    
    # COMBINAR TODOS LOS FILTROS (AND)
    mask_final = mask_fecha & mask_no_lch & mask_inversion & mask_subpro & mask_no_htm
    
    if verbose:
        print(f"\n[WHERE FINAL] Todos los filtros combinados (AND)")
        print(f"  Registros que cumplen: {mask_final.sum():,}")
    
    # Aplicar filtros
    df_filtrado = df_base[mask_final].copy()
    
    # =========================================================================
    # PASO 3: SELECT - Transformaciones
    # =========================================================================
    
    # Transformación Cod_Pro: Fondos mutuos → 'Inversion Financiera Privado'
    df_filtrado['Cod_Pro'] = df_filtrado['Cod_Pro'].replace(
        PRODUCTOS_FONDOS_MUTUOS,
        'Inversion Financiera Privado'
    )
    
    # Crear columna Instrumento = primeros 3 caracteres del Nemotecnico
    df_filtrado['Instrumento'] = df_filtrado['Nemotecnico'].str[:3]
    
    # =========================================================================
    # PASO 4: Verificar y seleccionar columnas de salida
    # =========================================================================
    
    # Verificar columnas extra existen
    for col in config['columnas_extra']:
        if col not in df_filtrado.columns:
            if verbose:
                print(f"  ADVERTENCIA: Columna '{col}' no existe, creando con valor 0")
            df_filtrado[col] = 0
    
    df_salida = df_filtrado[columnas_salida].copy()
    
    if verbose:
        print(f"\n{'=' * 70}")
        print(f"RESULTADO: {len(df_salida):,} registros")
        print(f"{'=' * 70}")
        print(f"\n  Distribución Instrumento:")
        print(df_salida['Instrumento'].value_counts().to_string())
    
    return df_salida


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _obtener_fecha_proceso(df_fecha: pd.DataFrame) -> pd.Timestamp:
    """Extrae la fecha de proceso del DataFrame de fechas."""
    fecha = df_fecha.loc[0, 'Fecha']
    if not isinstance(fecha, pd.Timestamp):
        fecha = pd.to_datetime(fecha)
    return fecha


def _asegurar_datetime(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Asegura que una columna sea de tipo datetime."""
    if not pd.api.types.is_datetime64_any_dtype(df[columna]):
        df = df.copy()
        df[columna] = pd.to_datetime(df[columna])
    return df


def _crear_mask_sufijos(
    serie: pd.Series,
    sufijos: List[str],
    longitudes: List[int]
) -> pd.Series:
    """
    Crea una máscara OR para múltiples sufijos.
    
    Args:
        serie: Serie de strings a evaluar
        sufijos: Lista de sufijos a buscar
        longitudes: Lista de longitudes para cada sufijo (str[-N:])
    
    Returns:
        Serie booleana con True donde algún sufijo coincide
    """
    mask = pd.Series(False, index=serie.index)
    for sufijo, longitud in zip(sufijos, longitudes):
        mask = mask | serie.str[-longitud:].eq(sufijo)
    return mask


# =============================================================================
# FUNCIONES DE COMPATIBILIDAD (DEPRECADAS)
# =============================================================================

def genera_cartera_inv_001(
    df_base: pd.DataFrame,
    df_fecha: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    DEPRECADO: Usar genera_cartera_inv(tipo='disponible').
    
    Mantiene compatibilidad con código existente.
    """
    import warnings
    warnings.warn(
        "genera_cartera_inv_001() está deprecado. "
        "Usar genera_cartera_inv(tipo='disponible')",
        DeprecationWarning,
        stacklevel=2
    )
    return genera_cartera_inv(df_base, df_fecha, tipo='disponible', verbose=verbose)


def genera_cartera_inv_pacto(
    df_base: pd.DataFrame,
    df_fecha: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    DEPRECADO: Usar genera_cartera_inv(tipo='pacto').
    
    Mantiene compatibilidad con código existente.
    """
    import warnings
    warnings.warn(
        "genera_cartera_inv_pacto() está deprecado. "
        "Usar genera_cartera_inv(tipo='pacto')",
        DeprecationWarning,
        stacklevel=2
    )
    return genera_cartera_inv(df_base, df_fecha, tipo='pacto', verbose=verbose)
