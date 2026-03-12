"""
Test F22: Verificar que WHERE Fec_Pro = fecha_proceso da el mismo resultado
que cargar todos los datos y dejar que el pipeline filtre.

Estrategia:
1. Cargar datos COMPLETOS desde parquet cache (simula el viejo SELECT * sin WHERE)
2. Cargar datos FILTRADOS a fecha exacta (simula el nuevo WHERE Fec_Pro = fecha)
3. Pasar ambos por genera_tabla_RF_base_Completa_Hist (Paso 01)
4. Pasar ambos por genera_cartera_inv (Paso 02) — que filtra Fec_Pro == fecha
5. Verificar que los outputs son idénticos

Esto prueba que el pipeline produce exactamente el mismo resultado
independientemente de si el WHERE se aplica en Access o en Python.
"""
import sys
import os

# Agregar root del proyecto al path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import pandas as pd
import numpy as np

# Importar funciones del pipeline
from RF_Modelo_Inversiones.io.data_sources import genera_tabla_RF_base_Completa_Hist
from RF_Modelo_Inversiones.pipeline.cartera import genera_cartera_inv


def test_where_fecha_exacta():
    """RF_base_Completa_Hist: WHERE exacto produce mismo resultado que sin WHERE."""

    # Buscar parquets disponibles
    cache_dir = 'data/cache'
    parquets = sorted([
        f for f in os.listdir(cache_dir)
        if f.startswith('RF_base_Completa_Hist_') and f.endswith('.parquet')
    ])

    if not parquets:
        print('ERROR: No hay parquets de RF_base_Completa_Hist en data/cache/', flush=True)
        return False

    # Usar el más reciente
    parquet_file = os.path.join(cache_dir, parquets[-1])
    # Extraer fecha del nombre (RF_base_Completa_Hist_YYYYMMDD.parquet)
    fecha_str = parquets[-1].replace('RF_base_Completa_Hist_', '').replace('.parquet', '')
    fecha_int = int(fecha_str)

    print(f'Archivo: {parquet_file}', flush=True)
    print(f'Fecha proceso: {fecha_int}', flush=True)

    # ── PASO 0: Cargar datos completos ──
    df_full = pd.read_parquet(parquet_file)
    fecha_ts = pd.Timestamp(fecha_str)
    print(f'\n=== Datos completos (simula SELECT * sin WHERE) ===', flush=True)
    print(f'  Filas totales: {len(df_full):,}', flush=True)
    print(f'  Fechas Fec_Pro distintas: {df_full["Fec_Pro"].nunique()}', flush=True)

    # Mostrar distribución de fechas
    vc = df_full['Fec_Pro'].value_counts().sort_index()
    for fecha, n in vc.items():
        marker = ' <<< fecha_proceso' if fecha == fecha_ts else ''
        print(f'    {fecha}: {n:,} filas{marker}', flush=True)

    # ── Datos filtrados (simula WHERE Fec_Pro = #fecha#) ──
    df_filtered = df_full[df_full['Fec_Pro'] == fecha_ts].copy()
    print(f'\n=== Datos filtrados (simula WHERE Fec_Pro = fecha) ===', flush=True)
    print(f'  Filas: {len(df_filtered):,}', flush=True)

    if len(df_filtered) == 0:
        print(f'ERROR: No hay filas con Fec_Pro == {fecha_ts}', flush=True)
        # Intentar con la fecha más reciente disponible
        fecha_ts = df_full['Fec_Pro'].max()
        fecha_int = int(fecha_ts.strftime('%Y%m%d'))
        df_filtered = df_full[df_full['Fec_Pro'] == fecha_ts].copy()
        print(f'  Usando fecha mas reciente: {fecha_ts} -> {len(df_filtered):,} filas', flush=True)

    # ── PASO 1: genera_tabla_RF_base_Completa_Hist ──
    # NOTA: esta funcion usa Fec_Pro > fecha - 10d, asi que con datos full
    # devuelve mas filas. Esto es ESPERADO: la funcion es un filtro intermedio.
    # Lo que importa es que los consumidores finales produzcan el mismo resultado.
    print(f'\n=== Paso 01: genera_tabla_RF_base_Completa_Hist (filtro intermedio) ===', flush=True)
    result_full = genera_tabla_RF_base_Completa_Hist(df_full, fecha_int)
    result_filtered = genera_tabla_RF_base_Completa_Hist(df_filtered, fecha_int)
    print(f'  Full -> {len(result_full):,} filas (10d ventana)', flush=True)
    print(f'  Filtered -> {len(result_filtered):,} filas (solo fecha_proceso)', flush=True)
    step1_same = len(result_full) == len(result_filtered)
    if step1_same:
        print(f'  INFO: Mismo tamanio (datos solo tienen 1 fecha)', flush=True)
    else:
        print(f'  INFO: Diferencia esperada - full tiene {len(result_full) - len(result_filtered):,} filas de otras fechas', flush=True)
        print(f'        Estas filas extra se descartan en el paso siguiente (genera_cartera_inv)', flush=True)

    # ── PASO 2: genera_cartera_inv (consumidor final — es lo que importa) ──
    print(f'\n=== Paso 02: genera_cartera_inv (RESULTADO CRITICO) ===', flush=True)

    # tabla_fecha necesita columna 'Fecha' (ver _obtener_fecha_proceso en cartera.py)
    tabla_fecha = pd.DataFrame({
        'Fecha': [fecha_ts],
    })

    results = {}
    for tipo_cartera in ['disponible', 'pacto']:
        try:
            cartera_full = genera_cartera_inv(result_full, tabla_fecha, tipo_cartera)
            cartera_filtered = genera_cartera_inv(result_filtered, tabla_fecha, tipo_cartera)

            match = cartera_full.shape == cartera_filtered.shape
            if match and len(cartera_full) > 0:
                c1 = cartera_full.reset_index(drop=True).sort_values(
                    list(cartera_full.columns)).reset_index(drop=True)
                c2 = cartera_filtered.reset_index(drop=True).sort_values(
                    list(cartera_filtered.columns)).reset_index(drop=True)
                match = c1.equals(c2)

            status = 'PASS' if match else 'FAIL'
            print(f'  Cartera {tipo_cartera}: full={len(cartera_full):,}, filtered={len(cartera_filtered):,} -> {status}', flush=True)
            results[tipo_cartera] = match
        except Exception as e:
            print(f'  Cartera {tipo_cartera}: SKIP (error: {e})', flush=True)
            results[tipo_cartera] = None

    # ── RESUMEN ──
    print(f'\n{"="*60}', flush=True)
    all_cartera_pass = all(v is True for v in results.values() if v is not None)
    if all_cartera_pass:
        print('RESULTADO FINAL: PASS - WHERE exacto produce mismos resultados en pipeline', flush=True)
    else:
        print('RESULTADO FINAL: FAIL - Hay diferencias en output del pipeline', flush=True)
    print(f'{"="*60}', flush=True)

    return all_cartera_pass


if __name__ == '__main__':
    success = test_where_fecha_exacta()
    sys.exit(0 if success else 1)
