"""
Modelo de Inversiones - Banco Falabella
========================================

Este módulo implementa el modelo de inversiones para el proceso diario
de Banco Falabella. Orquesta el pipeline completo:

1. Carga de datos (Access/pickle/BQ)
2. Pipeline de liquidación (27 pasos de Access → Python)
3. Generación de tabla final y tabla de desarrollo
4. Post-proceso "Maestro" (RepasaCodigoSubProducto, CartAdcnl, cuadratura)
5. Exportación a Excel ("Modelo de Inversiones.xlsx") y CSV

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
from config import config_rutas as cr  # Configuración de rutas del proyecto

# Importación de módulos del modelo de inversiones
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


# Carga de configuración desde archivo YAML
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# TODO: Configurar rutas específicas del modelo en config_rutas_ext_y_archivos.yaml
# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
# ARCHIVO_INPUT = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['ms_access_input'])
# RUTA_PARAMETROS = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['excel_parametros_input'])
# RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_inversiones']['excel_output'])



# =============================================================================
# POST-PROCESO "MAESTRO" (ActualizaModeloInversiones)
# =============================================================================

def ejecutar_maestro_inversiones(
    resultados_pasos_20_27: dict,
    fecha_proceso: datetime,
    ruta_output_excel: Path,
    ruta_csv_cartera_adicional: Path,
    ruta_balance: Path = None,
    verbose: bool = True,
) -> dict:
    """
    Orquesta el post-proceso del Maestro Modelo de Inversiones.

    Replica la macro ActualizaModeloInversiones del archivo
    "Maestro Modelo de Inversiones.xlsm". Toma los resultados de los
    pasos 20-27 (ya calculados) y genera:
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
        Dict con:
        - 'df_interfaz': Hoja INTERFAZ_MODELO_INVERSIONES
        - 'df_modelo_inversiones': Hoja MODELO_INVERSIONES
        - 'df_ml_access': Hoja ML_ACCESS
        - 'df_cart_adcnl': Hoja CartAdcnl
        - 'ruta_excel': Path del Excel generado
        - 'ruta_csv': Path del CSV generado
        - 'flujo_clp_total': Suma de Flujo_CLP
        - 'monto_contable': Monto contable del balance
        - 'diferencia': Diferencia modelo vs contable
    """
    if verbose:
        print("\n" + "=" * 60)
        print("POST-PROCESO: Maestro Modelo de Inversiones")
        print("=" * 60)

    resultado_maestro = {}

    # --- 1. Generar hoja MODELO_INVERSIONES (14 cols) ---
    if verbose:
        print("\n  [1/7] Generando hoja MODELO_INVERSIONES...")
    df_tabla_desarrollo = resultados_pasos_20_27['tabla_desarrollo']
    df_modelo_inv = generar_hoja_modelo_inversiones(df_tabla_desarrollo)
    resultado_maestro['df_modelo_inversiones'] = df_modelo_inv
    if verbose:
        print(f"    ✓ {len(df_modelo_inv):,} filas, {len(df_modelo_inv.columns)} columnas")

    # --- 2. Generar hoja ML_ACCESS (31 cols, sin RepasaCodigo) ---
    if verbose:
        print("\n  [2/7] Generando hoja ML_ACCESS...")
    df_tabla_excel = resultados_pasos_20_27['tabla_excel']
    df_ml_access = generar_hoja_ml_access(df_tabla_excel)
    resultado_maestro['df_ml_access'] = df_ml_access
    if verbose:
        print(f"    ✓ {len(df_ml_access):,} filas, {len(df_ml_access.columns)} columnas")

    # --- 3. Generar hoja INTERFAZ (31 cols, con RepasaCodigo) ---
    if verbose:
        print("\n  [3/7] Generando hoja INTERFAZ (RepasaCodigoSubProducto)...")
    df_interfaz = generar_hoja_interfaz(df_tabla_excel)
    resultado_maestro['df_interfaz'] = df_interfaz
    if verbose:
        n_reemplazados = (df_interfaz['CODIGO_SUBPRODUCTO'] != df_ml_access['CODIGO_SUBPRODUCTO']).sum()
        print(f"    ✓ {len(df_interfaz):,} filas, {n_reemplazados:,} códigos reemplazados")

    # --- 4. Generar hoja CartAdcnl (54 cols, códigos originales) ---
    # VBA: CarteraAdicional se ejecuta ANTES de RepasaCodigoSubProducto,
    # por lo que CartAdcnl usa los códigos originales (pre-RepasaCodigo).
    if verbose:
        print("\n  [4/7] Generando hoja CartAdcnl...")
    df_cart_adcnl = generar_hoja_cartera_adicional(df_ml_access)
    resultado_maestro['df_cart_adcnl'] = df_cart_adcnl
    if verbose:
        print(f"    ✓ {len(df_cart_adcnl):,} filas, {len(df_cart_adcnl.columns)} columnas")

    # --- 5. Exportar Excel ---
    if verbose:
        print("\n  [5/7] Exportando Excel...")
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
    if verbose:
        print("\n  [6/7] Exportando CSV cartera adicional...")
    ruta_csv = exportar_csv_cartera_adicional(
        df_cart_adcnl=df_cart_adcnl,
        fecha_proceso=fecha_proceso,
        ruta_directorio=ruta_csv_cartera_adicional,
        verbose=verbose,
    )
    resultado_maestro['ruta_csv'] = ruta_csv

    # --- 7. Cuadratura contra balance contable ---
    if verbose:
        print("\n  [7/7] Cuadratura modelo vs balance...")
    flujo_clp_total = sumar_flujo_clp(df_modelo_inv, verbose=verbose)
    resultado_maestro['flujo_clp_total'] = flujo_clp_total

    monto_contable = 0.0
    if ruta_balance is not None:
        monto_contable = obtener_monto_contable(ruta_balance, verbose=verbose)
    elif verbose:
        print("    ⚠ Ruta de balance no proporcionada, cuadratura omitida")
    resultado_maestro['monto_contable'] = monto_contable

    diferencia, _ = reportar_diferencia_modelo_vs_contable(
        flujo_clp_total, monto_contable, verbose=verbose)
    resultado_maestro['diferencia'] = diferencia

    if verbose:
        print("\n" + "=" * 60)
        print("POST-PROCESO COMPLETADO")
        print("=" * 60)

    return resultado_maestro


# =============================================================================
# FUNCIÓN PRINCIPAL DE EJECUCIÓN
# =============================================================================

def ejecutar_modelo(fecha_t: datetime) -> bool:
    """
    Función principal que orquesta la ejecución completa del modelo.

    TODO: Integrar con pipeline completo (Fase F).
    Por ahora, el flujo real se invoca llamando directamente a
    ejecutar_pasos_20_a_27() y luego ejecutar_maestro_inversiones().
    
    Args:
        fecha_t: Fecha de proceso en formato datetime
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso contrario
    """
    print("\n" + "=" * 60)
    print("INICIO MODELO DE INVERSIONES")
    print(f"Fecha de proceso: {fecha_t.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    try:
        # TODO: Fase F — integrar con pipeline completo:
        # 1. Carga de datos desde Access/BQ
        # 2. Pipeline de liquidación (pasos 1-19)
        # 3. ejecutar_pasos_20_a_27() → resultados
        # 4. ejecutar_maestro_inversiones(resultados, ...) → Excel + CSV + cuadratura
        # 5. Carga a GCP/BigQuery
        
        print("  ⚠ Pipeline completo aún no integrado.")
        print("  Use ejecutar_maestro_inversiones() directamente para el post-proceso.")
        
        print("\n" + "=" * 60)
        print("PROCESO FINALIZADO")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO DE INVERSIONES:")
        print(f"   {str(e)}")
        print("\n" + "=" * 60)
        print("PROCESO TERMINADO CON ERRORES")
        print("=" * 60)
        return False


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python ml_inversiones.py YYYY-MM-DD")
        sys.exit(1)
    
    fecha_proceso_str = sys.argv[1]
    
    try:
        fecha_proceso = datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)
    
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)
