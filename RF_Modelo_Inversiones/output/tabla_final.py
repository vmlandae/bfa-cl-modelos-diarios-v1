"""
Generador de tabla final de inversiones.

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧

Este módulo implementa los pasos 20-27 del modelo de inversiones de Access:
- Paso 20: Precios del día (TCRC)
- Paso 21: Tabla final de inversiones (UNION de flujos)
- Pasos 22-27: Integración con tabla de desarrollo

SQL de referencia (Access):
    RF_PLI_044e_Modelo_Inversiones_Tabla_Final
    RF_PLI_047 a RF_PLI_050

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Literal
from datetime import datetime
import warnings


# =============================================================================
# CONSTANTES
# =============================================================================

COLUMNAS_TABLA_FINAL: List[str] = [
    'Fec_Pro',
    'Cod_Emp',
    'Moneda',
    'Cod_A_P',
    'Cod_Pro',
    'Cod_Sub_Pro',
    'Fec_Pago',
    'Dias_Pago',
    'Cap_Amort',
    'Int_Total_Cont',
    'VP_Cap_Amort',
    'VP_Int_Total_Cont',
]
"""Columnas de la tabla final de inversiones (RF_PLI_Modelo_Inversiones_Final_CLP)."""

COLUMNAS_TABLA_DESARROLLO: List[str] = [
    'Fec_Pro',
    'Cod_Emp',
    'Moneda',
    'Cod_A_P',
    'Cod_Pro',
    'Cod_Sub_Pro',
    'Fec_Pago',
    'Dias_Pago',
    'Cap_Amort',
    'Int_Total_Cont',
    'VP_Cap_Amort',
    'VP_Int_Total_Cont',
    'Precio_Mid',
    'Flujo_CLP',
]
"""Columnas de la tabla de desarrollo interna."""

MAPEO_COLUMNAS_EXCEL: Dict[str, str] = {
    'Fec_Pro': 'FECHA PROCESO',
    'Cod_Emp': 'CODIGO_EMPRESA',
    'Moneda': 'MONEDA_ORIGEN',
    'Cod_A_P': 'COD ACT/PAS',
    'Cod_Pro': 'COD_PRO',
    'Cod_Sub_Pro': 'COD_SUB_PRO',
    'Fec_Pago': 'FECHA DE PAGO',
    'Dias_Pago': 'PLAZO_PAGO',
    'Cap_Amort': 'FLUJO_CAPITAL',
    'Int_Total_Cont': 'FLUJO_INTERES',
    'VP_Cap_Amort': 'VP_CAP',
    'VP_Int_Total_Cont': 'VP_INT_CONT',
    'Precio_Mid': 'PRECIO_MID',
    'Flujo_CLP': 'FLUJO_CLP',
}
"""Mapeo de columnas internas a nombres para Excel."""

CODIGO_EMPRESA: int = 1
"""Código de empresa (constante en el modelo)."""

CODIGO_ACTIVO_PASIVO: str = 'ACT'
"""Código activo/pasivo: ACT = Activo."""

CODIGO_PRODUCTO: str = 'ML_C46_Inversiones_Financieras'
"""Código de producto base."""


# =============================================================================
# FUNCIONES PARA PASO 20: PRECIOS DEL DÍA
# =============================================================================

def generar_precios_dia(
    df_precios: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    instrumento: str = 'TCRC',
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera tabla de precios del día filtrando por fecha e instrumento.
    
    Implementa paso 20: RF_PLI_045_Gener_Precios_Dia
    
    SQL de referencia:
        SELECT Fecha, NEMOTECNICO, Instrumento, Precio_Mid 
        INTO Precios_Dia
        FROM RF_Base_Diaria_Precios
        WHERE Instrumento = "TCRC" AND Fecha = @fecha_proceso
    
    Args:
        df_precios: Tabla RF_Base_Diaria_Precios con precios históricos.
        fecha_proceso: Fecha de proceso (int YYYYMMDD, str o datetime).
        instrumento: Instrumento a filtrar (default 'TCRC' para UF).
        verbose: Si True, muestra mensajes de progreso.
        
    Returns:
        DataFrame con columnas [Fecha, NEMOTECNICO, Instrumento, Precio_Mid].
        
    Example:
        >>> precios_dia = generar_precios_dia(
        ...     tablas['RF_Base_Diaria_Precios'],
        ...     fecha_proceso=20260115,
        ...     instrumento='TCRC'
        ... )
    """
    if verbose:
        print(f"\n[Paso 20] Generando precios del día...")
        print(f"  Instrumento: {instrumento}")
    
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    # Normalizar columna Fecha en df_precios si es necesario
    df = df_precios.copy()
    if df['Fecha'].dtype != 'datetime64[ns]':
        df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    # Filtrar
    mask = (df['Fecha'] == fecha) & (df['Instrumento'] == instrumento)
    resultado = df.loc[mask, ['Fecha', 'NEMOTECNICO', 'Instrumento', 'Precio_Mid']].copy()
    
    if verbose:
        if len(resultado) > 0:
            precio = resultado['Precio_Mid'].iloc[0]
            print(f"  ✓ Precio {instrumento}: {precio:,.4f}")
        else:
            print(f"  ⚠ No se encontró precio para {instrumento} en fecha {fecha}")
    
    return resultado


# =============================================================================
# FUNCIONES PARA PASO 21: TABLA FINAL DE INVERSIONES
# =============================================================================

def formatear_flujo_instrumento(
    df_flujo: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    moneda: str,
    cod_sub_pro: str,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Formatea un flujo de liquidación al esquema estándar de la tabla final.
    
    Implementa queries RF_PLI_008b a RF_PLI_043b (*_Final)
    
    SQL de referencia:
        SELECT 
            RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro,
            1 AS Cod_Emp,
            '{moneda}' AS Moneda,
            'ACT' AS Cod_A_P,
            'ML_C46_Inversiones_Financieras' AS Cod_Pro,
            '{cod_sub_pro}' AS Cod_Sub_Pro,
            Fecha + Dia AS Fec_Pago,
            Dia AS Dias_Pago,
            Monto_Liquidar AS Cap_Amort,
            0 AS Int_Total_Cont,
            Monto_Liquidar AS VP_Cap_Amort,
            0 AS VP_Int_Total_Cont
        FROM Flujo_{instrumento}
        WHERE Dia > 0 AND Monto_Liquidar > 0
    
    Args:
        df_flujo: DataFrame con flujo de liquidación (columnas Dia, Monto_Liquidar).
        fecha_proceso: Fecha de proceso.
        moneda: Código de moneda ('CLP' o 'CLF').
        cod_sub_pro: Código de sub-producto final.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame formateado con COLUMNAS_TABLA_FINAL.
    """
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    # Filtrar Dia > 0 y Monto_Liquidar > 0
    df = df_flujo.copy()
    mask = (df['Dia'] > 0) & (df['Monto_Liquidar'] > 0)
    df = df.loc[mask].copy()
    
    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin flujos para {cod_sub_pro}")
        # Retornar DataFrame vacío con columnas correctas
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Construir DataFrame formateado
    resultado = pd.DataFrame({
        'Fec_Pro': fecha,
        'Cod_Emp': CODIGO_EMPRESA,
        'Moneda': moneda,
        'Cod_A_P': CODIGO_ACTIVO_PASIVO,
        'Cod_Pro': CODIGO_PRODUCTO,
        'Cod_Sub_Pro': cod_sub_pro,
        'Fec_Pago': fecha + pd.to_timedelta(df['Dia'].values, unit='D'),
        'Dias_Pago': df['Dia'].values,
        'Cap_Amort': df['Monto_Liquidar'].values,
        'Int_Total_Cont': 0,
        'VP_Cap_Amort': df['Monto_Liquidar'].values,
        'VP_Int_Total_Cont': 0,
    })
    
    if verbose:
        total = resultado['Cap_Amort'].sum()
        print(f"    ✓ {cod_sub_pro}: {len(resultado)} flujos, total={total:,.0f}")
    
    return resultado


def generar_cartera_garantias(
    df_base: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera cartera de garantías (RF_PLI_001b/c_CarteraInv_Gtia).
    
    SQL de referencia:
        SELECT ... FROM RF_base_Completa_Hist
        WHERE Cod_Pro LIKE 'Inversion Financiera%'
          AND (Cod_Sub_Pro LIKE '%Gtia' OR Cod_Sub_Pro LIKE '%Gtia_Liq')
        GROUP BY Fec_Pro, Cod_Emp, Moneda, Dias_Liq
    
    Args:
        df_base: Tabla RF_base_Completa_Hist con cartera completa.
        fecha_proceso: Fecha de proceso.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con cartera de garantías formateada.
    """
    if verbose:
        print(f"\n  Generando cartera de garantías...")
    
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    df = df_base.copy()
    
    # Filtrar por fecha de proceso
    if 'Fec_Pro' in df.columns:
        df['Fec_Pro'] = pd.to_datetime(df['Fec_Pro'])
        df = df[df['Fec_Pro'] == fecha]
    
    # Filtro: Inversión Financiera con garantía
    mask_producto = df['Cod_Pro'].str.startswith('Inversion Financiera', na=False)
    mask_gtia = (
        df['Cod_Sub_Pro'].str.endswith('Gtia', na=False) |
        df['Cod_Sub_Pro'].str.endswith('Gtia_Liq', na=False)
    )
    df = df.loc[mask_producto & mask_gtia].copy()
    
    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin garantías en cartera")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Agregar columna Instrumento
    df['Instrumento'] = df['Nemotecnico'].str[:3]
    
    # Agrupar por Dias_Liq
    cols_grupo = ['Fec_Pro', 'Cod_Emp', 'Moneda', 'Dias_Liq']
    cols_suma = ['Cap_Amort', 'Int_Total_Cont', 'VP_Cap_Amort', 'VP_Int_Total']
    
    # Asegurar que las columnas existen
    for col in cols_suma:
        if col not in df.columns:
            df[col] = 0
    
    df_agrupado = df.groupby(cols_grupo, as_index=False)[cols_suma].sum()
    
    # Formatear al esquema final
    resultado = pd.DataFrame({
        'Fec_Pro': fecha,
        'Cod_Emp': CODIGO_EMPRESA,
        'Moneda': df_agrupado['Moneda'],
        'Cod_A_P': CODIGO_ACTIVO_PASIVO,
        'Cod_Pro': 'ML_C46_Inversiones_Financieras_Gtia',
        'Cod_Sub_Pro': 'ML_C46_Inversiones_Financieras_Gtia',
        'Fec_Pago': fecha + pd.to_timedelta(df_agrupado['Dias_Liq'].values, unit='D'),
        'Dias_Pago': df_agrupado['Dias_Liq'].values,
        'Cap_Amort': df_agrupado['Cap_Amort'].values,
        'Int_Total_Cont': df_agrupado['Int_Total_Cont'].values,
        'VP_Cap_Amort': df_agrupado['VP_Cap_Amort'].values,
        'VP_Int_Total_Cont': df_agrupado['VP_Int_Total'].values,
    })
    
    if verbose:
        total = resultado['Cap_Amort'].sum()
        print(f"    ✓ Garantías: {len(resultado)} registros, total={total:,.0f}")
    
    return resultado


def generar_cartera_pactos(
    df_pactos: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera cartera de pactos (RF_PLI_044c_Modelo_Inversiones_Pacto_FB).
    
    SQL de referencia:
        SELECT 
            Fecha AS Fec_Pro,
            1 AS Cod_Emp,
            Moneda,
            'ACT' AS Cod_A_P,
            'ML_C46_Inversiones_Financieras' AS Cod_Pro,
            'ML_C46_Inversiones_Financieras_Pcto' AS Cod_Sub_Pro,
            Fecha + Dias_Pacto AS Fec_Pago,
            Dias_Pacto AS Dias_Pago,
            Monto AS Cap_Amort,
            0 AS Int_Total_Cont,
            Monto AS VP_Cap_Amort,
            0 AS VP_Int_Total_Cont
        FROM RF_PLI_044b_Modelo_Inversiones_Pacto_FB
    
    Args:
        df_pactos: DataFrame con pactos (columnas Moneda, Dias_Pacto, Monto).
        fecha_proceso: Fecha de proceso.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con cartera de pactos formateada.
    """
    if verbose:
        print(f"\n  Generando cartera de pactos...")
    
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    df = df_pactos.copy()
    
    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin pactos en cartera")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Construir DataFrame formateado
    resultado = pd.DataFrame({
        'Fec_Pro': fecha,
        'Cod_Emp': CODIGO_EMPRESA,
        'Moneda': df['Moneda'].values,
        'Cod_A_P': CODIGO_ACTIVO_PASIVO,
        'Cod_Pro': CODIGO_PRODUCTO,
        'Cod_Sub_Pro': 'ML_C46_Inversiones_Financieras_Pcto',
        'Fec_Pago': fecha + pd.to_timedelta(df['Dias_Pacto'].values, unit='D'),
        'Dias_Pago': df['Dias_Pacto'].values,
        'Cap_Amort': df['Monto'].values,
        'Int_Total_Cont': 0,
        'VP_Cap_Amort': df['Monto'].values,
        'VP_Int_Total_Cont': 0,
    })
    
    if verbose:
        total = resultado['Cap_Amort'].sum()
        print(f"    ✓ Pactos: {len(resultado)} registros, total={total:,.0f}")
    
    return resultado


def generar_tabla_final_inversiones(
    flujos: Dict[str, pd.DataFrame],
    fecha_proceso: Union[int, str, datetime],
    df_base: Optional[pd.DataFrame] = None,
    df_pactos: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera la tabla final de inversiones consolidando todos los flujos.
    
    Implementa paso 21: RF_PLI_044e_Modelo_Inversiones_Tabla_Final
    
    Esta función realiza el UNION ALL de:
    - 6 flujos de instrumentos (GobCLP, GobCLF, DPF, DPR, BBC, LCH)
    - Cartera de garantías (opcional)
    - Cartera de pactos (opcional)
    
    SQL de referencia:
        SELECT * FROM RF_PLI_008b_CarteraGobCLP_Final
        UNION ALL SELECT * FROM RF_PLI_015b_CarteraGobCLF_Final
        UNION ALL SELECT * FROM RF_PLI_022b_CarteraDPF_Final
        UNION ALL SELECT * FROM RF_PLI_029b_CarteraDPR_Final
        UNION ALL SELECT * FROM RF_PLI_036b_CarteraLCH_Final
        UNION ALL SELECT * FROM RF_PLI_043b_CarteraBBC_Final
        UNION ALL SELECT * FROM RF_PLI_001c_CarteraInv_Gtia
        UNION ALL SELECT * FROM RF_PLI_044c_Modelo_Inversiones_Pacto_FB
    
    Args:
        flujos: Diccionario con flujos por instrumento.
            Claves esperadas: 'GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH'
            Valores: DataFrames con columnas [Dia, Monto_Liquidar, ...]
        fecha_proceso: Fecha de proceso.
        df_base: Tabla RF_base_Completa_Hist para extraer garantías (opcional).
        df_pactos: DataFrame con pactos FB (opcional).
        verbose: Si True, muestra mensajes de progreso.
        
    Returns:
        DataFrame con tabla final consolidada (RF_PLI_Modelo_Inversiones_Final_CLP).
        
    Example:
        >>> flujos = {
        ...     'GobCLP': flujo_gob_clp,
        ...     'GobCLF': flujo_gob_clf,
        ...     'DPF': flujo_dpf,
        ...     'DPR': flujo_dpr,
        ...     'BBC': flujo_bbc,
        ...     'LCH': flujo_lch,
        ... }
        >>> tabla_final = generar_tabla_final_inversiones(
        ...     flujos=flujos,
        ...     fecha_proceso=20260115,
        ...     df_base=tablas['RF_base_Completa_Hist'],
        ...     df_pactos=df_pactos_fb
        ... )
    """
    if verbose:
        print("="*60)
        print("[Paso 21] Generando tabla final de inversiones")
        print("="*60)
    
    # Configuración de instrumentos (moneda y cod_sub_pro)
    CONFIG_INSTRUMENTOS = {
        'GobCLP': ('CLP', 'ML_C46_Inversiones_Financieras_GOBCLP'),
        'GobCLF': ('CLF', 'ML_C46_Inversiones_Financieras_GOBCLF'),
        'DPF': ('CLP', 'ML_C46_Inversiones_Financieras_DPFCLP'),
        'DPR': ('CLF', 'ML_C46_Inversiones_Financieras_DPRCLF'),
        'BBC': ('CLP', 'ML_C46_Inversiones_Financieras_CORPCLP'),
        'LCH': ('CLF', 'ML_C46_Inversiones_Financieras_LCHR'),
    }
    
    dfs_a_concatenar = []
    
    # Procesar cada instrumento
    if verbose:
        print("\n  Procesando flujos de instrumentos:")
    
    for instrumento, (moneda, cod_sub_pro) in CONFIG_INSTRUMENTOS.items():
        if instrumento in flujos and flujos[instrumento] is not None:
            df_formateado = formatear_flujo_instrumento(
                df_flujo=flujos[instrumento],
                fecha_proceso=fecha_proceso,
                moneda=moneda,
                cod_sub_pro=cod_sub_pro,
                verbose=verbose
            )
            if len(df_formateado) > 0:
                dfs_a_concatenar.append(df_formateado)
        elif verbose:
            print(f"    - {instrumento}: no proporcionado")
    
    # Agregar garantías si se proporciona df_base
    if df_base is not None:
        df_garantias = generar_cartera_garantias(df_base, fecha_proceso, verbose)
        if len(df_garantias) > 0:
            dfs_a_concatenar.append(df_garantias)
    
    # Agregar pactos si se proporcionan
    if df_pactos is not None:
        df_pactos_fmt = generar_cartera_pactos(df_pactos, fecha_proceso, verbose)
        if len(df_pactos_fmt) > 0:
            dfs_a_concatenar.append(df_pactos_fmt)
    
    # Concatenar todo
    if len(dfs_a_concatenar) == 0:
        if verbose:
            print("\n  ⚠ Sin datos para concatenar")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    resultado = pd.concat(dfs_a_concatenar, ignore_index=True)
    
    if verbose:
        print("\n" + "="*60)
        print(f"  RESUMEN TABLA FINAL:")
        print(f"  - Total registros: {len(resultado):,}")
        print(f"  - Total Cap_Amort: {resultado['Cap_Amort'].sum():,.0f}")
        print(f"  - Columnas: {list(resultado.columns)}")
        print("="*60)
    
    return resultado


# =============================================================================
# FUNCIONES PARA PASOS 22-27: INTEGRACIÓN TABLA DESARROLLO
# =============================================================================

def agregar_precio_y_flujo_clp(
    df_inversiones: pd.DataFrame,
    df_precios_dia: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Agrega precio UF y calcula flujo en CLP.
    
    Implementa parte del paso 23: JOIN con Precios_Dia y cálculo de Flujo_CLP.
    
    SQL de referencia:
        SELECT ..., 
            Precios_Dia.Precio_Mid,
            IIF(Moneda = 'CLF', Cap_Amort * Precio_Mid, Cap_Amort) AS Flujo_CLP
        FROM RF_PLI_Modelo_Inversiones_Final_CLP
        LEFT JOIN Precios_Dia ON Fec_Pro = Fecha
    
    Args:
        df_inversiones: Tabla de inversiones (RF_PLI_Modelo_Inversiones_Final_CLP).
        df_precios_dia: Precios del día (Precios_Dia filtrado por TCRC).
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con columnas Precio_Mid y Flujo_CLP agregadas.
    """
    # Obtener precio UF del día
    if len(df_precios_dia) > 0:
        precio_uf = df_precios_dia['Precio_Mid'].iloc[0]
    else:
        warnings.warn("No se encontró precio UF, usando 0")
        precio_uf = 0
    
    df = df_inversiones.copy()
    df['Precio_Mid'] = precio_uf
    
    # Calcular Flujo_CLP según moneda
    df['Flujo_CLP'] = np.where(
        df['Moneda'] == 'CLF',
        df['Cap_Amort'] * precio_uf,
        df['Cap_Amort']
    )
    
    if verbose:
        print(f"  ✓ Precio UF aplicado: {precio_uf:,.4f}")
        print(f"  ✓ Flujo_CLP total: {df['Flujo_CLP'].sum():,.0f}")
    
    return df


def extraer_cartera_especial(
    df_cartera: pd.DataFrame,
    tipo: Literal['FFMM', 'HTM', 'RT'],
    fecha_proceso: Union[int, str, datetime],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Extrae cartera especial (FFMM, HTM o RT) de la cartera de inversiones.
    
    Estos tipos NO pasan por el modelo de liquidación porque:
    - FFMM: Liquidez inmediata (T+0/T+1)
    - HTM: Held-to-Maturity, compromiso de no venta
    - RT: Renta en tránsito, ya comprometida
    
    Args:
        df_cartera: Cartera de inversiones completa.
        tipo: Tipo de cartera a extraer ('FFMM', 'HTM', 'RT').
        fecha_proceso: Fecha de proceso.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con cartera especial formateada.
    """
    if verbose:
        print(f"\n  Extrayendo cartera {tipo}...")
    
    FILTROS = {
        'FFMM': {'patron': 'MUTUOS', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_FFMM'},
        'HTM': {'patron': 'HTM', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_HTM'},
        'RT': {'patron': 'RT|Transito', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_RT'},
    }
    
    if tipo not in FILTROS:
        raise ValueError(f"Tipo '{tipo}' inválido. Válidos: {list(FILTROS.keys())}")
    
    filtro = FILTROS[tipo]
    
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    df = df_cartera.copy()
    
    # Filtrar por patrón en Cod_Sub_Pro
    mask = df['Cod_Sub_Pro'].str.contains(filtro['patron'], na=False, case=False, regex=True)
    df = df.loc[mask].copy()
    
    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin registros {tipo}")
        return pd.DataFrame(columns=COLUMNAS_TABLA_DESARROLLO)
    
    # Determinar columna de días
    col_dias = 'Dias_Liq' if 'Dias_Liq' in df.columns else 'Dias_Vcto'
    
    # Formatear
    resultado = pd.DataFrame({
        'Fec_Pro': fecha,
        'Cod_Emp': CODIGO_EMPRESA,
        'Moneda': df['Moneda'].values,
        'Cod_A_P': CODIGO_ACTIVO_PASIVO,
        'Cod_Pro': CODIGO_PRODUCTO,
        'Cod_Sub_Pro': filtro['cod_sub_pro'],
        'Fec_Pago': fecha + pd.to_timedelta(df[col_dias].values, unit='D'),
        'Dias_Pago': df[col_dias].values,
        'Cap_Amort': df['Cap_Amort'].values if 'Cap_Amort' in df.columns else df['VP_Cap_Amort'].values,
        'Int_Total_Cont': df['Int_Total_Cont'].values if 'Int_Total_Cont' in df.columns else 0,
        'VP_Cap_Amort': df['VP_Cap_Amort'].values,
        'VP_Int_Total_Cont': df['VP_Int_Total'].values if 'VP_Int_Total' in df.columns else 0,
    })
    
    if verbose:
        total = resultado['Cap_Amort'].sum()
        print(f"    ✓ {tipo}: {len(resultado)} registros, total={total:,.0f}")
    
    return resultado


def generar_tabla_desarrollo_completa(
    df_modelo_inversiones: pd.DataFrame,
    df_precios_dia: pd.DataFrame,
    df_cartera_ffmm: Optional[pd.DataFrame] = None,
    df_cartera_htm: Optional[pd.DataFrame] = None,
    df_cartera_rt: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera la tabla de desarrollo completa integrando todos los flujos.
    
    Implementa pasos 22-26 del modelo de Access.
    
    Args:
        df_modelo_inversiones: Flujos del modelo de liquidación (paso 21).
        df_precios_dia: Precios TCRC del día.
        df_cartera_ffmm: Cartera de fondos mutuos (opcional).
        df_cartera_htm: Cartera held-to-maturity (opcional).
        df_cartera_rt: Cartera renta en tránsito (opcional).
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con tabla de desarrollo completa.
    """
    if verbose:
        print("\n" + "="*60)
        print("[Pasos 22-26] Generando tabla de desarrollo completa")
        print("="*60)
    
    dfs_a_concatenar = []
    
    # Paso 23: Agregar modelo liquidación con precio y flujo CLP
    if verbose:
        print("\n  [23] Procesando modelo de liquidación...")
    df_ml = agregar_precio_y_flujo_clp(df_modelo_inversiones, df_precios_dia, verbose)
    dfs_a_concatenar.append(df_ml)
    if verbose:
        print(f"       ML: {len(df_ml):,} registros")
    
    # Paso 24: Agregar FFMM
    if df_cartera_ffmm is not None and len(df_cartera_ffmm) > 0:
        if verbose:
            print("\n  [24] Procesando FFMM...")
        df_ffmm = agregar_precio_y_flujo_clp(df_cartera_ffmm, df_precios_dia, verbose=False)
        dfs_a_concatenar.append(df_ffmm)
        if verbose:
            print(f"       FFMM: {len(df_ffmm):,} registros")
    
    # Paso 25: Agregar HTM
    if df_cartera_htm is not None and len(df_cartera_htm) > 0:
        if verbose:
            print("\n  [25] Procesando HTM...")
        df_htm = agregar_precio_y_flujo_clp(df_cartera_htm, df_precios_dia, verbose=False)
        dfs_a_concatenar.append(df_htm)
        if verbose:
            print(f"       HTM: {len(df_htm):,} registros")
    
    # Paso 26: Agregar RT
    if df_cartera_rt is not None and len(df_cartera_rt) > 0:
        if verbose:
            print("\n  [26] Procesando RT...")
        df_rt = agregar_precio_y_flujo_clp(df_cartera_rt, df_precios_dia, verbose=False)
        dfs_a_concatenar.append(df_rt)
        if verbose:
            print(f"       RT: {len(df_rt):,} registros")
    
    # Consolidar
    resultado = pd.concat(dfs_a_concatenar, ignore_index=True)
    
    if verbose:
        print("\n" + "="*60)
        print(f"  RESUMEN TABLA DESARROLLO:")
        print(f"  - Total registros: {len(resultado):,}")
        print(f"  - Total Flujo_CLP: {resultado['Flujo_CLP'].sum():,.0f}")
        print("="*60)
    
    return resultado


def formatear_para_excel(
    df_tabla_desarrollo: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Formatea la tabla de desarrollo para exportación a Excel.
    
    Implementa paso 27: RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel
    
    Args:
        df_tabla_desarrollo: DataFrame con flujos consolidados.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con columnas renombradas y adicionales para Excel.
    """
    if verbose:
        print("\n[Paso 27] Formateando para Excel...")
    
    df = df_tabla_desarrollo.copy()
    
    # Agregar columnas constantes
    df['OPERACION'] = 'INVERSIONES'
    df['MONEDA_COMPENSACION'] = df['Moneda']
    df['COMPENSACION'] = 'NO'
    
    # Renombrar columnas
    df = df.rename(columns=MAPEO_COLUMNAS_EXCEL)
    
    # Ordenar columnas según formato esperado
    columnas_orden = [
        'FECHA PROCESO', 'CODIGO_EMPRESA', 'OPERACION', 'COD ACT/PAS',
        'MONEDA_ORIGEN', 'MONEDA_COMPENSACION', 'COMPENSACION',
        'COD_PRO', 'COD_SUB_PRO', 'FECHA DE PAGO', 'PLAZO_PAGO',
        'FLUJO_CAPITAL', 'FLUJO_INTERES', 'VP_CAP', 'VP_INT_CONT',
        'PRECIO_MID', 'FLUJO_CLP'
    ]
    
    # Solo incluir columnas que existen
    columnas_existentes = [c for c in columnas_orden if c in df.columns]
    df = df[columnas_existentes]
    
    if verbose:
        print(f"  ✓ Formateado: {len(df):,} registros, {len(df.columns)} columnas")
    
    return df


# =============================================================================
# FUNCIÓN WRAPPER COMPLETA
# =============================================================================

def ejecutar_pasos_20_a_27(
    flujos: Dict[str, pd.DataFrame],
    tablas: Dict[str, pd.DataFrame],
    fecha_proceso: Union[int, str, datetime],
    df_pactos: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Ejecuta los pasos 20-27 completos del modelo de inversiones.
    
    Args:
        flujos: Diccionario con flujos por instrumento.
        tablas: Diccionario con tablas linkeadas (RF_Base_Diaria_Precios, etc.).
        fecha_proceso: Fecha de proceso.
        df_pactos: DataFrame con pactos (opcional).
        verbose: Si True, muestra mensajes.
        
    Returns:
        Diccionario con:
        - 'precios_dia': Precios del día
        - 'tabla_final_inversiones': Tabla final paso 21
        - 'tabla_desarrollo': Tabla desarrollo pasos 22-26
        - 'tabla_excel': Tabla formateada paso 27
    """
    resultados = {}
    
    # Paso 20: Precios del día
    if 'RF_Base_Diaria_Precios' in tablas:
        resultados['precios_dia'] = generar_precios_dia(
            tablas['RF_Base_Diaria_Precios'],
            fecha_proceso,
            verbose=verbose
        )
    else:
        if verbose:
            print("⚠ RF_Base_Diaria_Precios no disponible")
        resultados['precios_dia'] = pd.DataFrame()
    
    # Paso 21: Tabla final de inversiones
    df_base = tablas.get('RF_base_Completa_Hist')
    resultados['tabla_final_inversiones'] = generar_tabla_final_inversiones(
        flujos=flujos,
        fecha_proceso=fecha_proceso,
        df_base=df_base,
        df_pactos=df_pactos,
        verbose=verbose
    )
    
    # Pasos 22-26: Tabla de desarrollo
    # TODO: Extraer carteras especiales FFMM, HTM, RT si están disponibles
    resultados['tabla_desarrollo'] = generar_tabla_desarrollo_completa(
        df_modelo_inversiones=resultados['tabla_final_inversiones'],
        df_precios_dia=resultados['precios_dia'],
        verbose=verbose
    )
    
    # Paso 27: Formato Excel
    resultados['tabla_excel'] = formatear_para_excel(
        resultados['tabla_desarrollo'],
        verbose=verbose
    )
    
    return resultados
