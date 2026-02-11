"""
output/__init__.py - Exports para módulo de salida.

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧

Módulo para generación de tablas finales y formateo de salidas.
"""

from .tabla_final import (
    # Constantes
    COLUMNAS_TABLA_FINAL,
    COLUMNAS_TABLA_DESARROLLO,
    COLUMNAS_EXCEL_FINAL,
    MAPEO_COLUMNAS_EXCEL,
    CODIGO_EMPRESA,
    CODIGO_ACTIVO_PASIVO,
    CODIGO_PRODUCTO,
    UMBRAL_DIAS_PACTO,
    # Funciones principales
    formatear_flujo_instrumento,
    generar_cartera_garantias,
    generar_cartera_pactos,
    generar_monto_fuera_plazo_instrumento,
    generar_pactos_fuera_plazo_todos,
    generar_tabla_final_inversiones,
    # Funciones de integración
    generar_precios_dia,
    agregar_precio_y_flujo_clp,
    generar_tabla_desarrollo_completa,
    formatear_para_excel,
    ejecutar_pasos_20_a_27,
    # Funciones de extracción de carteras especiales
    extrae_cartera_ffmm,
    extraer_cartera_ffmm_para_tabla_desarrollo,
    extrae_cartera_htm,
    extraer_cartera_htm_para_tabla_desarrollo,
    extrae_cartera_rt,
    extraer_cartera_rt_para_tabla_desarrollo,
)

from .excel_writer import (
    generar_hoja_modelo_inversiones,
    generar_hoja_interfaz,
    generar_hoja_ml_access,
    aplicar_repasa_codigo_subproducto,
    exportar_excel_modelo_inversiones,
)

from .cartera_adicional import (
    COLUMNAS_CART_ADCNL,
    generar_hoja_cartera_adicional,
    exportar_csv_cartera_adicional,
)

__all__ = [
    # Constantes
    'COLUMNAS_TABLA_FINAL',
    'COLUMNAS_TABLA_DESARROLLO',
    'COLUMNAS_EXCEL_FINAL',
    'MAPEO_COLUMNAS_EXCEL',
    'CODIGO_EMPRESA',
    'CODIGO_ACTIVO_PASIVO',
    'CODIGO_PRODUCTO',
    'UMBRAL_DIAS_PACTO',
    'COLUMNAS_CART_ADCNL',
    # Funciones principales (tabla_final.py)
    'formatear_flujo_instrumento',
    'generar_cartera_garantias',
    'generar_cartera_pactos',
    'generar_monto_fuera_plazo_instrumento',
    'generar_pactos_fuera_plazo_todos',
    'generar_tabla_final_inversiones',
    # Funciones de integración (tabla_final.py)
    'generar_precios_dia',
    'agregar_precio_y_flujo_clp',
    'generar_tabla_desarrollo_completa',
    'formatear_para_excel',
    'ejecutar_pasos_20_a_27',
    # Funciones de extracción de carteras especiales
    'extrae_cartera_ffmm',
    'extraer_cartera_ffmm_para_tabla_desarrollo',
    'extrae_cartera_htm',
    'extraer_cartera_htm_para_tabla_desarrollo',
    'extrae_cartera_rt',
    'extraer_cartera_rt_para_tabla_desarrollo',
    # Funciones de escritura Excel (excel_writer.py)
    'generar_hoja_modelo_inversiones',
    'generar_hoja_interfaz',
    'generar_hoja_ml_access',
    'aplicar_repasa_codigo_subproducto',
    'exportar_excel_modelo_inversiones',
    # Funciones de cartera adicional (cartera_adicional.py)
    'generar_hoja_cartera_adicional',
    'exportar_csv_cartera_adicional',
]
