"""
Calculo de periodos de facturacion y expansion diaria para TC CMR.

Etapas:
1. Calcular FINI/FIFIN para cada registro (np.select vectorizado)
2. Expandir cada registro a nivel diario (date_range + explode)
"""

import pandas as pd
import numpy as np
from datetime import datetime


def crear_clave_diames_vectorizado(fechas: pd.Series) -> pd.Series:
    """
    Crea la clave dia_mes para lookup de factores (VECTORIZADO).
    Formato: "dia_mes" (ej: "15_1" para el 15 de enero)
    """
    return fechas.dt.day.astype(str) + "_" + fechas.dt.month.astype(str)


def agregar_periodos_facturacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula FINI y FIFIN para cada registro de la cartera.
    VERSION VECTORIZADA usando np.select (equivalente a dplyr::case_when).

    Args:
        df: DataFrame con columnas FVC y FF

    Returns:
        DataFrame con columnas FINI y FIFIN agregadas
    """
    print("        - Calculando periodos de facturacion...")

    df = df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df['FVC']):
        df['FVC'] = pd.to_datetime(df['FVC'])

    mes = df['FVC'].dt.month
    ff = df['FF'].astype(int)

    # ===== Calcular FINI (vectorizado con np.select) =====
    condiciones_fini = [
        ff < 15,
        (ff == 15) & (mes == 3),
        ff == 15,
        ff.isin([20, 25, 30]),
        ff == 28
    ]

    valores_fini = [
        df['FVC'] - pd.DateOffset(months=1) + pd.Timedelta(days=15),
        df['FVC'] - pd.DateOffset(months=1) + pd.Timedelta(days=14),
        df['FVC'] - pd.DateOffset(months=1) + pd.Timedelta(days=15),
        df['FVC'] - pd.Timedelta(days=15),
        df['FVC'] - pd.Timedelta(days=13)
    ]

    default_fini = df['FVC'] - pd.DateOffset(months=1) + pd.Timedelta(days=15)

    df['FINI'] = np.select(condiciones_fini, valores_fini, default=default_fini)
    df['FINI'] = pd.to_datetime(df['FINI'])

    # ===== Calcular FIFIN (vectorizado) =====
    condiciones_fifin = [
        ff < 15,
        (ff == 15) & (mes == 2),
        ff == 15,
        ff.isin([20, 25, 30]),
        ff == 28
    ]

    fvc_menos_15 = df['FVC'] - pd.Timedelta(days=15)
    fvc_menos_13 = df['FVC'] - pd.Timedelta(days=13)

    valores_fifin = [
        df['FVC'] + pd.Timedelta(days=14),
        df['FVC'] + pd.Timedelta(days=13),
        df['FVC'] + pd.Timedelta(days=14),
        fvc_menos_15 + pd.DateOffset(months=1) - pd.Timedelta(days=1),
        fvc_menos_13 + pd.DateOffset(months=1) - pd.Timedelta(days=1)
    ]

    default_fifin = df['FVC'] + pd.Timedelta(days=14)

    df['FIFIN'] = np.select(condiciones_fifin, valores_fifin, default=default_fifin)
    df['FIFIN'] = pd.to_datetime(df['FIFIN'])

    print(f"          Periodos calculados para {len(df):,} registros")

    return df


def expandir_a_diario(cartera: pd.DataFrame) -> pd.DataFrame:
    """
    Expande cada registro de la cartera a nivel diario.
    VERSION VECTORIZADA usando pd.date_range y explode.
    Equivalente a tidyr::unnest de R.

    Args:
        cartera: DataFrame con columnas FINI, FIFIN

    Returns:
        DataFrame expandido con una fila por dia (columna FECHIX)
    """
    print("        - Expandiendo flujos a nivel diario...")

    cartera = cartera.copy()

    cartera['FECHIX'] = list(map(
        lambda fini, fifin: pd.date_range(start=fini, end=fifin, freq='D').tolist(),
        cartera['FINI'],
        cartera['FIFIN']
    ))

    df_expandido = cartera.explode('FECHIX', ignore_index=True)
    df_expandido['FECHIX'] = pd.to_datetime(df_expandido['FECHIX'])

    print(f"          Flujos diarios: {len(df_expandido):,} filas")

    return df_expandido
