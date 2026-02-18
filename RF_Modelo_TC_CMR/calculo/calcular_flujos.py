"""
Calculo de flujos, revolventes y PAGO_EST para TC CMR.

Incluye:
- Carga de datos Fase 2 (CSV + Perfil_Factor)
- Factores por periodo desplazado
- Revolventes (REVOL1-4)
- Normalizacion de factores cuando SUMA_FACTORES > 1
- PAGO_EST = FLUJO_MES * FACTOR
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from .calcular_fechas import (
    crear_clave_diames_vectorizado,
    agregar_periodos_facturacion,
    expandir_a_diario
)


def cargar_datos_fase2(
    ruta_csv: Path,
    ruta_perfil_factor: Path,
    factor_ajuste: float = 0.9165
) -> tuple:
    """
    Carga los datos necesarios para Fase 2.

    1. Lee INPUT_TC-CMR_FAC_ANT.csv, filtra TC sin V/R, agrega por (FVC, PP, FF)
    2. Lee Perfil_Factor.csv (perfiles de pago)

    Args:
        ruta_csv: Ruta al CSV de salida de Fase 1
        ruta_perfil_factor: Ruta al archivo Perfil_Factor.csv
        factor_ajuste: Factor global de ajuste (default 0.9165)

    Returns:
        (cartera_agregada, perfiles, fecha_proceso)
    """
    print("        - Cargando CSV de Fase 1...")

    cartera = pd.read_csv(
        ruta_csv,
        sep=';',
        encoding='latin-1',
        low_memory=False
    )
    cartera.columns = cartera.columns.str.strip()

    fecha_str = str(cartera['FECHA_PROCESO'].iloc[0])
    fecha_proceso = datetime.strptime(fecha_str, '%Y%m%d')
    print(f"          Fecha proceso: {fecha_proceso.date()}")
    print(f"          Cartera original: {len(cartera):,} filas")

    # Filtrar: solo TC (codigo_producto = TC) y excluir destinos V/R
    cartera_filtrada = cartera[
        (cartera['CODIGO_PRODUCTO'] == 'TC') &
        (~cartera['DESTINOCREDITO'].isin(['V', 'R']))
    ].copy()

    print(f"          Cartera filtrada (TC, sin V/R): {len(cartera_filtrada):,} filas")

    # Convertir AMORTIZACION e INTERES a numerico
    cartera_filtrada['AMORTIZACION'] = pd.to_numeric(
        cartera_filtrada['AMORTIZACION'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)
    cartera_filtrada['INTERES'] = pd.to_numeric(
        cartera_filtrada['INTERES'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)

    # SALDO = AMORTIZACION + INTERES
    cartera_filtrada['SALDO'] = cartera_filtrada['AMORTIZACION'] + cartera_filtrada['INTERES']

    # Parsear FVC
    cartera_filtrada['FVC'] = pd.to_datetime(
        cartera_filtrada['FECHA_VENCIMIENTO_CUOTA'].astype(str),
        format='%Y%m%d'
    )

    # Asegurar FF es numerico
    cartera_filtrada['FF'] = pd.to_numeric(cartera_filtrada['FF'], errors='coerce').fillna(0).astype(int)

    # Agregar por (FVC, PP, FF)
    cartera_agregada = (
        cartera_filtrada
        .groupby(['FVC', 'PP', 'FF'], as_index=False)
        .agg({'SALDO': 'sum'})
    )

    # Aplicar factor de ajuste global
    cartera_agregada['SALDO'] = cartera_agregada['SALDO'] * factor_ajuste
    cartera_agregada = cartera_agregada.sort_values(['FVC', 'PP']).reset_index(drop=True)

    print(f"          Cartera agregada: {len(cartera_agregada):,} filas")

    # Cargar perfiles de pago
    print("        - Cargando Perfil_Factor.csv...")
    perfiles = pd.read_csv(
        ruta_perfil_factor,
        sep=';',
        decimal=',',
        encoding='latin-1'
    )
    perfiles.columns = perfiles.columns.str.strip()

    # Seleccionar y renombrar columnas relevantes
    # El CSV tiene columnas: DIAMES, PP, FACTOR (o similar)
    col_map = {}
    for col in perfiles.columns:
        col_upper = col.upper()
        if 'DIA' in col_upper and 'MES' in col_upper:
            col_map[col] = 'DIAMES'
        elif col_upper == 'PP' or 'PERFIL' in col_upper:
            col_map[col] = 'PP'
        elif 'FACTOR' in col_upper:
            col_map[col] = 'FACTOR'

    if col_map:
        perfiles = perfiles.rename(columns=col_map)

    perfiles_clean = perfiles[['DIAMES', 'PP', 'FACTOR']].copy()
    print(f"          Perfiles: {len(perfiles_clean):,} filas")

    return cartera_agregada, perfiles_clean, fecha_proceso


def calcular_suma_factores(flujos_diarios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la suma de factores por grupo FVC/PP/FF.
    Usa groupby().transform() para agregar sin cambiar el numero de filas.
    """
    flujos_diarios = flujos_diarios.copy()
    flujos_diarios['SUMA_FACTORES'] = flujos_diarios.groupby(
        ['FVC', 'PP', 'FF']
    )['FACTOR'].transform('sum')
    return flujos_diarios


def calcular_factores_periodo_desplazado(
    cartera_con_periodos: pd.DataFrame,
    perfiles: pd.DataFrame,
    meses_adelante: int
) -> pd.DataFrame:
    """
    Calcula la suma de factores para un periodo desplazado N meses.
    Desplaza FINI/FIFIN, expande a diario, hace join con perfiles.
    """
    nombre_col = f'SUMA_FACTORES_{meses_adelante}'

    cartera = cartera_con_periodos.copy()

    cartera['FINI_DESP'] = cartera['FINI'] + pd.DateOffset(months=meses_adelante)
    cartera['FIFIN_DESP'] = cartera['FIFIN'] + pd.DateOffset(months=meses_adelante)

    cartera['FECHAS_DESP'] = list(map(
        lambda fini, fifin: pd.date_range(start=fini, end=fifin, freq='D').tolist(),
        cartera['FINI_DESP'],
        cartera['FIFIN_DESP']
    ))

    expandido = cartera[['FVC', 'PP', 'FF', 'FECHAS_DESP']].explode(
        'FECHAS_DESP', ignore_index=True
    )
    expandido['FECHAS_DESP'] = pd.to_datetime(expandido['FECHAS_DESP'])

    expandido['DIAMES'] = crear_clave_diames_vectorizado(expandido['FECHAS_DESP'])

    perfiles_limpios = perfiles[['DIAMES', 'PP', 'FACTOR']].drop_duplicates(
        subset=['DIAMES', 'PP']
    )
    expandido = expandido.merge(perfiles_limpios, on=['DIAMES', 'PP'], how='left')
    expandido['FACTOR'] = expandido['FACTOR'].fillna(0)

    resultado = expandido.groupby(['FVC', 'PP', 'FF'])['FACTOR'].sum().reset_index()
    resultado.columns = ['FVC', 'PP', 'FF', nombre_col]

    return resultado


def calcular_revolventes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los montos revolventes (REVOL1-3) y el residual (REVOL4).
    Replica exactamente la logica de R.
    """
    df = df.copy()

    # Ajustar sumas de factores (maximo 1)
    df['SUM_FAC_PAG_ADJ'] = np.minimum(df['SUMA_FACTORES'], 1.0)
    df['SUM_FAC_PAG1_ADJ'] = np.minimum(df['SUMA_FACTORES_1'], 1.0)
    df['SUM_FAC_PAG2_ADJ'] = np.minimum(df['SUMA_FACTORES_2'], 1.0)
    df['SUM_FAC_PAG3_ADJ'] = np.minimum(df['SUMA_FACTORES_3'], 1.0)

    # Factores de revolving: si suma > 1, frevol = 0; sino frevol = 1 - suma
    df['FREVOL1'] = np.where(df['SUMA_FACTORES'] > 1, 0.0, 1 - df['SUMA_FACTORES'])
    df['FREVOL11'] = np.where(df['SUMA_FACTORES_1'] > 1, 0.0, 1 - df['SUMA_FACTORES_1'])
    df['FREVOL12'] = np.where(df['SUMA_FACTORES_2'] > 1, 0.0, 1 - df['SUMA_FACTORES_2'])
    df['FREVOL13'] = np.where(df['SUMA_FACTORES_3'] > 1, 0.0, 1 - df['SUMA_FACTORES_3'])

    # Montos revolventes
    df['REVOL1'] = df['SALDO'] * df['FREVOL1']
    df['REVOL2'] = df['REVOL1'] * df['FREVOL11']
    df['REVOL3'] = df['REVOL2'] * df['FREVOL12']

    # Residual no realocado
    df['REVOL4'] = df['REVOL1'] - (
        df['REVOL1'] * df['SUM_FAC_PAG1_ADJ'] +
        df['REVOL2'] * df['SUM_FAC_PAG2_ADJ'] +
        df['REVOL3'] * df['SUM_FAC_PAG3_ADJ']
    )
    df['REVOL4'] = np.maximum(df['REVOL4'], 0)

    return df


def crear_revolventes_futuros(cartera_rev: pd.DataFrame) -> pd.DataFrame:
    """
    Genera las filas que asignan los montos revolventes a fechas futuras.
    REV1 va al mes siguiente, REV2 a 2 meses, REV3 a 3 meses.
    """
    rev1 = cartera_rev[['FVC', 'PP', 'FF', 'REVOL1']].copy()
    rev1['FVC'] = rev1['FVC'] + pd.DateOffset(months=1)
    rev1 = rev1.rename(columns={'REVOL1': 'REV1'})
    rev1['REV2'] = 0.0
    rev1['REV3'] = 0.0

    rev2 = cartera_rev[['FVC', 'PP', 'FF', 'REVOL2']].copy()
    rev2['FVC'] = rev2['FVC'] + pd.DateOffset(months=2)
    rev2['REV1'] = 0.0
    rev2 = rev2.rename(columns={'REVOL2': 'REV2'})
    rev2['REV3'] = 0.0

    rev3 = cartera_rev[['FVC', 'PP', 'FF', 'REVOL3']].copy()
    rev3['FVC'] = rev3['FVC'] + pd.DateOffset(months=3)
    rev3['REV1'] = 0.0
    rev3['REV2'] = 0.0
    rev3 = rev3.rename(columns={'REVOL3': 'REV3'})

    return pd.concat([rev1, rev2, rev3], ignore_index=True)


def agregar_revolventes(revolventes_futuros: pd.DataFrame) -> pd.DataFrame:
    """Agrega revolventes por FVC/PP/FF."""
    return revolventes_futuros.groupby(['FVC', 'PP', 'FF']).agg({
        'REV1': 'sum',
        'REV2': 'sum',
        'REV3': 'sum'
    }).reset_index()


def crear_residuales(cartera_rev: pd.DataFrame) -> pd.DataFrame:
    """Genera las filas para los montos que se proyectan a 12 meses."""
    residuales = cartera_rev[['FVC', 'PP', 'FF', 'REVOL4']].copy()
    residuales['FVC'] = residuales['FVC'] + pd.DateOffset(months=12)
    residuales = residuales.rename(columns={'REVOL4': 'PAGO_EST'})
    return residuales


def calcular_flujos(
    cartera: pd.DataFrame,
    perfiles: pd.DataFrame,
    fecha_proceso: datetime
) -> pd.DataFrame:
    """
    Funcion principal que orquesta el calculo completo de flujos.
    Replica exactamente la logica del main.R de la version en R.
    """
    # Paso 1: Calcular periodos de facturacion
    print("        - Calculando periodos de facturacion...")
    cartera_con_periodos = agregar_periodos_facturacion(cartera)

    # Paso 2: Calcular factores para periodos desplazados (meses 1, 2, 3)
    print("        - Calculando factores para periodos futuros...")
    factores_mes1 = calcular_factores_periodo_desplazado(cartera_con_periodos, perfiles, 1)
    factores_mes2 = calcular_factores_periodo_desplazado(cartera_con_periodos, perfiles, 2)
    factores_mes3 = calcular_factores_periodo_desplazado(cartera_con_periodos, perfiles, 3)

    # Paso 3: Expandir a nivel diario y calcular factores del periodo actual
    flujos_diarios = expandir_a_diario(cartera_con_periodos)

    flujos_diarios['DIAMES'] = crear_clave_diames_vectorizado(flujos_diarios['FECHIX'])
    flujos_diarios['MONTO'] = flujos_diarios['SALDO']

    perfiles_unicos = perfiles.drop_duplicates(subset=['DIAMES', 'PP'])
    flujos_diarios = flujos_diarios.merge(perfiles_unicos, on=['DIAMES', 'PP'], how='left')
    flujos_diarios['FACTOR'] = flujos_diarios['FACTOR'].fillna(0)

    print("        - Calculando suma de factores...")
    flujos_diarios = calcular_suma_factores(flujos_diarios)
    print(f"          Flujos diarios: {len(flujos_diarios):,} filas")

    # Paso 4: Calcular revolventes
    print("        - Calculando revolventes...")

    cartera_con_factores = cartera_con_periodos.merge(
        flujos_diarios[['FVC', 'PP', 'FF', 'SUMA_FACTORES']].drop_duplicates(),
        on=['FVC', 'PP', 'FF'],
        how='left'
    )
    cartera_con_factores = cartera_con_factores.merge(factores_mes1, on=['FVC', 'PP', 'FF'], how='left')
    cartera_con_factores = cartera_con_factores.merge(factores_mes2, on=['FVC', 'PP', 'FF'], how='left')
    cartera_con_factores = cartera_con_factores.merge(factores_mes3, on=['FVC', 'PP', 'FF'], how='left')

    for col in ['SUMA_FACTORES', 'SUMA_FACTORES_1', 'SUMA_FACTORES_2', 'SUMA_FACTORES_3']:
        cartera_con_factores[col] = cartera_con_factores[col].fillna(0)

    cartera_rev = calcular_revolventes(cartera_con_factores)

    revolventes_futuros = crear_revolventes_futuros(cartera_rev)
    revolventes_agregados = agregar_revolventes(revolventes_futuros)

    residuales = crear_residuales(cartera_rev)

    # Paso 5: Ensamblar flujos finales
    print("        - Ensamblando flujos finales...")

    flujos_con_rev = flujos_diarios.merge(
        revolventes_agregados, on=['FVC', 'PP', 'FF'], how='left'
    )
    flujos_con_rev['REV1'] = flujos_con_rev['REV1'].fillna(0)
    flujos_con_rev['REV2'] = flujos_con_rev['REV2'].fillna(0)
    flujos_con_rev['REV3'] = flujos_con_rev['REV3'].fillna(0)

    # FLUJO_MES y PAGO_EST
    flujos_con_rev['FLUJO_MES'] = (
        flujos_con_rev['SALDO'] +
        flujos_con_rev['REV1'] +
        flujos_con_rev['REV2'] +
        flujos_con_rev['REV3']
    )
    flujos_con_rev['SUMAFACT'] = flujos_con_rev['SUMA_FACTORES']

    # Normalizar factor si suma > 1
    flujos_con_rev['FACTOR'] = np.where(
        flujos_con_rev['SUMA_FACTORES'] > 1,
        flujos_con_rev['FACTOR'] / flujos_con_rev['SUMA_FACTORES'],
        flujos_con_rev['FACTOR']
    )

    # Pago estimado
    flujos_con_rev['PAGO_EST'] = flujos_con_rev['FLUJO_MES'] * flujos_con_rev['FACTOR']

    # Paso 6: Preparar output final
    print("        - Preparando output final...")

    # Filtrar solo fechas >= fecha_proceso
    modelados = flujos_con_rev[flujos_con_rev['FECHIX'] >= fecha_proceso].copy()
    modelados['FPROCES'] = fecha_proceso
    modelados['RESIDUAL'] = (modelados['FECHIX'] - fecha_proceso).dt.days
    modelados['CLASIFIC'] = 'Modelado'

    # Residuales (no realocados)
    no_realocados = residuales.copy()
    no_realocados['FPROCES'] = fecha_proceso
    no_realocados['FECHIX'] = no_realocados['FVC']
    no_realocados['DIAMES'] = ''
    no_realocados['FACTOR'] = 0
    no_realocados['SUMAFACT'] = 0
    no_realocados['MONTO'] = 0
    no_realocados['SALDO'] = 0
    no_realocados['REV1'] = 0
    no_realocados['REV2'] = 0
    no_realocados['REV3'] = 0
    no_realocados['FLUJO_MES'] = 0
    no_realocados['RESIDUAL'] = 999
    no_realocados['CLASIFIC'] = 'NoRealocado'

    cols_output = [
        'FPROCES', 'FVC', 'FECHIX', 'PP', 'FF', 'DIAMES', 'FACTOR', 'SUMAFACT',
        'MONTO', 'SALDO', 'REV1', 'REV2', 'REV3', 'FLUJO_MES', 'PAGO_EST',
        'RESIDUAL', 'CLASIFIC'
    ]

    modelados_final = modelados[cols_output].copy()
    no_realocados_final = no_realocados[cols_output].copy()

    output_final = pd.concat([modelados_final, no_realocados_final], ignore_index=True)

    print(f"          Total flujos: {len(output_final):,} filas")

    return output_final


def ejecutar_calculo_flujos(
    ruta_csv: Path,
    ruta_perfil_factor: Path,
    fecha_proceso: datetime,
    factor_ajuste: float = 0.9165
) -> pd.DataFrame:
    """
    Entry point para Fase 2: carga datos y calcula flujos.

    Args:
        ruta_csv: Ruta al CSV de Fase 1 (INPUT_TC-CMR_FAC_ANT.csv)
        ruta_perfil_factor: Ruta a Perfil_Factor.csv
        fecha_proceso: Fecha de proceso
        factor_ajuste: Factor global de ajuste (default 0.9165)

    Returns:
        DataFrame con flujos calculados (17 columnas)
    """
    cartera, perfiles, _ = cargar_datos_fase2(
        ruta_csv, ruta_perfil_factor, factor_ajuste
    )

    flujos = calcular_flujos(cartera, perfiles, fecha_proceso)

    return flujos
