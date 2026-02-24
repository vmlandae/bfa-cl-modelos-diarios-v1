"""
Post-proceso y cuadratura del Modelo de Inversiones.

Implementa las funciones de validación que ejecuta la macro
ActualizaModeloInversiones después de generar las tablas:
- SumarFlujoCLP: suma de Flujo_CLP para cuadratura.
- SumarMontoContable: lectura del balance contable para comparación.
- MensajeDiferenciaModeloContraBalance: reporte de diferencia.

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
from pathlib import Path
from typing import Union, Optional, Tuple
from datetime import datetime


# =============================================================================
# CONSTANTES
# =============================================================================

CATEGORIAS_CONTABLES = [
    'Inversion Financiera Privado',
    'Inversion Financiera Publico',
    'INVERSIONES FINANCIERAS FONDOS MUTUOS',
]
"""Categorías contables para la cuadratura (VLOOKUP en el balance)."""


# =============================================================================
# FUNCIONES DE CUADRATURA
# =============================================================================

def sumar_flujo_clp(df_modelo_inversiones: pd.DataFrame,
                    verbose: bool = True) -> float:
    """
    Suma la columna Flujo_CLP de la hoja MODELO_INVERSIONES.

    Replica la macro SumarFlujoCLP que recorre la columna N (Flujo_CLP)
    para obtener el monto total del modelo.

    Args:
        df_modelo_inversiones: DataFrame de la hoja MODELO_INVERSIONES.
        verbose: Si True, muestra el resultado.

    Returns:
        Suma total de Flujo_CLP.
    """
    if 'Flujo_CLP' not in df_modelo_inversiones.columns:
        if verbose:
            print("  ⚠ Columna Flujo_CLP no encontrada")
        return 0.0

    total = df_modelo_inversiones['Flujo_CLP'].sum()

    if verbose:
        print(f"  Flujo CLP total (modelo): ${total:,.0f}")

    return total


def obtener_monto_contable(
    ruta_balance: Union[str, Path],
    categorias: Optional[list] = None,
    verbose: bool = True,
) -> float:
    """
    Lee el monto contable desde RF_Generador_Balance_Carteras.xlsm.

    Replica la macro SumarMontoContable que hace VLOOKUP en la hoja
    'Cuadratura' del archivo de balance, buscando 3 categorías contables
    y sumando sus montos.

    Args:
        ruta_balance: Ruta al archivo RF_Generador_Balance_Carteras.xlsm.
        categorias: Lista de categorías a buscar (default: CATEGORIAS_CONTABLES).
        verbose: Si True, muestra detalles.

    Returns:
        Suma de los montos contables de las categorías encontradas.
    """
    if categorias is None:
        categorias = CATEGORIAS_CONTABLES

    ruta = Path(ruta_balance)
    if not ruta.exists():
        if verbose:
            print(f"  ⚠ Archivo de balance no encontrado: {ruta}")
        return 0.0

    try:
        df_cuadratura = pd.read_excel(
            ruta, sheet_name='Cuadratura', engine='openpyxl')
    except Exception as e:
        if verbose:
            print(f"  ⚠ Error leyendo balance: {e}")
        return 0.0

    # La hoja Cuadratura tiene categorías en una columna y montos en otra.
    # El VLOOKUP del VBA busca en columnas C3:C4 (col 3=nombre, col 4=monto).
    # Identificamos las columnas por posición (0-based: col 2 = nombre, col 3 = monto)
    if len(df_cuadratura.columns) < 4:
        if verbose:
            print(f"  ⚠ Hoja Cuadratura no tiene suficientes columnas")
        return 0.0

    col_nombre = df_cuadratura.columns[2]  # Columna C
    col_monto = df_cuadratura.columns[3]   # Columna D

    total = 0.0
    for cat in categorias:
        match = df_cuadratura[df_cuadratura[col_nombre] == cat]
        if not match.empty:
            monto = match.iloc[0][col_monto]
            total += float(monto) if pd.notna(monto) else 0.0
            if verbose:
                print(f"    - {cat}: ${float(monto):,.0f}" if pd.notna(monto)
                      else f"    - {cat}: No disponible")
        elif verbose:
            print(f"    - {cat}: No encontrada en balance")

    if verbose:
        print(f"  Monto contable total: ${total:,.0f}")

    return total


def reportar_diferencia_modelo_vs_contable(
    flujo_clp_modelo: float,
    monto_contable: float,
    verbose: bool = True,
) -> Tuple[float, str]:
    """
    Calcula y reporta la diferencia entre el modelo y el balance contable.

    Replica la macro MensajeDiferenciaModeloContraBalance que muestra un
    popup con la diferencia.

    Args:
        flujo_clp_modelo: Suma de Flujo_CLP del modelo.
        monto_contable: Suma de montos contables del balance.
        verbose: Si True, muestra el reporte.

    Returns:
        Tupla con (diferencia, mensaje formateado).
    """
    diferencia = flujo_clp_modelo - monto_contable

    mensaje = (
        f"Modelo de inversiones:   ${flujo_clp_modelo:,.0f}\n"
        f"Cuadratura Contable:     ${monto_contable:,.0f}\n"
        f"Monto diferencia total:  ${diferencia:,.0f}"
    )

    if verbose:
        print("\n" + "=" * 50)
        print("  CUADRATURA MODELO vs BALANCE")
        print("=" * 50)
        print(f"  {mensaje}")
        print("=" * 50)

    return diferencia, mensaje
