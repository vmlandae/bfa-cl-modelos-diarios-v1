"""Lectura de datos locales: reportes, logs, snapshots, benchmarks."""

import json
from pathlib import Path
from typing import Optional

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Reportes de ejecución
# ---------------------------------------------------------------------------

def _reports_dir() -> Path:
    return _BASE_DIR / "reports"


def listar_fechas_con_reporte() -> list[str]:
    """Devuelve fechas YYYYMMDD que tienen reporte_ejecucion.json, desc."""
    carpetas = []
    reports = _reports_dir()
    if not reports.exists():
        return []
    for d in reports.iterdir():
        if d.is_dir() and (d / "reporte_ejecucion.json").exists():
            carpetas.append(d.name)
    return sorted(carpetas, reverse=True)


def cargar_reporte_ejecucion(fecha_yyyymmdd: str) -> Optional[dict]:
    """Lee reporte_ejecucion.json de una fecha dada (local)."""
    path = _reports_dir() / fecha_yyyymmdd / "reporte_ejecucion.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Logs JSONL
# ---------------------------------------------------------------------------

def _logs_dir() -> Path:
    return _BASE_DIR / "logs"


def listar_fechas_con_log() -> list[str]:
    """Devuelve fechas YYYYMMDD que tienen modelos.jsonl, desc."""
    carpetas = []
    logs = _logs_dir()
    if not logs.exists():
        return []
    for d in logs.iterdir():
        if d.is_dir() and (d / "modelos.jsonl").exists():
            carpetas.append(d.name)
    return sorted(carpetas, reverse=True)


def cargar_log_jsonl(fecha_yyyymmdd: str) -> list[dict]:
    """Parsea modelos.jsonl de una fecha, omitiendo líneas inválidas."""
    path = _logs_dir() / fecha_yyyymmdd / "modelos.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ---------------------------------------------------------------------------
# Snapshots / Manifests
# ---------------------------------------------------------------------------

def _snapshots_dir() -> Path:
    return _BASE_DIR / "snapshots"


def listar_fechas_con_snapshot() -> list[str]:
    """Devuelve fechas YYYYMMDD que tienen manifest, desc."""
    manifests = _snapshots_dir() / "manifests"
    if not manifests.exists():
        return []
    return sorted(
        [p.stem for p in manifests.glob("*.json")],
        reverse=True,
    )


def cargar_manifest_snapshot(fecha_yyyymmdd: str) -> Optional[dict]:
    """Lee el manifest de snapshots de una fecha."""
    path = _snapshots_dir() / "manifests" / f"{fecha_yyyymmdd}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Benchmark historial
# ---------------------------------------------------------------------------

def cargar_benchmark_historial() -> list[dict]:
    """Lee todas las entradas del benchmark JSONL."""
    path = _BASE_DIR / "data" / "benchmark" / "historial.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
