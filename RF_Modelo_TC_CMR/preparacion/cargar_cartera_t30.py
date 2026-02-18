"""
Carga de carteras historicas T-30 para el modelo TC CMR.

Carga 6 carteras (una por cada dia de facturacion: 5, 10, 15, 20, 25, 30)
con registros que vencen dentro de 0-30 dias, para estimar revolventes.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Tuple

from .cargar_cartera import buscar_archivo_cartera


# Mapeo fijo de VENCIMIENTO a dia de FACTURACION (constantes del Excel)
VENCIMIENTO_A_FACTURACION = {
    5: 19,
    10: 24,
    15: 29,
    20: 4,
    25: 9,
    30: 14
}


def edate(fecha: datetime, meses: int) -> datetime:
    """Equivalente a EDATE de Excel: suma meses a una fecha."""
    return fecha + relativedelta(months=meses)


def calcular_fecha_requerida_t30(fecha_proceso: datetime, ff: int) -> datetime:
    """
    Calcula la fecha D (Requerido) para un FF dado.

    Formulas del Excel CREA_CARTERA_14P.xlsm:
    - D3 = EDATE(B3-DAY(B3)+1,-1)  -> Primer dia del mes anterior
    - D_row = IF(DAY($B$3)>=B_row, EDATE($D$3+B_row,1), EDATE($D$3+B_row,0))-1
    """
    dia_facturacion = VENCIMIENTO_A_FACTURACION.get(ff, ff)

    # D3 = Primer dia del mes anterior
    primer_dia_mes = fecha_proceso.replace(day=1)
    d3 = edate(primer_dia_mes, -1)

    # D3 + dia_facturacion dias
    d3_plus_fact = d3 + timedelta(days=dia_facturacion)

    dia_proceso = fecha_proceso.day

    if dia_proceso >= dia_facturacion:
        fecha_req = edate(d3_plus_fact, 1) - timedelta(days=1)
    else:
        fecha_req = edate(d3_plus_fact, 0) - timedelta(days=1)

    return fecha_req


def calcular_fechas_t30(
    fecha_proceso: datetime,
    ruta_cartera: Path = None
) -> List[Tuple[datetime, str]]:
    """
    Calcula las 6 fechas T-30 para cada dia de facturacion.

    Usa la misma logica del Excel CREA_CARTERA_14P.xlsm:
    - Calcula fecha requerida D
    - Busca archivo disponible en D, D+1, D+2... D+5 (fallback)

    Returns:
        Lista de tuplas (fecha_t30, ff_str) donde fecha_t30 es datetime
        y ff_str es '05','10', etc.
    """
    from .cargar_cartera import ajustar_dia_habil

    dias_ff = [5, 10, 15, 20, 25, 30]
    resultado = []

    for ff in dias_ff:
        fecha_req = calcular_fecha_requerida_t30(fecha_proceso, ff)

        fecha_disponible = None

        if ruta_cartera:
            for offset in range(6):  # 0, 1, 2, 3, 4, 5
                fecha_buscar = fecha_req + timedelta(days=offset)
                fecha_str = fecha_buscar.strftime('%Y%m%d')

                archivo = buscar_archivo_cartera(ruta_cartera, fecha_str)
                if archivo is not None:
                    fecha_disponible = fecha_buscar
                    break

        if fecha_disponible is None:
            fecha_disponible = fecha_req

        fecha_t30 = ajustar_dia_habil(fecha_disponible)
        resultado.append((fecha_t30, f'{ff:02d}'))

    return resultado


def tratamiento_mesmora(
    df: pd.DataFrame,
    fecha_proceso: datetime,
    ff: str,
    fecha_archivo_t30: str = None
) -> pd.DataFrame:
    """
    Aplica tratamiento para registros de cartera T-30.

    Equivalente VBA: Sub TRATAMIENTO_MESMORA(FF)

    1. Ordena por SISTEMA, CODIGO_EMPRESA, COD_ACT_PAS
    2. Elimina registros TR
    3. Calcula VENCIMIENTO y RESIDUAL
    4. Filtra: RESIDUAL entre 0 y 30, VENCIMIENTO = FF (o >=28 si FF=30)
    5. Marca OPERACION = 'A' y DESTINOCREDITO = 'A'
    6. Sobrescribe FECHA_CREACION con la fecha del archivo T-30
    """
    df = df.copy()

    # Ordenar
    df = df.sort_values(['SISTEMA', 'CODIGO_EMPRESA', 'COD_ACT_PAS'])

    # Eliminar TR
    df = df[df['SISTEMA'] != 'TR']

    # Calcular VENCIMIENTO (ultimos 2 digitos de FECHA_VENCIMIENTO_CUOTA)
    fvc_str = df['FECHA_VENCIMIENTO_CUOTA'].astype(str).str.strip()
    df['VENCIMIENTO'] = pd.to_numeric(fvc_str.str[-2:], errors='coerce').fillna(0).astype(int)

    # Calcular RESIDUAL usando vectorizacion
    fecha_venc = pd.to_datetime(fvc_str, format='%Y%m%d', errors='coerce')
    fecha_proc = pd.to_datetime(
        df['FECHA_PROCESO'].astype(str).str.strip(), format='%Y%m%d', errors='coerce'
    )
    df['RESIDUAL'] = (fecha_venc - fecha_proc).dt.days.fillna(-100).astype(int)

    # Filtrar por RESIDUAL (0 a 30)
    df = df[(df['RESIDUAL'] > 0) & (df['RESIDUAL'] <= 30)]

    # Filtrar por VENCIMIENTO
    ff_int = int(ff)
    if ff_int == 30:
        # Para FF=30, incluir tambien dias 28, 29, 30, 31
        df = df[df['VENCIMIENTO'] >= 28]
    else:
        df = df[df['VENCIMIENTO'] == ff_int]

    # Marcar como registros T-30
    df['OPERACION'] = 'A'
    df['DESTINOCREDITO'] = 'A'

    # Sobrescribir FECHA_CREACION con la fecha del archivo T-30
    if fecha_archivo_t30:
        df['FECHA_CREACION'] = fecha_archivo_t30

    # Asignar FF y RES para compatibilidad con estructura de salida
    df['FF'] = df['VENCIMIENTO']
    df['RES'] = df['RESIDUAL']

    return df


def cargar_carteras_t30(
    fecha_proceso: datetime,
    ruta_cartera: Path
) -> pd.DataFrame:
    """
    Carga las 6 carteras T-30 (una por cada dia de facturacion).

    Equivalente VBA: Loop que llama CARGA_INTERFAZ_DATOS_CMR_t_30 6 veces.

    Returns:
        DataFrame con todos los registros T-30 combinados
    """
    print("        - Cargando carteras T-30...")

    fechas_t30 = calcular_fechas_t30(fecha_proceso, ruta_cartera)
    dfs_t30 = []

    for fecha_t30, ff in fechas_t30:
        fecha_str = fecha_t30.strftime('%Y%m%d')
        ruta_archivo = buscar_archivo_cartera(ruta_cartera, fecha_str)

        nombre_mostrar = (
            ruta_archivo.name if ruta_archivo
            else f"ProductosMercadoLiquidezCMR{fecha_str}.TXT/txt"
        )
        print(f"          {nombre_mostrar} (FF={ff})")

        if ruta_archivo is None:
            print(f"          [WARN] Archivo no encontrado, saltando...")
            continue

        try:
            df_t30 = pd.read_csv(
                ruta_archivo,
                sep=';',
                encoding='latin-1',
                dtype=str,
                low_memory=False,
                na_values=[],
                keep_default_na=False
            )

            df_t30 = tratamiento_mesmora(df_t30, fecha_proceso, ff, fecha_str)

            if len(df_t30) > 0:
                dfs_t30.append(df_t30)
                print(f"          -> {len(df_t30):,} registros")

        except Exception as e:
            print(f"          [ERR] Error: {e}")

    if dfs_t30:
        df_combinado = pd.concat(dfs_t30, ignore_index=True)
        print(f"        - Total registros T-30: {len(df_combinado):,}")
        return df_combinado
    else:
        print(f"        - No se encontraron registros T-30")
        return pd.DataFrame()
