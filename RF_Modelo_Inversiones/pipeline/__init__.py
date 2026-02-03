"""
Módulo pipeline para RF_Modelo_Inversiones.

Contiene funciones para el procesamiento del pipeline de liquidación:
- cartera: Generación de carteras (disponible/pacto)
- agregaciones: Funciones de agregación genéricas (GROUP BY + SUM)
"""

from .cartera import (
    genera_cartera_inv,
    genera_cartera_inv_001,  # Deprecado
    genera_cartera_inv_pacto,  # Deprecado
    FILTROS_CARTERA,
    PRODUCTOS_FONDOS_MUTUOS,
    COLUMNAS_BASE_SALIDA,
)

from .agregaciones import (
    agregar_por_columnas,
    generar_monto_total_instrumento,
    generar_haircut_dia,
    generar_monto_plazo_pacto,
    agregar_vp_flujo,
)

__all__ = [
    # Cartera
    'genera_cartera_inv',
    'genera_cartera_inv_001',
    'genera_cartera_inv_pacto',
    'FILTROS_CARTERA',
    'PRODUCTOS_FONDOS_MUTUOS',
    'COLUMNAS_BASE_SALIDA',
    # Agregaciones
    'agregar_por_columnas',
    'generar_monto_total_instrumento',
    'generar_haircut_dia',
    'generar_monto_plazo_pacto',
    'agregar_vp_flujo',
]
