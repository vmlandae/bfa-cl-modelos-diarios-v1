"""
Carga puntual del Excel productivo de Prepago CMR a la tabla BQ
report_mr_prepago_cmr_dly para una fecha de proceso.

Uso:
    python -m tools.cargar_prepago_cmr_productivo 2026-04-24
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

# Path por defecto: productivo historico
RUTA_PRODUCTIVO_TEMPLATE = (
    r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Prepago_CMR\Prepago_CMR_Historia"
    r"\{fecha_compacta}_Prepago_TC_CMR.xlsx"
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python -m tools.cargar_prepago_cmr_productivo YYYY-MM-DD [ruta_xlsm]")
        return 1

    fecha = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d")
    fecha_compacta = fecha.strftime("%Y%m%d")

    if len(sys.argv) >= 3:
        ruta = Path(sys.argv[2])
    else:
        ruta = Path(RUTA_PRODUCTIVO_TEMPLATE.format(fecha_compacta=fecha_compacta))

    if not ruta.exists():
        print(f"ERROR: no existe el archivo {ruta}")
        return 1

    print(f"Fecha: {fecha.date()}")
    print(f"Origen: {ruta}")
    print(f"Destino BQ: report_mr_prepago_cmr_dly (TRUNCATE)")
    print()

    resultado = cargar_tablas_bigquery(
        fecha_t=fecha,
        ruta_archivo=ruta,
        hoja_archivo="DESARROLLO",
        tabla_respaldo="report_mr_prepago_cmr_dly",
        esquema_tabla=crear_esquema_base(),
        tipo_carga="TRUNCATE",
    )
    print(resultado)
    return 0 if str(resultado).startswith("[") and "Carga exitosa" in str(resultado) else 1


if __name__ == "__main__":
    sys.exit(main())
