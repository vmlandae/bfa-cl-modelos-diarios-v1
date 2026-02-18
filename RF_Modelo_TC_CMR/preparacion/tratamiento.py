"""
Clasificacion de registros de cartera CMR (TRATAMIENTO).

Clasifica cada cuota como N(ormal), R(eemplazo) o V(encido)
segun la diferencia de dias entre fecha de vencimiento y fecha de proceso.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from typing import Tuple


def calcular_corte(fecha_proceso: datetime) -> int:
    """
    Calcula CORTE segun la fecha de proceso.

    Equivalente VBA:
        =IF(AND(DAY(EOMONTH(R[-11]C,0))=31,DAY(R[-11]C)>=15),17,16)
    """
    ultimo_dia = calendar.monthrange(fecha_proceso.year, fecha_proceso.month)[1]
    dia_actual = fecha_proceso.day

    if ultimo_dia == 31 and dia_actual >= 15:
        return 17
    else:
        return 16


def tratamiento(
    df: pd.DataFrame,
    fecha_proceso: datetime,
    corte: int
) -> Tuple[pd.DataFrame, float, float]:
    """
    Aplica TRATAMIENTO a la cartera.

    Equivalente VBA: Sub TRATAMIENTO()

    Operaciones:
    1. Ordena por SISTEMA, CODIGO_EMPRESA, COD_ACT_PAS
    2. Marca OPERACION='O', DESTINOCREDITO='N'
    3. Elimina registros con CODIGO_PRODUCTO='TR'
    4. Calcula FF (dia de vencimiento) y RES (residual)
    5. Ordena por RES descendente
    6. Calcula FACTURACION (RES > 0 y <= CORTE) y marca como 'R'
    7. Calcula MONTO_MORA (RES <= 0) y marca como 'V'

    Returns:
        (df_tratado, monto_mora, facturacion)
    """
    print(f"        - Aplicando TRATAMIENTO (CORTE={corte})...")

    df = df.copy()
    filas_inicial = len(df)

    # 1. Ordenar por SISTEMA, CODIGO_EMPRESA, COD_ACT_PAS
    df = df.sort_values(
        ['SISTEMA', 'CODIGO_EMPRESA', 'COD_ACT_PAS']
    ).reset_index(drop=True)

    # Guardar indice de posicion para sort estable (replicar comportamiento Excel)
    df['_SORT_ORDER_'] = range(len(df))

    # 2. Marcar OPERACION='O', DESTINOCREDITO='N'
    df['OPERACION'] = 'O'
    df['DESTINOCREDITO'] = 'N'

    # 2b. Sobrescribir FECHA_CREACION con FECHA_PROCESO
    df['FECHA_CREACION'] = df['FECHA_PROCESO']

    # 3. Eliminar registros TR
    df = df[df['CODIGO_PRODUCTO'] != 'TR'].reset_index(drop=True)
    filas_sin_tr = len(df)
    print(f"        - Eliminados TR: {filas_inicial - filas_sin_tr:,} filas")

    # 4. Calcular FF (VENCIMIENTO) = ultimos 2 digitos de FECHA_VENCIMIENTO_CUOTA
    fvc_str = df['FECHA_VENCIMIENTO_CUOTA'].astype(str).str.strip()
    df['FF'] = pd.to_numeric(fvc_str.str[-2:], errors='coerce').fillna(0).astype(int)

    # 5. Calcular RES (RESIDUAL) = FECHA_VENCIMIENTO - FECHA_PROCESO
    fecha_venc = pd.to_datetime(fvc_str, format='%Y%m%d', errors='coerce')
    fecha_proc = pd.to_datetime(
        df['FECHA_PROCESO'].astype(str).str.strip(), format='%Y%m%d', errors='coerce'
    )
    df['RES'] = (fecha_venc - fecha_proc).dt.days.fillna(-100).astype(int)

    # 6. Ordenar por RES descendente, con sort estable via _SORT_ORDER_
    df = df.sort_values(
        ['RES', '_SORT_ORDER_'], ascending=[False, True]
    ).reset_index(drop=True)

    # Convertir AMORTIZACION e INTERES a numerico para calculos
    df['AMORTIZACION_NUM'] = pd.to_numeric(
        df['AMORTIZACION'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)
    df['INTERES_NUM'] = pd.to_numeric(
        df['INTERES'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    ).fillna(0)

    # 7. Calcular FACTURACION y marcar 'R'
    mask_facturacion = (df['RES'] > 0) & (df['RES'] <= corte)
    facturacion = (
        df.loc[mask_facturacion, 'AMORTIZACION_NUM'] +
        df.loc[mask_facturacion, 'INTERES_NUM']
    ).sum()
    df.loc[mask_facturacion, 'DESTINOCREDITO'] = 'R'

    # 8. Calcular MONTO_MORA y marcar 'V'
    mask_mora = df['RES'] <= 0
    monto_mora = (
        df.loc[mask_mora, 'AMORTIZACION_NUM'] +
        df.loc[mask_mora, 'INTERES_NUM']
    ).sum()
    df.loc[mask_mora, 'DESTINOCREDITO'] = 'V'

    # Limpiar columnas auxiliares
    df = df.drop(columns=['AMORTIZACION_NUM', 'INTERES_NUM', '_SORT_ORDER_'])

    conteo = df['DESTINOCREDITO'].value_counts()
    print(f"        - Clasificacion: N={conteo.get('N', 0):,} "
          f"R={conteo.get('R', 0):,} V={conteo.get('V', 0):,}")
    print(f"        - MONTO_MORA: {monto_mora:,.0f}")
    print(f"        - FACTURACION: {facturacion:,.0f}")

    return df, monto_mora, facturacion
