"""
Módulo de cálculo de liquidación para RF_Modelo_Inversiones.

Este módulo contiene funciones para el cálculo de flujos de liquidación
de instrumentos financieros, incluyendo:
- Generación de cartera por instrumento
- Cálculo de montos totales y ponderadores
- Cálculo del flujo de liquidación diario

Uso:
    from RF_Modelo_Inversiones.pipeline.liquidacion import (
        generar_cartera_instrumento,
        generar_cartera_pond,
        generar_monto_total_instrumento,
        calcular_flujo_liquidacion,
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import datetime
import numpy as np
import pandas as pd
from typing import Optional, List


# =============================================================================
# CONSTANTES
# =============================================================================

# Columnas estándar de salida para cartera
COLUMNAS_CARTERA_DISP = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
    'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 'Dias_Vcto'
]

COLUMNAS_CARTERA_PACTO = COLUMNAS_CARTERA_DISP + ['Dias_Pacto']


# =============================================================================
# FASE 1.1: FILTRAR CARTERA POR INSTRUMENTO
# =============================================================================

def generar_cartera_instrumento(
    df_base: pd.DataFrame,
    cols_de_salida: List[str],
    instrumento: List[str],
    nombre_instrumento: str,
    filtro_moneda: Optional[str] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Filtra la cartera base por códigos de instrumento y opcionalmente por moneda.
    
    Args:
        df_base: DataFrame con la cartera completa (RF_PLI_001_CarteraInv)
        cols_de_salida: Lista de columnas a mantener en el output
        instrumento: Lista de códigos de instrumento a filtrar (ej: ['BCP', 'BTP', 'BTU'])
        nombre_instrumento: Nombre descriptivo para logging (ej: "GobCLP")
        filtro_moneda: Moneda opcional para filtrar (ej: "CLP"). 
            Si None, no filtra por moneda.
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame filtrado con las columnas especificadas
    
    Example:
        >>> df_gobclp = generar_cartera_instrumento(
        ...     df_base=df_cartera_inv,
        ...     cols_de_salida=COLUMNAS_CARTERA_DISP,
        ...     instrumento=['BCP', 'BTP', 'BTU'],
        ...     nombre_instrumento='GobCLP',
        ...     filtro_moneda='CLP'
        ... )
    """
    # Filtrar por códigos de instrumento
    mask = df_base['Instrumento'].isin(instrumento)
    
    # Filtrar adicionalmente por moneda si se especifica
    if filtro_moneda is not None:
        mask = mask & (df_base['Moneda'] == filtro_moneda)
    
    # Seleccionar columnas existentes
    cols_existentes = [c for c in cols_de_salida if c in df_base.columns]
    df_filtrado = df_base[mask][cols_existentes].copy()
    
    if verbose:
        filtro_msg = f" y moneda {filtro_moneda}" if filtro_moneda else ""
        print(f"Cartera {nombre_instrumento}: {len(df_filtrado):,} registros "
              f"(filtro instrumento {instrumento}{filtro_msg})")
    
    return df_filtrado


# =============================================================================
# FASE 1.2: CALCULAR MONTO TOTAL
# =============================================================================

def generar_monto_total_instrumento(
    df_cartera_instrumento: pd.DataFrame,
    cols_de_agrupacion: List[str],
    cols_suma: List[str],
    nombre_tabla: str = "",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Calcula el monto total agrupado (VP_Flujo = VP_Cap_Amort + VP_Int_Total).
    
    Args:
        df_cartera_instrumento: DataFrame con la cartera filtrada
        cols_de_agrupacion: Columnas para GROUP BY (ej: ['Cod_Pro', 'Moneda'])
        cols_suma: Columnas a sumar (ej: ['VP_Cap_Amort', 'VP_Int_Total'])
        nombre_tabla: Nombre descriptivo para logging
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas de agrupación + VP_Flujo (suma de cols_suma)
    
    SQL de referencia:
        SELECT Cod_Pro, Moneda, Sum(VP_Cap_Amort + VP_Int_Total) AS VP_Flujo
        FROM RF_PLI_002_CarteraGobCLP
        GROUP BY Cod_Pro, Moneda;
    """
    # Agrupar y sumar
    df_monto_total = (
        df_cartera_instrumento
        .groupby(cols_de_agrupacion)[cols_suma]
        .sum()
        .reset_index()
    )
    
    # Crear columna VP_Flujo = suma de columnas
    df_monto_total['VP_Flujo'] = df_monto_total[cols_suma].sum(axis=1)
    
    # Eliminar columnas intermedias
    df_monto_total = df_monto_total.drop(columns=cols_suma)
    
    if verbose:
        total = df_monto_total['VP_Flujo'].sum()
        print(f"Monto total {nombre_tabla}: {len(df_monto_total):,} registros, "
              f"VP_Flujo total = {total:,.2f}")
    
    return df_monto_total


# =============================================================================
# FASE 1.3: CALCULAR PONDERADORES
# =============================================================================

def generar_cartera_pond(
    df_cartera_instrumento: pd.DataFrame,
    df_montototal: pd.DataFrame,
    output_table_name: str = "",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera cartera ponderada (peso de cada registro sobre el total).
    
    Ponderador = (VP_Cap_Amort + VP_Int_Total) / VP_Flujo
    
    Args:
        df_cartera_instrumento: DataFrame con la cartera filtrada
        df_montototal: DataFrame con monto total por grupo (de generar_monto_total_instrumento)
        output_table_name: Nombre descriptivo para logging
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas originales + Ponderador
    
    SQL de referencia:
        SELECT RF_CarteraGobCLP.*, 
               (VP_Cap_Amort + VP_Int_Total) / VP_Flujo AS Ponderador
        FROM RF_CarteraGobCLP 
        INNER JOIN RF_CarteraGobCLP_MonTotal ON Cod_Pro AND Moneda;
    """
    # Hacer merge entre cartera y monto total
    # El monto total tiene cols_de_agrupacion + VP_Flujo
    # Detectar columnas de join (todas menos VP_Flujo)
    cols_join = [c for c in df_montototal.columns if c != 'VP_Flujo']
    
    df_merged = pd.merge(
        df_cartera_instrumento, 
        df_montototal, 
        on=cols_join, 
        how='inner',
        suffixes=('', '_total')
    )
    
    # Calcular ponderador
    df_merged['Ponderador'] = (
        (df_merged['VP_Cap_Amort'] + df_merged['VP_Int_Total']) / 
        df_merged['VP_Flujo']
    )
    
    # Seleccionar columnas de salida (originales + Ponderador)
    cols_originales = df_cartera_instrumento.columns.tolist()
    cols_salida = cols_originales + ['Ponderador']
    
    df_output = df_merged[cols_salida].copy()
    
    if verbose:
        prom_pond = df_output['Ponderador'].mean()
        print(f"Cartera ponderada {output_table_name}: {len(df_output):,} registros, "
              f"Ponderador promedio = {prom_pond:.4f}")
    
    return df_output


# =============================================================================
# FASE FINAL: CALCULAR FLUJO DE LIQUIDACIÓN
# =============================================================================

def calcular_flujo_liquidacion(
    df_cartera_mon_total: pd.DataFrame,
    df_haircut_dia_pcto: pd.DataFrame,
    df_monto_liquidar: pd.DataFrame,
    nombre_instrumento: str = "Generico",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Calcula el flujo de liquidación diario para cualquier instrumento.
    
    Traducción parametrizada de las funciones VBA MontoLiq{Instrumento}() a Python.
    Esta función es genérica y puede usarse para: GobCLP, GobCLF, DPF, DPR, LCH, BBC.
    
    Lógica de negocio:
    1. Inicia con monto total (día 0)
    2. Cada día hábil se liquida un monto fijo
    3. El haircut se aplica exponencialmente acumulado
    4. Nuevos pactos entran con descuento por haircut
    5. No se liquida en fines de semana (DiaSem = 6 o 7)
    
    Args:
        df_cartera_mon_total: DataFrame con columna 'VP_Flujo' (monto total inicial)
        df_haircut_dia_pcto: DataFrame con columnas:
            - Dia: número de día
            - DiaSem: día de la semana (1=Lun, 6=Sáb, 7=Dom)
            - Haircut: factor de haircut acumulado
            - Monto_Pacto: monto de pactos que vencen ese día
        df_monto_liquidar: DataFrame con columna 'Monto a Liquidar' (diario)
        nombre_instrumento: Nombre para logging (ej: "GobCLP")
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con flujo diario:
            - Dia: número de día (0 = inicial, 1..N = días)
            - DiaSem: día de la semana (None para día 0)
            - Haircut: factor de haircut del día
            - Monto_Liquidar: monto liquidado ese día
    
    Reglas de liquidación:
        - Día 0: monto inicial (sin liquidación)
        - Días hábiles: liquidar monto planificado si hay saldo
        - Fines de semana: no liquidar (Monto_Liquidar = 0)
        - Saldo insuficiente: liquidar lo disponible (parcial)
        - Saldo negativo: no liquidar (Monto_Liquidar = 0)
    """
    if verbose:
        print("\n" + "=" * 70)
        print(f"CALCULANDO FLUJO DE LIQUIDACIÓN: {nombre_instrumento}")
        print("=" * 70)
    
    # 1. INICIALIZACIÓN
    monto_tot = df_cartera_mon_total['VP_Flujo'].iloc[0]
    monto_acum = monto_tot
    
    if verbose:
        print(f"Monto inicial (día 0): {monto_tot:,.2f}")
    
    # Lista para almacenar resultados
    flujo_salida = []
    
    # Registro inicial (día 0)
    flujo_salida.append({
        'Dia': 0,
        'DiaSem': None,
        'Haircut': 0.0,
        'Monto_Liquidar': monto_tot
    })
    
    # Factores iniciales
    factor_ti = 0.0
    
    # Monto diario planificado (es constante para todos los días)
    monto_liq_diario = df_monto_liquidar['Monto a Liquidar'].iloc[0]
    
    if verbose:
        print(f"Monto diario planificado: {monto_liq_diario:,.2f}")
    
    # 2. LOOP POR CADA DÍA
    for idx, row_haircut in df_haircut_dia_pcto.iterrows():
        
        dia = int(row_haircut['Dia'])
        dia_sem = int(row_haircut['DiaSem'])
        factor_t = row_haircut['Haircut']
        monto_pacto = row_haircut.get('Monto_Pacto', 0)
        
        # Calcular haircut incremental del día
        # MontoHC_t = max(0, Monto_Acum * (exp(factor_t) - exp(factor_ti)))
        monto_hc_t = max(
            0,
            monto_acum * (np.exp(factor_t) - np.exp(factor_ti))
        )
        
        # Determinar monto planificado (0 si es fin de semana)
        if dia_sem in [6, 7]:  # Sábado o Domingo
            monto_liq_planificado = 0.0
        else:
            monto_liq_planificado = monto_liq_diario
        
        # 3. APLICAR REGLAS DE LIQUIDACIÓN
        saldo_disponible = monto_acum - monto_liq_planificado - monto_hc_t
        
        # Regla 1: Hay suficiente saldo para liquidar todo
        if saldo_disponible >= 0:
            monto_liq = monto_liq_planificado
        
        # Regla 2: Déficit parcial -> liquidar lo disponible
        elif saldo_disponible < 0 and abs(saldo_disponible) / max(monto_liq_planificado, 1) < 1:
            monto_liq = max(0, monto_acum - monto_hc_t) if dia_sem not in [6, 7] else 0
        
        # Regla 3: Déficit total -> no liquidar
        else:
            monto_liq = 0.0
        
        flujo_salida.append({
            'Dia': dia,
            'DiaSem': dia_sem,
            'Haircut': factor_t,
            'Monto_Liquidar': monto_liq
        })
        
        # 4. ACTUALIZAR MONTO ACUMULADO
        if monto_acum < 0 and monto_pacto > 0:
            # Caso 1: Monto negativo, entra nuevo pacto -> resetear
            monto_acum = monto_pacto * np.exp(-1 * factor_t)
        elif monto_acum > 0 and monto_pacto > 0:
            # Caso 2: Monto positivo, entra nuevo pacto -> acumular
            monto_acum = (
                monto_acum + 
                monto_pacto * np.exp(-1 * factor_t) - 
                monto_liq - 
                monto_hc_t
            )
        else:
            # Caso 3: No hay pacto nuevo -> solo descontar
            monto_acum = monto_acum - monto_liq - monto_hc_t
        
        # Actualizar factor anterior
        factor_ti = factor_t
    
    # 5. CREAR DATAFRAME DE SALIDA
    df_flujo = pd.DataFrame(flujo_salida)
    
    if verbose:
        dias_liquidacion = (df_flujo['Monto_Liquidar'] > 0).sum() - 1  # -1 por día 0
        monto_total_liq = df_flujo.iloc[1:]['Monto_Liquidar'].sum()  # Excluir día 0
        print(f"\n{'=' * 70}")
        print(f"RESULTADO: {len(df_flujo)} días generados")
        print(f"  Días con liquidación: {dias_liquidacion}")
        print(f"  Monto total liquidado: {monto_total_liq:,.2f}")
        print(f"{'=' * 70}")
    
    return df_flujo


# =============================================================================
# ALIAS PARA COMPATIBILIDAD
# =============================================================================

def monto_liq_gob_clp(
    df_cartera_mon_total: pd.DataFrame,
    df_haircut_dia_pcto: pd.DataFrame,
    df_monto_liquidar: pd.DataFrame
) -> pd.DataFrame:
    """
    DEPRECADO: Usar calcular_flujo_liquidacion() en código nuevo.
    
    Alias mantenido para compatibilidad hacia atrás.
    """
    import warnings
    warnings.warn(
        "monto_liq_gob_clp() está deprecado. "
        "Usar calcular_flujo_liquidacion()",
        DeprecationWarning,
        stacklevel=2
    )
    return calcular_flujo_liquidacion(
        df_cartera_mon_total, 
        df_haircut_dia_pcto, 
        df_monto_liquidar,
        nombre_instrumento="GobCLP"
    )
