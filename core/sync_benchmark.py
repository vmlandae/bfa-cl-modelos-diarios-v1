"""
Sincronizacion de benchmark historial a BigQuery.

Inserta cada entrada benchmark en una tabla dedicada ``reportes_benchmark``.
Si la insercion falla, se ignora silenciosamente (el JSONL local es respaldo).

Tabla destino:
    bfa_cl_prd_financial_risk_dly_proc_models.reportes_benchmark

Uso::

    from core.sync_benchmark import sync_benchmark_a_bigquery

    sync_benchmark_a_bigquery(entry_dict)
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuracion BigQuery
_PROJECT = "bfa-cl-trade-price-report-dev"
_DATASET = "bfa_cl_prd_financial_risk_dly_proc_models"
_TABLE = "reportes_benchmark"
_TABLE_FULL = f"{_PROJECT}.{_DATASET}.{_TABLE}"

_SCHEMA = [
    {"name": "fecha", "type": "DATE", "mode": "REQUIRED"},
    {"name": "timestamp_insert", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "total_seg", "type": "FLOAT", "mode": "REQUIRED"},
    {"name": "por_modelo", "type": "STRING", "mode": "NULLABLE"},
    {"name": "fase", "type": "STRING", "mode": "NULLABLE"},
    {"name": "hostname", "type": "STRING", "mode": "NULLABLE"},
    {"name": "status", "type": "STRING", "mode": "NULLABLE"},
]


def _get_bq_client():
    """Crea un cliente BigQuery usando las credenciales del proyecto."""
    from google.cloud import bigquery
    from config.config_rutas import obtener_ruta_credenciales_gcp
    import os

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
        obtener_ruta_credenciales_gcp()
    )
    return bigquery.Client(project=_PROJECT)


def _ensure_table(client) -> None:
    """Crea la tabla de benchmark si no existe."""
    from google.cloud import bigquery

    table_ref = client.dataset(_DATASET).table(_TABLE)
    try:
        client.get_table(table_ref)
    except Exception:
        schema = [
            bigquery.SchemaField(f["name"], f["type"], mode=f["mode"])
            for f in _SCHEMA
        ]
        table = bigquery.Table(table_ref, schema=schema)
        table.description = "Historial de benchmark de ejecucion de modelos RF"
        client.create_table(table)
        logger.info("Tabla %s creada en BigQuery", _TABLE_FULL)


def sync_benchmark_a_bigquery(entry: Dict[str, Any]) -> bool:
    """Inserta una entrada de benchmark en BigQuery.

    Args:
        entry: Dict con campos fecha, total_seg, por_modelo, fase, hostname, status.

    Returns:
        True si la insercion fue exitosa, False si fallo.
    """
    try:
        client = _get_bq_client()
        _ensure_table(client)

        row = {
            "fecha": entry["fecha"],
            "timestamp_insert": datetime.now().isoformat(),
            "total_seg": entry["total_seg"],
            "por_modelo": json.dumps(
                entry.get("por_modelo", {}), ensure_ascii=False
            ),
            "fase": entry.get("fase", "mixta"),
            "hostname": entry.get("hostname", ""),
            "status": entry.get("status", ""),
        }

        errors = client.insert_rows_json(_TABLE_FULL, [row])

        if errors:
            logger.warning("Error insertando benchmark en BQ: %s", errors)
            return False

        logger.info("Benchmark sincronizado a BigQuery: %s", _TABLE_FULL)
        return True

    except Exception as e:
        logger.debug("No se pudo sincronizar benchmark a BQ: %s", e)
        return False


def cargar_benchmark_desde_bq(dias: int = 90) -> List[Dict[str, Any]]:
    """Lee historial de benchmark desde BigQuery.

    Args:
        dias: Cantidad de dias hacia atras a consultar.

    Returns:
        Lista de dicts con el mismo formato que historial.jsonl.
    """
    try:
        from google.cloud import bigquery as bq

        client = _get_bq_client()
        sql = f"""
            SELECT fecha, total_seg, por_modelo, fase, hostname, status
            FROM `{_TABLE_FULL}`
            WHERE fecha >= DATE_SUB(CURRENT_DATE(), INTERVAL @dias DAY)
            ORDER BY fecha, timestamp_insert
        """
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("dias", "INT64", dias),
            ]
        )
        df = client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
        if df.empty:
            return []

        entries: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            por_modelo: dict = {}
            raw = row.get("por_modelo")
            if raw:
                try:
                    por_modelo = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    pass
            entries.append({
                "fecha": str(row["fecha"]),
                "total_seg": float(row["total_seg"]),
                "por_modelo": por_modelo,
                "fase": row.get("fase", "mixta"),
                "hostname": row.get("hostname", ""),
                "status": row.get("status", ""),
            })
        return entries

    except Exception as e:
        logger.debug("No se pudo leer benchmark desde BQ: %s", e)
        return []


def seed_benchmark_desde_jsonl() -> int:
    """Carga el historial JSONL existente a BigQuery (migracion unica).

    Returns:
        Cantidad de entradas insertadas exitosamente.
    """
    jsonl_path = BASE_DIR / "data" / "benchmark" / "historial.jsonl"
    if not jsonl_path.exists():
        logger.info("No hay historial.jsonl para migrar")
        return 0

    entries: list[dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return 0

    ok = 0
    for entry in entries:
        if sync_benchmark_a_bigquery(entry):
            ok += 1

    logger.info("Seed completado: %d/%d entradas migradas a BQ", ok, len(entries))
    return ok
