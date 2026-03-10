"""
Escritura de archivos Excel con xlsxwriter.

Reemplaza el uso de ut.cargar_datos_xlsm() (openpyxl) por escritura directa
con xlsxwriter, que es ~2x mas rapido para crear archivos nuevos.

Uso tipico:
    guardar_excel(
        ruta_archivo="output/modelo.xlsx",
        hojas={"DESARROLLO": df_desarrollo, "FLUJOS": df_flujos},
        formatos_columnas={"FECHA_PROCESO": "dd-mm-yyyy", "MONTO": "#,##0.00"}
    )
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Union
from collections import OrderedDict


def guardar_excel(
    ruta_archivo: Union[str, Path],
    hojas: Dict[str, pd.DataFrame],
    formatos_columnas: Optional[Dict[str, str]] = None,
) -> Path:
    """
    Escribe un archivo Excel (.xlsx) con una o mas hojas usando xlsxwriter.

    A diferencia de ut.cargar_datos_xlsm (que abre un .xlsm existente y
    reescribe hoja por hoja con openpyxl), esta funcion crea el archivo
    desde cero. Todas las hojas deben proporcionarse de una vez.

    Args:
        ruta_archivo: Ruta del archivo de salida.
        hojas: Dict ordenado {nombre_hoja: DataFrame}.
        formatos_columnas: Dict {nombre_columna: formato_excel} aplicado a
            todas las hojas que contengan esa columna.
            Ej: {"FECHA_PROCESO": "dd-mm-yyyy", "MONTO": "#,##0.00"}

    Returns:
        Path del archivo generado.
    """
    ruta = Path(ruta_archivo)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(ruta, engine='xlsxwriter') as writer:
        for nombre_hoja, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)

            if formatos_columnas:
                workbook = writer.book
                worksheet = writer.sheets[nombre_hoja]
                for col_idx, col_name in enumerate(df.columns):
                    if col_name in formatos_columnas:
                        fmt = workbook.add_format(
                            {'num_format': formatos_columnas[col_name]}
                        )
                        worksheet.set_column(col_idx, col_idx, None, fmt)

    return ruta
