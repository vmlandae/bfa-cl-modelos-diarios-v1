"""
Módulo pipeline para RF_Modelo_Inversiones.

Contiene funciones para el procesamiento del pipeline de liquidación:
- cartera: Generación de carteras (disponible/pacto)
- agregaciones: Funciones de agregación genéricas (GROUP BY + SUM)
- haircut: Cálculo de factores de haircut
- liquidacion: Cálculo de flujos de liquidación
- orquestador: Coordinación del pipeline completo

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧
"""

# Cartera
from .cartera import (
    genera_cartera_inv,
    genera_cartera_inv_001,  # Deprecado
    genera_cartera_inv_pacto,  # Deprecado
    FILTROS_CARTERA,
    PRODUCTOS_FONDOS_MUTUOS,
    COLUMNAS_BASE_SALIDA,
)

# Agregaciones
from .agregaciones import (
    agregar_por_columnas,
    generar_monto_total_instrumento as agregar_monto_total,
    generar_haircut_dia as agregar_haircut_dia,
    generar_monto_plazo_pacto,
    agregar_vp_flujo,
)

# Haircut
from .haircut import (
    generar_cartera_haircut,
    generar_haircut_dia,
    agregar_dia_semana,
    combinar_haircut_con_pactos,
    filtrar_monto_liquidar,
)

# Liquidación
from .liquidacion import (
    generar_cartera_instrumento,
    generar_cartera_pond,
    generar_monto_total_instrumento,
    calcular_flujo_liquidacion,
    monto_liq_gob_clp,  # Deprecado
    COLUMNAS_CARTERA_DISP,
    COLUMNAS_CARTERA_PACTO,
)

# Orquestador
from .orquestador import (
    generar_flujo_liquidacion_instrumento,
    listar_tipos_instrumento,
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
    'agregar_monto_total',
    'agregar_haircut_dia',
    'generar_monto_plazo_pacto',
    'agregar_vp_flujo',
    # Haircut
    'generar_cartera_haircut',
    'generar_haircut_dia',
    'agregar_dia_semana',
    'combinar_haircut_con_pactos',
    'filtrar_monto_liquidar',
    # Liquidación
    'generar_cartera_instrumento',
    'generar_cartera_pond',
    'generar_monto_total_instrumento',
    'calcular_flujo_liquidacion',
    'monto_liq_gob_clp',
    'COLUMNAS_CARTERA_DISP',
    'COLUMNAS_CARTERA_PACTO',
    # Orquestador
    'generar_flujo_liquidacion_instrumento',
    'listar_tipos_instrumento',
]
