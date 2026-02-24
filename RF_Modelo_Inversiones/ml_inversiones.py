"""
Modelo de Inversiones - Banco Falabella
========================================

Orquesta el pipeline completo del modelo de inversiones:

1. Carga de datos (Access vía caché parquet + Excel parámetros)
2. Generación de RF_base_Completa_Hist filtrada
3. Generación de carteras (disponible y pacto)
4. Pipeline de liquidación por instrumento
5. Pasos 20-27 (tabla desarrollo + tabla excel)
6. Post-proceso Maestro (hojas Excel, CSV, cuadratura)

Ejecutable desde main.py vía orquestador:
    modelo.ejecutar_modelo(fecha_proceso)

Ejecutable directamente:
    python -m RF_Modelo_Inversiones.ml_inversiones --fecha 2026-02-19

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut

# Configuración de importación para ejecución directa
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importación de módulos internos
from config import config_rutas as cr

# Pipeline
from RF_Modelo_Inversiones.io import cargar_tablas_ml_inversiones, DataSourceMode
from RF_Modelo_Inversiones.pipeline.cartera import genera_cartera_inv
from RF_Modelo_Inversiones.pipeline.orquestador import generar_flujo_liquidacion_instrumento
from RF_Modelo_Inversiones.output.tabla_final import ejecutar_pasos_20_a_27
from RF_Modelo_Inversiones.output.excel_writer import (
    generar_hoja_modelo_inversiones,
    generar_hoja_interfaz,
    generar_hoja_ml_access,
    exportar_excel_modelo_inversiones,
)
from RF_Modelo_Inversiones.output.cartera_adicional import (
    generar_hoja_cartera_adicional,
    exportar_csv_cartera_adicional,
)
from RF_Modelo_Inversiones.pipeline.post_proceso import (
    sumar_flujo_clp,
    obtener_monto_contable,
    reportar_diferencia_modelo_vs_contable,
)
import RF_Modelo_Inversiones.dev.helpers as helpers


# Carga de configuración desde archivo YAML
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Rutas configuradas
RUTA_EXCEL_OUTPUT = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['excel_output'])
RUTA_CSV_OUTPUT = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['csv_output_dir'])
RUTA_BALANCE = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['ruta_balance'])

# Mapa de instrumentos → tabla de factores
MAPA_FACTORES = {
    'GobCLP': 'RF_FactCLP_Gob', 'GobCLF': 'RF_FactCLF_Gob',
    'DPF': 'RF_FactCLP_Banc', 'BBC': 'RF_FactCLP_Banc',
    'DPR': 'RF_FactCLF_Banc', 'LCH': 'RF_FactCLF_Banc',
}



# =============================================================================
# ETAPAS DEL PIPELINE
# =============================================================================

def cargar_datos(fecha_int: int, forzar_recarga: bool = False) -> dict:
    """
    [1/6] Carga datos desde Access (con caché parquet) y Excel.

    Args:
        fecha_int: Fecha de proceso como YYYYMMDD
        forzar_recarga: Si True, ignora caché y lee de Access

    Returns:
        Dict con todos los DataFrames necesarios
    """
    print("[1/6] Cargando datos...")
    tablas = cargar_tablas_ml_inversiones(
        fecha_proceso=fecha_int,
        modo=DataSourceMode.LIVE,
        forzar_recarga=forzar_recarga,
        verbose=True,
    )

    # Generar RF_base_Completa_Hist filtrada
    tablas['RF_base_Completa_Hist'] = helpers.genera_tabla_RF_base_Completa_Hist(
        tablas['RF_base_Completa_Hist_Input'], fecha_int)
    print(f"      ✓ RF_base_Completa_Hist: {len(tablas['RF_base_Completa_Hist']):,} filas")

    return tablas


def generar_carteras(tablas: dict, fecha_int: int) -> tuple:
    """
    [2/6] Genera carteras de inversión (disponible y pacto).

    Returns:
        (df_cartera_inv, df_cartera_pacto)
    """
    print("\n[2/6] Generando carteras...")
    tabla_fecha = pd.DataFrame({'Fecha': [pd.to_datetime(str(fecha_int), format='%Y%m%d')]})
    df_cartera_inv = genera_cartera_inv(
        tablas['RF_base_Completa_Hist'], tabla_fecha, 'disponible', verbose=True)
    df_cartera_pacto = genera_cartera_inv(
        tablas['RF_base_Completa_Hist'], tabla_fecha, 'pacto', verbose=True)
    return df_cartera_inv, df_cartera_pacto


def generar_flujos(tablas: dict, df_cartera_inv, df_cartera_pacto, fecha_int: int) -> dict:
    """
    [3/6] Genera flujos de liquidación por instrumento.

    Returns:
        Dict[instrumento, DataFrame flujo]
    """
    print("\n[3/6] Generando flujos de liquidación...")
    flujos = {}
    for inst, tabla_factores in MAPA_FACTORES.items():
        tablas_inst = {
            tabla_factores: tablas[tabla_factores],
            'FPL': tablas['FPL'],
            'RF_MontosLiq': tablas['RF_MontosLiq'],
        }
        flujo, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv, df_cartera_pacto, tablas_inst, inst, fecha_int, verbose=False)
        flujos[inst] = flujo
        total = flujo['Monto_Liquidar'].sum() if 'Monto_Liquidar' in flujo.columns else 0
        print(f"      {inst}: {len(flujo)} dias, Monto: {total:,.0f}")
    return flujos


def ejecutar_pipeline_tablas(flujos: dict, tablas: dict, fecha_int: int, df_cartera_pacto) -> dict:
    """
    [4/6] Ejecuta pasos 20-27 (tabla desarrollo + tabla excel).

    Returns:
        Dict con 'tabla_desarrollo' y 'tabla_excel'
    """
    print("\n[4/6] Ejecutando pasos 20-27...")
    tablas_input = {
        'RF_Base_Diaria_Precios': tablas['RF_Base_Diaria_Precios'],
        'RF_base_Completa_Hist': tablas['RF_base_Completa_Hist'],
        'RF_base_Completa_Hist_Input': tablas['RF_base_Completa_Hist_Input'],
    }
    resultado = ejecutar_pasos_20_a_27(
        flujos=flujos, tablas=tablas_input, fecha_proceso=fecha_int,
        df_cartera_inv_pacto=df_cartera_pacto, verbose=True)

    print(f"      ✓ tabla_desarrollo: {len(resultado['tabla_desarrollo']):,} filas")
    print(f"      ✓ tabla_excel:      {len(resultado['tabla_excel']):,} filas")
    return resultado


def ejecutar_maestro_inversiones(
    resultados_pasos_20_27: dict,
    fecha_proceso: datetime,
    ruta_output_excel: Path,
    ruta_csv_cartera_adicional: Path,
    ruta_balance: Path = None,
    verbose: bool = True,
) -> dict:
    """
    [5/6] Post-proceso Maestro: genera hojas Excel, CSV y cuadratura.

    Replica la macro ActualizaModeloInversiones del archivo
    "Maestro Modelo de Inversiones.xlsm". Toma los resultados de los
    pasos 20-27 y genera:
    1. Hoja MODELO_INVERSIONES (14 cols con Precio_Mid y Flujo_CLP)
    2. Hoja ML_ACCESS (31 cols, códigos de sub-producto originales)
    3. Hoja INTERFAZ (31 cols, con RepasaCodigoSubProducto aplicado)
    4. Hoja CartAdcnl (54 cols, cartera adicional expandida)
    5. Archivo Excel "Modelo de Inversiones.xlsx"
    6. Archivo CSV de cartera adicional
    7. Cuadratura contra balance contable

    Args:
        resultados_pasos_20_27: Dict retornado por ejecutar_pasos_20_a_27().
        fecha_proceso: Fecha de proceso.
        ruta_output_excel: Ruta del archivo Excel de salida.
        ruta_csv_cartera_adicional: Directorio para el CSV de cartera adicional.
        ruta_balance: Ruta al archivo RF_Generador_Balance_Carteras.xlsm (opcional).
        verbose: Si True, muestra mensajes de progreso.

    Returns:
        Dict con DataFrames de cada hoja, rutas, y métricas de cuadratura.
    """
    if verbose:
        print("\n[5/6] Post-proceso Maestro...")

    resultado_maestro = {}

    # --- 1. Generar hoja MODELO_INVERSIONES (14 cols) ---
    df_tabla_desarrollo = resultados_pasos_20_27['tabla_desarrollo']
    df_modelo_inv = generar_hoja_modelo_inversiones(df_tabla_desarrollo)
    resultado_maestro['df_modelo_inversiones'] = df_modelo_inv
    if verbose:
        print(f"      MODELO_INVERSIONES: {len(df_modelo_inv):,} filas")

    # --- 2. Generar hoja ML_ACCESS (31 cols, sin RepasaCodigo) ---
    df_tabla_excel = resultados_pasos_20_27['tabla_excel']
    df_ml_access = generar_hoja_ml_access(df_tabla_excel)
    resultado_maestro['df_ml_access'] = df_ml_access
    if verbose:
        print(f"      ML_ACCESS: {len(df_ml_access):,} filas")

    # --- 3. Generar hoja INTERFAZ (31 cols, con RepasaCodigo) ---
    df_interfaz = generar_hoja_interfaz(df_tabla_excel)
    resultado_maestro['df_interfaz'] = df_interfaz
    if verbose:
        n_reemplazados = (df_interfaz['CODIGO_SUBPRODUCTO'] != df_ml_access['CODIGO_SUBPRODUCTO']).sum()
        print(f"      INTERFAZ: {len(df_interfaz):,} filas, {n_reemplazados:,} códigos reemplazados")

    # --- 4. Generar hoja CartAdcnl (54 cols, códigos originales) ---
    df_cart_adcnl = generar_hoja_cartera_adicional(df_ml_access)
    resultado_maestro['df_cart_adcnl'] = df_cart_adcnl
    if verbose:
        print(f"      CartAdcnl: {len(df_cart_adcnl):,} filas")

    # --- 5. Exportar Excel ---
    ruta_excel = exportar_excel_modelo_inversiones(
        df_interfaz=df_interfaz,
        df_modelo_inversiones=df_modelo_inv,
        df_ml_access=df_ml_access,
        df_cart_adcnl=df_cart_adcnl,
        ruta_output=ruta_output_excel,
        verbose=verbose,
    )
    resultado_maestro['ruta_excel'] = ruta_excel

    # --- 6. Exportar CSV cartera adicional ---
    ruta_csv = exportar_csv_cartera_adicional(
        df_cart_adcnl=df_cart_adcnl,
        fecha_proceso=fecha_proceso,
        ruta_directorio=ruta_csv_cartera_adicional,
        verbose=verbose,
    )
    resultado_maestro['ruta_csv'] = ruta_csv

    # --- 7. Cuadratura contra balance contable ---
    if verbose:
        print("\n[6/6] Cuadratura modelo vs balance...")
    flujo_clp_total = sumar_flujo_clp(df_modelo_inv, verbose=verbose)
    resultado_maestro['flujo_clp_total'] = flujo_clp_total

    monto_contable = 0.0
    if ruta_balance is not None:
        monto_contable = obtener_monto_contable(ruta_balance, verbose=verbose)
    elif verbose:
        print("      ⚠ Ruta de balance no proporcionada, cuadratura omitida")
    resultado_maestro['monto_contable'] = monto_contable

    diferencia, _ = reportar_diferencia_modelo_vs_contable(
        flujo_clp_total, monto_contable, verbose=verbose)
    resultado_maestro['diferencia'] = diferencia

    return resultado_maestro


# =============================================================================
# FUNCIÓN PRINCIPAL — INTERFAZ CON ORQUESTADOR
# =============================================================================

def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """
    Ejecuta el pipeline completo del modelo de inversiones.

    Esta función es invocada por el orquestador (core/orquestador.py)
    vía importlib.import_module('RF_Modelo_Inversiones.ml_inversiones').ejecutar_modelo(fecha).

    Args:
        fecha_proceso: Fecha de proceso en formato datetime

    Returns:
        bool: True si la ejecución fue exitosa
    """
    try:
        print("\n" + "=" * 60)
        print("INICIO DEL PROCESO - MODELO DE INVERSIONES")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("=" * 60 + "\n")

        fecha_int = int(fecha_proceso.strftime('%Y%m%d'))
        forzar_recarga = os.environ.get('CACHE_FORZAR_RECARGA', '') == '1'

        # 1. Carga de datos
        tablas = cargar_datos(fecha_int, forzar_recarga=forzar_recarga)

        # 2. Carteras
        df_cartera_inv, df_cartera_pacto = generar_carteras(tablas, fecha_int)

        # 3. Flujos de liquidación
        flujos = generar_flujos(tablas, df_cartera_inv, df_cartera_pacto, fecha_int)

        # 4. Pasos 20-27
        resultado = ejecutar_pipeline_tablas(flujos, tablas, fecha_int, df_cartera_pacto)

        # 5-6. Maestro + cuadratura
        ruta_excel = Path(RUTA_EXCEL_OUTPUT)
        ruta_excel.parent.mkdir(parents=True, exist_ok=True)

        maestro = ejecutar_maestro_inversiones(
            resultados_pasos_20_27=resultado,
            fecha_proceso=fecha_proceso,
            ruta_output_excel=ruta_excel,
            ruta_csv_cartera_adicional=Path(RUTA_CSV_OUTPUT),
            ruta_balance=Path(RUTA_BALANCE) if RUTA_BALANCE else None,
            verbose=True,
        )

        # Resumen
        print("\n" + "=" * 60)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("=" * 60)
        print(f"  Excel:          {maestro['ruta_excel']}")
        print(f"  CSV:            {maestro['ruta_csv']}")
        print(f"  Flujo CLP:      {maestro['flujo_clp_total']:,.0f}")
        print(f"  Monto contable: {maestro['monto_contable']:,.0f}")
        print(f"  Diferencia:     {maestro['diferencia']:,.0f}")

        return True

    except Exception as e:
        print(f"\nERROR EN EL MODELO DE INVERSIONES:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("PROCESO TERMINADO CON ERRORES")
        print("=" * 60)
        return False


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Modelo de Inversiones - Pipeline completo',
        epilog='Ejemplo: python -m RF_Modelo_Inversiones.ml_inversiones --fecha 2026-02-19',
    )
    parser.add_argument('--fecha', type=str, required=True,
                        help='Fecha de proceso (YYYY-MM-DD)')
    parser.add_argument('--forzar-recarga', action='store_true',
                        help='Ignorar caché parquet y leer de Access')
    args = parser.parse_args()

    fecha_dt = datetime.strptime(args.fecha, '%Y-%m-%d')
    if args.forzar_recarga:
        os.environ['CACHE_FORZAR_RECARGA'] = '1'

    exito = ejecutar_modelo(fecha_dt)

    if not exito:
        sys.exit(1)
