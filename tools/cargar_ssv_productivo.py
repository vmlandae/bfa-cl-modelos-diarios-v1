"""
Carga puntual del Excel productivo MT_SSV a la tabla BQ
report_mr_ssv_dly para una fecha de proceso.

Lee la hoja DESARROLLO del MT_SSV.XLSM productivo (red Z:) y la sube
a BigQuery con TRUNCATE, reutilizando la misma logica de carga que el
pipeline diario (`cargar_tablas_bigquery`).

Uso:
    python -m tools.cargar_ssv_productivo YYYY-MM-DD [ruta_xlsm]
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from carga_modelos_gcp.cargar_output_modelos_bigquery_dly import (
    cargar_tablas_bigquery,
    crear_esquema_base,
)

# Path por defecto: MT productivo en la red corporativa.
RUTA_PRODUCTIVA_DEFAULT = (
    r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\MT_SSV.XLSM"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python -m tools.cargar_ssv_productivo YYYY-MM-DD [ruta_xlsm]")
        return 1

    try:
        fecha = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{sys.argv[1]}' incorrecto. Use YYYY-MM-DD.")
        return 1

    if len(sys.argv) >= 3:
        ruta = Path(sys.argv[2])
    else:
        ruta = Path(RUTA_PRODUCTIVA_DEFAULT)

    if not ruta.exists():
        print(f"ERROR: no existe el archivo {ruta}")
        return 1

    print(f"Fecha:      {fecha.date()}")
    print(f"Origen:     {ruta}")
    print(f"Hoja:       DESARROLLO")
    print(f"Destino BQ: report_mr_ssv_dly (TRUNCATE)")
    print()

    resultado = cargar_tablas_bigquery(
        fecha_t=fecha,
        ruta_archivo=ruta,
        hoja_archivo="DESARROLLO",
        tabla_respaldo="report_mr_ssv_dly",
        esquema_tabla=crear_esquema_base(),
        tipo_carga="TRUNCATE",
    )
    print(resultado)
    ok = isinstance(resultado, str) and "Carga exitosa" in resultado
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
