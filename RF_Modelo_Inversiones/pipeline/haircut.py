"""
Módulo de cálculo de haircut para RF_Modelo_Inversiones.

Este módulo contiene funciones para el cálculo de haircuts sobre
carteras de inversiones, incluyendo:
- Aplicación de factores de haircut por plazo
- Agregación de haircut por día
- Combinación con montos de pactos
- Filtrado de montos a liquidar

Uso:
    from RF_Modelo_Inversiones.pipeline.haircut import (
        generar_cartera_haircut,
        generar_haircut_dia,
        agregar_dia_semana,
        combinar_haircut_con_pactos,
        filtrar_monto_liquidar,
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import datetime
import numpy as np
import pandas as pd
from typing import Union, List


# =============================================================================
# FASE 2.1: APLICAR FACTORES DE HAIRCUT
# =============================================================================

def generar_cartera_haircut(
    df_cartera_pond: pd.DataFrame,
    df_factores: pd.DataFrame,
    df_fpl: pd.DataFrame,
    filtro_instrumento: Union[str, List[str]],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera cartera con factores de haircut aplicados.
    
    Realiza un JOIN entre la cartera ponderada y la tabla de factores,
    aplicando el máximo entre Factor y Haircut (piso FPL).
    
    Args:
        df_cartera_pond: DataFrame cartera ponderada con columnas:
            - Ponderador: peso de cada registro
            - Dias_Vcto: días al vencimiento
        df_factores: DataFrame con factores por plazo (RF_FactCLP_Gob), columnas:
            - Desde, Hasta: rango de días
            - Dia: día del factor
            - Factor: factor de haircut
        df_fpl: DataFrame Floor Piso Liquidez (FPL), columnas:
            - Instrumento: nombre del instrumento
            - Haircut: valor mínimo de haircut
        filtro_instrumento: Nombre del instrumento para filtrar FPL.
            Puede ser string o lista de strings (ej: "Gobierno CLP" o ["LCH", "BBC"])
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas originales + Dia, Factor, FactorPond
    
    Raises:
        ValueError: Si no se encuentra Haircut para el instrumento especificado
    
    SQL de referencia:
        SELECT RF_CarteraGobCLP_Pond.*, RF_FactCLP_Gob.Dia, RF_FactCLP_Gob.Factor,
               Ponderador * (0.5*((Factor+Haircut)+ABS(Factor-Haircut))) AS FactorPond
        FROM FPL, RF_CarteraGobCLP_Pond 
        INNER JOIN RF_FactCLP_Gob ON (Dias_Vcto <= Hasta) AND (Dias_Vcto >= Desde)
        WHERE FPL.Instrumento = "Gobierno CLP";
    
    Nota: 
        La fórmula 0.5*((A+B)+|A-B|) = MAX(A,B) se usa en Access para calcular
        el máximo entre Factor y Haircut. En Python usamos np.maximum() directamente.
    """
    if verbose:
        print("\n" + "=" * 70)
        print("FASE 2.1: Cartera con Haircut (RF_PLI_0XX_CarteraHC)")
        print("=" * 70)
        print(f"Registros cartera entrada: {len(df_cartera_pond):,}")
        print(f"Registros factores: {len(df_factores):,}")
    
    # =========================================================================
    # PASO 1: Obtener Haircut desde FPL
    # =========================================================================
    if isinstance(filtro_instrumento, str):
        filtro_instrumento = [filtro_instrumento]
    
    mask_fpl = df_fpl['Instrumento'].isin(filtro_instrumento)
    haircut_valores = df_fpl.loc[mask_fpl, 'Haircut'].values
    
    if len(haircut_valores) == 0:
        raise ValueError(
            f"No se encontró Haircut para instrumento: {filtro_instrumento}. "
            f"Instrumentos disponibles: {df_fpl['Instrumento'].unique().tolist()}"
        )
    
    # Si hay múltiples valores, tomar el máximo (caso LCH que combina varios)
    haircut = haircut_valores[0] if len(haircut_valores) == 1 else haircut_valores.max()
    
    if verbose:
        print(f"\n[FPL] Haircut para '{filtro_instrumento}': {haircut:.6f}")
    
    # =========================================================================
    # PASO 2: JOIN cartera con factores (Dias_Vcto BETWEEN Desde AND Hasta)
    # =========================================================================
    # Cross join usando key temporal
    df_cartera_temp = df_cartera_pond.copy()
    df_cartera_temp['_key'] = 1
    df_factores_temp = df_factores.copy()
    df_factores_temp['_key'] = 1
    
    df_cross = pd.merge(df_cartera_temp, df_factores_temp, on='_key', how='outer')
    df_cross = df_cross.drop(columns=['_key'])
    
    # Filtrar por rango: Dias_Vcto >= Desde AND Dias_Vcto <= Hasta
    mask_rango = (
        (df_cross['Dias_Vcto'] >= df_cross['Desde']) & 
        (df_cross['Dias_Vcto'] <= df_cross['Hasta'])
    )
    df_joined = df_cross[mask_rango].copy()
    
    if verbose:
        print(f"\n[JOIN] Registros después de JOIN con factores: {len(df_joined):,}")
        if len(df_joined) == 0:
            print("  ⚠️ ADVERTENCIA: JOIN vacío, verificar rangos de Dias_Vcto")
    
    # =========================================================================
    # PASO 3: Calcular FactorPond = Ponderador * MAX(Factor, Haircut)
    # =========================================================================
    df_joined['FactorPond'] = df_joined['Ponderador'] * np.maximum(
        df_joined['Factor'], 
        haircut
    )
    
    if verbose:
        print(f"\n[CALC] FactorPond = Ponderador * MAX(Factor, {haircut:.6f})")
        print(f"  Factor min: {df_joined['Factor'].min():.6f}")
        print(f"  Factor max: {df_joined['Factor'].max():.6f}")
        print(f"  FactorPond sum: {df_joined['FactorPond'].sum():.6f}")
    
    # =========================================================================
    # PASO 4: Seleccionar columnas de salida
    # =========================================================================
    cols_cartera = [c for c in df_cartera_pond.columns if c != '_key']
    cols_salida = cols_cartera + ['Dia', 'Factor', 'FactorPond']
    
    df_salida = df_joined[cols_salida].copy()
    
    if verbose:
        print(f"\n{'=' * 70}")
        print(f"RESULTADO: {len(df_salida):,} registros generados")
        print(f"{'=' * 70}")
    
    return df_salida


# =============================================================================
# FASE 2.2: AGREGAR HAIRCUT POR DÍA
# =============================================================================

def generar_haircut_dia(
    df_cartera_hc: pd.DataFrame, 
    verbose: bool = True
) -> pd.DataFrame:
    """
    Agrega haircut por día (suma de FactorPond).
    
    Args:
        df_cartera_hc: DataFrame con cartera y haircuts, columnas:
            - Dia: día del factor
            - FactorPond: factor ponderado
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, Haircut
    
    SQL de referencia:
        SELECT Dia, sum(FactorPond) AS Haircut
        FROM RF_PLI_005_CarteraHC
        GROUP BY Dia
        ORDER BY Dia;
    """
    if verbose:
        print("\n" + "-" * 50)
        print("FASE 2.2: Haircut por Día (RF_PLI_0XX_Haircut_Dia)")
        print("-" * 50)
        print(f"Registros entrada: {len(df_cartera_hc):,}")
    
    # Agrupar por Dia y sumar FactorPond
    df_resultado = (
        df_cartera_hc
        .groupby('Dia')['FactorPond']
        .sum()
        .reset_index()
    )
    df_resultado.columns = ['Dia', 'Haircut']
    
    # Ordenar por Dia
    df_resultado = df_resultado.sort_values('Dia').reset_index(drop=True)
    
    if verbose:
        print(f"Registros salida: {len(df_resultado):,}")
        print(f"Rango días: {df_resultado['Dia'].min()} a {df_resultado['Dia'].max()}")
    
    return df_resultado


# =============================================================================
# FASE 2.3: AGREGAR DÍA DE SEMANA
# =============================================================================

def agregar_dia_semana(
    df_haircut_dia: pd.DataFrame,
    fecha_proceso: Union[pd.Timestamp, datetime.datetime, int],
    verbose: bool = True
) -> pd.DataFrame:
    """
    Agrega día de la semana al DataFrame de haircut.
    
    Args:
        df_haircut_dia: DataFrame con haircuts por día, columnas:
            - Dia: número de día (offset desde fecha_proceso)
            - Haircut: valor del haircut
        fecha_proceso: Fecha de proceso (datetime o int YYYYMMDD)
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, DiaSem, Haircut
        Donde DiaSem: 1=Lunes, 2=Martes, ..., 7=Domingo
    
    SQL de referencia:
        SELECT Dia, weekday(Fecha + Dia, 2) AS DiaSem, Haircut
        FROM RF_Fecha_Proceso_Carteras, RF_PLI_006_Haircut_Dia;
    
    Nota: 
        weekday(..., 2) en Access retorna Lunes=1, ..., Domingo=7.
        En pandas dayofweek retorna Lunes=0, ..., Domingo=6.
        Por eso sumamos 1 al resultado.
    """
    if verbose:
        print("\n" + "-" * 50)
        print("FASE 2.3: Haircut con Día Semana (RF_PLI_0XXb_Haircut_Dia)")
        print("-" * 50)
        print(f"Registros entrada: {len(df_haircut_dia):,}")
    
    # Convertir fecha_proceso a Timestamp si es necesario
    if isinstance(fecha_proceso, int):
        fecha_proceso = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif not isinstance(fecha_proceso, (pd.Timestamp, datetime.datetime)):
        fecha_proceso = pd.to_datetime(fecha_proceso)
    
    df_resultado = df_haircut_dia.copy()
    
    # Calcular fecha para cada día y obtener día de semana
    df_resultado['_fecha'] = fecha_proceso + pd.to_timedelta(df_resultado['Dia'], unit='D')
    df_resultado['DiaSem'] = df_resultado['_fecha'].dt.dayofweek + 1
    
    # Seleccionar columnas en orden correcto
    df_resultado = df_resultado[['Dia', 'DiaSem', 'Haircut']].copy()
    
    if verbose:
        dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        dia_nombre = dias_semana[fecha_proceso.dayofweek]
        print(f"Fecha proceso: {fecha_proceso.strftime('%Y-%m-%d')} ({dia_nombre})")
        print(f"Registros salida: {len(df_resultado):,}")
    
    return df_resultado


# =============================================================================
# FASE 3: COMBINAR HAIRCUT CON PACTOS
# =============================================================================

def combinar_haircut_con_pactos(
    df_haircut_dia_sem: pd.DataFrame,
    df_monto_plazo_pacto: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Combina haircut diario con montos de pactos que vencen cada día.
    
    Realiza un LEFT JOIN para agregar los montos de pactos que vencen
    en cada día al DataFrame de haircuts.
    
    Args:
        df_haircut_dia_sem: DataFrame con haircuts por día, columnas:
            - Dia: número de día
            - DiaSem: día de la semana (1-7)
            - Haircut: valor del haircut
        df_monto_plazo_pacto: DataFrame con montos por plazo de pacto, columnas:
            - Dias_Pacto: días hasta vencimiento del pacto
            - Monto: monto del pacto
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, DiaSem, Haircut, Monto_Pacto
    
    SQL de referencia:
        SELECT Dia, DiaSem, Haircut, 
               IIf(IsNull(Monto), 0, Monto) AS Monto_Pacto
        FROM RF_PLI_006b_Haircut_Dia 
        LEFT JOIN RF_PLI_003b_GobCLP_MontoPlazo_Pacto ON Dia = Dias_Pacto
        ORDER BY Dia;
    """
    if verbose:
        print("\n" + "=" * 70)
        print("FASE 3: Combinar Haircut + Pactos (RF_PLI_0XXc_Haircut_Dia_Pcto)")
        print("=" * 70)
        print(f"Registros haircut: {len(df_haircut_dia_sem):,}")
        print(f"Registros pactos: {len(df_monto_plazo_pacto):,}")
    
    # LEFT JOIN en Dia = Dias_Pacto
    df_resultado = pd.merge(
        df_haircut_dia_sem,
        df_monto_plazo_pacto,
        left_on='Dia',
        right_on='Dias_Pacto',
        how='left'
    )
    
    # Llenar nulos con 0 y renombrar columna
    df_resultado['Monto_Pacto'] = df_resultado['Monto'].fillna(0)
    
    # Seleccionar columnas finales
    df_resultado = df_resultado[['Dia', 'DiaSem', 'Haircut', 'Monto_Pacto']].copy()
    
    # Ordenar por Dia
    df_resultado = df_resultado.sort_values('Dia').reset_index(drop=True)
    
    if verbose:
        dias_con_pacto = (df_resultado['Monto_Pacto'] > 0).sum()
        monto_total_pactos = df_resultado['Monto_Pacto'].sum()
        print(f"\nRegistros salida: {len(df_resultado):,}")
        print(f"Días con vencimiento de pactos: {dias_con_pacto}")
        print(f"Monto total pactos: {monto_total_pactos:,.2f}")
        print(f"{'=' * 70}")
    
    return df_resultado


# =============================================================================
# FASE 4: FILTRAR MONTO A LIQUIDAR
# =============================================================================

def filtrar_monto_liquidar(
    df_montos_liq: pd.DataFrame,
    instrumento: str,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Filtra montos a liquidar por instrumento específico.
    
    Args:
        df_montos_liq: DataFrame con montos a liquidar (RF_MontosLiq), columnas:
            - Instrumento: nombre del instrumento
            - Monto Mercado: monto total del mercado
            - % participacion: porcentaje de participación
            - Monto a Liquidar: monto diario a liquidar
        instrumento: Nombre del instrumento a filtrar (ej: "Gobierno CLP")
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame filtrado con el instrumento especificado
    
    SQL de referencia:
        SELECT Instrumento, [Monto Mercado], [% participacion], [Monto a Liquidar]
        FROM RF_MontosLiq
        WHERE Instrumento = 'Gobierno CLP';
    """
    if verbose:
        print("\n" + "-" * 50)
        print(f"FASE 4: Monto a Liquidar ({instrumento})")
        print("-" * 50)
    
    # Filtrar por instrumento
    mask = df_montos_liq['Instrumento'] == instrumento
    df_resultado = df_montos_liq[mask].copy()
    
    if verbose:
        if len(df_resultado) > 0:
            monto = df_resultado['Monto a Liquidar'].iloc[0]
            print(f"Monto diario a liquidar: {monto:,.2f}")
        else:
            instrumentos_disponibles = df_montos_liq['Instrumento'].unique().tolist()
            print(f"⚠️ ADVERTENCIA: No se encontró instrumento '{instrumento}'")
            print(f"   Disponibles: {instrumentos_disponibles}")
    
    return df_resultado
