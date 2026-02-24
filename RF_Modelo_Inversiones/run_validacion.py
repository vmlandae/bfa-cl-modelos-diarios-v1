import argparse
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

from RF_Modelo_Inversiones.io import (
    cargar_tablas_ml_inversiones,
    DataSourceMode,
    genera_tabla_RF_base_Completa_Hist,
)
from RF_Modelo_Inversiones.pipeline.cartera import genera_cartera_inv
from RF_Modelo_Inversiones.pipeline.orquestador import generar_flujo_liquidacion_instrumento
from RF_Modelo_Inversiones.output.tabla_final import ejecutar_pasos_20_a_27
from RF_Modelo_Inversiones.ml_inversiones import ejecutar_maestro_inversiones
from config import config_rutas as cr


def parse_args():
    parser = argparse.ArgumentParser(
        description='Validación del Modelo de Inversiones',
        epilog="""Ejemplo de uso:
  python -m RF_Modelo_Inversiones.run_validacion --fecha 2026-02-11
        """
    )
    parser.add_argument(
        '--fecha', type=str, required=True,
        help='Fecha de proceso (YYYY-MM-DD)')
    parser.add_argument(
        '--forzar-recarga', action='store_true',
        help='Ignorar caché parquet y leer directamente de Access')
    return parser.parse_args()


def main():
    args = parse_args()
    fecha_dt = datetime.strptime(args.fecha, '%Y-%m-%d')
    FECHA = int(fecha_dt.strftime('%Y%m%d'))

    OUTPUT_DIR = Path('RF_Modelo_Inversiones/output_validacion')
    OUTPUT_DIR.mkdir(exist_ok=True)

    # --- Paso 1: Carga LIVE ---
    print('=' * 70)
    print('PASO 1: Cargando datos LIVE...')
    tablas = cargar_tablas_ml_inversiones(
        fecha_proceso=FECHA, modo=DataSourceMode.LIVE,
        forzar_recarga=args.forzar_recarga, verbose=True)

    # --- Paso 2: Generar RF_base_Completa_Hist ---
    print('\nGenerando RF_base_Completa_Hist...')
    tablas['RF_base_Completa_Hist'] = genera_tabla_RF_base_Completa_Hist(
        tablas['RF_base_Completa_Hist_Input'], FECHA)
    print(f'  RF_base_Completa_Hist: {len(tablas["RF_base_Completa_Hist"]):,} filas')

    # --- Paso 3: Carteras ---
    print('\n' + '=' * 70)
    print('PASO 2: Generando carteras...')
    tabla_fecha = pd.DataFrame({'Fecha': [pd.to_datetime(str(FECHA), format='%Y%m%d')]})
    df_cartera_inv = genera_cartera_inv(tablas['RF_base_Completa_Hist'], tabla_fecha, 'disponible', verbose=True)
    df_cartera_pacto = genera_cartera_inv(tablas['RF_base_Completa_Hist'], tabla_fecha, 'pacto', verbose=True)

    # --- Paso 4: Flujos de liquidación ---
    print('\n' + '=' * 70)
    print('PASO 3: Generando flujos de liquidación...')
    MAPA_FACTORES = {
        'GobCLP': 'RF_FactCLP_Gob', 'GobCLF': 'RF_FactCLF_Gob',
        'DPF': 'RF_FactCLP_Banc', 'BBC': 'RF_FactCLP_Banc',
        'DPR': 'RF_FactCLF_Banc', 'LCH': 'RF_FactCLF_Banc',
    }
    flujos = {}
    for inst, tabla_factores in MAPA_FACTORES.items():
        tablas_inst = {tabla_factores: tablas[tabla_factores], 'FPL': tablas['FPL'], 'RF_MontosLiq': tablas['RF_MontosLiq']}
        flujo, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv, df_cartera_pacto, tablas_inst, inst, FECHA, verbose=False)
        flujos[inst] = flujo
        total = flujo['Monto_Liquidar'].sum() if 'Monto_Liquidar' in flujo.columns else 0
        print(f'  {inst}: {len(flujo)} dias, Monto: {total:,.0f}')

    # --- Paso 5: Pasos 20-27 ---
    print('\n' + '=' * 70)
    print('PASO 4: Ejecutando pasos 20-27...')
    tablas_input = {
        'RF_Base_Diaria_Precios': tablas['RF_Base_Diaria_Precios'],
        'RF_base_Completa_Hist': tablas['RF_base_Completa_Hist'],
        'RF_base_Completa_Hist_Input': tablas['RF_base_Completa_Hist_Input'],
    }
    resultado = ejecutar_pasos_20_a_27(
        flujos=flujos, tablas=tablas_input, fecha_proceso=FECHA,
        df_cartera_inv_pacto=df_cartera_pacto, verbose=True)

    print(f'\n  tabla_desarrollo: {len(resultado["tabla_desarrollo"]):,} filas')
    print(f'  tabla_excel:      {len(resultado["tabla_excel"]):,} filas')

    # --- Paso 6: Maestro ---
    print('\n' + '=' * 70)
    print('PASO 5: Ejecutando Maestro...')
    ruta_excel = OUTPUT_DIR / f'{FECHA}_Modelo de Inversiones.xlsx'
    ruta_csv = OUTPUT_DIR

    # Ruta al balance para cuadratura (desde config YAML)
    with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as f:
        config_ext = yaml.safe_load(f)
    ruta_balance = cr.resolver_ruta(
        config_ext['modelos']['ml_inversiones']['ruta_balance'])

    maestro = ejecutar_maestro_inversiones(
        resultados_pasos_20_27=resultado,
        fecha_proceso=fecha_dt,
        ruta_output_excel=ruta_excel,
        ruta_csv_cartera_adicional=ruta_csv,
        ruta_balance=ruta_balance,
        verbose=True)

    print('\n' + '=' * 70)
    print('RESULTADO FINAL')
    print('=' * 70)
    print(f'  Excel: {maestro["ruta_excel"]}')
    print(f'  CSV:   {maestro["ruta_csv"]}')
    print(f'  Flujo CLP total: {maestro["flujo_clp_total"]:,.0f}')
    print(f'  Monto contable:  {maestro["monto_contable"]:,.0f}')
    print(f'  Diferencia:      {maestro["diferencia"]:,.0f}')
    print('  DONE!')


if __name__ == '__main__':
    main()
