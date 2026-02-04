"""
Módulo orquestador del pipeline de liquidación para RF_Modelo_Inversiones.

Este módulo coordina todo el pipeline de liquidación, invocando las funciones
de los módulos cartera, haircut y liquidación en el orden correcto.

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧

Uso:
    from RF_Modelo_Inversiones.pipeline.orquestador import (
        generar_flujo_liquidacion_instrumento,
    )
    
    flujo, queries = generar_flujo_liquidacion_instrumento(
        df_cartera_inv=df_cartera,
        df_cartera_inv_pacto=df_pactos,
        tablas=tablas_base,
        tipo_instrumento='GobCLP',
        fecha_proceso=20260131,
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import datetime
import pandas as pd
from typing import Dict, Tuple, Any, Union

# Imports desde módulos del pipeline
from .liquidacion import (
    generar_cartera_instrumento,
    generar_cartera_pond,
    generar_monto_total_instrumento,
    calcular_flujo_liquidacion,
    COLUMNAS_CARTERA_DISP,
    COLUMNAS_CARTERA_PACTO,
)
from .haircut import (
    generar_cartera_haircut,
    generar_haircut_dia,
    agregar_dia_semana,
    combinar_haircut_con_pactos,
    filtrar_monto_liquidar,
)
from .agregaciones import generar_monto_plazo_pacto

# Import de configuración centralizada
try:
    from ..config.instrumentos import (
        INSTRUMENTOS,
        obtener_instrumento,
        listar_instrumentos,
    )
    _CONFIG_DISPONIBLE = True
except ImportError:
    _CONFIG_DISPONIBLE = False
    # Fallback a configuración local si no está disponible
    INSTRUMENTOS = {}


# =============================================================================
# CONFIGURACIÓN DE INSTRUMENTOS (FALLBACK)
# =============================================================================
# Esta configuración se usa solo si config/instrumentos.py no está disponible.
# En producción, siempre debe usarse la configuración centralizada.

CONFIGURACION_INSTRUMENTOS_FALLBACK: Dict[str, Dict[str, Any]] = {
    'GobCLP': {
        'nombre_completo': 'Gobierno CLP',
        'codigos_disp': ['BCP', 'BTP', 'BCU', 'BTU'],
        'codigos_pacto': ['BCP', 'BTP', 'BCU', 'BTU'],
        'moneda': 'CLP',
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLP_Gob',
        'instrumento_fpl': 'Gobierno CLP',
        'instrumento_montos_liq': 'Gobierno CLP',
        'nombre_salida': 'Flujo_GobCLP',
        'cod_sub_pro_final': 'ML_C46_GobCLP',
    },
    'GobCLF': {
        'nombre_completo': 'Gobierno CLF',
        'codigos_disp': ['BCU', 'BTU'],
        'codigos_pacto': ['BCU', 'BTU', 'CER'],
        'moneda': 'CLF',
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLF_Gob',
        'instrumento_fpl': 'Gobierno UF',
        'instrumento_montos_liq': 'Gobierno UF',
        'nombre_salida': 'Flujo_GobCLF',
        'cod_sub_pro_final': 'ML_C46_GobCLF',
    },
    'DPF': {
        'nombre_completo': 'Depósitos a Plazo Fijo CLP',
        'codigos_disp': ['DPF'],
        'codigos_pacto': ['DPF', 'FFM'],
        'moneda': 'CLP',
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLP_Priv',
        'instrumento_fpl': 'Dep Plz Fijo CLP',
        'instrumento_montos_liq': 'Dep Plz Fijo CLP',
        'nombre_salida': 'Flujo_DPF',
        'cod_sub_pro_final': 'ML_C46_DPF',
    },
    'DPR': {
        'nombre_completo': 'Depósitos a Plazo Reajustable CLF',
        'codigos_disp': ['DPR'],
        'codigos_pacto': ['DPR'],
        'moneda': 'CLF',
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLF_Priv',
        'instrumento_fpl': 'Dep Plz Reaj UF',
        'instrumento_montos_liq': 'Dep Plz Reaj UF',
        'nombre_salida': 'Flujo_DPR',
        'cod_sub_pro_final': 'ML_C46_DPR',
    },
    'BBC': {
        'nombre_completo': 'Bonos Banco Central CLP',
        'codigos_disp': ['BBC', 'PDC'],
        'codigos_pacto': ['BBC', 'PDC'],
        'moneda': 'CLF',
        'filtro_moneda': 'CLP',  # BBC requiere filtro por moneda
        'tabla_factores': 'RF_FactCLP_Gob',
        'instrumento_fpl': 'BBC',
        'instrumento_montos_liq': 'BBC',
        'nombre_salida': 'Flujo_BBC',
        'cod_sub_pro_final': 'ML_C46_BBC',
    },
    'LCH': {
        'nombre_completo': 'Letras de Crédito Hipotecario',
        'codigos_disp': ['LCH', 'BBC'],
        'codigos_pacto': ['LCH', 'BBC'],
        'moneda': 'CLF',
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLF_Priv',
        'instrumento_fpl': ['LCH', 'BBC'],  # Múltiples instrumentos
        'instrumento_montos_liq': 'LCH',
        'nombre_salida': 'Flujo_LCH',
        'cod_sub_pro_final': 'ML_C46_LCH',
    },
}


def _obtener_config_instrumento(tipo_instrumento: str) -> Dict[str, Any]:
    """
    Obtiene la configuración del instrumento desde config/ o fallback.
    
    Prioriza la configuración centralizada de config/instrumentos.py.
    Si no está disponible, usa el fallback local.
    """
    if _CONFIG_DISPONIBLE and tipo_instrumento in INSTRUMENTOS:
        config = INSTRUMENTOS[tipo_instrumento]
        # Convertir dataclass a dict para compatibilidad
        return {
            'nombre_completo': config.nombre_completo,
            'codigos_disp': config.codigos_disp,
            'codigos_pacto': config.codigos_pacto,
            'moneda': config.moneda,
            'filtro_moneda': config.filtro_moneda,
            'tabla_factores': config.tabla_factores,
            'instrumento_fpl': config.instrumento_fpl,
            'instrumento_montos_liq': config.instrumento_montos_liq,
            'nombre_salida': config.nombre_salida,
            'cod_sub_pro_final': config.cod_sub_pro_final,
        }
    elif tipo_instrumento in CONFIGURACION_INSTRUMENTOS_FALLBACK:
        return CONFIGURACION_INSTRUMENTOS_FALLBACK[tipo_instrumento]
    else:
        tipos_disponibles = (
            listar_instrumentos() if _CONFIG_DISPONIBLE 
            else list(CONFIGURACION_INSTRUMENTOS_FALLBACK.keys())
        )
        raise ValueError(
            f"Tipo de instrumento no válido: '{tipo_instrumento}'. "
            f"Opciones disponibles: {tipos_disponibles}"
        )


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def generar_flujo_liquidacion_instrumento(
    df_cartera_inv: pd.DataFrame,
    df_cartera_inv_pacto: pd.DataFrame,
    tablas: Dict[str, pd.DataFrame],
    tipo_instrumento: str,
    fecha_proceso: Union[int, datetime.datetime, pd.Timestamp],
    verbose: bool = True
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Pipeline completo de liquidación parametrizado por instrumento.
    
    Ejecuta todo el flujo de liquidación para un instrumento específico:
    1. Filtrar cartera por instrumento (disponible y pacto)
    2. Calcular monto total y ponderadores
    3. Aplicar factores de haircut
    4. Agregar montos de pacto por día
    5. Calcular flujo de liquidación diario
    
    Args:
        df_cartera_inv: Cartera de inversiones disponible (RF_PLI_001_CarteraInv)
        df_cartera_inv_pacto: Cartera de inversiones en pacto (RF_PLI_001d_CarteraInv_Pcto)
        tablas: Dict con tablas base necesarias:
            - 'RF_FactXXX_YYY': Tabla de factores según el instrumento
            - 'FPL': Floor Piso Liquidez
            - 'RF_MontosLiq': Montos a liquidar
        tipo_instrumento: Clave del instrumento
            Opciones: 'GobCLP', 'GobCLF', 'DPF', 'DPR', 'LCH', 'BBC'
        fecha_proceso: Fecha de proceso (int YYYYMMDD o datetime)
        verbose: Mostrar progreso detallado
    
    Returns:
        Tupla con:
        - DataFrame con flujo diario: Dia, DiaSem, Haircut, Monto_Liquidar
        - Dict con todas las queries intermedias generadas
    
    Example:
        >>> flujo, queries = generar_flujo_liquidacion_instrumento(
        ...     df_cartera_inv=queries['RF_PLI_001_CarteraInv'],
        ...     df_cartera_inv_pacto=queries['RF_PLI_001d_CarteraInv_Pcto'],
        ...     tablas={
        ...         'RF_FactCLP_Gob': df_factores,
        ...         'FPL': df_fpl,
        ...         'RF_MontosLiq': df_montos,
        ...     },
        ...     tipo_instrumento='GobCLP',
        ...     fecha_proceso=20260131,
        ...     verbose=True
        ... )
    
    Raises:
        ValueError: Si el tipo de instrumento no es válido
        ValueError: Si falta una tabla requerida en `tablas`
    """
    # Obtener configuración del instrumento
    config = _obtener_config_instrumento(tipo_instrumento)
    queries_generadas: Dict[str, pd.DataFrame] = {}
    
    # Obtener filtro de moneda si existe
    filtro_moneda = config.get('filtro_moneda', None)
    
    if verbose:
        print("\n" + "=" * 70)
        print(f"PIPELINE DE LIQUIDACIÓN: {config['nombre_completo']}")
        print("=" * 70)
        print(f"Tipo: {tipo_instrumento}")
        print(f"Códigos disponible: {config['codigos_disp']}")
        print(f"Códigos pacto: {config['codigos_pacto']}")
        if filtro_moneda:
            print(f"Filtro moneda: {filtro_moneda}")
        print(f"Tabla factores: {config['tabla_factores']}")
        print(f"Instrumento FPL: {config['instrumento_fpl']}")
    
    # =========================================================================
    # PASO 1: Filtrar cartera por instrumento (disponible)
    # =========================================================================
    df_cartera_instr = generar_cartera_instrumento(
        df_cartera_inv,
        COLUMNAS_CARTERA_DISP,
        config['codigos_disp'],
        tipo_instrumento,
        filtro_moneda=filtro_moneda,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Cartera{tipo_instrumento}'] = df_cartera_instr
    
    # =========================================================================
    # PASO 2: Calcular monto total
    # =========================================================================
    df_monto_total = generar_monto_total_instrumento(
        df_cartera_instrumento=df_cartera_instr,
        cols_de_agrupacion=['Fec_Pro', 'Cod_Pro', 'Moneda'],
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        nombre_tabla=tipo_instrumento,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Cartera{tipo_instrumento}_MonTotal'] = df_monto_total
    
    # =========================================================================
    # PASO 3: Calcular ponderadores
    # =========================================================================
    df_cartera_pond = generar_cartera_pond(
        df_cartera_instrumento=df_cartera_instr,
        df_montototal=df_monto_total,
        output_table_name=f'Cartera{tipo_instrumento}_Pond',
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Cartera{tipo_instrumento}_Pond'] = df_cartera_pond
    
    # =========================================================================
    # PASO 4: Filtrar cartera pactos y calcular monto por plazo
    # =========================================================================
    df_cartera_pacto = generar_cartera_instrumento(
        df_cartera_inv_pacto,
        COLUMNAS_CARTERA_PACTO,
        config['codigos_pacto'],
        f'{tipo_instrumento}_Pacto',
        filtro_moneda=filtro_moneda,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Cartera{tipo_instrumento}_Pacto'] = df_cartera_pacto
    
    df_monto_plazo_pacto = generar_monto_plazo_pacto(
        df_cartera_pacto,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_{tipo_instrumento}_MontoPlazo_Pacto'] = df_monto_plazo_pacto
    
    # =========================================================================
    # PASO 5: Aplicar haircut
    # =========================================================================
    tabla_factores_nombre = config['tabla_factores']
    if tabla_factores_nombre not in tablas:
        raise ValueError(
            f"Tabla de factores '{tabla_factores_nombre}' no encontrada. "
            f"Tablas disponibles: {list(tablas.keys())}"
        )
    df_factores = tablas[tabla_factores_nombre]
    
    if 'FPL' not in tablas:
        raise ValueError("Tabla 'FPL' (Floor Piso Liquidez) no encontrada en tablas")
    
    df_cartera_hc = generar_cartera_haircut(
        df_cartera_pond=df_cartera_pond,
        df_factores=df_factores,
        df_fpl=tablas['FPL'],
        filtro_instrumento=config['instrumento_fpl'],
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_CarteraHC_{tipo_instrumento}'] = df_cartera_hc
    
    # =========================================================================
    # PASO 6: Agregar haircut por día
    # =========================================================================
    df_haircut_dia = generar_haircut_dia(df_cartera_hc, verbose=verbose)
    queries_generadas[f'RF_PLI_Haircut_Dia_{tipo_instrumento}'] = df_haircut_dia
    
    # =========================================================================
    # PASO 7: Agregar día de semana
    # =========================================================================
    df_haircut_dia_sem = agregar_dia_semana(
        df_haircut_dia,
        fecha_proceso=fecha_proceso,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Haircut_Dia_b_{tipo_instrumento}'] = df_haircut_dia_sem
    
    # =========================================================================
    # PASO 8: Combinar haircut con pactos
    # =========================================================================
    df_haircut_dia_pcto = combinar_haircut_con_pactos(
        df_haircut_dia_sem,
        df_monto_plazo_pacto,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_Haircut_Dia_Pcto_{tipo_instrumento}'] = df_haircut_dia_pcto
    
    # =========================================================================
    # PASO 9: Obtener monto a liquidar
    # =========================================================================
    if 'RF_MontosLiq' not in tablas:
        raise ValueError("Tabla 'RF_MontosLiq' no encontrada en tablas")
    
    df_monto_liquidar = filtrar_monto_liquidar(
        tablas['RF_MontosLiq'],
        instrumento=config['instrumento_montos_liq'],
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_MontoLiquidar_{tipo_instrumento}'] = df_monto_liquidar
    
    # =========================================================================
    # PASO 10: Calcular flujo de liquidación
    # =========================================================================
    df_flujo = calcular_flujo_liquidacion(
        df_cartera_mon_total=df_monto_total,
        df_haircut_dia_pcto=df_haircut_dia_pcto,
        df_monto_liquidar=df_monto_liquidar,
        nombre_instrumento=tipo_instrumento,
        verbose=verbose
    )
    queries_generadas[config['nombre_salida']] = df_flujo
    
    if verbose:
        print("\n" + "=" * 70)
        print(f"PIPELINE COMPLETADO: {config['nombre_salida']}")
        print("=" * 70)
        print(f"Registros generados: {len(df_flujo)}")
        if len(df_flujo) > 0:
            print(f"Monto inicial (día 0): {df_flujo.loc[0, 'Monto_Liquidar']:,.2f}")
            monto_total_liq = df_flujo.iloc[1:]['Monto_Liquidar'].sum()
            print(f"Suma total liquidaciones: {monto_total_liq:,.2f}")
        print(f"Queries intermedias generadas: {len(queries_generadas)}")
    
    return df_flujo, queries_generadas


def listar_tipos_instrumento() -> list:
    """
    Lista los tipos de instrumento disponibles.
    
    Returns:
        Lista de códigos de instrumento (ej: ['GobCLP', 'GobCLF', ...])
    """
    if _CONFIG_DISPONIBLE:
        return listar_instrumentos()
    else:
        return list(CONFIGURACION_INSTRUMENTOS_FALLBACK.keys())
