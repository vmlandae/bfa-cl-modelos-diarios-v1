"""
Generador de Cartera Adicional para Modelo de Inversiones.

Replica la macro CarteraAdicional del archivo "Maestro Modelo de Inversiones.xlsm".
Toma la tabla Excel (31 cols, con códigos de sub-producto originales, PRE-RepasaCodigo)
y la expande a la estructura CartAdcnl (54 cols) con campos fijos y exporta como CSV.

Nota: En VBA, CarteraAdicional se ejecuta ANTES de RepasaCodigoSubProducto,
por lo que recibe los códigos originales (ej: _LCHR, _GOBCLP), no los genéricos.

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
from pathlib import Path
from typing import Union
from datetime import datetime


# =============================================================================
# CONSTANTES
# =============================================================================

COLUMNAS_CART_ADCNL = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P',
    'Fuente', 'Sistema',
    'Cod_Pro', 'Cod_Sub_Pro', 'Num_Oper', 'Num_Cup',
    'Correlativo', 'Emisor', 'Nemotecnico', 'Tasa_Emi', 'Tasa_Cont',
    'Tasa_Transferencia',
    'Compensacion',
    'Fec_Cre', 'Fec_Ini_Cup', 'Fec_Vcto_Cup', 'Fec_Rep', 'Fec_Vcto', 'Fec_Pago',
    'Dias_Liq', 'Dias_Vcto', 'Dias_Pago',
    'Cap_Amort', 'Int_Total_Cont', 'Int_Devengado',
    'VP_Cap_Amort', 'VP_Int_Total',
    'Flujo_Liq',
    'Moneda_Liq', 'Tipo_Cupon', 'Cod_Area_Neg', 'Cod_Estrategia',
    'Tipo_Book', 'Clasificacion_Contable',
    'RUT_cli', 'Nombre_Cli', 'Dias_Pacto',
    'Tir_Compra', 'VP_Cap_Amort_Comp', 'VP_Int_Total_Comp',
    'Tir_Mcdo', 'VP_Cap_Amort_TasAnt', 'VP_Int_Total_TasAnt',
    'VP_Int_Total_Cont',
    'Empresa_Relacionada', 'Pais', ' Renovacion', 'Cupo',
    'Estrategia cobertura', 'Tipo cobertura',
]
"""Columnas de la hoja CartAdcnl (54 columnas)."""


# Mapeo de columnas Excel (INTERFAZ) a columnas CartAdcnl
# Basado en la macro VBA CarteraAdicional que mapea rangos de INTERFAZ a CartAdcnl.
# Referencia: arr1=A(Fec_Pro), arr2=B(Cod_Emp), arr3=E(Moneda_Origen),
# arr4=D(Cod_A_P), arr5=H(Cod_Pro), arr6=I(Cod_Sub_Pro), etc.
_MAPEO_INTERFAZ_A_CARTADCNL = {
    'FECHA PROCESO': 'Fec_Pro',
    'CODIGO_EMPRESA': 'Cod_Emp',
    'MONEDA_ORIGEN': 'Moneda',
    'COD ACT/PAS': 'Cod_A_P',
    'CODIGO_PRODUCTO': 'Cod_Pro',
    'CODIGO_SUBPRODUCTO': 'Cod_Sub_Pro',
    'COMPENSACION': 'Compensacion',
    'FECHA_VENCIMIENTO_CUOTA': 'Fec_Vcto_Cup',
    'FECHA PAGO': 'Fec_Pago',
    'FECHA_REPRICING': 'Fec_Rep',
    'AMORTIZACION': 'Cap_Amort',
    'INTERES': 'Int_Total_Cont',
    'INTERES_DEVENGADO': 'Int_Devengado',
    'VP_AMORTIZACION': 'VP_Cap_Amort',
    'VP_INTERES': 'VP_Int_Total',
    'MONEDA_COMPENSACION': 'Moneda_Liq',
    'TIPO_CUOTA': 'Tipo_Cupon',
    'AREA NEGOCIO': 'Cod_Area_Neg',
    'CODIGO_ESTRATEGIA': 'Cod_Estrategia',
    'CLASIFICACION_CONTABLE': 'Clasificacion_Contable',
    'TASA CF': 'Tasa_Cont',
}


def generar_hoja_cartera_adicional(df_tabla_excel: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la hoja CartAdcnl a partir de la tabla Excel (31 cols).

    Replica la macro CarteraAdicional del VBA que mapea columnas de la tabla
    Excel a CartAdcnl, agrega campos fijos ('CARTERA ADICIONAL', 'RF') y rellena
    columnas numéricas restantes con 0.

    En VBA, CarteraAdicional se ejecuta ANTES de RepasaCodigoSubProducto,
    por lo que recibe los códigos originales (ej: _LCHR, _GOBCLP).

    Args:
        df_tabla_excel: DataFrame formato Excel (31 cols, códigos originales
            pre-RepasaCodigo).

    Returns:
        DataFrame con 54 columnas para la hoja CartAdcnl.
    """
    n = len(df_tabla_excel)
    result = pd.DataFrame(index=range(n))

    # Mapear columnas que existen
    for col_excel, col_cart in _MAPEO_INTERFAZ_A_CARTADCNL.items():
        if col_excel in df_tabla_excel.columns:
            result[col_cart] = df_tabla_excel[col_excel].values

    # Campos fijos
    result['Fuente'] = 'CARTERA ADICIONAL'
    result['Sistema'] = 'RF'

    # Fec_Vcto = misma que Fec_Vcto_Cup (según macro VBA: Rng10=G, Rng13=M)
    if 'Fec_Vcto_Cup' in result.columns:
        result['Fec_Vcto'] = result['Fec_Vcto_Cup'].values

    # Campos vacíos/nulos
    for col in ['Num_Oper', 'Num_Cup', 'Correlativo', 'Emisor', 'Nemotecnico',
                'Tasa_Emi', 'Tasa_Transferencia', 'Fec_Cre', 'Fec_Ini_Cup',
                'Dias_Liq', 'Dias_Vcto', 'Dias_Pago', 'RUT_cli', 'Nombre_Cli']:
        if col not in result.columns:
            result[col] = None

    # Campos numéricos fijos en 0
    for col in ['Flujo_Liq', 'Dias_Pacto',
                'Tir_Compra', 'VP_Cap_Amort_Comp', 'VP_Int_Total_Comp',
                'Tir_Mcdo', 'VP_Cap_Amort_TasAnt', 'VP_Int_Total_TasAnt',
                'VP_Int_Total_Cont',
                'Empresa_Relacionada', 'Pais', ' Renovacion', 'Cupo',
                'Estrategia cobertura', 'Tipo cobertura']:
        if col not in result.columns:
            result[col] = 0

    # Tipo_Book = mismo que Cod_Estrategia (según macro VBA: arr24 → AJ y AK)
    if 'Cod_Estrategia' in result.columns:
        result['Tipo_Book'] = result['Cod_Estrategia'].values

    # Asegurar orden de columnas
    for col in COLUMNAS_CART_ADCNL:
        if col not in result.columns:
            result[col] = None

    return result[COLUMNAS_CART_ADCNL]


def exportar_csv_cartera_adicional(
    df_cart_adcnl: pd.DataFrame,
    fecha_proceso: Union[int, str, datetime],
    ruta_directorio: Union[str, Path],
    verbose: bool = True,
) -> Path:
    """
    Exporta la hoja CartAdcnl como CSV.

    Replica la exportación que hace la macro VBA:
    ``Z:\\RF_PROCESOS\\RF_Modelos\\CARTERA_ADICIONAL\\{YYYYMMDD}_Modelo_Inversiones.CSV``

    Args:
        df_cart_adcnl: DataFrame con la cartera adicional (54 cols).
        fecha_proceso: Fecha de proceso.
        ruta_directorio: Directorio destino del CSV.
        verbose: Si True, muestra mensajes.

    Returns:
        Path del archivo CSV generado.
    """
    # Normalizar fecha
    if isinstance(fecha_proceso, int):
        fecha = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif isinstance(fecha_proceso, str):
        fecha = pd.to_datetime(fecha_proceso)
    else:
        fecha = fecha_proceso

    dia_proceso = fecha.strftime('%Y%m%d')
    nombre_archivo = f"{dia_proceso}_Modelo_Inversiones.CSV"
    ruta = Path(ruta_directorio) / nombre_archivo

    if verbose:
        print(f"\n  Exportando CSV cartera adicional: {nombre_archivo}")

    # Crear directorio si no existe
    ruta.parent.mkdir(parents=True, exist_ok=True)

    df_cart_adcnl.to_csv(ruta, index=False, encoding='latin-1')

    if verbose:
        print(f"    ✓ CSV generado: {ruta}")
        print(f"      {len(df_cart_adcnl):,} filas, {len(df_cart_adcnl.columns)} columnas")

    return ruta
