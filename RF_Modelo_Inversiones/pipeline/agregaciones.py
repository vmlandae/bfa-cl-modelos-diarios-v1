"""
Módulo de agregaciones genéricas para RF_Modelo_Inversiones.

Este módulo contiene funciones de agregación (GROUP BY + SUM) que unifican
la lógica repetida en múltiples funciones:
- generar_monto_total_instrumento()
- generar_haircut_dia()
- generar_monto_plazo_pacto()

Uso:
    from RF_Modelo_Inversiones.pipeline.agregaciones import agregar_por_columnas
    
    df_total = agregar_por_columnas(
        df, 
        cols_grupo=['Instrumento'], 
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        col_total='VP_Flujo'
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
from typing import List, Optional, Union


def agregar_por_columnas(
    df: pd.DataFrame,
    cols_grupo: Union[str, List[str]],
    cols_suma: Union[str, List[str]],
    col_total: Optional[str] = None,
    ordenar_por: Optional[Union[str, List[str]]] = None,
    nombre_log: str = "",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Agregación genérica con GROUP BY + SUM.
    
    Reemplaza la lógica repetida en funciones como:
    - generar_monto_total_instrumento(): GROUP BY Instrumento, SUM(VP_Flujo)
    - generar_haircut_dia(): GROUP BY Dia, SUM(FactorPond)
    - generar_monto_plazo_pacto(): GROUP BY Dias_Pacto, SUM(VP_Cap_Amort + VP_Int_Total)
    
    Args:
        df: DataFrame de entrada
        cols_grupo: Columna(s) para GROUP BY
        cols_suma: Columna(s) para sumar
        col_total: Si se especifica, crea una columna con la suma de cols_suma
                  y elimina las columnas originales
        ordenar_por: Columna(s) para ordenar el resultado (opcional)
        nombre_log: Nombre para mostrar en el log (opcional)
        verbose: Si True, muestra información del resultado
    
    Returns:
        DataFrame agrupado con las sumas
    
    Example:
        >>> # Equivalente a generar_monto_total_instrumento()
        >>> df_total = agregar_por_columnas(
        ...     df_cartera,
        ...     cols_grupo='Instrumento',
        ...     cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        ...     col_total='VP_Flujo',
        ...     nombre_log='Monto Total por Instrumento'
        ... )
        
        >>> # Equivalente a generar_haircut_dia()
        >>> df_hc = agregar_por_columnas(
        ...     df_haircut,
        ...     cols_grupo='Dia',
        ...     cols_suma='FactorPond',
        ...     ordenar_por='Dia',
        ...     nombre_log='Haircut por Día'
        ... )
    """
    # Normalizar a listas
    if isinstance(cols_grupo, str):
        cols_grupo = [cols_grupo]
    if isinstance(cols_suma, str):
        cols_suma = [cols_suma]
    
    # Validar columnas existen
    cols_faltantes = [c for c in cols_grupo + cols_suma if c not in df.columns]
    if cols_faltantes:
        raise ValueError(f"Columnas no encontradas en DataFrame: {cols_faltantes}")
    
    # Agregar
    df_agg = df.groupby(cols_grupo, as_index=False)[cols_suma].sum()
    
    # Si se solicita columna total, sumar las columnas y eliminar originales
    if col_total:
        df_agg[col_total] = df_agg[cols_suma].sum(axis=1)
        df_agg = df_agg.drop(columns=cols_suma)
    
    # Ordenar si se especifica
    if ordenar_por:
        if isinstance(ordenar_por, str):
            ordenar_por = [ordenar_por]
        df_agg = df_agg.sort_values(ordenar_por).reset_index(drop=True)
    
    # Log
    if verbose and nombre_log:
        print(f"  [{nombre_log}] {len(df_agg):,} registros agrupados")
    
    return df_agg


def generar_monto_total_instrumento(
    df_cartera: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera monto total por instrumento.
    
    Equivalente a la función original en helpers.py.
    
    Args:
        df_cartera: DataFrame con columnas 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total'
        verbose: Si True, muestra información
    
    Returns:
        DataFrame con columnas ['Instrumento', 'VP_Flujo']
    """
    return agregar_por_columnas(
        df_cartera,
        cols_grupo='Instrumento',
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        col_total='VP_Flujo',
        nombre_log='Monto Total Instrumento' if verbose else '',
        verbose=verbose
    )


def generar_haircut_dia(
    df_cartera_hc: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera haircut agregado por día.
    
    Equivalente a la función original en helpers.py.
    
    Args:
        df_cartera_hc: DataFrame con columnas 'Dia', 'FactorPond'
        verbose: Si True, muestra información
    
    Returns:
        DataFrame con columnas ['Dia', 'FactorPond']
    
    SQL de referencia:
        SELECT Dia, sum(FactorPond) AS FactorPond
        FROM RF_PLI_004_CarteraGobCLP_HC
        GROUP BY Dia
        ORDER BY Dia;
    """
    return agregar_por_columnas(
        df_cartera_hc,
        cols_grupo='Dia',
        cols_suma='FactorPond',
        ordenar_por='Dia',
        nombre_log='Haircut por Día' if verbose else '',
        verbose=verbose
    )


def generar_monto_plazo_pacto(
    df_cartera_pacto: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera monto total por plazo de pacto.
    
    Equivalente a la función original en helpers.py.
    
    Args:
        df_cartera_pacto: DataFrame con columnas 'Dias_Pacto', 'VP_Cap_Amort', 'VP_Int_Total'
        verbose: Si True, muestra información
    
    Returns:
        DataFrame con columnas ['Dias_Pacto', 'Monto']
    
    SQL de referencia:
        SELECT Dias_Pacto, sum(VP_Cap_Amort + VP_Int_Total) AS Monto
        FROM RF_PLI_002_CarteraGobCLP_Pacto
        GROUP BY Dias_Pacto
        ORDER BY Dias_Pacto;
    """
    df_resultado = agregar_por_columnas(
        df_cartera_pacto,
        cols_grupo='Dias_Pacto',
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        col_total='Monto',
        ordenar_por='Dias_Pacto',
        nombre_log='Monto Plazo Pacto' if verbose else '',
        verbose=verbose
    )
    return df_resultado


def agregar_vp_flujo(
    df: pd.DataFrame,
    cols_grupo: Union[str, List[str]],
    verbose: bool = True,
    nombre_log: str = ""
) -> pd.DataFrame:
    """
    Agregación específica para VP_Flujo = VP_Cap_Amort + VP_Int_Total.
    
    Conveniencia para el caso común de sumar capital e intereses.
    
    Args:
        df: DataFrame con columnas 'VP_Cap_Amort', 'VP_Int_Total'
        cols_grupo: Columna(s) para GROUP BY
        verbose: Si True, muestra información
        nombre_log: Nombre para el log
    
    Returns:
        DataFrame agrupado con columna 'VP_Flujo'
    """
    return agregar_por_columnas(
        df,
        cols_grupo=cols_grupo,
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        col_total='VP_Flujo',
        nombre_log=nombre_log,
        verbose=verbose
    )
