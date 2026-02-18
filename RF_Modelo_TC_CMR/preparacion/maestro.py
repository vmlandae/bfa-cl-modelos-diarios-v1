"""
Orquestacion Fase 1 (MAESTRO) del modelo TC CMR.

Coordina: cargar TXT -> TRATAMIENTO -> cargar T-30 -> asignar PP -> CSV output.
Genera tambien archivo de parametros de fechas de facturacion para el script R.
"""

import pandas as pd
import calendar
from pathlib import Path
from datetime import datetime
from typing import Dict

from .cargar_cartera import cargar_cartera_txt
from .tratamiento import calcular_corte, tratamiento
from .cargar_cartera_t30 import cargar_carteras_t30


# Columnas base del TXT original (36)
COLUMNAS_BASE = [
    'FECHA_PROCESO', 'SISTEMA', 'CODIGO_EMPRESA', 'OPERACION', 'COD_ACT_PAS',
    'MONEDA_ORIGEN', 'MONEDA_COMPENSACION', 'COMPENSACION', 'CODIGO_PRODUCTO',
    'CODIGO_SUBPRODUCTO', 'DESTINOCREDITO', 'FECHA_CREACION', 'NUMERO_CUOTA',
    'FECHA_INICIO_CUOTA', 'FECHA_VENCIMIENTO_CUOTA', 'FECHA_PAGO', 'FECHA_REPRICING',
    'AMORTIZACION', 'INTERES', 'INTERES_DEVENGADO', 'VP_AMORTIZACION', 'VP_INTERES',
    'FACTOR_DE_RIESGO', 'TIPO_CUOTA', 'AREA_NEGOCIO', 'CODIGO_EJECUTIVO',
    'CODIGO_ESTRATEGIA', 'CLASIFICACION_CONTABLE', 'TIPO_TASA', 'INDEXADOR',
    'TASA', 'TASA_CF', 'SPREAD', 'MAYORISTAMINORISTA', 'MARCA_CUMPLIMIENTO',
    'EMPRESA_RELACIONADA'
]

# Columnas calculadas/mapeadas (4)
COLUMNAS_CALCULADAS = ['PERFIL', 'FF', 'RES', 'PP']


def asignar_pp(df: pd.DataFrame, tabla_perfiles_pp: dict) -> pd.DataFrame:
    """
    Asigna PP usando VLOOKUP de PERFIL en tabla DIN.

    Equivalente VBA:
        =IFERROR(VLOOKUP(RC[-3],DIN!R1C9:R25C10,2,0),"P0")

    Args:
        tabla_perfiles_pp: dict {perfil_str: pp_str}, cargado desde tabla_perfiles_pp.csv
    """
    df = df.copy()
    df['PP'] = df['PERFIL'].map(tabla_perfiles_pp).fillna('P0')

    conteo_pp = df['PP'].value_counts().head(10)
    print(f"        - Top 10 PP asignados:")
    for pp, cnt in conteo_pp.items():
        print(f"            {pp}: {cnt:,}")

    return df


def generar_output_csv(
    df: pd.DataFrame,
    fecha_proceso: datetime,
    ruta_output: Path
) -> str:
    """
    Genera INPUT_TC-CMR_FAC_ANT.csv con la estructura correcta.

    Columnas finales (40):
    1-36: Columnas originales del TXT (hasta EMPRESA_RELACIONADA)
    37: PERFIL (= MODELO_PERFIL del TXT)
    38: FF (dia de vencimiento, calculado)
    39: RES (residual, calculado)
    40: PP (lookup de PERFIL)
    """
    print(f"        - Generando CSV de salida...")

    columnas_output = COLUMNAS_BASE + COLUMNAS_CALCULADAS

    columnas_disponibles = [c for c in columnas_output if c in df.columns]
    columnas_faltantes = [c for c in columnas_output if c not in df.columns]

    if columnas_faltantes:
        print(f"          [WARN] Columnas faltantes: {columnas_faltantes}")

    df_output = df[columnas_disponibles].copy()

    nombre_csv = 'INPUT_TC-CMR_FAC_ANT.csv'
    ruta_csv = ruta_output / nombre_csv

    ruta_csv.parent.mkdir(parents=True, exist_ok=True)

    df_output.to_csv(ruta_csv, sep=';', index=False, encoding='latin-1')

    print(f"          Archivo: {ruta_csv.name}")
    print(f"          Filas: {len(df_output):,}")
    print(f"          Columnas: {len(columnas_disponibles)}")

    return str(ruta_csv)


def calcular_fechas_facturacion(fecha_proceso: datetime) -> list:
    """
    Calcula las fechas de facturacion para cada dia de corte (5, 10, 15, 20, 25, 30).

    Para cada dia de facturacion:
    - Si dia_facturacion >= dia_proceso: usa el mes anterior
    - Si dia_facturacion < dia_proceso: usa el mes actual
    - Ajusta al ultimo dia del mes si el dia no existe (ej: 30 en febrero -> 28/29)
    """
    dias_facturacion = [5, 10, 15, 20, 25, 30]
    resultado = []

    dia_proceso = fecha_proceso.day
    mes_proceso = fecha_proceso.month
    ano_proceso = fecha_proceso.year

    for dia_fact in dias_facturacion:
        if dia_fact >= dia_proceso:
            # Mes anterior
            if mes_proceso == 1:
                mes = 12
                ano = ano_proceso - 1
            else:
                mes = mes_proceso - 1
                ano = ano_proceso
        else:
            # Mes actual
            mes = mes_proceso
            ano = ano_proceso

        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        dia_ajustado = min(dia_fact, ultimo_dia_mes)

        fecha_fact = datetime(ano, mes, dia_ajustado)
        resultado.append((fecha_fact.strftime('%Y%m%d'), f'{dia_fact:02d}'))

    return resultado


def crear_txt_ff(
    fecha_proceso: datetime,
    ruta_output: Path
) -> str:
    """
    Genera archivo de parametros de fechas de facturacion para script R.

    Equivalente VBA: Sub Crea_TXT_FF()

    Salida: {YYYYMMDD}_Parametros_FechasFacturacion_ModeloCMR.txt

    Contenido (7 lineas):
        FECHAFACTURACION;DIAFACT
        20251219;05
        ...
    """
    fecha_str = fecha_proceso.strftime('%Y%m%d')
    nombre_archivo = f"{fecha_str}_Parametros_FechasFacturacion_ModeloCMR.txt"

    ruta_previo_input = Path("Y:/RRFF-GCP/ModelosDiarios/Previo-Input")
    if ruta_previo_input.exists():
        ruta_ff = ruta_previo_input / nombre_archivo
    else:
        ruta_ff = ruta_output / nombre_archivo

    fechas_ff = calcular_fechas_facturacion(fecha_proceso)

    lineas = ['FECHAFACTURACION;DIAFACT']
    for fecha_fact, dia_fact in fechas_ff:
        lineas.append(f'{fecha_fact};{dia_fact}')

    ruta_ff.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_ff, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas))

    print(f"        - Parametros FF: {ruta_ff}")
    for linea in lineas:
        print(f"            {linea}")

    return str(ruta_ff)


def ejecutar_maestro(
    fecha_proceso: datetime,
    ruta_data_local: Path,
    tabla_perfiles_pp: dict,
    ruta_cartera_red: Path = None
) -> Dict:
    """
    Ejecuta el proceso MAESTRO completo.

    Equivalente VBA: Sub MAESTRO()

    Args:
        fecha_proceso: Fecha de proceso
        ruta_data_local: Directorio local con archivos copiados (data/)
        tabla_perfiles_pp: dict {perfil: pp} desde tabla_perfiles_pp.csv
        ruta_cartera_red: Ruta de red para buscar TXT (si data/ no tiene)

    Returns:
        dict con: exito, archivo_output, archivo_ff, total_registros,
                  monto_mora, facturacion, corte
    """
    print("      [1/5] Calculando CORTE...")
    corte = calcular_corte(fecha_proceso)
    print(f"            CORTE = {corte}")

    print("      [2/5] Cargando cartera TXT...")
    df = cargar_cartera_txt(fecha_proceso, ruta_data_local)

    print("      [3/5] Aplicando TRATAMIENTO...")
    df, monto_mora, facturacion = tratamiento(df, fecha_proceso, corte)

    print("      [4/5] Cargando carteras T-30...")
    df_t30 = cargar_carteras_t30(fecha_proceso, ruta_data_local)
    if len(df_t30) > 0:
        for col in df.columns:
            if col not in df_t30.columns:
                df_t30[col] = ''
        df = pd.concat([df, df_t30[df.columns]], ignore_index=True)
        print(f"        - Total combinado: {len(df):,} registros")

    # Sobrescribir FECHA_PROCESO de todos los registros
    fecha_proceso_str = fecha_proceso.strftime('%Y%m%d')
    df['FECHA_PROCESO'] = fecha_proceso_str

    # Renombrar MODELO_PERFIL a PERFIL
    if 'MODELO_PERFIL' in df.columns:
        df = df.rename(columns={'MODELO_PERFIL': 'PERFIL'})

    # Asignar PP
    print("      [5/5] Asignando PP...")
    df = asignar_pp(df, tabla_perfiles_pp)

    # Generar CSV
    ruta_csv = generar_output_csv(df, fecha_proceso, ruta_data_local)

    # Generar archivo de parametros FF
    ruta_ff = crear_txt_ff(fecha_proceso, ruta_data_local)

    return {
        'exito': True,
        'archivo_output': ruta_csv,
        'archivo_ff': ruta_ff,
        'total_registros': len(df),
        'monto_mora': monto_mora,
        'facturacion': facturacion,
        'corte': corte
    }
