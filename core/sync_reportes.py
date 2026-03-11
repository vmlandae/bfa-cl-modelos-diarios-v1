"""
Sincronización de reportes de ejecución a BigQuery.

Inserta el reporte JSON completo + log JSONL en una tabla de BigQuery
para supervisión remota. Si la inserción falla (sin internet, permisos, etc.),
guarda el reporte localmente como pendiente para reintento posterior.

Tabla destino:
    bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion

Uso::

    from core.sync_reportes import sync_reporte_a_bigquery

    # Después de generar el reporte
    sync_reporte_a_bigquery(reporte_dict, log_jsonl_path)
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración BigQuery
_PROJECT = "bfa-cl-trade-price-report-dev"
_DATASET = "bfa_cl_prd_financial_risk_dly_proc_models"
_TABLE = "reportes_ejecucion"
_TABLE_FULL = f"{_PROJECT}.{_DATASET}.{_TABLE}"

# Cola local de reportes pendientes (si BQ falla)
_PENDING_DIR = BASE_DIR / "reports" / "_pendientes_sync"

# Esquema de la tabla (para auto-creación)
_SCHEMA = [
    {"name": "fecha_proceso", "type": "DATE", "mode": "REQUIRED"},
    {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "hostname", "type": "STRING", "mode": "REQUIRED"},
    {"name": "status_global", "type": "STRING", "mode": "REQUIRED"},
    {"name": "duracion_total_seg", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "modelos_ok", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "modelos_error", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "alertas", "type": "STRING", "mode": "REPEATED"},
    {"name": "reporte_json", "type": "STRING", "mode": "NULLABLE"},
    {"name": "log_jsonl", "type": "STRING", "mode": "NULLABLE"},
]


def _get_bq_client():
    """Crea un cliente BigQuery usando las credenciales del proyecto."""
    from google.cloud import bigquery
    from config.config_rutas import obtener_ruta_credenciales_gcp
    import os

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(obtener_ruta_credenciales_gcp())
    return bigquery.Client(project=_PROJECT)


def _ensure_table(client) -> None:
    """Crea la tabla de reportes si no existe."""
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
        table.description = "Reportes de ejecución diaria de modelos RF"
        client.create_table(table)
        logger.info(f"📋 Tabla {_TABLE_FULL} creada en BigQuery")


def _leer_log_jsonl(fecha_str: str) -> str:
    """Lee el archivo de log JSONL de la fecha dada."""
    log_path = BASE_DIR / "logs" / fecha_str / "modelos.jsonl"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8")
        # Limitar a 1MB para no exceder límites de BQ STRING
        if len(content) > 1_000_000:
            content = content[:1_000_000] + "\n... (truncado a 1MB)"
        return content
    return ""


def sync_reporte_a_bigquery(
    reporte: Dict[str, Any],
    fecha_str: Optional[str] = None,
) -> bool:
    """Inserta el reporte de ejecución en BigQuery.

    Args:
        reporte: Dict generado por ReporteEjecucion.generar().
        fecha_str: Fecha YYYYMMDD para leer los logs. Si None, se deriva del reporte.

    Returns:
        True si la inserción fue exitosa, False si falló (queda pendiente local).
    """
    if fecha_str is None:
        fecha_str = reporte.get("fecha_proceso", "").replace("-", "")

    try:
        client = _get_bq_client()
        _ensure_table(client)

        log_content = _leer_log_jsonl(fecha_str)

        row = {
            "fecha_proceso": reporte["fecha_proceso"],
            "timestamp": reporte["timestamp"],
            "hostname": reporte["hostname"],
            "status_global": reporte["status_global"],
            "duracion_total_seg": reporte.get("duracion_total_seg"),
            "modelos_ok": reporte.get("modelos_ok"),
            "modelos_error": reporte.get("modelos_error"),
            "alertas": reporte.get("alertas", []),
            "reporte_json": json.dumps(reporte, ensure_ascii=False),
            "log_jsonl": log_content,
        }

        errors = client.insert_rows_json(_TABLE_FULL, [row])

        if errors:
            logger.error(f"❌ Error insertando reporte en BQ: {errors}")
            _guardar_pendiente(reporte, fecha_str)
            return False

        logger.info(f"✅ Reporte sincronizado a BigQuery: {_TABLE_FULL}")
        return True

    except Exception as e:
        logger.warning(
            f"⚠️ No se pudo sincronizar reporte a BigQuery: {e}. "
            "Guardado localmente como pendiente."
        )
        logger.debug(traceback.format_exc())
        _guardar_pendiente(reporte, fecha_str)
        return False


def _guardar_pendiente(reporte: Dict[str, Any], fecha_str: str) -> None:
    """Guarda el reporte como archivo pendiente para reintento posterior."""
    _PENDING_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _PENDING_DIR / f"reporte_{fecha_str}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Reporte pendiente guardado: {path}")


def sync_pendientes() -> int:
    """Reintenta sincronizar reportes pendientes.

    Returns:
        Cantidad de reportes sincronizados exitosamente.
    """
    if not _PENDING_DIR.exists():
        return 0

    pendientes = sorted(_PENDING_DIR.glob("reporte_*.json"))
    if not pendientes:
        return 0

    logger.info(f"🔄 Reintentando {len(pendientes)} reportes pendientes...")
    ok_count = 0

    for path in pendientes:
        try:
            with open(path, "r", encoding="utf-8") as f:
                reporte = json.load(f)
            fecha_str = reporte.get("fecha_proceso", "").replace("-", "")

            client = _get_bq_client()
            _ensure_table(client)

            log_content = _leer_log_jsonl(fecha_str)

            row = {
                "fecha_proceso": reporte["fecha_proceso"],
                "timestamp": reporte["timestamp"],
                "hostname": reporte["hostname"],
                "status_global": reporte["status_global"],
                "duracion_total_seg": reporte.get("duracion_total_seg"),
                "modelos_ok": reporte.get("modelos_ok"),
                "modelos_error": reporte.get("modelos_error"),
                "alertas": reporte.get("alertas", []),
                "reporte_json": json.dumps(reporte, ensure_ascii=False),
                "log_jsonl": log_content,
            }

            errors = client.insert_rows_json(_TABLE_FULL, [row])
            if not errors:
                path.unlink()
                ok_count += 1
                logger.info(f"✅ Pendiente sincronizado: {path.name}")
            else:
                logger.warning(f"⚠️ Pendiente aún con error: {path.name} → {errors}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo sincronizar pendiente {path.name}: {e}")

    return ok_count
