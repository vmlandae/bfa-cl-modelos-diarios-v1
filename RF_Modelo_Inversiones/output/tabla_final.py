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

# Columnas esperadas al extraer cartera FFMM desde RF_base_Completa_Hist
# corresponde a la lista de campos seleccionados en la consulta SQL de la
# especificación. Se usan como referencia para seleccionar/ordenar columnas.
COLUMNAS_FFMM_EXTRACCION: List[str] = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P', 'Cod_Pro', 'Cod_Sub_Pro',
    'Num_Oper', 'Num_Cup', 'Emisor', 'Nemotecnico', 'Tasa_Emi', 'Compensacion',
    'Fec_Cre', 'Fec_Ini_Cup', 'Fec_Vcto_Cup', 'Fec_Rep', 'Fec_Vcto',
    'Dias_Liq', 'Dias_Vcto', 'Cap_Amort', 'Int_Total_Cont', 'Int_Devengado',
    'Tasa_Cont', 'VP_Cap_Amort', 'VP_Int_Total', 'Tipo_Cupon', 'Cod_Area_Neg',
    'Cod_Estrategia', 'Tipo_Book', 'Clasificacion_Contable', 'RUT_cli',
    'Nombre_Cli', 'Moneda_Liq', 'Dias_Pacto', 'Factor_Riesgo',
    'Codigo_Ejecutivo', 'Indexador', 'tasa', 'tasa_CF', 'spread'
]

MAPEO_COLUMNAS_EXCEL: Dict[str, str] = {
    'Fec_Pro': 'FECHA PROCESO',
    'Cod_Emp': 'CODIGO_EMPRESA',
    'Moneda': 'MONEDA_ORIGEN',
    'Cod_A_P': 'COD ACT/PAS',
    'Cod_Pro': 'CODIGO_PRODUCTO',
    'Cod_Sub_Pro': 'CODIGO_SUBPRODUCTO',
    'Fec_Pago': 'FECHA PAGO',
    'Cap_Amort': 'AMORTIZACION',
    'Int_Total_Cont': 'INTERES',
    'VP_Cap_Amort': 'VP_AMORTIZACION',
    'VP_Int_Total_Cont': 'VP_INTERES',
    'VP_Int_Total': 'VP_INTERES',
}
"""Mapeo de columnas internas a nombres para Excel (RF_PLI_049)."""

COLUMNAS_EXCEL_FINAL: List[str] = [
    'FECHA PROCESO',
    'CODIGO_EMPRESA',
    'OPERACION',
    'COD ACT/PAS',
    'MONEDA_ORIGEN',
    'MONEDA_COMPENSACION',
    'COMPENSACION',
    'CODIGO_PRODUCTO',
    'CODIGO_SUBPRODUCTO',
    'FECHA CREACION',
    'NUMERO_CUOTA',
    'FECHA_INICIO_CUOTA',
    'FECHA_VENCIMIENTO_CUOTA',
    'FECHA PAGO',
    'FECHA_REPRICING',
    'AMORTIZACION',
    'INTERES',
    'INTERES_DEVENGADO',
    'VP_AMORTIZACION',
    'VP_INTERES',
    'FACTOR DE RIESGO',
    'TIPO_CUOTA',
    'AREA NEGOCIO',
    'CODIGO_ EJECUTIVO',
    'CODIGO_ESTRATEGIA',
    'CLASIFICACION_CONTABLE',
    'TIPO TASA',
    'INDEXADOR',
    'TASA',
    'TASA CF',
    'SPREAD',
]
"""Columnas del Excel final (RF_Tabla_Desarrollo_Final / RF_PLI_050)."""

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
        if len(resultado) == 0:
            print(f"  ⚠ No se encontraron precios para {instrumento} en {fecha.date()}")
        else:
        # hagamos un print del precio de la UF y del USD del día
        # esto es: NEMOTECNICO 'CLF' y 'USD'
            print(f"  ✓ Precios encontrados: {len(resultado)} registros")
            for nemotecnico in ['CLF', 'USD']:
                precio = resultado.loc[resultado['NEMOTECNICO'] == nemotecnico, 'Precio_Mid']
                if not precio.empty:
                    print(f"    - {nemotecnico}: {precio.iloc[0]:,.4f}")
                else:
                    print(f"    - {nemotecnico}: No disponible")

 
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
    
    # Verificar si df_base está vacío o sin columnas necesarias
    if df.empty or 'Cod_Pro' not in df.columns:
        if verbose:
            print(f"    ⚠ Sin datos de cartera base")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
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
    
    # Verificar si df_pactos está vacío o sin columnas necesarias
    if df.empty or 'Moneda' not in df.columns:
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


# =============================================================================
# FUNCIONES PARA PACTOS FUERA DE PLAZO (>90 DÍAS)
# =============================================================================

# Mapeo de instrumentos a sufijos de código de sub-producto
_MAPEO_INSTRUMENTO_PACTO: Dict[str, tuple] = {
    'GobCLP': ('CLP', '_GOBCLP'),
    'GobCLF': ('CLF', '_GOBCLF'),
    'DPF': ('CLP', '_DPFCLP'),
    'DPR': ('CLF', '_DPRCLF'),
    'BBC': ('CLP', '_CORPCLP'),
    'LCH': ('CLF', '_LCHR'),
}
"""Mapeo instrumento -> (moneda, sufijo_cod_sub_pro) para pactos fuera de plazo."""

# Umbral de días para considerar pacto "fuera de plazo"
UMBRAL_DIAS_PACTO: int = 90
"""Pactos con Dias_Pacto > 90 no entran en modelo de liquidación, van directo a tabla final."""


def generar_monto_fuera_plazo_instrumento(
    df_cartera_pacto: pd.DataFrame,
    instrumento: Literal['GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH'],
    umbral_dias: int = UMBRAL_DIAS_PACTO,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Filtra pactos fuera de plazo (>umbral_dias) para un instrumento específico.
    
    Implementa la lógica de queries RF_PLI_XXXc_Monto_FueraPlazo donde:
    - XXX = 008 (GobCLP), 015 (GobCLF), 022 (DPF), 029 (DPR), 036 (LCH), 043 (BBC)
    
    SQL de referencia (ejemplo GobCLP):
        SELECT Moneda, Dias_Pacto, Sum(Monto) AS Monto
        FROM RF_PLI_008b_MontoPlazo_Pacto_GOBCLP
        GROUP BY Moneda, Dias_Pacto
        HAVING Dias_Pacto > 90
    
    La tabla de entrada RF_PLI_XXXb viene de filtrar RF_PLI_001d_CarteraInv_Pcto
    por el instrumento correspondiente.
    
    Args:
        df_cartera_pacto: DataFrame con cartera de pactos (RF_PLI_001d_CarteraInv_Pcto).
            Columnas requeridas: Nemotecnico, Dias_Pacto, Monto_CLP/Monto_CLF.
        instrumento: Código del instrumento ('GobCLP', 'GobCLF', etc.).
        umbral_dias: Umbral de días para filtrar (default 90).
        verbose: Si True, muestra mensajes de debug.
        
    Returns:
        DataFrame con columnas [Moneda, Dias_Pacto, Monto] filtrado por instrumento
        y agrupado por Moneda/Dias_Pacto para pactos > umbral_dias.
    """
    if instrumento not in _MAPEO_INSTRUMENTO_PACTO:
        raise ValueError(f"Instrumento '{instrumento}' no válido. "
                        f"Opciones: {list(_MAPEO_INSTRUMENTO_PACTO.keys())}")
    
    moneda, _ = _MAPEO_INSTRUMENTO_PACTO[instrumento]
    
    if df_cartera_pacto.empty:
        return pd.DataFrame(columns=['Moneda', 'Dias_Pacto', 'Monto'])
    
    # Determinar columna de monto según moneda
    col_monto = f'Monto_{moneda}'
    if col_monto not in df_cartera_pacto.columns:
        # Fallback a columna genérica si existe
        if 'Monto' in df_cartera_pacto.columns:
            col_monto = 'Monto'
        else:
            return pd.DataFrame(columns=['Moneda', 'Dias_Pacto', 'Monto'])
    
    # Filtrar por instrumento basándose en Nemotecnico
    # La lógica de filtro depende del instrumento:
    # - GobCLP/GobCLF: BTU*, BTP*, BCU*, PDBC*, PRC*
    # - DPF: BFAL*, BISA*, etc.
    # - DPR: Similares en CLF
    # - BBC/LCH: Otros nemotécnicos corporativos
    
    # Por ahora, asumimos que df_cartera_pacto ya viene filtrada o
    # tiene columna 'Instrumento' si necesitamos filtrar
    df = df_cartera_pacto.copy()
    
    if 'Instrumento' in df.columns:
        df = df[df['Instrumento'] == instrumento]
    
    if df.empty or 'Dias_Pacto' not in df.columns:
        return pd.DataFrame(columns=['Moneda', 'Dias_Pacto', 'Monto'])
    
    # Filtrar por umbral
    df_fuera = df[df['Dias_Pacto'] > umbral_dias].copy()
    
    if df_fuera.empty:
        return pd.DataFrame(columns=['Moneda', 'Dias_Pacto', 'Monto'])
    
    # Agregar columna Moneda si no existe
    df_fuera['Moneda'] = moneda
    
    # Agrupar por Moneda y Dias_Pacto
    resultado = df_fuera.groupby(['Moneda', 'Dias_Pacto'], as_index=False).agg({
        col_monto: 'sum'
    }).rename(columns={col_monto: 'Monto'})
    
    if verbose:
        print(f"    - {instrumento}: {len(resultado)} grupos, "
              f"Monto total={resultado['Monto'].sum():,.0f}")
    
    return resultado


def generar_pactos_fuera_plazo_todos(
    df_cartera_pacto: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    umbral_dias: int = UMBRAL_DIAS_PACTO,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera tabla consolidada de pactos fuera de plazo para todos los instrumentos.
    
    Implementa RF_PLI_044c_Modelo_Inversiones_Pacto_FB que hace UNION de:
    - RF_PLI_008c_Monto_FueraPlazo_GOBCLP
    - RF_PLI_015c_Monto_FueraPlazo_GOBCLF
    - RF_PLI_022c_Monto_FueraPlazo_DPF
    - RF_PLI_029c_Monto_FueraPlazo_DPR
    - RF_PLI_036c_Monto_FueraPlazo_LCH
    - RF_PLI_043c_Monto_FueraPlazo_BBC
    
    Y luego formatea al esquema de tabla final de inversiones.
    
    Lógica de negocio:
        Los pactos con Dias_Pacto > 90 días no entran en el modelo de liquidación
        (horizonte 90 días), por lo que se agregan directamente a la tabla final
        con VP = Monto (sin descuento, se asume vencen después del horizonte).
    
    Args:
        df_cartera_pacto: DataFrame con cartera de pactos (RF_PLI_001d_CarteraInv_Pcto).
            Debe contener columnas para determinar instrumento y montos.
        fecha_proceso: Fecha de proceso.
        umbral_dias: Umbral de días para considerar "fuera de plazo" (default 90).
        verbose: Si True, muestra mensajes de progreso.
        
    Returns:
        DataFrame con esquema de COLUMNAS_TABLA_FINAL, listo para concatenar.
    """
    if verbose:
        print(f"\n  Generando pactos fuera de plazo (>{umbral_dias} días)...")
    
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    
    if df_cartera_pacto.empty:
        if verbose:
            print(f"    ⚠ Sin pactos en cartera de entrada")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Procesar cada instrumento
    instrumentos = ['GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH']
    dfs_por_instrumento = []
    
    for instr in instrumentos:
        df_fuera = generar_monto_fuera_plazo_instrumento(
            df_cartera_pacto=df_cartera_pacto,
            instrumento=instr,
            umbral_dias=umbral_dias,
            verbose=verbose
        )
        if not df_fuera.empty:
            dfs_por_instrumento.append(df_fuera)
    
    if not dfs_por_instrumento:
        if verbose:
            print(f"    ⚠ Sin pactos fuera de plazo")
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # UNION de todos los instrumentos
    df_union = pd.concat(dfs_por_instrumento, ignore_index=True)
    
    # Formatear al esquema de tabla final
    resultado = pd.DataFrame({
        'Fec_Pro': fecha,
        'Cod_Emp': CODIGO_EMPRESA,
        'Moneda': df_union['Moneda'].values,
        'Cod_A_P': CODIGO_ACTIVO_PASIVO,
        'Cod_Pro': CODIGO_PRODUCTO,
        'Cod_Sub_Pro': 'ML_C46_Inversiones_Financieras_Pcto',
        'Fec_Pago': fecha + pd.to_timedelta(df_union['Dias_Pacto'].values, unit='D'),
        'Dias_Pago': df_union['Dias_Pacto'].values,
        'Cap_Amort': df_union['Monto'].values,
        'Int_Total_Cont': 0,
        'VP_Cap_Amort': df_union['Monto'].values,  # VP = Monto (sin descuento)
        'VP_Int_Total_Cont': 0,
    })
    
    if verbose:
        total = resultado['Cap_Amort'].sum()
        n_registros = len(resultado)
        print(f"    ✓ Pactos fuera plazo: {n_registros} registros, total={total:,.0f}")
    
    return resultado


def generar_tabla_final_inversiones(
    flujos: Dict[str, pd.DataFrame],
    fecha_proceso: Union[int, str, datetime],
    df_base: Optional[pd.DataFrame] = None,
    df_cartera_inv_pacto: Optional[pd.DataFrame] = None,
    umbral_dias_pacto: int = UMBRAL_DIAS_PACTO,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera la tabla final de inversiones consolidando todos los flujos.
    
    Implementa paso 21: RF_PLI_044e_Modelo_Inversiones_Tabla_Final
    
    Esta función realiza el UNION ALL de:
    - 6 flujos de instrumentos (GobCLP, GobCLF, DPF, DPR, BBC, LCH)
    - Cartera de garantías (desde RF_base_Completa_Hist)
    - Pactos fuera de plazo (>90 días, desde RF_PLI_001d_CarteraInv_Pcto)
    
    NOTA: Los pactos con Dias_Pacto > 90 no entran en el modelo de liquidación
    (horizonte de 90 días), por lo que se agregan directamente aquí con VP = Monto.
    
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
        df_cartera_inv_pacto: Tabla RF_PLI_001d_CarteraInv_Pcto para pactos (opcional).
            Se filtrarán pactos con Dias_Pacto > umbral_dias_pacto.
        umbral_dias_pacto: Umbral para pactos fuera de plazo (default 90).
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
        ...     df_cartera_inv_pacto=tablas['RF_PLI_001d_CarteraInv_Pcto']
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
        'LCH': ('CLF', 'ML_C46_Inversiones_Financieras_CORPCLF'),
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
    
    # Agregar pactos fuera de plazo (>90 días) desde cartera de pactos
    if df_cartera_inv_pacto is not None:
        df_pactos_fuera = generar_pactos_fuera_plazo_todos(
            df_cartera_pacto=df_cartera_inv_pacto,
            fecha_proceso=fecha_proceso,
            umbral_dias=umbral_dias_pacto,
            verbose=verbose
        )
        if len(df_pactos_fuera) > 0:
            dfs_a_concatenar.append(df_pactos_fuera)
    
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

    # Precio_Mid: UF para CLF, 1.0 para CLP (y otras monedas en CLP)
    df['Precio_Mid'] = np.where(
        df['Moneda'] == 'CLF',
        precio_uf,
        1.0
    )
    
    # Calcular Flujo_CLP = (VP_Cap_Amort + VP_Int_Total_Cont) * Precio_Mid
    # Misma fórmula que FFMM/HTM/RT en tabla_desarrollo
    df['Flujo_CLP'] = (df['VP_Cap_Amort'] + df['VP_Int_Total_Cont']) * df['Precio_Mid']
    
    if verbose:
        print(f"  ✓ Precio UF aplicado: {precio_uf:,.4f}")
        print(f"  ✓ Flujo_CLP total: {df['Flujo_CLP'].sum():,.0f}")
    
    return df

def extrae_cartera_ffmm(
    df_cartera: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    columnas_relevantes: Optional[List[str]] = COLUMNAS_FFMM_EXTRACCION,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Extrae cartera de fondos mutuos (FFMM) de la cartera de inversiones.
    
    Estos instrumentos NO pasan por el modelo de liquidación porque tienen liquidez inmediata (T+0/T+1).
    
    Args:
        df_cartera: Cartera de inversiones completa.
        fecha_proceso: Fecha de proceso.
        columnas_relevantes: Lista de columnas a seleccionar para la cartera FFMM.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con cartera FFMM formateada.

    SQL de referencia:
SELECT
    RF_base_Completa_Hist.Fec_Pro,
    RF_base_Completa_Hist.Cod_Emp,
    RF_base_Completa_Hist.Moneda,
    RF_base_Completa_Hist.Cod_A_P,
    "ML_C46_Inversiones_Financieras" AS Cod_Pro,
    "ML_C46_Inversiones_Financieras_FFMM" AS Cod_Sub_Pro,
    RF_base_Completa_Hist.Num_Oper,
    RF_base_Completa_Hist.Num_Cup,
    RF_base_Completa_Hist.Emisor,
    RF_base_Completa_Hist.Nemotecnico,
    RF_base_Completa_Hist.Tasa_Emi,
    RF_base_Completa_Hist.Compensacion,
    RF_base_Completa_Hist.Fec_Cre,
    RF_base_Completa_Hist.Fec_Ini_Cup,
    RF_base_Completa_Hist.Fec_Vcto_Cup,
    RF_base_Completa_Hist.Fec_Rep,
    RF_base_Completa_Hist.Fec_Vcto,
    RF_base_Completa_Hist.Dias_Liq,
    RF_base_Completa_Hist.Dias_Vcto,
    RF_base_Completa_Hist.Cap_Amort,
    RF_base_Completa_Hist.Int_Total_Cont,
    0 AS Int_Devengado,
    RF_base_Completa_Hist.Tasa_Cont,
    RF_base_Completa_Hist.VP_Cap_Amort,
    RF_base_Completa_Hist.VP_Int_Total,
    RF_base_Completa_Hist.Tipo_Cupon,
    RF_base_Completa_Hist.Cod_Area_Neg,
    RF_base_Completa_Hist.Cod_Estrategia,
    RF_base_Completa_Hist.Tipo_Book,
    RF_base_Completa_Hist.Clasificacion_Contable,
    RF_base_Completa_Hist.RUT_cli,
    RF_base_Completa_Hist.Nombre_Cli,
    RF_base_Completa_Hist.Moneda_Liq,
    RF_base_Completa_Hist.Dias_Pacto,
    "" AS Factor_Riesgo,
    "" AS Codigo_Ejecutivo,
    "" AS Indexador,
    "" AS tasa,
    "" AS tasa_CF,
    "" AS spread
FROM
    RF_Fecha_Proceso_Carteras
    INNER JOIN RF_base_Completa_Hist ON RF_Fecha_Proceso_Carteras.Fecha = RF_base_Completa_Hist.Fec_Pro
WHERE
    RF_base_Completa_Hist.Cod_Pro <> "Spot"
    AND RF_base_Completa_Hist.Cod_Pro LIKE "INVERSIONES FINANCIERAS FONDOS MUTUOS";


    Es decir, 
    se toma la tabla RF_base_Completa_Hist,
      se seleccionan las columnas relevantes,
      se filtra por fecha de proceso, 
      se filtra que Cod_Pro sea distinto de "Spot", # condición redundante que sacamos 
      y que cumpla 'Cod_Pro LIKE "INVERSIONES FINANCIERAS FONDOS MUTUOS"'
      # en Access, el LIKE es case-insensitive por defecto, 
      # y además, si no tiene wildcards, actúa como un igual a.
      # por tanto lo más parecido es un fullmatch
      y finalmente, se llenan las columnas Cod_Pro y Cod_Sub_Pro con los valores fijos indicados
      y se llenan las columnas adicionales con valores vacíos o ceros según corresponda.



    """
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:        
        fecha = fecha_proceso
    if verbose:
        print(f"\n  Extrayendo cartera FFMM para fecha {fecha.date()}...")

    # Filtrar por fecha de proceso
    df = df_cartera.copy()
    if 'Fec_Pro' in df.columns:
        df['Fec_Pro'] = pd.to_datetime(df['Fec_Pro'])
        df = df[df['Fec_Pro'] == fecha]
    # Filtrar por Cod_Pro
    mask = df['Cod_Pro'].astype(str).str.fullmatch('INVERSIONES FINANCIERAS FONDOS MUTUOS', na=False, case=False)
    df = df.loc[mask].copy()
    # Se llenan las columnas Cod_Pro y Cod_Sub_Pro con los valores fijos indicados
    df['Cod_Pro'] = 'ML_C46_Inversiones_Financieras'
    df['Cod_Sub_Pro'] = 'ML_C46_Inversiones_Financieras_FFMM'
    # Se llenan las columnas adicionales con valores vacíos o ceros según corresponda.
    #  0 AS Int_Devengado,    "" AS Factor_Riesgo, "" AS Codigo_Ejecutivo, "" AS Indexador,
    # "" AS tasa, "" AS tasa_CF, "" AS spread
    columnas_adicionales = {
        'Int_Devengado': 0,
        'Factor_Riesgo': "",
        'Codigo_Ejecutivo': "",
        'Indexador': "",
        'tasa': "",
        'tasa_CF': "",
        'spread': ""
    }
    for col, valor in columnas_adicionales.items():
        df[col] = valor
    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin registros FFMM")
        return pd.DataFrame(columns=columnas_relevantes)
    else:
        if verbose:
            print(f"    ✓ FFMM: {len(df)} registros encontrados")
        return df[columnas_relevantes].copy()
def extraer_cartera_ffmm_para_tabla_desarrollo(df_extrae_cartera_ffmm: pd.DataFrame,
                                               
                                               df_precios_dia: pd.DataFrame,
                                               columnas_relevantes: Optional[List[str]] = COLUMNAS_TABLA_DESARROLLO,
                                               verbose: bool = True) -> pd.DataFrame:
    """
    función para replicar esta query:
    INSERT INTO 
    RF_Tabla_Desarrollo_Interna ( Fec_Pro, Cod_Emp, Moneda, Cod_A_P, Cod_Pro, Cod_Sub_Pro, Fec_Pago, Dias_Pago, Cap_Amort, Int_Total_Cont, VP_Cap_Amort, VP_Int_Total_Cont, Precio_Mid, Flujo_CLP )
    SELECT
      RF_PLI_044f_CarteraInv_FFMM.Fec_Pro, RF_PLI_044f_CarteraInv_FFMM.Cod_Emp,
        RF_PLI_044f_CarteraInv_FFMM.Moneda, RF_PLI_044f_CarteraInv_FFMM.Cod_A_P,
        RF_PLI_044f_CarteraInv_FFMM.Cod_Pro, RF_PLI_044f_CarteraInv_FFMM.Cod_Sub_Pro,
          RF_PLI_044f_CarteraInv_FFMM.Fec_Vcto_Cup AS Fec_Pago, 
          RF_PLI_044f_CarteraInv_FFMM.Dias_Liq AS Dias_Pago,
            RF_PLI_044f_CarteraInv_FFMM.Cap_Amort, 
            RF_PLI_044f_CarteraInv_FFMM.Int_Total_Cont,
              RF_PLI_044f_CarteraInv_FFMM.VP_Cap_Amort,
                RF_PLI_044f_CarteraInv_FFMM.VP_Int_Total AS VP_Int_Total_Cont,
                  Precios_Dia.Precio_Mid,
                    ([RF_PLI_044f_CarteraInv_FFMM].[VP_Cap_Amort]+[RF_PLI_044f_CarteraInv_FFMM].[VP_Int_Total])*[Precios_Dia].[Precio_Mid] AS Flujo_CLP
    FROM 
    Precios_Dia 
    INNER JOIN 
    RF_PLI_044f_CarteraInv_FFMM 
    ON 
    Precios_Dia.NEMOTECNICO = RF_PLI_044f_CarteraInv_FFMM.Moneda;

    """
    # Fec_Vcto_Cup AS Fec_Pago,
    # Dias_Liq AS Dias_Pago,
    # VP_Int_Total AS VP_Int_Total_Cont,
    # ([RF_PLI_044f_CarteraInv_FFMM].[VP_Cap_Amort]+[RF_PLI_044f_CarteraInv_FFMM].[VP_Int_Total])*[Precios_Dia].[Precio_Mid] AS Flujo_CLP
    if verbose:
        print(f"\n  Formateando cartera FFMM para tabla de desarrollo...")
    df = df_extrae_cartera_ffmm.copy()
    # Cambio de nombres de columnas según SQL de referencia
    df = df.rename(columns={
        'Fec_Vcto_Cup': 'Fec_Pago',
        'Dias_Liq': 'Dias_Pago',
        'VP_Int_Total': 'VP_Int_Total_Cont'
    })
    # Agregar Precio_Mid desde df_precios_dia
    if len(df_precios_dia) > 0:
        # buscamos por la moneda, ya que  Precios_Dia.NEMOTECNICO = RF_PLI_044f_CarteraInv_FFMM.Moneda;
        df = df.merge(df_precios_dia[['NEMOTECNICO', 'Precio_Mid']], left_on='Moneda', right_on='NEMOTECNICO', how='left')
    # construimos Flujo_CLP = (VP_Cap_Amort + VP_Int_Total_Cont) * Precio_Mid
    df['Flujo_CLP'] = (df['VP_Cap_Amort'] + df['VP_Int_Total_Cont']) * df['Precio_Mid']
    if verbose:
        print(f"  ✓ Cartera FFMM formateada para tabla de desarrollo: {len(df)} registros")
    return df[columnas_relevantes].copy()


def extrae_cartera_htm(
    df_cartera_input: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    columnas_relevantes: Optional[List[str]] = COLUMNAS_FFMM_EXTRACCION,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Extrae cartera HTM (Held-to-Maturity) desde RF_base_Completa_Hist_Input.
    
    IMPORTANTE: A diferencia de FFMM y RT, HTM usa la tabla _Input (sin procesar),
    no RF_base_Completa_Hist.

    SQL de referencia (RF_PLI_044i_CarteraInv_HTM):

    SELECT RF_base_Completa_Hist_Input.Fec_Pro, RF_base_Completa_Hist_Input.Cod_Emp,
        RF_base_Completa_Hist_Input.Moneda, RF_base_Completa_Hist_Input.Cod_A_P,
        "ML_C46_Inversiones_Financieras" AS Cod_Pro,
        IIf(
            RF_base_Completa_Hist_Input.Cod_Sub_Pro LIKE "*LCHR*",
            "ML_C46_Inversiones_Financieras_LCHR",
            IIf(
                RF_base_Completa_Hist_Input.Cod_Sub_Pro LIKE "*BBC*",
                "ML_C46_Inversiones_Financieras_BBC",
                "ML_C46_Inversiones_Financieras_Gob"
            )
        ) AS Cod_Sub_Pro,
        RF_base_Completa_Hist_Input.Num_Oper, RF_base_Completa_Hist_Input.Num_Cup,
        RF_base_Completa_Hist_Input.Emisor, RF_base_Completa_Hist_Input.Nemotecnico,
        RF_base_Completa_Hist_Input.Tasa_Emi, RF_base_Completa_Hist_Input.Compensacion,
        RF_base_Completa_Hist_Input.Fec_Cre, RF_base_Completa_Hist_Input.Fec_Ini_Cup,
        RF_base_Completa_Hist_Input.Fec_Vcto_Cup, RF_base_Completa_Hist_Input.Fec_Rep,
        RF_base_Completa_Hist_Input.Fec_Vcto,
        RF_base_Completa_Hist_Input.Dias_Liq, RF_base_Completa_Hist_Input.Dias_Vcto,
        RF_base_Completa_Hist_Input.Cap_Amort, RF_base_Completa_Hist_Input.Int_Total_Cont,
        0 AS Int_Devengado,
        RF_base_Completa_Hist_Input.Tasa_Cont,
        RF_base_Completa_Hist_Input.VP_Cap_Amort, RF_base_Completa_Hist_Input.VP_Int_Total,
        RF_base_Completa_Hist_Input.Tipo_Cupon, RF_base_Completa_Hist_Input.Cod_Area_Neg,
        RF_base_Completa_Hist_Input.Cod_Estrategia, RF_base_Completa_Hist_Input.Tipo_Book,
        RF_base_Completa_Hist_Input.Clasificacion_Contable,
        RF_base_Completa_Hist_Input.RUT_cli, RF_base_Completa_Hist_Input.Nombre_Cli,
        RF_base_Completa_Hist_Input.Moneda_Liq, RF_base_Completa_Hist_Input.Dias_Pacto,
        "" AS Factor_Riesgo, "" AS Codigo_Ejecutivo, "" AS Indexador,
        "" AS tasa, "" AS tasa_CF, "" AS spread
    FROM RF_Fecha_Proceso_Carteras
    INNER JOIN RF_base_Completa_Hist_Input
        ON RF_Fecha_Proceso_Carteras.Fecha = RF_base_Completa_Hist_Input.Fec_Pro
    WHERE RF_base_Completa_Hist_Input.Cod_Pro <> "Spot"
        AND RF_base_Completa_Hist_Input.Cod_Pro <> "IRS"
        AND RF_base_Completa_Hist_Input.Clasificacion_Contable = "HTM"
        AND Left(RF_base_Completa_Hist_Input.Cod_Pro, 5) <> "Venta"
        AND Right(RF_base_Completa_Hist_Input.Cod_Sub_Pro, 8) <> 'TGR_Pcto'
        AND RF_base_Completa_Hist_Input.Cod_Sub_Pro NOT LIKE "*RT*"
        AND Right(RF_base_Completa_Hist_Input.Cod_Sub_Pro, 4) <> 'Gtia'
        AND Right(RF_base_Completa_Hist_Input.Cod_Sub_Pro, 8) <> 'Gtia_Liq';

    Args:
        df_cartera_input: Tabla RF_base_Completa_Hist_Input (sin procesar).
        fecha_proceso: Fecha de proceso.
        columnas_relevantes: Lista de columnas a seleccionar.
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con cartera HTM formateada.
    """
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    if verbose:
        print(f"\n  Extrayendo cartera HTM para fecha {fecha.date()}...")

    df = df_cartera_input.copy()

    # Filtrar por fecha de proceso (INNER JOIN RF_Fecha_Proceso_Carteras ON Fecha = Fec_Pro)
    if 'Fec_Pro' in df.columns:
        df['Fec_Pro'] = pd.to_datetime(df['Fec_Pro'])
        df = df[df['Fec_Pro'] == fecha]

    # WHERE condiciones:
    # 1. Cod_Pro <> "Spot"
    mask = df['Cod_Pro'].astype(str) != 'Spot'
    # 2. Cod_Pro <> "IRS"
    mask = mask & (df['Cod_Pro'].astype(str) != 'IRS')
    # 3. Clasificacion_Contable = "HTM"
    mask = mask & (df['Clasificacion_Contable'].astype(str) == 'HTM')
    # 4. Left(Cod_Pro, 5) <> "Venta"  (Cod_Pro no empieza con "Venta")
    mask = mask & (~df['Cod_Pro'].astype(str).str[:5].eq('Venta'))
    # 5. Right(Cod_Sub_Pro, 8) <> 'TGR_Pcto'  (Cod_Sub_Pro no termina en "TGR_Pcto")
    cod_sub_pro_str = df['Cod_Sub_Pro'].astype(str)
    mask = mask & (~cod_sub_pro_str.str[-8:].eq('TGR_Pcto'))
    # 6. Cod_Sub_Pro NOT LIKE "*RT*"  (Cod_Sub_Pro no contiene "RT")
    mask = mask & (~cod_sub_pro_str.str.contains('RT', na=False, case=False))
    # 7. Right(Cod_Sub_Pro, 4) <> 'Gtia'  (Cod_Sub_Pro no termina en "Gtia")
    mask = mask & (~cod_sub_pro_str.str[-4:].eq('Gtia'))
    # 8. Right(Cod_Sub_Pro, 8) <> 'Gtia_Liq'  (Cod_Sub_Pro no termina en "Gtia_Liq")
    mask = mask & (~cod_sub_pro_str.str[-8:].eq('Gtia_Liq'))

    df = df.loc[mask].copy()

    # Cod_Pro fijo
    df['Cod_Pro'] = 'ML_C46_Inversiones_Financieras'

    # Cod_Sub_Pro con lógica IIF:
    # IIf(Cod_Sub_Pro LIKE "*LCHR*", "ML_C46_Inversiones_Financieras_LCHR",
    #     IIf(Cod_Sub_Pro LIKE "*BBC*", "ML_C46_Inversiones_Financieras_BBC",
    #         "ML_C46_Inversiones_Financieras_Gob"))
    # Nota: Access LIKE "*X*" es case-insensitive y equivale a .str.contains("X", case=False)
    # Usamos el Cod_Sub_Pro original (antes de sobreescribir Cod_Pro) que ya guardamos en cod_sub_pro_str
    # pero necesitamos recalcular porque filtramos filas
    cod_sub_pro_original = df['Cod_Sub_Pro'].astype(str)
    cond_lchr = cod_sub_pro_original.str.contains('LCHR', na=False, case=False)
    cond_bbc = cod_sub_pro_original.str.contains('BBC', na=False, case=False)
    df['Cod_Sub_Pro'] = np.where(
        cond_lchr, 'ML_C46_Inversiones_Financieras_LCHR',
        np.where(
            cond_bbc, 'ML_C46_Inversiones_Financieras_BBC',
            'ML_C46_Inversiones_Financieras_Gob'
        )
    )

    # Columnas adicionales con valores fijos (0 o "")
    columnas_adicionales = {
        'Int_Devengado': 0,
        'Factor_Riesgo': "",
        'Codigo_Ejecutivo': "",
        'Indexador': "",
        'tasa': "",
        'tasa_CF': "",
        'spread': ""
    }
    for col, valor in columnas_adicionales.items():
        df[col] = valor

    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin registros HTM")
        return pd.DataFrame(columns=columnas_relevantes)
    else:
        if verbose:
            print(f"    ✓ HTM: {len(df)} registros encontrados")
        return df[columnas_relevantes].copy()


def extraer_cartera_htm_para_tabla_desarrollo(
    df_extrae_cartera_htm: pd.DataFrame,
    df_precios_dia: pd.DataFrame,
    columnas_relevantes: Optional[List[str]] = COLUMNAS_TABLA_DESARROLLO,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Formatea cartera HTM para insertar en RF_Tabla_Desarrollo_Interna.

    DIFERENCIA vs FFMM: Fec_Pago = Fec_Vcto (NO Fec_Vcto_Cup)

    SQL de referencia (RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM):

    INSERT INTO RF_Tabla_Desarrollo_Interna (
        Fec_Pro, Cod_Emp, Moneda, Cod_A_P, Cod_Pro, Cod_Sub_Pro,
        Fec_Pago, Dias_Pago, Cap_Amort, Int_Total_Cont,
        VP_Cap_Amort, VP_Int_Total_Cont, Precio_Mid, Flujo_CLP
    )
    SELECT
        RF_PLI_044i_CarteraInv_HTM.Fec_Pro,
        RF_PLI_044i_CarteraInv_HTM.Cod_Emp,
        RF_PLI_044i_CarteraInv_HTM.Moneda,
        RF_PLI_044i_CarteraInv_HTM.Cod_A_P,
        RF_PLI_044i_CarteraInv_HTM.Cod_Pro,
        RF_PLI_044i_CarteraInv_HTM.Cod_Sub_Pro,
        RF_PLI_044i_CarteraInv_HTM.Fec_Vcto AS Fec_Pago,      -- ¡Fec_Vcto, no Fec_Vcto_Cup!
        RF_PLI_044i_CarteraInv_HTM.Dias_Liq AS Dias_Pago,
        RF_PLI_044i_CarteraInv_HTM.Cap_Amort,
        RF_PLI_044i_CarteraInv_HTM.Int_Total_Cont,
        RF_PLI_044i_CarteraInv_HTM.VP_Cap_Amort,
        RF_PLI_044i_CarteraInv_HTM.VP_Int_Total AS VP_Int_Total_Cont,
        Precios_Dia.Precio_Mid,
        ([RF_PLI_044i_CarteraInv_HTM].[VP_Cap_Amort]
         + [RF_PLI_044i_CarteraInv_HTM].[VP_Int_Total])
         * [Precios_Dia].[Precio_Mid] AS Flujo_CLP
    FROM Precios_Dia
    INNER JOIN RF_PLI_044i_CarteraInv_HTM
        ON Precios_Dia.NEMOTECNICO = RF_PLI_044i_CarteraInv_HTM.Moneda;

    Args:
        df_extrae_cartera_htm: Cartera HTM extraída con extrae_cartera_htm().
        df_precios_dia: Precios del día (filtrado por NEMOTECNICO si aplica).
        columnas_relevantes: Columnas de salida.
        verbose: Si True, muestra mensajes.

    Returns:
        DataFrame con columnas COLUMNAS_TABLA_DESARROLLO.
    """
    if verbose:
        print(f"\n  Formateando cartera HTM para tabla de desarrollo...")
    df = df_extrae_cartera_htm.copy()
    # Cambio de nombres de columnas según SQL de referencia:
    # Fec_Vcto AS Fec_Pago  (¡NO Fec_Vcto_Cup como en FFMM!)
    # Dias_Liq AS Dias_Pago
    # VP_Int_Total AS VP_Int_Total_Cont
    df = df.rename(columns={
        'Fec_Vcto': 'Fec_Pago',
        'Dias_Liq': 'Dias_Pago',
        'VP_Int_Total': 'VP_Int_Total_Cont'
    })
    # Agregar Precio_Mid desde df_precios_dia
    # INNER JOIN Precios_Dia ON Precios_Dia.NEMOTECNICO = CarteraInv_HTM.Moneda
    if len(df_precios_dia) > 0:
        df = df.merge(df_precios_dia[['NEMOTECNICO', 'Precio_Mid']], left_on='Moneda', right_on='NEMOTECNICO', how='inner')
    # Flujo_CLP = (VP_Cap_Amort + VP_Int_Total_Cont) * Precio_Mid
    df['Flujo_CLP'] = (df['VP_Cap_Amort'] + df['VP_Int_Total_Cont']) * df['Precio_Mid']
    if verbose:
        print(f"  ✓ Cartera HTM formateada para tabla de desarrollo: {len(df)} registros")
    return df[columnas_relevantes].copy()


def extrae_cartera_rt(
    df_cartera: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    columnas_relevantes: Optional[List[str]] = COLUMNAS_FFMM_EXTRACCION,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Extrae cartera de Renta en Tránsito (RT) de la cartera de inversiones.

    SQL de referencia (RF_PLI_044g_CarteraInv_RT):

    SELECT RF_base_Completa_Hist.Fec_Pro, RF_base_Completa_Hist.Cod_Emp,
        RF_base_Completa_Hist.Moneda, RF_base_Completa_Hist.Cod_A_P,
        "ML_C46_Inversiones_Financieras" AS Cod_Pro,
        "ML_C46_Inversiones_Financieras_RT" AS Cod_Sub_Pro,
        RF_base_Completa_Hist.Num_Oper, RF_base_Completa_Hist.Num_Cup,
        RF_base_Completa_Hist.Emisor, RF_base_Completa_Hist.Nemotecnico,
        RF_base_Completa_Hist.Tasa_Emi, RF_base_Completa_Hist.Compensacion,
        RF_base_Completa_Hist.Fec_Cre, RF_base_Completa_Hist.Fec_Ini_Cup,
        RF_base_Completa_Hist.Fec_Vcto_Cup, RF_base_Completa_Hist.Fec_Rep,
        RF_base_Completa_Hist.Fec_Vcto,
        RF_base_Completa_Hist.Dias_Liq, RF_base_Completa_Hist.Dias_Vcto,
        RF_base_Completa_Hist.Cap_Amort, RF_base_Completa_Hist.Int_Total_Cont,
        0 AS Int_Devengado,
        RF_base_Completa_Hist.Tasa_Cont,
        RF_base_Completa_Hist.VP_Cap_Amort, RF_base_Completa_Hist.VP_Int_Total,
        RF_base_Completa_Hist.Tipo_Cupon, RF_base_Completa_Hist.Cod_Area_Neg,
        RF_base_Completa_Hist.Cod_Estrategia, RF_base_Completa_Hist.Tipo_Book,
        RF_base_Completa_Hist.Clasificacion_Contable,
        RF_base_Completa_Hist.RUT_cli, RF_base_Completa_Hist.Nombre_Cli,
        RF_base_Completa_Hist.Moneda_Liq, RF_base_Completa_Hist.Dias_Pacto,
        "" AS Factor_Riesgo, "" AS Codigo_Ejecutivo, "" AS Indexador,
        "" AS tasa, "" AS tasa_CF, "" AS spread
    FROM RF_Fecha_Proceso_Carteras
    INNER JOIN RF_base_Completa_Hist
        ON RF_Fecha_Proceso_Carteras.Fecha = RF_base_Completa_Hist.Fec_Pro
    WHERE RF_base_Completa_Hist.Cod_Pro <> "Spot"
        AND RF_base_Completa_Hist.Cod_Sub_Pro Like "*RT*";

    Es decir:
    se toma la tabla RF_base_Completa_Hist,
    se filtra por fecha de proceso,
    se filtra que Cod_Pro sea distinto de "Spot",
    y que Cod_Sub_Pro contenga "RT" (Access LIKE "*RT*" es contains case-insensitive).
    Luego se llenan las columnas Cod_Pro y Cod_Sub_Pro con los valores fijos
    y las columnas adicionales con valores vacíos o ceros.

    Args:
        df_cartera: Tabla RF_base_Completa_Hist (ya procesada).
        fecha_proceso: Fecha de proceso.
        columnas_relevantes: Lista de columnas a seleccionar.
        verbose: Si True, muestra mensajes.

    Returns:
        DataFrame con cartera RT formateada.
    """
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso
    if verbose:
        print(f"\n  Extrayendo cartera RT para fecha {fecha.date()}...")

    df = df_cartera.copy()

    # Filtrar por fecha de proceso
    if 'Fec_Pro' in df.columns:
        df['Fec_Pro'] = pd.to_datetime(df['Fec_Pro'])
        df = df[df['Fec_Pro'] == fecha]

    # WHERE condiciones:
    # 1. Cod_Pro <> "Spot"
    mask = df['Cod_Pro'].astype(str) != 'Spot'
    # 2. Cod_Sub_Pro Like "*RT*"  (Cod_Sub_Pro contiene "RT")
    mask = mask & df['Cod_Sub_Pro'].astype(str).str.contains('RT', na=False, case=False)

    df = df.loc[mask].copy()

    # Cod_Pro y Cod_Sub_Pro fijos
    df['Cod_Pro'] = 'ML_C46_Inversiones_Financieras'
    df['Cod_Sub_Pro'] = 'ML_C46_Inversiones_Financieras_RT'

    # Columnas adicionales con valores fijos
    columnas_adicionales = {
        'Int_Devengado': 0,
        'Factor_Riesgo': "",
        'Codigo_Ejecutivo': "",
        'Indexador': "",
        'tasa': "",
        'tasa_CF': "",
        'spread': ""
    }
    for col, valor in columnas_adicionales.items():
        df[col] = valor

    if len(df) == 0:
        if verbose:
            print(f"    ⚠ Sin registros RT")
        return pd.DataFrame(columns=columnas_relevantes)
    else:
        if verbose:
            print(f"    ✓ RT: {len(df)} registros encontrados")
        return df[columnas_relevantes].copy()


def extraer_cartera_rt_para_tabla_desarrollo(
    df_extrae_cartera_rt: pd.DataFrame,
    df_precios_dia: pd.DataFrame,
    columnas_relevantes: Optional[List[str]] = COLUMNAS_TABLA_DESARROLLO,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Formatea cartera RT para insertar en RF_Tabla_Desarrollo_Interna.

    DIFERENCIA vs FFMM: Fec_Pago = Fec_Vcto (NO Fec_Vcto_Cup)

    SQL de referencia (RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT):

    INSERT INTO RF_Tabla_Desarrollo_Interna (
        Fec_Pro, Cod_Emp, Moneda, Cod_A_P, Cod_Pro, Cod_Sub_Pro,
        Fec_Pago, Dias_Pago, Cap_Amort, Int_Total_Cont,
        VP_Cap_Amort, VP_Int_Total_Cont, Precio_Mid, Flujo_CLP
    )
    SELECT
        RF_PLI_044g_CarteraInv_RT.Fec_Pro,
        RF_PLI_044g_CarteraInv_RT.Cod_Emp,
        RF_PLI_044g_CarteraInv_RT.Moneda,
        RF_PLI_044g_CarteraInv_RT.Cod_A_P,
        RF_PLI_044g_CarteraInv_RT.Cod_Pro,
        RF_PLI_044g_CarteraInv_RT.Cod_Sub_Pro,
        RF_PLI_044g_CarteraInv_RT.Fec_Vcto AS Fec_Pago,       -- ¡Fec_Vcto, no Fec_Vcto_Cup!
        RF_PLI_044g_CarteraInv_RT.Dias_Liq AS Dias_Pago,
        RF_PLI_044g_CarteraInv_RT.Cap_Amort,
        RF_PLI_044g_CarteraInv_RT.Int_Total_Cont,
        RF_PLI_044g_CarteraInv_RT.VP_Cap_Amort,
        RF_PLI_044g_CarteraInv_RT.VP_Int_Total AS VP_Int_Total_Cont,
        Precios_Dia.Precio_Mid,
        ([RF_PLI_044g_CarteraInv_RT].[VP_Cap_Amort]
         + [RF_PLI_044g_CarteraInv_RT].[VP_Int_Total])
         * [Precios_Dia].[Precio_Mid] AS Flujo_CLP
    FROM Precios_Dia
    INNER JOIN RF_PLI_044g_CarteraInv_RT
        ON Precios_Dia.NEMOTECNICO = RF_PLI_044g_CarteraInv_RT.Moneda;

    Args:
        df_extrae_cartera_rt: Cartera RT extraída con extrae_cartera_rt().
        df_precios_dia: Precios del día.
        columnas_relevantes: Columnas de salida.
        verbose: Si True, muestra mensajes.

    Returns:
        DataFrame con columnas COLUMNAS_TABLA_DESARROLLO.
    """
    if verbose:
        print(f"\n  Formateando cartera RT para tabla de desarrollo...")
    df = df_extrae_cartera_rt.copy()
    # Cambio de nombres de columnas según SQL de referencia:
    # Fec_Vcto AS Fec_Pago  (¡NO Fec_Vcto_Cup como en FFMM!)
    # Dias_Liq AS Dias_Pago
    # VP_Int_Total AS VP_Int_Total_Cont
    df = df.rename(columns={
        'Fec_Vcto': 'Fec_Pago',
        'Dias_Liq': 'Dias_Pago',
        'VP_Int_Total': 'VP_Int_Total_Cont'
    })
    # Agregar Precio_Mid desde df_precios_dia
    # INNER JOIN Precios_Dia ON Precios_Dia.NEMOTECNICO = CarteraInv_RT.Moneda
    if len(df_precios_dia) > 0:
        df = df.merge(df_precios_dia[['NEMOTECNICO', 'Precio_Mid']], left_on='Moneda', right_on='NEMOTECNICO', how='inner')
    # Flujo_CLP = (VP_Cap_Amort + VP_Int_Total_Cont) * Precio_Mid
    df['Flujo_CLP'] = (df['VP_Cap_Amort'] + df['VP_Int_Total_Cont']) * df['Precio_Mid']
    if verbose:
        print(f"  ✓ Cartera RT formateada para tabla de desarrollo: {len(df)} registros")
    return df[columnas_relevantes].copy()


# def extraer_cartera_especial(
#     df_cartera: pd.DataFrame,
#     tipo: Literal['FFMM', 'HTM', 'RT'],
#     fecha_proceso: Union[int, str, datetime],
#     columnas_relevantes: Optional[List[str]] = COLUMNAS_FFMM_EXTRACCION,
#     verbose: bool = True
# ) -> pd.DataFrame:
#     """
#     Extrae cartera especial (FFMM, HTM o RT) de la cartera de inversiones.
    
#     Estos tipos NO pasan por el modelo de liquidación porque:
#     - FFMM: Liquidez inmediata (T+0/T+1)
#     - HTM: Held-to-Maturity, compromiso de no venta
#     - RT: Renta en tránsito, ya comprometida
    
#     Args:
#         df_cartera: Cartera de inversiones completa.
#         tipo: Tipo de cartera a extraer ('FFMM', 'HTM', 'RT').
#         fecha_proceso: Fecha de proceso.
#         columnas_relevantes: Columnas relevantes para la extracción.
        
#     Returns:
#         DataFrame con cartera especial formateada.
#     """
#     if verbose:
#         print(f"\n  Extrayendo cartera {tipo}...")
    
#     FILTROS = {
#         'FFMM': {'patron': '^INVERSIONES FINANCIERAS FONDOS MUTUOS$', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_FFMM'},
#         'HTM': {'patron': 'HTM', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_HTM'},
#         'RT': {'patron': 'RT|Transito', 'cod_sub_pro': 'ML_C46_Inversiones_Financieras_RT'},
#     }
    
#     if tipo not in FILTROS:
#         raise ValueError(f"Tipo '{tipo}' inválido. Válidos: {list(FILTROS.keys())}")
    
#     filtro = FILTROS[tipo]
    
#     # Normalizar fecha
#     if isinstance(fecha_proceso, int):
#         fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
#     elif isinstance(fecha_proceso, str):
#         fecha = pd.to_datetime(fecha_proceso)
#     else:
#         fecha = fecha_proceso
    
#     df = df_cartera.copy()
    
#     # Filtrar por patrón en Cod_Sub_Pro
#     mask = df['Cod_Sub_Pro'].str.contains(filtro['patron'], na=False, case=False, regex=True)
#     df = df.loc[mask].copy()
    
#     if len(df) == 0:
#         if verbose:
#             print(f"    ⚠ Sin registros {tipo}")
#         return pd.DataFrame(columns=columnas_relevantes)
    
#     # Determinar columna de días
#     col_dias = 'Dias_Liq' if 'Dias_Liq' in df.columns else 'Dias_Vcto'
    
#     # Formatear
#     resultado = pd.DataFrame({
#         'Fec_Pro': fecha,
#         'Cod_Emp': CODIGO_EMPRESA,
#         'Moneda': df['Moneda'].values,
#         'Cod_A_P': CODIGO_ACTIVO_PASIVO,
#         'Cod_Pro': CODIGO_PRODUCTO,
#         'Cod_Sub_Pro': filtro['cod_sub_pro'],
#         'Fec_Pago': fecha + pd.to_timedelta(df[col_dias].values, unit='D'),
#         'Dias_Pago': df[col_dias].values,
#         'Cap_Amort': df['Cap_Amort'].values if 'Cap_Amort' in df.columns else df['VP_Cap_Amort'].values,
#         'Int_Total_Cont': df['Int_Total_Cont'].values if 'Int_Total_Cont' in df.columns else 0,
#         'VP_Cap_Amort': df['VP_Cap_Amort'].values,
#         'VP_Int_Total_Cont': df['VP_Int_Total'].values if 'VP_Int_Total' in df.columns else 0,
#     })
    
#     if verbose:
#         total = resultado['Cap_Amort'].sum()
#         print(f"    ✓ {tipo}: {len(resultado)} registros, total={total:,.0f}")
    
#     return resultado


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
    
    NOTA: df_cartera_ffmm, df_cartera_htm, df_cartera_rt deben venir ya 
    formateados con las funciones extraer_cartera_X_para_tabla_desarrollo(),
    es decir, ya tienen las columnas COLUMNAS_TABLA_DESARROLLO incluyendo
    Precio_Mid y Flujo_CLP. Solo df_modelo_inversiones necesita que se le
    aplique agregar_precio_y_flujo_clp.
    
    Args:
        df_modelo_inversiones: Flujos del modelo de liquidación (paso 21).
        df_precios_dia: Precios TCRC del día.
        df_cartera_ffmm: Cartera FFMM ya formateada para desarrollo (opcional).
        df_cartera_htm: Cartera HTM ya formateada para desarrollo (opcional).
        df_cartera_rt: Cartera RT ya formateada para desarrollo (opcional).
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
    
    # Paso 24: Agregar FFMM (ya viene formateado con Precio_Mid y Flujo_CLP)
    if df_cartera_ffmm is not None and len(df_cartera_ffmm) > 0:
        if verbose:
            print("\n  [24] Agregando FFMM (ya formateado)...")
        dfs_a_concatenar.append(df_cartera_ffmm)
        if verbose:
            print(f"       FFMM: {len(df_cartera_ffmm):,} registros")
    
    # Paso 25: Agregar HTM (ya viene formateado con Precio_Mid y Flujo_CLP)
    if df_cartera_htm is not None and len(df_cartera_htm) > 0:
        if verbose:
            print("\n  [25] Agregando HTM (ya formateado)...")
        dfs_a_concatenar.append(df_cartera_htm)
        if verbose:
            print(f"       HTM: {len(df_cartera_htm):,} registros")
    
    # Paso 26: Agregar RT (ya viene formateado con Precio_Mid y Flujo_CLP)
    if df_cartera_rt is not None and len(df_cartera_rt) > 0:
        if verbose:
            print("\n  [26] Agregando RT (ya formateado)...")
        dfs_a_concatenar.append(df_cartera_rt)
        if verbose:
            print(f"       RT: {len(df_cartera_rt):,} registros")
    
    # Consolidar
    resultado = pd.concat(dfs_a_concatenar, ignore_index=True)
    
    if verbose:
        print("\n" + "="*60)
        print(f"  RESUMEN TABLA DESARROLLO:")
        print(f"  - Total registros: {len(resultado):,}")
        print(f"  - Total Flujo_CLP: {resultado['Flujo_CLP'].sum():,.0f}")
        print("="*60)
    
    return resultado


def _formatear_ml_para_excel(df_tabla_final: pd.DataFrame) -> pd.DataFrame:
    """
    Formatea la parte ML (modelo de liquidación) de RF_PLI_049.
    
    Constantes fijas para AREA NEGOCIO, CODIGO_ESTRATEGIA, CLASIFICACION_CONTABLE.
    Todas las fechas (FECHA PAGO, VENCIMIENTO_CUOTA, REPRICING) = Fec_Pago.
    """
    df = df_tabla_final.copy()
    return pd.DataFrame({
        'FECHA PROCESO': df['Fec_Pro'].values,
        'CODIGO_EMPRESA': df['Cod_Emp'].values,
        'OPERACION': "",
        'COD ACT/PAS': df['Cod_A_P'].values,
        'MONEDA_ORIGEN': df['Moneda'].values,
        'MONEDA_COMPENSACION': df['Moneda'].values,
        'COMPENSACION': "C",
        'CODIGO_PRODUCTO': df['Cod_Pro'].values,
        'CODIGO_SUBPRODUCTO': df['Cod_Sub_Pro'].values,
        'FECHA CREACION': "",
        'NUMERO_CUOTA': "",
        'FECHA_INICIO_CUOTA': "",
        'FECHA_VENCIMIENTO_CUOTA': df['Fec_Pago'].values,
        'FECHA PAGO': df['Fec_Pago'].values,
        'FECHA_REPRICING': df['Fec_Pago'].values,
        'AMORTIZACION': df['Cap_Amort'].values,
        'INTERES': df['Int_Total_Cont'].values,
        'INTERES_DEVENGADO': 0,
        'VP_AMORTIZACION': df['VP_Cap_Amort'].values,
        'VP_INTERES': df['VP_Int_Total_Cont'].values,
        'FACTOR DE RIESGO': "",
        'TIPO_CUOTA': 1,
        'AREA NEGOCIO': "TRADING TASAS",
        'CODIGO_ EJECUTIVO': "",
        'CODIGO_ESTRATEGIA': "TRADING TASAS",
        'CLASIFICACION_CONTABLE': "P&L",
        'TIPO TASA': 1,
        'INDEXADOR': "",
        'TASA': "",
        'TASA CF': "",
        'SPREAD': "",
    })


def _formatear_ffmm_para_excel(df_cartera_ffmm: pd.DataFrame) -> pd.DataFrame:
    """
    Formatea la parte FFMM de RF_PLI_049.
    
    DIFERENCIA vs ML:
    - FECHA PAGO y FECHA_VENCIMIENTO_CUOTA = Fec_Vcto_Cup (no Fec_Pago)
    - FECHA_REPRICING = Fec_Vcto (no Fec_Pago) 
    - AREA NEGOCIO = Cod_Estrategia (dato de cartera, no constante)
    - CODIGO_ESTRATEGIA = Cod_Estrategia (dato de cartera)
    - CLASIFICACION_CONTABLE = Clasificacion_Contable (dato de cartera)
    - VP_INTERES = VP_Int_Total (no VP_Int_Total_Cont)
    """
    df = df_cartera_ffmm.copy()
    return pd.DataFrame({
        'FECHA PROCESO': df['Fec_Pro'].values,
        'CODIGO_EMPRESA': df['Cod_Emp'].values,
        'OPERACION': "",
        'COD ACT/PAS': df['Cod_A_P'].values,
        'MONEDA_ORIGEN': df['Moneda'].values,
        'MONEDA_COMPENSACION': df['Moneda'].values,
        'COMPENSACION': "C",
        'CODIGO_PRODUCTO': df['Cod_Pro'].values,
        'CODIGO_SUBPRODUCTO': df['Cod_Sub_Pro'].values,
        'FECHA CREACION': "",
        'NUMERO_CUOTA': "",
        'FECHA_INICIO_CUOTA': "",
        'FECHA_VENCIMIENTO_CUOTA': df['Fec_Vcto_Cup'].values,
        'FECHA PAGO': df['Fec_Vcto_Cup'].values,
        'FECHA_REPRICING': df['Fec_Vcto'].values,
        'AMORTIZACION': df['Cap_Amort'].values,
        'INTERES': df['Int_Total_Cont'].values,
        'INTERES_DEVENGADO': 0,
        'VP_AMORTIZACION': df['VP_Cap_Amort'].values,
        'VP_INTERES': df['VP_Int_Total'].values,
        'FACTOR DE RIESGO': "",
        'TIPO_CUOTA': 1,
        'AREA NEGOCIO': df['Cod_Estrategia'].values,
        'CODIGO_ EJECUTIVO': "",
        'CODIGO_ESTRATEGIA': df['Cod_Estrategia'].values,
        'CLASIFICACION_CONTABLE': df['Clasificacion_Contable'].values,
        'TIPO TASA': 1,
        'INDEXADOR': "",
        'TASA': "",
        'TASA CF': "",
        'SPREAD': "",
    })


def _formatear_rt_htm_para_excel(df_cartera: pd.DataFrame) -> pd.DataFrame:
    """
    Formatea la parte RT o HTM de RF_PLI_049 (mismo esquema entre ambos).
    
    DIFERENCIA vs FFMM:
    - FECHA PAGO, FECHA_VENCIMIENTO_CUOTA y FECHA_REPRICING = Fec_Vcto (las 3)
    
    DIFERENCIA vs ML:
    - AREA NEGOCIO, CODIGO_ESTRATEGIA, CLASIFICACION_CONTABLE = datos de cartera
    - VP_INTERES = VP_Int_Total (no VP_Int_Total_Cont)
    """
    df = df_cartera.copy()
    return pd.DataFrame({
        'FECHA PROCESO': df['Fec_Pro'].values,
        'CODIGO_EMPRESA': df['Cod_Emp'].values,
        'OPERACION': "",
        'COD ACT/PAS': df['Cod_A_P'].values,
        'MONEDA_ORIGEN': df['Moneda'].values,
        'MONEDA_COMPENSACION': df['Moneda'].values,
        'COMPENSACION': "C",
        'CODIGO_PRODUCTO': df['Cod_Pro'].values,
        'CODIGO_SUBPRODUCTO': df['Cod_Sub_Pro'].values,
        'FECHA CREACION': "",
        'NUMERO_CUOTA': "",
        'FECHA_INICIO_CUOTA': "",
        'FECHA_VENCIMIENTO_CUOTA': df['Fec_Vcto'].values,
        'FECHA PAGO': df['Fec_Vcto'].values,
        'FECHA_REPRICING': df['Fec_Vcto'].values,
        'AMORTIZACION': df['Cap_Amort'].values,
        'INTERES': df['Int_Total_Cont'].values,
        'INTERES_DEVENGADO': 0,
        'VP_AMORTIZACION': df['VP_Cap_Amort'].values,
        'VP_INTERES': df['VP_Int_Total'].values,
        'FACTOR DE RIESGO': "",
        'TIPO_CUOTA': 1,
        'AREA NEGOCIO': df['Cod_Estrategia'].values,
        'CODIGO_ EJECUTIVO': "",
        'CODIGO_ESTRATEGIA': df['Cod_Estrategia'].values,
        'CLASIFICACION_CONTABLE': df['Clasificacion_Contable'].values,
        'TIPO TASA': 1,
        'INDEXADOR': "",
        'TASA': "",
        'TASA CF': "",
        'SPREAD': "",
    })


def formatear_para_excel(
    df_tabla_final: pd.DataFrame,
    df_cartera_ffmm: Optional[pd.DataFrame] = None,
    df_cartera_htm: Optional[pd.DataFrame] = None,
    df_cartera_rt: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Formatea para exportación a Excel (RF_Tabla_Desarrollo_Final).
    
    Implementa RF_PLI_049_Tabla_Desarrollo_Modelo_Inversiones y
    RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel.
    
    ARQUITECTURA: Es un UNION ALL de 4 fuentes con mapeos DISTINTOS por fuente:
    - ML (RF_PLI_046): constantes fijas para AREA NEGOCIO="TRADING TASAS",
      CLASIFICACION_CONTABLE="P&L"; fechas todas = Fec_Pago
    - FFMM (RF_PLI_044f): FECHA PAGO = Fec_Vcto_Cup, REPRICING = Fec_Vcto;
      AREA NEGOCIO/ESTRATEGIA/CLASIFICACION desde datos de cartera
    - RT (RF_PLI_044g): todas las fechas = Fec_Vcto; datos de cartera
    - HTM (RF_PLI_044i): todas las fechas = Fec_Vcto; datos de cartera
    
    IMPORTANTE: Los inputs FFMM/HTM/RT deben ser las carteras completas
    (output de extrae_cartera_ffmm/htm/rt), NO los _para_tabla_desarrollo,
    porque se necesitan columnas como Cod_Estrategia, Clasificacion_Contable,
    Fec_Vcto_Cup, Fec_Vcto que se pierden en el formateo intermedio.

    Args:
        df_tabla_final: Output del paso 21 (RF_PLI_Modelo_Inversiones_Final_CLP).
        df_cartera_ffmm: Cartera FFMM (output de extrae_cartera_ffmm, columnas completas).
        df_cartera_htm: Cartera HTM (output de extrae_cartera_htm, columnas completas).
        df_cartera_rt: Cartera RT (output de extrae_cartera_rt, columnas completas).
        verbose: Si True, muestra mensajes.
        
    Returns:
        DataFrame con 31 columnas según formato Excel (RF_Tabla_Desarrollo_Final).
    """
    if verbose:
        print("\n[Paso 27] Formateando para Excel (RF_PLI_049 → RF_PLI_050)...")
    
    dfs = []
    
    # 1. ML: modelo de liquidación (RF_PLI_046)
    df_ml = _formatear_ml_para_excel(df_tabla_final)
    dfs.append(df_ml)
    if verbose:
        print(f"  ML:   {len(df_ml):,} registros")
    
    # 2. FFMM (RF_PLI_044f)
    if df_cartera_ffmm is not None and len(df_cartera_ffmm) > 0:
        df_ffmm = _formatear_ffmm_para_excel(df_cartera_ffmm)
        dfs.append(df_ffmm)
        if verbose:
            print(f"  FFMM: {len(df_ffmm):,} registros")
    
    # 3. RT (RF_PLI_044g)
    if df_cartera_rt is not None and len(df_cartera_rt) > 0:
        df_rt = _formatear_rt_htm_para_excel(df_cartera_rt)
        dfs.append(df_rt)
        if verbose:
            print(f"  RT:   {len(df_rt):,} registros")
    
    # 4. HTM (RF_PLI_044i)
    if df_cartera_htm is not None and len(df_cartera_htm) > 0:
        df_htm = _formatear_rt_htm_para_excel(df_cartera_htm)
        dfs.append(df_htm)
        if verbose:
            print(f"  HTM:  {len(df_htm):,} registros")
    
    resultado = pd.concat(dfs, ignore_index=True)
    
    # Asegurar orden de columnas según RF_PLI_050
    resultado = resultado[COLUMNAS_EXCEL_FINAL]
    
    if verbose:
        print(f"  ✓ Formateado: {len(resultado):,} registros, {len(resultado.columns)} columnas")
    
    return resultado


# =============================================================================
# FUNCIÓN WRAPPER COMPLETA
# =============================================================================

def ejecutar_pasos_20_a_27(
    flujos: Dict[str, pd.DataFrame],
    tablas: Dict[str, pd.DataFrame],
    fecha_proceso: Union[int, str, datetime],
    df_cartera_inv_pacto: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Ejecuta los pasos 20-27 completos del modelo de inversiones.
    
    Args:
        flujos: Diccionario con flujos por instrumento.
        tablas: Diccionario con tablas linkeadas. Requiere:
            - 'RF_Base_Diaria_Precios'
            - 'RF_base_Completa_Hist'
            - 'RF_base_Completa_Hist_Input' (para HTM)
        fecha_proceso: Fecha de proceso.
        df_cartera_inv_pacto: Cartera de pactos (RF_PLI_001d) para filtrar >90 días.
        verbose: Si True, muestra mensajes.
        
    Returns:
        Diccionario con:
        - 'precios_dia': Precios del día
        - 'tabla_final_inversiones': Tabla final paso 21
        - 'tabla_desarrollo': Tabla desarrollo pasos 22-26
        - 'tabla_excel': Tabla formateada paso 27 (31 columnas)
        - 'cartera_ffmm': Cartera FFMM extraída
        - 'cartera_htm': Cartera HTM extraída
        - 'cartera_rt': Cartera RT extraída
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
        df_cartera_inv_pacto=df_cartera_inv_pacto,
        verbose=verbose
    )
    
    # Extraer carteras especiales (FFMM, HTM, RT)
    df_precios_todos = resultados['precios_dia']
    df_precio_clf = df_precios_todos
    if not df_precio_clf.empty and 'NEMOTECNICO' in df_precio_clf.columns:
        df_precio_clf = df_precio_clf[df_precio_clf['NEMOTECNICO'] == 'CLF']
    
    # FFMM (desde RF_base_Completa_Hist)
    # FFMM usa JOIN con Precios_Dia completo (Moneda puede ser USD, CLP, CLF)
    cartera_ffmm = None
    ffmm_desarrollo = None
    if df_base is not None:
        cartera_ffmm = extrae_cartera_ffmm(df_base, fecha_proceso, verbose=verbose)
        if len(cartera_ffmm) > 0:
            ffmm_desarrollo = extraer_cartera_ffmm_para_tabla_desarrollo(
                cartera_ffmm, df_precios_todos, verbose=verbose
            )
    resultados['cartera_ffmm'] = cartera_ffmm
    
    # HTM (desde RF_base_Completa_Hist_Input)
    cartera_htm = None
    htm_desarrollo = None
    df_base_input = tablas.get('RF_base_Completa_Hist_Input')
    if df_base_input is not None:
        cartera_htm = extrae_cartera_htm(df_base_input, fecha_proceso, verbose=verbose)
        if len(cartera_htm) > 0:
            htm_desarrollo = extraer_cartera_htm_para_tabla_desarrollo(
                cartera_htm, df_precio_clf, verbose=verbose
            )
    resultados['cartera_htm'] = cartera_htm
    
    # RT (desde RF_base_Completa_Hist)
    cartera_rt = None
    rt_desarrollo = None
    if df_base is not None:
        cartera_rt = extrae_cartera_rt(df_base, fecha_proceso, verbose=verbose)
        if len(cartera_rt) > 0:
            rt_desarrollo = extraer_cartera_rt_para_tabla_desarrollo(
                cartera_rt, df_precio_clf, verbose=verbose
            )
    resultados['cartera_rt'] = cartera_rt
    
    # Pasos 22-26: Tabla de desarrollo interna
    resultados['tabla_desarrollo'] = generar_tabla_desarrollo_completa(
        df_modelo_inversiones=resultados['tabla_final_inversiones'],
        df_precios_dia=df_precio_clf,
        df_cartera_ffmm=ffmm_desarrollo,
        df_cartera_htm=htm_desarrollo,
        df_cartera_rt=rt_desarrollo,
        verbose=verbose
    )
    
    # Paso 27: Formato Excel (RF_PLI_049 → RF_PLI_050)
    # Usa carteras completas (no _desarrollo) porque necesita columnas extra
    resultados['tabla_excel'] = formatear_para_excel(
        df_tabla_final=resultados['tabla_final_inversiones'],
        df_cartera_ffmm=cartera_ffmm,
        df_cartera_htm=cartera_htm,
        df_cartera_rt=cartera_rt,
        verbose=verbose
    )
    
    return resultados
