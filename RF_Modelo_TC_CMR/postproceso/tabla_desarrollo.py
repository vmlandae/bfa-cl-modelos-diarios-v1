"""
Postproceso: mapeo de flujos calculados al schema DESARROLLO para BigQuery.

Agrega PAGO_EST por FECHIX y mapea a las 31 columnas del schema base
del repositorio (crear_esquema_base en cargar_output_modelos_bigquery_dly.py).
"""

import pandas as pd
import numpy as np
from datetime import datetime


def generar_tabla_desarrollo(
    flujos_df: pd.DataFrame,
    fecha_proceso: datetime
) -> pd.DataFrame:
    """
    Genera la tabla DESARROLLO a partir de los flujos calculados en Fase 2.

    Agrega PAGO_EST por FECHIX y mapea a las 31 columnas del schema base.

    Args:
        flujos_df: DataFrame de salida de calcular_flujos (17 cols incluyendo PAGO_EST)
        fecha_proceso: Fecha de proceso

    Returns:
        DataFrame con 31 columnas del schema DESARROLLO
    """
    print("        - Agregando PAGO_EST por FECHIX...")

    # Agregar PAGO_EST por fecha (FECHIX) para obtener un flujo por dia
    flujos_agg = flujos_df.groupby('FECHIX', as_index=False).agg({
        'PAGO_EST': 'sum'
    })

    num_registros = len(flujos_agg)
    print(f"          Registros agregados: {num_registros:,}")

    print("        - Construyendo tabla DESARROLLO...")

    tabla_desarrollo = pd.DataFrame({
        "FECHA_PROCESO": [fecha_proceso] * num_registros,
        "CODIGO_EMPRESA": [1] * num_registros,
        "OPERACION": [np.nan] * num_registros,
        "COD_ACT/PAS": ["ACT"] * num_registros,
        "MONEDA_ORIGEN": ["CLP"] * num_registros,
        "MONEDA_COMPENSACION": ["CLP"] * num_registros,
        "COMPENSACION": [np.nan] * num_registros,
        "CODIGO_PRODUCTO": ["ML_TC_CMR_Ingreso"] * num_registros,
        "CODIGO_SUBPRODUCTO": ["ML_TC_CMR_Ingreso"] * num_registros,
        "FECHA_CREACION": [np.nan] * num_registros,
        "NUMERO_CUOTA": [np.nan] * num_registros,
        "FECHA_INICIO_CUOTA": [np.nan] * num_registros,
        "FECHA_VENCIMIENTO_CUOTA": flujos_agg['FECHIX'].values,
        "FECHA_PAGO": flujos_agg['FECHIX'].values,
        "FECHA_REPRICING": flujos_agg['FECHIX'].values,
        "AMORTIZACION": flujos_agg['PAGO_EST'].abs().values,
        "INTERES": [np.nan] * num_registros,
        "INTERES_DEVENGADO": [np.nan] * num_registros,
        "VP_AMORTIZACION": [np.nan] * num_registros,
        "VP_INTERES": [np.nan] * num_registros,
        "FACTOR_DE_RIESGO": [np.nan] * num_registros,
        "TIPO_CUOTA": [1] * num_registros,
        "AREA_NEGOCIO": ["BALANCE TASAS"] * num_registros,
        "CODIGO_EJECUTIVO": [np.nan] * num_registros,
        "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * num_registros,
        "CLASIFICACION_CONTABLE": ["HTM"] * num_registros,
        "TIPO_TASA": [1] * num_registros,
        "INDEXADOR": [np.nan] * num_registros,
        "TASA": [np.nan] * num_registros,
        "TASA_CF": [np.nan] * num_registros,
        "SPREAD": [np.nan] * num_registros,
    })

    print(f"          Tabla DESARROLLO: {len(tabla_desarrollo):,} registros, "
          f"{len(tabla_desarrollo.columns)} columnas")

    return tabla_desarrollo
