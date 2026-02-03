"""
Generador de Tabla Final de Inversiones
========================================

Este módulo reemplaza las 12 queries anidadas de Access con ~50 líneas de Python limpio.

Lógica subyacente:
1. Tomar los flujos de liquidación calculados para cada instrumento (GobCLP, GobCLF, DPF, DPR, LCH, BBC)
2. Formatear cada flujo con un esquema de columnas estándar
3. Agregar la cartera de garantías (Gtia)
4. Agregar los pactos
5. Unir todo en una sola tabla final

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
import warnings
from datetime import datetime
from typing import Dict, Optional

# =============================================================================
# IMPORTAR CONFIGURACIÓN CENTRALIZADA
# =============================================================================

try:
    from RF_Modelo_Inversiones.config.instrumentos import (
        INSTRUMENTOS,
        COLUMNAS_TABLA_FINAL,
        CODIGO_EMPRESA,
        CODIGO_ACTIVO_PASIVO,
        CODIGO_PRODUCTO,
        obtener_instrumento,
        listar_instrumentos,
    )
    _CONFIG_CENTRALIZADA = True
except ImportError:
    # Fallback para ejecución directa desde dev/
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from RF_Modelo_Inversiones.config.instrumentos import (
            INSTRUMENTOS,
            COLUMNAS_TABLA_FINAL,
            CODIGO_EMPRESA,
            CODIGO_ACTIVO_PASIVO,
            CODIGO_PRODUCTO,
            obtener_instrumento,
            listar_instrumentos,
        )
        _CONFIG_CENTRALIZADA = True
    except ImportError:
        _CONFIG_CENTRALIZADA = False
        warnings.warn(
            "No se pudo importar config/instrumentos.py. Usando configuración local.",
            DeprecationWarning
        )
        
        # Fallback: definir localmente si no se puede importar
        COLUMNAS_TABLA_FINAL = [
            'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P', 'Cod_Pro', 'Cod_Sub_Pro',
            'Fec_Pago', 'Dias_Pago', 'Cap_Amort', 'Int_Total_Cont',
            'VP_Cap_Amort', 'VP_Int_Total_Cont'
        ]
        CODIGO_EMPRESA = 'BFA'
        CODIGO_ACTIVO_PASIVO = 'A'
        CODIGO_PRODUCTO = 'RF_Inversiones_Financieras'

# =============================================================================
# CONFIGURACIÓN DE INSTRUMENTOS (derivada de config centralizada)
# =============================================================================

def _construir_instrumentos_config() -> dict:
    """
    Construye el mapeo simplificado de instrumentos desde la config centralizada.
    
    Returns:
        Dict con formato {'GobCLP': {'moneda': 'CLP', 'sufijo': 'GOBCLP'}, ...}
    """
    if _CONFIG_CENTRALIZADA:
        config = {}
        for nombre, cfg in INSTRUMENTOS.items():
            # Extraer sufijo del cod_sub_pro_final
            # Ej: 'ML_C46_Inversiones_Financieras_GOBCLP' -> 'GOBCLP'
            sufijo = cfg.cod_sub_pro_final.split('_')[-1]
            config[nombre] = {
                'moneda': cfg.moneda,
                'sufijo': sufijo,
                'cod_sub_pro_final': cfg.cod_sub_pro_final,
            }
        return config
    else:
        # Fallback hardcoded
        return {
            'GobCLP': {'moneda': 'CLP', 'sufijo': 'GOBCLP', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_GOBCLP'},
            'GobCLF': {'moneda': 'CLF', 'sufijo': 'GOBCLF', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_GOBCLF'},
            'DPF':    {'moneda': 'CLP', 'sufijo': 'DPFCLP', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_DPFCLP'},
            'DPR':    {'moneda': 'CLF', 'sufijo': 'DPRCLF', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_DPRCLF'},
            'LCH':    {'moneda': 'CLF', 'sufijo': 'LCHR', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_LCHR'},
            'BBC':    {'moneda': 'CLP', 'sufijo': 'CORPCLP', 'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_CORPCLP'},
        }

INSTRUMENTOS_CONFIG = _construir_instrumentos_config()


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================

def formatear_flujo_instrumento(df_flujo: pd.DataFrame, 
                                 tipo_instrumento: str,
                                 fecha_proceso: datetime) -> pd.DataFrame:
    """
    Convierte un DataFrame de flujos de liquidación al formato estándar de la tabla final.
    
    Esta función reemplaza las 6 queries idénticas:
    - RF_PLI_008b_CarteraGobCLP_Final
    - RF_PLI_015b_CarteraGobCLF_Final
    - RF_PLI_022b_CarteraDPF_Final
    - RF_PLI_029b_CarteraDPR_Final
    - RF_PLI_036b_CarteraLCH_Final
    - RF_PLI_043b_CarteraBBC_Final
    
    Args:
        df_flujo: DataFrame con columnas ['Dia', 'Monto_Liquidar']
        tipo_instrumento: Clave del instrumento ('GobCLP', 'GobCLF', etc.)
        fecha_proceso: Fecha de proceso
        
    Returns:
        DataFrame con el esquema estándar de COLUMNAS_TABLA_FINAL
    """
    if tipo_instrumento not in INSTRUMENTOS_CONFIG:
        raise KeyError(
            f"Instrumento '{tipo_instrumento}' no existe. "
            f"Disponibles: {list(INSTRUMENTOS_CONFIG.keys())}"
        )
    
    config = INSTRUMENTOS_CONFIG[tipo_instrumento]
    
    # Filtrar: solo días > 0 y montos > 0
    df = df_flujo[(df_flujo['Dia'] > 0) & (df_flujo['Monto_Liquidar'] > 0)].copy()
    
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Construir tabla con esquema estándar
    # Usar cod_sub_pro_final directamente desde config (single source of truth)
    cod_sub_pro = config.get('cod_sub_pro_final', f"ML_C46_Inversiones_Financieras_{config['sufijo']}")
    
    return pd.DataFrame({
        'Fec_Pro': fecha_proceso,
        'Cod_Emp': CODIGO_EMPRESA if _CONFIG_CENTRALIZADA else 1,
        'Moneda': config['moneda'],
        'Cod_A_P': CODIGO_ACTIVO_PASIVO if _CONFIG_CENTRALIZADA else 'ACT',
        'Cod_Pro': CODIGO_PRODUCTO if _CONFIG_CENTRALIZADA else 'ML_C46_Inversiones_Financieras',
        'Cod_Sub_Pro': cod_sub_pro,
        'Fec_Pago': fecha_proceso + pd.to_timedelta(df['Dia'], unit='D'),
        'Dias_Pago': df['Dia'].values,
        'Cap_Amort': df['Monto_Liquidar'].values,
        'Int_Total_Cont': 0,
        'VP_Cap_Amort': df['Monto_Liquidar'].values,
        'VP_Int_Total_Cont': 0
    })


def generar_cartera_garantias(df_base: pd.DataFrame, 
                               fecha_proceso: datetime) -> pd.DataFrame:
    """
    Genera la cartera de inversiones con garantía.
    
    Reemplaza las queries:
    - RF_PLI_001b_CarteraInv_Gtia (filtro inicial)
    - RF_PLI_001c_CarteraInv_Gtia (agregación)
    
    Lógica:
    1. Filtrar por Cod_Pro = 'Inversion Financiera' y Cod_Sub_Pro termina en 'Gtia' o 'Gtia_Liq'
    2. Agrupar por Fec_Pro, Cod_Emp, Moneda, Dias_Liq
    3. Sumar Cap_Amort, Int_Total_Cont, VP_Cap_Amort, VP_Int_Total
    """
    # Paso 1: Filtrar inversiones con garantía
    mask = (
        (df_base['Cod_Pro'].str[:20] == 'Inversion Financiera') &
        (df_base['Cod_Sub_Pro'].str.endswith('Gtia') | 
         df_base['Cod_Sub_Pro'].str.endswith('Gtia_Liq'))
    )
    df_gtia = df_base[mask].copy()
    
    if df_gtia.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    # Paso 2: Agrupar y sumar
    df_agg = df_gtia.groupby(['Fec_Pro', 'Cod_Emp', 'Moneda', 'Dias_Liq']).agg({
        'Cap_Amort': 'sum',
        'Int_Total_Cont': 'sum',
        'VP_Cap_Amort': 'sum',
        'VP_Int_Total': 'sum'
    }).reset_index()
    
    # Paso 3: Formatear al esquema estándar
    return pd.DataFrame({
        'Fec_Pro': df_agg['Fec_Pro'],
        'Cod_Emp': df_agg['Cod_Emp'],
        'Moneda': df_agg['Moneda'],
        'Cod_A_P': 'ACT',
        'Cod_Pro': 'ML_C46_Inversiones_Financieras_Gtia',
        'Cod_Sub_Pro': 'ML_C46_Inversiones_Financieras_Gtia',
        'Fec_Pago': df_agg['Fec_Pro'] + pd.to_timedelta(df_agg['Dias_Liq'], unit='D'),
        'Dias_Pago': df_agg['Dias_Liq'],
        'Cap_Amort': df_agg['Cap_Amort'],
        'Int_Total_Cont': df_agg['Int_Total_Cont'],
        'VP_Cap_Amort': df_agg['VP_Cap_Amort'],
        'VP_Int_Total_Cont': df_agg['VP_Int_Total']
    })


def generar_cartera_pactos(df_pactos: pd.DataFrame, 
                            fecha_proceso: datetime) -> pd.DataFrame:
    """
    Genera la cartera de pactos.
    
    Reemplaza la query RF_PLI_044c_Modelo_Inversiones_Pacto_FB.
    """
    if df_pactos.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    return pd.DataFrame({
        'Fec_Pro': fecha_proceso,
        'Cod_Emp': 1,
        'Moneda': df_pactos['Moneda'],
        'Cod_A_P': 'ACT',
        'Cod_Pro': 'ML_C46_Inversiones_Financieras',
        'Cod_Sub_Pro': 'ML_C46_Inversiones_Financieras_Pcto',
        'Fec_Pago': fecha_proceso + pd.to_timedelta(df_pactos['Dias_Pacto'], unit='D'),
        'Dias_Pago': df_pactos['Dias_Pacto'].values,
        'Cap_Amort': df_pactos['Monto'].values,
        'Int_Total_Cont': 0,
        'VP_Cap_Amort': df_pactos['Monto'].values,
        'VP_Int_Total_Cont': 0
    })


def generar_tabla_final_inversiones(
    flujos_por_instrumento: Dict[str, pd.DataFrame],
    df_base_cartera: pd.DataFrame,
    df_pactos: Optional[pd.DataFrame],
    fecha_proceso: datetime
) -> pd.DataFrame:
    """
    Función principal que genera la tabla final de inversiones.
    
    Reemplaza las queries:
    - RF_PLI_044_Modelo_Inversiones_Final (UNION de instrumentos)
    - RF_PLI_044d_Modelo_Inversiones_Full (UNION con pactos)
    - RF_PLI_044e_Modelo_Inversiones_Tabla_Final (SELECT INTO)
    
    Args:
        flujos_por_instrumento: Dict con DataFrames de flujos por instrumento
                                {'GobCLP': df_flujo_gobclp, 'GobCLF': df_flujo_gobclf, ...}
        df_base_cartera: DataFrame con la cartera base (RF_base_Completa_Hist)
        df_pactos: DataFrame con los pactos (puede ser None)
        fecha_proceso: Fecha de proceso
        
    Returns:
        DataFrame con la tabla final consolidada
    """
    tablas_a_unir = []
    
    # 1. Formatear flujos de cada instrumento
    for instrumento, df_flujo in flujos_por_instrumento.items():
        if instrumento in INSTRUMENTOS_CONFIG:
            df_formateado = formatear_flujo_instrumento(df_flujo, instrumento, fecha_proceso)
            if not df_formateado.empty:
                tablas_a_unir.append(df_formateado)
    
    # 2. Agregar cartera de garantías
    df_gtia = generar_cartera_garantias(df_base_cartera, fecha_proceso)
    if not df_gtia.empty:
        tablas_a_unir.append(df_gtia)
    
    # 3. Agregar pactos (si existen)
    if df_pactos is not None and not df_pactos.empty:
        df_pactos_fmt = generar_cartera_pactos(df_pactos, fecha_proceso)
        if not df_pactos_fmt.empty:
            tablas_a_unir.append(df_pactos_fmt)
    
    # 4. Unir todo (equivalente a UNION ALL)
    if not tablas_a_unir:
        return pd.DataFrame(columns=COLUMNAS_TABLA_FINAL)
    
    tabla_final = pd.concat(tablas_a_unir, ignore_index=True)
    
    return tabla_final[COLUMNAS_TABLA_FINAL]


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    # Ejemplo de uso con datos ficticios
    from datetime import datetime
    
    fecha = datetime(2026, 1, 15)
    
    # Simular flujos de instrumentos (en producción vienen de las funciones de helpers.py)
    flujos = {
        'GobCLP': pd.DataFrame({'Dia': [1, 2, 3], 'Monto_Liquidar': [1000, 2000, 1500]}),
        'GobCLF': pd.DataFrame({'Dia': [1, 5], 'Monto_Liquidar': [500, 800]}),
        'DPF': pd.DataFrame({'Dia': [2, 4], 'Monto_Liquidar': [300, 400]}),
    }
    
    # Simular cartera base (vacía para este ejemplo)
    df_base = pd.DataFrame(columns=['Cod_Pro', 'Cod_Sub_Pro', 'Fec_Pro', 'Cod_Emp', 
                                     'Moneda', 'Dias_Liq', 'Cap_Amort', 'Int_Total_Cont',
                                     'VP_Cap_Amort', 'VP_Int_Total'])
    
    # Generar tabla final
    tabla_final = generar_tabla_final_inversiones(
        flujos_por_instrumento=flujos,
        df_base_cartera=df_base,
        df_pactos=None,
        fecha_proceso=fecha
    )
    
    print("Tabla Final de Inversiones:")
    print(f"Registros: {len(tabla_final)}")
    print(tabla_final.to_string())
