"""
Validación: output de ejecutar_maestro_inversiones() vs referencia Excel.

Compara celda a celda las 4 hojas generadas por Python contra el archivo
de producción 20260115_Modelo de Inversiones.xlsx.

Uso:
    python RF_Modelo_Inversiones/dev/validar_maestro_vs_referencia.py

Prerrequisitos:
    - Pickles de datos en PROCESOS_DIARIOS_MODELOS/data/external/ml_inversiones/
    - Archivo de referencia en dev/macros_excel/20260115_Modelo de Inversiones.xlsx
"""

import pandas as pd
import numpy as np
import pickle
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROCESOS_DIARIOS_PATH = BASE_DIR.parent / 'PROCESOS_DIARIOS_MODELOS'
DATA_PATH = PROCESOS_DIARIOS_PATH / 'data' / 'external' / 'ml_inversiones'
MACROS_DIR = Path(__file__).resolve().parent / 'macros_excel'
REFERENCIA_XLSX = MACROS_DIR / '20260115_Modelo de Inversiones.xlsx'

FECHA_PROCESO = 20260115
UMBRAL_TOLERANCIA = 1e-6  # Misma tolerancia usada en el notebook


# =============================================================================
# Paso 1: Cargar datos y ejecutar pipeline (replica notebook cells 2-33)
# =============================================================================

def ejecutar_pipeline_completo():
    """Ejecuta pasos 1-27 del pipeline replicando el notebook."""
    import importlib
    from RF_Modelo_Inversiones.io import cargar_tablas_ml_inversiones, DataSourceMode
    from RF_Modelo_Inversiones.pipeline.cartera import genera_cartera_inv
    from RF_Modelo_Inversiones.pipeline.orquestador import (
        generar_flujo_liquidacion_instrumento,
        listar_tipos_instrumento,
    )
    from RF_Modelo_Inversiones.output.tabla_final import ejecutar_pasos_20_a_27
    import RF_Modelo_Inversiones.dev.helpers as helpers
    importlib.reload(helpers)

    print("=" * 70)
    print("PASO 1: Cargando tablas...")
    print("=" * 70)
    tablas = cargar_tablas_ml_inversiones(
        fecha_proceso=FECHA_PROCESO,
        data_path=DATA_PATH,
        modo=DataSourceMode.PICKLE,
        verbose=True,
    )

    # Generar RF_base_Completa_Hist
    tablas['RF_base_Completa_Hist'] = helpers.genera_tabla_RF_base_Completa_Hist(
        tablas['RF_base_Completa_Hist_Input'], FECHA_PROCESO
    )
    print(f"  RF_base_Completa_Hist: {len(tablas['RF_base_Completa_Hist']):,} filas")

    # Carteras
    print("\n" + "=" * 70)
    print("PASO 2: Generando carteras...")
    print("=" * 70)
    tabla_fecha = pd.DataFrame(
        {'Fecha': [pd.to_datetime(str(FECHA_PROCESO), format='%Y%m%d')]}
    )
    df_cartera_inv = genera_cartera_inv(
        df_base=tablas['RF_base_Completa_Hist'],
        df_fecha=tabla_fecha,
        tipo='disponible',
        verbose=True,
    )
    df_cartera_pacto = genera_cartera_inv(
        df_base=tablas['RF_base_Completa_Hist'],
        df_fecha=tabla_fecha,
        tipo='pacto',
        verbose=True,
    )

    # Flujos de liquidación
    print("\n" + "=" * 70)
    print("PASO 3: Generando flujos de liquidación...")
    print("=" * 70)
    INSTRUMENTOS = ['GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH']
    flujos = {}
    for instrumento in INSTRUMENTOS:
        if instrumento in ['GobCLP']:
            tabla_factores = 'RF_FactCLP_Gob'
        elif instrumento in ['GobCLF']:
            tabla_factores = 'RF_FactCLF_Gob'
        elif instrumento in ['DPF', 'BBC']:
            tabla_factores = 'RF_FactCLP_Banc'
        else:
            tabla_factores = 'RF_FactCLF_Banc'

        tablas_inst = {
            tabla_factores: tablas[tabla_factores],
            'FPL': tablas['FPL'],
            'RF_MontosLiq': tablas['RF_MontosLiq'],
        }
        flujo, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_pacto,
            tablas=tablas_inst,
            tipo_instrumento=instrumento,
            fecha_proceso=FECHA_PROCESO,
            verbose=False,
        )
        flujos[instrumento] = flujo
        total = flujo['Monto_Liquidar'].sum() if 'Monto_Liquidar' in flujo.columns else 0
        print(f"  {instrumento}: {len(flujo)} días, Monto: {total:,.0f}")

    # Pasos 20-27
    print("\n" + "=" * 70)
    print("PASO 4: Ejecutando pasos 20-27...")
    print("=" * 70)
    tablas_input = {
        'RF_Base_Diaria_Precios': tablas['RF_Base_Diaria_Precios'],
        'RF_base_Completa_Hist': tablas['RF_base_Completa_Hist'],
        'RF_base_Completa_Hist_Input': tablas['RF_base_Completa_Hist_Input'],
    }
    resultado = ejecutar_pasos_20_a_27(
        flujos=flujos,
        tablas=tablas_input,
        fecha_proceso=FECHA_PROCESO,
        df_cartera_inv_pacto=df_cartera_pacto,
        verbose=True,
    )

    print(f"\n  tabla_desarrollo: {len(resultado['tabla_desarrollo']):,} filas")
    print(f"  tabla_excel:      {len(resultado['tabla_excel']):,} filas")

    return resultado


# =============================================================================
# Paso 2: Generar hojas del maestro
# =============================================================================

def generar_hojas_maestro(resultado_pipeline):
    """Genera las 4 hojas usando nuestro código."""
    from RF_Modelo_Inversiones.output.excel_writer import (
        generar_hoja_modelo_inversiones,
        generar_hoja_interfaz,
        generar_hoja_ml_access,
    )
    from RF_Modelo_Inversiones.output.cartera_adicional import (
        generar_hoja_cartera_adicional,
    )

    print("\n" + "=" * 70)
    print("PASO 5: Generando hojas del Maestro...")
    print("=" * 70)

    df_tabla_desarrollo = resultado_pipeline['tabla_desarrollo']
    df_tabla_excel = resultado_pipeline['tabla_excel']

    hojas = {}

    # MODELO_INVERSIONES (14 cols, códigos originales)
    hojas['MODELO_INVERSIONES'] = generar_hoja_modelo_inversiones(df_tabla_desarrollo)
    print(f"  MODELO_INVERSIONES: {len(hojas['MODELO_INVERSIONES']):,} filas x {len(hojas['MODELO_INVERSIONES'].columns)} cols")

    # ML_ACCESS (31 cols, códigos originales, pre-RepasaCodigo)
    hojas['ML_ACCESS'] = generar_hoja_ml_access(df_tabla_excel)
    print(f"  ML_ACCESS: {len(hojas['ML_ACCESS']):,} filas x {len(hojas['ML_ACCESS'].columns)} cols")

    # CartAdcnl (54 cols, códigos originales, pre-RepasaCodigo)
    hojas['CartAdcnl'] = generar_hoja_cartera_adicional(hojas['ML_ACCESS'])
    print(f"  CartAdcnl: {len(hojas['CartAdcnl']):,} filas x {len(hojas['CartAdcnl'].columns)} cols")

    # INTERFAZ (31 cols, códigos genéricos, post-RepasaCodigo)
    hojas['INTERFAZ_MODELO_INVERSIONES'] = generar_hoja_interfaz(df_tabla_excel)
    print(f"  INTERFAZ: {len(hojas['INTERFAZ_MODELO_INVERSIONES']):,} filas x {len(hojas['INTERFAZ_MODELO_INVERSIONES'].columns)} cols")

    return hojas


# =============================================================================
# Paso 3: Cargar referencia y comparar
# =============================================================================

def cargar_referencia():
    """Carga el archivo de referencia de producción."""
    print("\n" + "=" * 70)
    print(f"PASO 6: Cargando referencia: {REFERENCIA_XLSX.name}")
    print("=" * 70)

    hojas_ref = {}
    for nombre in ['INTERFAZ_MODELO_INVERSIONES', 'MODELO_INVERSIONES', 'ML_ACCESS', 'CartAdcnl']:
        df = pd.read_excel(REFERENCIA_XLSX, sheet_name=nombre)
        # Eliminar columnas completamente vacías (None headers)
        df = df.loc[:, df.columns.notna()]
        # Eliminar filas completamente vacías (residuo de t-1)
        df = df.dropna(how='all').reset_index(drop=True)
        hojas_ref[nombre] = df
        print(f"  {nombre}: {len(df):,} filas x {len(df.columns)} cols")

    return hojas_ref


def comparar_hoja(nombre, df_python, df_ref):
    """Compara celda a celda una hoja Python vs referencia."""
    print(f"\n{'─' * 70}")
    print(f"  COMPARANDO: {nombre}")
    print(f"{'─' * 70}")

    # Verificar dimensiones
    if df_python.shape != df_ref.shape:
        print(f"  ❌ DIMENSIONES DIFERENTES:")
        print(f"     Python: {df_python.shape[0]} filas x {df_python.shape[1]} cols")
        print(f"     Ref:    {df_ref.shape[0]} filas x {df_ref.shape[1]} cols")

        # Comparar columnas
        cols_py = set(df_python.columns)
        cols_ref = set(df_ref.columns)
        if cols_py != cols_ref:
            solo_py = cols_py - cols_ref
            solo_ref = cols_ref - cols_py
            if solo_py:
                print(f"     Solo en Python: {solo_py}")
            if solo_ref:
                print(f"     Solo en Ref: {solo_ref}")

        # Comparar headers en orden
        print(f"     Python cols: {list(df_python.columns)}")
        print(f"     Ref    cols: {list(df_ref.columns)}")
        return False

    # Verificar headers
    if list(df_python.columns) != list(df_ref.columns):
        print(f"  ❌ HEADERS DIFERENTES:")
        for i, (cp, cr) in enumerate(zip(df_python.columns, df_ref.columns)):
            if cp != cr:
                print(f"     Col {i}: Python='{cp}' vs Ref='{cr}'")
        return False

    print(f"  ✓ Dimensiones: {df_python.shape[0]} filas x {df_python.shape[1]} cols")
    print(f"  ✓ Headers coinciden")

    # Ordenar ambos DataFrames por columnas clave para comparación justa
    key_cols_map = {
        'MODELO_INVERSIONES': ['Cod_Sub_Pro', 'Moneda', 'Fec_Pago', 'Dias_Pago', 'Cap_Amort'],
        'INTERFAZ_MODELO_INVERSIONES': ['CODIGO_SUBPRODUCTO', 'MONEDA_ORIGEN', 'FECHA PAGO', 'AMORTIZACION'],
        'ML_ACCESS': ['CODIGO_SUBPRODUCTO', 'MONEDA_ORIGEN', 'FECHA PAGO', 'AMORTIZACION'],
        'CartAdcnl': ['Cod_Sub_Pro', 'Moneda', 'Fec_Pago', 'Cap_Amort'],
    }
    key_cols = key_cols_map.get(nombre, list(df_python.columns)[:5])
    df_python = df_python.sort_values(by=key_cols, ignore_index=True, na_position='last')
    df_ref = df_ref.sort_values(by=key_cols, ignore_index=True, na_position='last')
    print(f"  ✓ Ordenados por {key_cols}")

    # Comparar celda a celda
    total_celdas = df_python.size
    celdas_exactas = 0
    celdas_tolerancia = 0
    celdas_diferentes = 0
    errores = []

    for col in df_python.columns:
        for idx in df_python.index:
            val_py = df_python.at[idx, col]
            val_ref = df_ref.at[idx, col]

            # Ambos NaN/None
            if pd.isna(val_py) and pd.isna(val_ref):
                celdas_exactas += 1
                continue

            # Uno NaN y otro no
            if pd.isna(val_py) != pd.isna(val_ref):
                # Tratar 0 vs NaN como match cercano en ciertos campos
                if (pd.isna(val_py) and val_ref == 0) or (val_py == 0 and pd.isna(val_ref)):
                    celdas_tolerancia += 1
                    continue
                # Tratar '' vs None
                if (pd.isna(val_py) and val_ref == '') or (val_py == '' and pd.isna(val_ref)):
                    celdas_tolerancia += 1
                    continue
                celdas_diferentes += 1
                if len(errores) < 20:
                    errores.append((idx, col, val_py, val_ref, 'NaN mismatch'))
                continue

            # Exactamente iguales
            if val_py == val_ref:
                celdas_exactas += 1
                continue

            # Numéricos: tolerancia relativa
            try:
                num_py = float(val_py)
                num_ref = float(val_ref)
                if num_ref != 0:
                    diff_rel = abs(num_py - num_ref) / abs(num_ref)
                else:
                    diff_rel = abs(num_py - num_ref)

                if diff_rel <= UMBRAL_TOLERANCIA:
                    celdas_tolerancia += 1
                else:
                    celdas_diferentes += 1
                    if len(errores) < 20:
                        errores.append((idx, col, val_py, val_ref, f'diff_rel={diff_rel:.2e}'))
            except (ValueError, TypeError):
                # Strings u otros tipos
                if str(val_py).strip() == str(val_ref).strip():
                    celdas_tolerancia += 1
                else:
                    celdas_diferentes += 1
                    if len(errores) < 20:
                        errores.append((idx, col, val_py, val_ref, 'value mismatch'))

    pct_ok = (celdas_exactas + celdas_tolerancia) / total_celdas * 100

    print(f"\n  Total celdas:       {total_celdas:,}")
    print(f"  Exactamente iguales: {celdas_exactas:,}")
    print(f"  Dentro tolerancia:  {celdas_tolerancia:,}")
    print(f"  DIFERENTES:         {celdas_diferentes:,}")
    print(f"  Match:              {pct_ok:.4f}%")

    if errores:
        print(f"\n  Primeras {len(errores)} diferencias:")
        for idx, col, val_py, val_ref, motivo in errores:
            print(f"    Fila {idx}, '{col}': Python={val_py} | Ref={val_ref} ({motivo})")

    return celdas_diferentes == 0


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("VALIDACIÓN: Maestro Modelo Inversiones Python vs Referencia")
    print(f"Fecha proceso: {FECHA_PROCESO}")
    print(f"Referencia: {REFERENCIA_XLSX.name}")
    print("=" * 70)

    # Ejecutar pipeline completo
    resultado_pipeline = ejecutar_pipeline_completo()

    # Generar hojas
    hojas_python = generar_hojas_maestro(resultado_pipeline)

    # Cargar referencia
    hojas_ref = cargar_referencia()

    # Comparar cada hoja
    print("\n" + "=" * 70)
    print("RESULTADOS DE VALIDACIÓN")
    print("=" * 70)

    resultados = {}
    for nombre in ['INTERFAZ_MODELO_INVERSIONES', 'MODELO_INVERSIONES', 'ML_ACCESS', 'CartAdcnl']:
        ok = comparar_hoja(nombre, hojas_python[nombre], hojas_ref[nombre])
        resultados[nombre] = ok

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    todas_ok = True
    for nombre, ok in resultados.items():
        estado = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {estado}  {nombre}")
        if not ok:
            todas_ok = False

    if todas_ok:
        print("\n🎉 TODAS LAS HOJAS COINCIDEN CON LA REFERENCIA")
    else:
        print("\n⚠️  HAY DIFERENCIAS — revisar errores arriba")

    sys.exit(0 if todas_ok else 1)
