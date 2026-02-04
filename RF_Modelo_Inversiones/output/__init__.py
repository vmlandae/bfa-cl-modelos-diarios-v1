"""
output/__init__.py - Exports para módulo de salida.

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧

Módulo para generación de tablas finales y formateo de salidas.
"""

from .tabla_final import (
    # Constantes
    COLUMNAS_TABLA_FINAL,
    COLUMNAS_TABLA_DESARROLLO,
    MAPEO_COLUMNAS_EXCEL,
    CODIGO_EMPRESA,
    CODIGO_ACTIVO_PASIVO,
    CODIGO_PRODUCTO,
    # Funciones principales
    formatear_flujo_instrumento,
    generar_cartera_garantias,
    generar_cartera_pactos,
    generar_tabla_final_inversiones,
    # Funciones de integración
    generar_precios_dia,
    agregar_precio_y_flujo_clp,
    extraer_cartera_especial,
    generar_tabla_desarrollo_completa,
    formatear_para_excel,
)

__all__ = [
    # Constantes
    'COLUMNAS_TABLA_FINAL',
    'COLUMNAS_TABLA_DESARROLLO',
    'MAPEO_COLUMNAS_EXCEL',
    'CODIGO_EMPRESA',
    'CODIGO_ACTIVO_PASIVO',
    'CODIGO_PRODUCTO',
    # Funciones principales
    'formatear_flujo_instrumento',
    'generar_cartera_garantias',
    'generar_cartera_pactos',
    'generar_tabla_final_inversiones',
    # Funciones de integración
    'generar_precios_dia',
    'agregar_precio_y_flujo_clp',
    'extraer_cartera_especial',
    'generar_tabla_desarrollo_completa',
    'formatear_para_excel',
]
