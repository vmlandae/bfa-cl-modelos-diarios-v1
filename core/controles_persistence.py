"""Persistencia BigQuery de la tabla ``controles_diarios`` (F29).

Patrón calcado de ``core/sync_reportes.py`` + ``core/sync_benchmark.py``:
- Crear tabla si no existe (particionada por fecha_proceso, clusterizada).
- Insertar filas vía ``insert_rows_json``.
- Fallback local en ``reports/_pendientes_controles/`` si BQ falla.
- ``sync_pendientes()`` retrasalos posteriormente.

El dataset destino es el mismo que ``reportes_ejecucion``:
``bfa_cl_prd_financial_risk_dly_proc_models``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from google.cloud import bigquery

from config.config_rutas import BASE_DIR

if TYPE_CHECKING:  # pragma: no cover
    from core.controles_outputs import ResultadoControles

logger = logging.getLogger("bfa_modelos.controles_persistence")

_PROJECT_ID = "bfa-cl-trade-price-report-dev"
_DATASET = "bfa_cl_prd_financial_risk_dly_proc_models"
_TABLA = "controles_diarios"
_TABLA_REF = f"{_PROJECT_ID}.{_DATASET}.{_TABLA}"

_PENDIENTES_DIR = BASE_DIR / "reports" / "_pendientes_controles"


_SCHEMA = [
    bigquery.SchemaField("fecha_proceso", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("hostname", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("modelo", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("tabla", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("check_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("nivel", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("mensaje", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("evidencia_json", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("fecha_anterior", "DATE", mode="NULLABLE"),
    bigquery.SchemaField("version_motor", "STRING", mode="NULLABLE"),
]


def _get_client() -> bigquery.Client:
    from config.config_rutas import obtener_ruta_credenciales_gcp
    cred_path = obtener_ruta_credenciales_gcp()
    return bigquery.Client.from_service_account_json(str(cred_path))


def crear_tabla_si_no_existe(client: Optional[bigquery.Client] = None) -> None:
    """Idempotente. Crea la tabla particionada+clusterizada si no existe."""
    cli = client or _get_client()
    try:
        cli.get_table(_TABLA_REF)
        return
    except Exception:
        pass

    tabla = bigquery.Table(_TABLA_REF, schema=_SCHEMA)
    tabla.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="fecha_proceso",
    )
    tabla.clustering_fields = ["modelo", "nivel"]
    cli.create_table(tabla)
    logger.info("Tabla %s creada (particionada + clusterizada).", _TABLA_REF)


def _check_a_row(check, fecha_proceso: str) -> dict:
    """Serializa un CheckResultado a dict listo para insert_rows_json."""
    return {
        "fecha_proceso": fecha_proceso,
        "timestamp": check.timestamp,
        "hostname": check.hostname,
        "modelo": check.modelo,
        "tabla": check.tabla,
        "check_id": check.check_id,
        "nivel": check.nivel,
        "mensaje": check.mensaje,
        "evidencia_json": json.dumps(check.evidencia, ensure_ascii=False, default=str),
        "fecha_anterior": check.fecha_anterior,
        "version_motor": check.version_motor,
    }


def escribir(resultado: "ResultadoControles") -> bool:
    """Persiste resultado en BQ. Si falla, guarda localmente para retry."""
    rows = [_check_a_row(c, resultado.fecha_proceso) for c in resultado.todos]
    if not rows:
        return True

    try:
        client = _get_client()
        crear_tabla_si_no_existe(client)
        errors = client.insert_rows_json(_TABLA_REF, rows)
        if errors:
            logger.error("Errores al insertar a %s: %s", _TABLA_REF, errors)
            _guardar_pendiente(rows, resultado.fecha_proceso, str(errors))
            return False
        logger.info("Persistidas %d filas a %s.", len(rows), _TABLA_REF)
        return True
    except Exception as exc:
        logger.exception("Excepción al persistir a %s: %s", _TABLA_REF, exc)
        _guardar_pendiente(rows, resultado.fecha_proceso, str(exc))
        return False


def _guardar_pendiente(rows: list[dict], fecha_proceso: str, motivo: str) -> Path:
    """Fallback local: vuelca filas a un JSON en ``reports/_pendientes_controles/``."""
    _PENDIENTES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = _PENDIENTES_DIR / f"{fecha_proceso}__{ts}.json"
    ruta.write_text(
        json.dumps({"motivo": motivo, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.warning("Filas guardadas localmente en %s para retry posterior.", ruta)
    return ruta


def sync_pendientes() -> int:
    """Reintenta subir todos los JSON pendientes. Retorna # filas subidas."""
    if not _PENDIENTES_DIR.exists():
        return 0
    pendientes = sorted(_PENDIENTES_DIR.glob("*.json"))
    if not pendientes:
        return 0

    client = _get_client()
    crear_tabla_si_no_existe(client)
    total = 0
    for ruta in pendientes:
        try:
            payload = json.loads(ruta.read_text(encoding="utf-8"))
            rows = payload.get("rows", [])
            if not rows:
                ruta.unlink()
                continue
            errors = client.insert_rows_json(_TABLA_REF, rows)
            if errors:
                logger.error("Sync pendiente %s falló: %s", ruta.name, errors)
                continue
            total += len(rows)
            ruta.unlink()
            logger.info("Sync pendiente %s OK (%d filas).", ruta.name, len(rows))
        except Exception as exc:
            logger.exception("No se pudo sincronizar %s: %s", ruta, exc)
    return total


def leer(
    fecha_desde: str,
    fecha_hasta: Optional[str] = None,
    nivel_min: str = "OK",
    modelos: Optional[list[str]] = None,
):
    """Lee controles diarios de un rango. Retorna DataFrame.

    Args:
        fecha_desde: ISO YYYY-MM-DD inclusive.
        fecha_hasta: ISO YYYY-MM-DD inclusive (default = fecha_desde).
        nivel_min: filtra niveles ≥ nivel_min (orden: INFO < OK < WARNING < CRITICAL).
        modelos: lista de keys de modelo (None = todos).
    """
    import pandas as pd  # lazy
    fecha_hasta = fecha_hasta or fecha_desde
    nivel_orden = {"INFO": 0, "OK": 1, "WARNING": 2, "CRITICAL": 3}
    min_rank = nivel_orden.get(nivel_min.upper(), 1)
    niveles_validos = [k for k, v in nivel_orden.items() if v >= min_rank]

    client = _get_client()
    try:
        client.get_table(_TABLA_REF)
    except Exception:
        return pd.DataFrame()

    sql = f"""
        SELECT *
        FROM `{_TABLA_REF}`
        WHERE fecha_proceso BETWEEN @desde AND @hasta
          AND nivel IN UNNEST(@niveles)
          {"AND modelo IN UNNEST(@modelos)" if modelos else ""}
        ORDER BY fecha_proceso DESC, modelo, nivel DESC, check_id
    """
    params = [
        bigquery.ScalarQueryParameter("desde", "DATE", fecha_desde),
        bigquery.ScalarQueryParameter("hasta", "DATE", fecha_hasta),
        bigquery.ArrayQueryParameter("niveles", "STRING", niveles_validos),
    ]
    if modelos:
        params.append(bigquery.ArrayQueryParameter("modelos", "STRING", modelos))
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    return client.query(sql, job_config=job_config).to_dataframe(
        create_bqstorage_client=False
    )


def _cli() -> int:
    """CLI auxiliar: crear tabla, sync de pendientes, lectura rápida."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Persistencia BQ de controles_diarios (F29)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("crear-tabla")
    sub.add_parser("sync-pendientes")
    leer_p = sub.add_parser("leer")
    leer_p.add_argument("--desde", required=True)
    leer_p.add_argument("--hasta", default=None)
    leer_p.add_argument("--nivel-min", default="OK")
    leer_p.add_argument("--modelos", nargs="*", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "crear-tabla":
        crear_tabla_si_no_existe()
        print(f"Tabla {_TABLA_REF} OK.")
    elif args.cmd == "sync-pendientes":
        n = sync_pendientes()
        print(f"{n} filas sincronizadas desde pendientes.")
    elif args.cmd == "leer":
        df = leer(args.desde, args.hasta, args.nivel_min, args.modelos)
        print(df.to_string(index=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_cli())
