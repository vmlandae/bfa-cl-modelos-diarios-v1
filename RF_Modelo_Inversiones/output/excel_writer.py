"""
Escritor de Excel para Modelo de Inversiones.

Implementa la lógica de la macro ActualizaModeloInversiones del archivo
"Maestro Modelo de Inversiones.xlsm", generando el archivo de output
"Modelo de Inversiones.xlsx" con las 4 hojas requeridas.

Hojas generadas:
    - INTERFAZ_MODELO_INVERSIONES: Tabla desarrollo con RepasaCodigoSubProducto
    - MODELO_INVERSIONES: Tabla final con Precio_Mid y Flujo_CLP (14 cols)
    - ML_ACCESS: Copia de INTERFAZ sin reemplazo de códigos (31 cols)
    - CartAdcnl: Cartera adicional expandida (54 cols)

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Union
from datetime import datetime

from .tabla_final import (
    COLUMNAS_TABLA_DESARROLLO,
    COLUMNAS_EXCEL_FINAL,
    CODIGO_PRODUCTO,
)


# =============================================================================
# CONSTANTES
# =============================================================================

SUFIJOS_REPASA = [
    'LCHR', 'Gob', 'BBC',
    'GOBCLP', 'GOBCLF', 'DPFCLP', 'DPRCLF', 'CORPCLP', 'CORPCLF',
]
"""Sufijos de CODIGO_SUBPRODUCTO que se reemplazan por el código base."""


# =============================================================================
# FUNCIONES PARA GENERACIÓN DE HOJAS
# =============================================================================

def generar_hoja_modelo_inversiones(df_tabla_desarrollo: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la hoja MODELO_INVERSIONES (14 columnas).

    Contiene la tabla de desarrollo con columnas internas incluyendo
    Precio_Mid y Flujo_CLP. Preserva los códigos de sub-producto originales
    (con sufijo por instrumento).

    Args:
        df_tabla_desarrollo: Output de generar_tabla_desarrollo_completa()
            con columnas COLUMNAS_TABLA_DESARROLLO.

    Returns:
        DataFrame con 14 columnas para la hoja MODELO_INVERSIONES.
    """
    return df_tabla_desarrollo[COLUMNAS_TABLA_DESARROLLO].copy()


def aplicar_repasa_codigo_subproducto(df: pd.DataFrame,
                                      col: str = 'CODIGO_SUBPRODUCTO'
                                      ) -> pd.DataFrame:
    """
    Replica la macro RepasaCodigoSubProducto del VBA.

    Recorre la columna de sub-producto y reemplaza los registros cuyo valor
    termine en alguno de los sufijos conocidos (LCHR, Gob, BBC, GOBCLP, etc.)
    por el código base 'ML_C46_Inversiones_Financieras'.

    También reemplaza la columna CODIGO_PRODUCTO al mismo valor (columna H
    en el VBA original, que corresponde a ActiveCell.Offset(0, -1)).

    Args:
        df: DataFrame con la columna a procesar.
        col: Nombre de la columna de sub-producto.

    Returns:
        DataFrame con los códigos reemplazados.
    """
    df = df.copy()
    col_pro = 'CODIGO_PRODUCTO'

    mask = pd.Series(False, index=df.index)
    for sufijo in SUFIJOS_REPASA:
        mask = mask | df[col].astype(str).str.endswith(sufijo, na=False)

    df.loc[mask, col] = CODIGO_PRODUCTO
    if col_pro in df.columns:
        df.loc[mask, col_pro] = CODIGO_PRODUCTO

    return df


def generar_hoja_interfaz(df_tabla_excel: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la hoja INTERFAZ_MODELO_INVERSIONES (31 columnas).

    Es la tabla en formato Excel (paso 27) con RepasaCodigoSubProducto aplicado.

    Args:
        df_tabla_excel: Output de formatear_para_excel() con COLUMNAS_EXCEL_FINAL.

    Returns:
        DataFrame con 31 columnas para la hoja INTERFAZ_MODELO_INVERSIONES.
    """
    return aplicar_repasa_codigo_subproducto(df_tabla_excel)


def generar_hoja_ml_access(df_tabla_excel: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la hoja ML_ACCESS (31 columnas).

    Es una copia de la tabla Excel SIN aplicar RepasaCodigoSubProducto,
    preservando los códigos de sub-producto originales por instrumento.

    En el flujo VBA original, CopiarTablaDesarrollo se ejecuta ANTES de
    RepasaCodigoSubProducto, por lo que ML_ACCESS tiene los códigos originales.

    Args:
        df_tabla_excel: Output de formatear_para_excel() con COLUMNAS_EXCEL_FINAL.

    Returns:
        DataFrame con 31 columnas para la hoja ML_ACCESS.
    """
    return df_tabla_excel[COLUMNAS_EXCEL_FINAL].copy()


# =============================================================================
# EXPORTACIÓN A EXCEL
# =============================================================================

def exportar_excel_modelo_inversiones(
    df_interfaz: pd.DataFrame,
    df_modelo_inversiones: pd.DataFrame,
    df_ml_access: pd.DataFrame,
    df_cart_adcnl: pd.DataFrame,
    ruta_output: Union[str, Path],
    verbose: bool = True,
) -> Path:
    """
    Genera el archivo 'Modelo de Inversiones.xlsx' con las 4 hojas.

    Replica la funcionalidad del Maestro que guarda el archivo final con
    SaveAs como .xlsx.

    Args:
        df_interfaz: Hoja INTERFAZ_MODELO_INVERSIONES (con RepasaCodigo).
        df_modelo_inversiones: Hoja MODELO_INVERSIONES (14 cols).
        df_ml_access: Hoja ML_ACCESS (31 cols, sin RepasaCodigo).
        df_cart_adcnl: Hoja CartAdcnl (54 cols).
        ruta_output: Ruta del archivo Excel de salida.
        verbose: Si True, muestra mensajes.

    Returns:
        Path del archivo generado.
    """
    ruta = Path(ruta_output)

    if verbose:
        print(f"\n  Exportando Excel: {ruta.name}")

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        df_interfaz.to_excel(
            writer, sheet_name='INTERFAZ_MODELO_INVERSIONES', index=False)
        df_modelo_inversiones.to_excel(
            writer, sheet_name='MODELO_INVERSIONES', index=False)
        df_ml_access.to_excel(
            writer, sheet_name='ML_ACCESS', index=False)
        df_cart_adcnl.to_excel(
            writer, sheet_name='CartAdcnl', index=False)
        # Hoja SIMBOLOGIA vacía (presente en el archivo original)
        pd.DataFrame().to_excel(
            writer, sheet_name='SIMBOLOGIA', index=False)

    if verbose:
        print(f"    ✓ Archivo generado: {ruta}")
        print(f"      INTERFAZ: {len(df_interfaz):,} filas")
        print(f"      MODELO_INVERSIONES: {len(df_modelo_inversiones):,} filas")
        print(f"      ML_ACCESS: {len(df_ml_access):,} filas")
        print(f"      CartAdcnl: {len(df_cart_adcnl):,} filas")

    return ruta
