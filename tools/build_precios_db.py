"""
Script para construir y mantener una base SQLite consolidada
con arquitectura writer/reader:

- writer: actualiza DB maestra en red (solo proceso central)
- reader: sincroniza copia local si cambia version remota

Uso:
    python tools/build_precios_db.py --role reader
    python tools/build_precios_db.py --role writer 20260325

Notas:
- En modo writer se aplica lock de archivo para evitar doble escritura.
- En modo reader no se procesan parquets: solo sync de la DB local.
"""

import argparse
import getpass
import glob
import hashlib
import json
import logging
import os
import shutil
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuracion base
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
DEFAULT_LOCAL_DB_PATH = os.path.join(BASE_DIR, "data", "precios_historico.db")
CONFIG_EXT_YAML = os.path.join(BASE_DIR, "config", "config_rutas_ext_y_archivos.yaml")
PARQUET_PATTERN = "RF_Base_Diaria_Precios_*.parquet"

DEFAULT_REMOTE_DB_PATH = r"\\vmdvorak\RF_PROCESOS\RF_Modelos\db_precios.db"
DEFAULT_REMOTE_VERSION_PATH = r"\\vmdvorak\RF_PROCESOS\RF_Modelos\db_precios.version"
DEFAULT_CSV_TCRC_PATH = r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Modelos\precios_TCRC.csv"
DEFAULT_READER_ROLE = "reader"
WRITER_LOCK_TIMEOUT_MINUTES = 10
MAX_LOCAL_FALLBACK_AGE_HOURS = 24

TABLE_PRECIOS = "precios"
TABLE_CAMBIOS = "cambios_audit"
TABLE_HASHES = "fecha_hashes"
TABLE_ARCHIVOS = "archivos_procesados"

DATA_COLS = [
    "Fecha",
    "ID_1",
    "ID_2",
    "ID_3",
    "ID_4",
    "ID_5",
    "NEMOTECNICO",
    "Instrumento",
    "Moneda",
    "Fuente",
    "Composicion",
    "Base",
    "Tipo",
    "Calculo",
    "Generico",
    "Familia",
    "Plazo_Ini",
    "Plazo_Fin",
    "Tasa_Bid",
    "Tasa_Mid",
    "Tasa_offer",
    "Precio_Bid",
    "Precio_Mid",
    "Precio_offer",
]

NUMERIC_COLS = [
    "Plazo_Ini",
    "Plazo_Fin",
    "Tasa_Bid",
    "Tasa_Mid",
    "Tasa_offer",
    "Precio_Bid",
    "Precio_Mid",
    "Precio_offer",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de configuracion/version
# ---------------------------------------------------------------------------
def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_external_config() -> dict:
    if not os.path.exists(CONFIG_EXT_YAML):
        return {}

    try:
        import yaml

        with open(CONFIG_EXT_YAML, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        log.warning("No se pudo leer config externa: %s", e)
        return {}


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute() or path_str.startswith("\\\\"):
        return path
    return Path(BASE_DIR) / path


def _precios_settings() -> dict:
    cfg = _load_external_config().get("precios_db", {})

    local_db = str(_resolve_path(cfg.get("db_local", DEFAULT_LOCAL_DB_PATH)))
    remote_db = str(_resolve_path(cfg.get("db_maestra_red", DEFAULT_REMOTE_DB_PATH)))
    remote_version = str(
        _resolve_path(cfg.get("version_maestra_red", DEFAULT_REMOTE_VERSION_PATH))
    )
    csv_tcrc = str(_resolve_path(cfg.get("csv_tcrc_red", DEFAULT_CSV_TCRC_PATH)))
    role = str(cfg.get("rol_orquestador", DEFAULT_READER_ROLE)).strip().lower()

    return {
        "local_db": local_db,
        "remote_db": remote_db,
        "remote_version": remote_version,
        "csv_tcrc": csv_tcrc,
        "role": role if role in {"reader", "writer"} else DEFAULT_READER_ROLE,
    }


def _read_version_file(version_path: str) -> dict | None:
    path = Path(version_path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Version invalida en %s: %s", path, e)
        return None


def _write_version_file(version_path: str, payload: dict) -> None:
    path = Path(version_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _copy_file_atomic(src: str, dst: str) -> None:
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dst_path.with_suffix(dst_path.suffix + ".tmp")
    shutil.copy2(src, tmp_path)
    os.replace(tmp_path, dst_path)


def _remote_version_fallback(remote_db_path: str) -> dict | None:
    db_path = Path(remote_db_path)
    if not db_path.exists():
        return None

    ts = datetime.fromtimestamp(db_path.stat().st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "version_utc": ts,
        "source": "remote_db_mtime_fallback",
        "fecha_proceso": "unknown",
        "row_count": None,
        "updated_by": "unknown",
        "host": "unknown",
    }


def _parse_version_utc(version_utc: str) -> datetime | None:
    """Parsea timestamp UTC del sidecar .version (YYYY-mm-ddTHH:MM:SSZ)."""
    if not version_utc:
        return None
    try:
        return datetime.strptime(version_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        return None


def _local_copy_age_hours(local_db_path: str, local_version_path: str) -> float | None:
    """Retorna antiguedad en horas de la copia local, usando .version o mtime."""
    now = datetime.now(timezone.utc)
    local_version = _read_version_file(local_version_path)

    if local_version:
        dt = _parse_version_utc(local_version.get("version_utc", ""))
        if dt:
            return (now - dt).total_seconds() / 3600

    db_path = Path(local_db_path)
    if db_path.exists():
        dt = datetime.fromtimestamp(db_path.stat().st_mtime, timezone.utc)
        return (now - dt).total_seconds() / 3600

    return None


def _log_fallback_staleness(local_db_path: str, local_version_path: str) -> None:
    """Loguea estado de antiguedad de la copia local en modo fallback."""
    age_h = _local_copy_age_hours(local_db_path, local_version_path)
    if age_h is None:
        log.warning("Fallback local: no fue posible estimar antiguedad de la copia.")
        return

    if age_h <= MAX_LOCAL_FALLBACK_AGE_HOURS:
        log.warning(
            "Fallback local habilitado: copia local con antiguedad %.1f h (<= %d h).",
            age_h,
            MAX_LOCAL_FALLBACK_AGE_HOURS,
        )
        return

    log.warning(
        "WARNING FUERTE: usando copia local con antiguedad %.1f h (> %d h). "
        "Revisar conectividad de red y refrescar DB local lo antes posible.",
        age_h,
        MAX_LOCAL_FALLBACK_AGE_HOURS,
    )


def sync_local_db_from_master() -> tuple[bool, str]:
    """
    Sincroniza DB local desde maestra remota solo si cambia version.

    Returns:
        (hubo_copia, motivo)
    """
    settings = _precios_settings()
    local_db = settings["local_db"]
    remote_db = settings["remote_db"]
    remote_version_path = settings["remote_version"]
    local_version_path = str(Path(local_db).with_suffix(".version"))

    remote_db_exists = Path(remote_db).exists()
    local_db_exists = Path(local_db).exists()

    if not remote_db_exists:
        if local_db_exists:
            log.warning("DB maestra no disponible. Se usa copia local existente.")
            _log_fallback_staleness(local_db, local_version_path)
            return False, "fallback_local_no_remote"
        raise RuntimeError(
            f"No existe DB maestra en red ({remote_db}) y no hay copia local disponible."
        )

    remote_version = _read_version_file(remote_version_path)
    if remote_version is None:
        remote_version = _remote_version_fallback(remote_db)
        log.warning("No existe .version remoto. Se usa fallback por mtime.")

    if remote_version is None:
        if local_db_exists:
            log.warning("No se pudo inferir version remota. Se usa copia local existente.")
            _log_fallback_staleness(local_db, local_version_path)
            return False, "fallback_local_no_remote_version"
        raise RuntimeError("No se pudo obtener version remota para bootstrap local.")

    local_version = _read_version_file(local_version_path)
    remote_version_utc = remote_version.get("version_utc")
    local_version_utc = (local_version or {}).get("version_utc")

    if not local_db_exists:
        _copy_file_atomic(remote_db, local_db)
        _write_version_file(local_version_path, remote_version)
        log.info("Bootstrap local desde DB maestra completado.")
        return True, "bootstrap"

    if local_version_utc and remote_version_utc and local_version_utc == remote_version_utc:
        log.info("DB local ya esta en ultima version (%s).", remote_version_utc)
        return False, "up_to_date"

    _copy_file_atomic(remote_db, local_db)
    _write_version_file(local_version_path, remote_version)
    log.info("DB local sincronizada a version remota %s.", remote_version_utc)
    return True, "updated"


# ---------------------------------------------------------------------------
# Writer lock
# ---------------------------------------------------------------------------
def _writer_lock_path(remote_db_path: str) -> str:
    return str(Path(remote_db_path).with_suffix(Path(remote_db_path).suffix + ".lock"))


def _acquire_writer_lock(remote_db_path: str) -> str:
    lock_path = _writer_lock_path(remote_db_path)
    lock = Path(lock_path)
    now = datetime.now(timezone.utc)

    if lock.exists():
        age_minutes = (
            now - datetime.fromtimestamp(lock.stat().st_mtime, timezone.utc)
        ).total_seconds() / 60
        if age_minutes > WRITER_LOCK_TIMEOUT_MINUTES:
            log.warning("Lock stale detectado (%.1f min). Se reemplaza.", age_minutes)
            lock.unlink()
        else:
            raise RuntimeError(
                f"Existe lock activo en {lock_path}. Reintente mas tarde o espere timeout."
            )

    payload = {
        "created_at_utc": _utc_now_str(),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "pid": os.getpid(),
    }
    with open(lock, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return lock_path


def _release_writer_lock(lock_path: str) -> None:
    path = Path(lock_path)
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# DB logic
# ---------------------------------------------------------------------------
def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_PRECIOS} (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha          TEXT NOT NULL,
            ID_1           TEXT,
            ID_2           TEXT,
            ID_3           TEXT,
            ID_4           TEXT,
            ID_5           TEXT,
            NEMOTECNICO    TEXT,
            Instrumento    TEXT,
            Moneda         TEXT,
            Fuente         TEXT,
            Composicion    TEXT,
            Base           TEXT,
            Tipo           TEXT,
            Calculo        TEXT,
            Generico       TEXT,
            Familia        TEXT,
            Plazo_Ini      REAL,
            Plazo_Fin      REAL,
            Tasa_Bid       REAL,
            Tasa_Mid       REAL,
            Tasa_offer     REAL,
            Precio_Bid     REAL,
            Precio_Mid     REAL,
            Precio_offer   REAL
        )
    """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_HASHES} (
            Fecha          TEXT PRIMARY KEY,
            block_hash     TEXT NOT NULL,
            n_rows         INTEGER,
            updated_at     TEXT
        )
    """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_CAMBIOS} (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha          TEXT,
            filas_anterior INTEGER,
            filas_nuevo    INTEGER,
            hash_anterior  TEXT,
            hash_nuevo     TEXT,
            detectado_en   TEXT
        )
    """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ARCHIVOS} (
            filename       TEXT PRIMARY KEY,
            processed_at   TEXT
        )
    """
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_precios_fecha ON {TABLE_PRECIOS} (Fecha)")
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_precios_instrumento ON {TABLE_PRECIOS} (Instrumento)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_precios_nemotecnico ON {TABLE_PRECIOS} (NEMOTECNICO)"
    )
    conn.commit()


def _fecha_fingerprint(count: int, sums: dict) -> str:
    parts = [str(count)]
    for col in NUMERIC_COLS:
        parts.append(f"{col}={sums.get(col, 0)}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _get_processed_files(conn: sqlite3.Connection) -> set:
    rows = conn.execute(f"SELECT filename FROM {TABLE_ARCHIVOS}").fetchall()
    return {r[0] for r in rows}


def _mark_processed(conn: sqlite3.Connection, filename: str) -> None:
    conn.execute(
        f"INSERT OR REPLACE INTO {TABLE_ARCHIVOS} (filename, processed_at) VALUES (?, ?)",
        (filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()


def process_parquet(conn: sqlite3.Connection, parquet_path: str) -> dict:
    log.info("Procesando %s ...", os.path.basename(parquet_path))

    df = pd.read_parquet(parquet_path)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=["Fecha"]).copy()
    n_dropped = n_before - len(df)
    if n_dropped:
        log.warning("  %d filas descartadas por Fecha invalida", n_dropped)
    df["Fecha"] = df["Fecha"].dt.strftime("%Y-%m-%d")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = {"inserted": 0, "replaced": 0, "unchanged": 0}

    grouped = df.groupby("Fecha")
    filas_por_fecha = grouped.size().to_dict()
    sums_por_fecha = grouped[NUMERIC_COLS].sum().to_dict(orient="index")
    new_hashes = {
        fecha: _fecha_fingerprint(filas_por_fecha[fecha], sums_por_fecha[fecha])
        for fecha in filas_por_fecha
    }
    fechas_en_lote = list(new_hashes.keys())

    placeholders = ",".join("?" for _ in fechas_en_lote)
    existing = pd.read_sql_query(
        f"SELECT Fecha, block_hash, n_rows FROM {TABLE_HASHES} WHERE Fecha IN ({placeholders})",
        conn,
        params=fechas_en_lote,
    )
    existing_hashes = dict(zip(existing["Fecha"], existing["block_hash"]))
    existing_rows = dict(zip(existing["Fecha"], existing["n_rows"]))

    set_nuevas = set(f for f in fechas_en_lote if f not in existing_hashes)
    set_cambio = set(
        f
        for f in fechas_en_lote
        if f in existing_hashes and existing_hashes[f] != new_hashes[f]
    )
    set_ok = set(
        f
        for f in fechas_en_lote
        if f in existing_hashes and existing_hashes[f] == new_hashes[f]
    )

    stats["unchanged"] = sum(filas_por_fecha.get(f, 0) for f in set_ok)

    if set_nuevas:
        df_new = df[df["Fecha"].isin(set_nuevas)][DATA_COLS]
        df_new.to_sql(TABLE_PRECIOS, conn, if_exists="append", index=False)
        stats["inserted"] += len(df_new)
        conn.executemany(
            f"INSERT INTO {TABLE_HASHES} (Fecha, block_hash, n_rows, updated_at) VALUES (?, ?, ?, ?)",
            [(f, new_hashes[f], filas_por_fecha.get(f, 0), now_str) for f in set_nuevas],
        )

    if set_cambio:
        df_cambio = df[df["Fecha"].isin(set_cambio)][DATA_COLS]
        conn.executemany(f"DELETE FROM {TABLE_PRECIOS} WHERE Fecha = ?", [(f,) for f in set_cambio])
        df_cambio.to_sql(TABLE_PRECIOS, conn, if_exists="append", index=False)
        stats["replaced"] += len(df_cambio)

        for fecha in set_cambio:
            n_rows = filas_por_fecha.get(fecha, 0)
            old_hash = existing_hashes[fecha]
            old_rows = existing_rows.get(fecha, 0)
            conn.execute(
                f"UPDATE {TABLE_HASHES} SET block_hash=?, n_rows=?, updated_at=? WHERE Fecha=?",
                (new_hashes[fecha], n_rows, now_str, fecha),
            )
            conn.execute(
                f"INSERT INTO {TABLE_CAMBIOS} (Fecha, filas_anterior, filas_nuevo, hash_anterior, hash_nuevo, detectado_en) VALUES (?,?,?,?,?,?)",
                (fecha, old_rows, n_rows, old_hash, new_hashes[fecha], now_str),
            )
            log.info("  CAMBIO en %s: %d -> %d filas", fecha, old_rows, n_rows)

    conn.commit()
    log.info(
        "  -> insertados=%d | reemplazados=%d | sin cambio=%d",
        stats["inserted"],
        stats["replaced"],
        stats["unchanged"],
    )
    return stats


def export_tcrc_csv(conn: sqlite3.Connection, csv_path: str) -> int:
    df_tcrc = pd.read_sql(
        "SELECT Fecha, Instrumento, Moneda, Base, Precio_Mid "
        "FROM precios WHERE Instrumento = 'TCRC' AND Moneda IN ('USD', 'CLF', 'CLP')",
        conn,
    )
    df_tcrc.columns = df_tcrc.columns.str.upper()

    out_path = Path(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_tcrc.to_csv(out_path, index=False, encoding="utf-8-sig", sep=";", decimal=",")
    log.info("CSV TCRC actualizado en %s con %d filas", out_path, len(df_tcrc))
    return len(df_tcrc)


def _update_remote_version(conn: sqlite3.Connection, fecha_proceso: str | None) -> None:
    settings = _precios_settings()
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_PRECIOS}").fetchone()[0]
    payload = {
        "version_utc": _utc_now_str(),
        "fecha_proceso": fecha_proceso or "ALL",
        "row_count": count,
        "updated_by": getpass.getuser(),
        "host": socket.gethostname(),
    }
    _write_version_file(settings["remote_version"], payload)
    log.info("Version remota actualizada: %s", payload["version_utc"])


def build_full(date_filter: str = None, force: bool = False, role: str | None = None) -> None:
    settings = _precios_settings()
    active_role = (role or settings["role"]).strip().lower()

    if active_role == "reader":
        _, reason = sync_local_db_from_master()
        log.info("Modo reader finalizado (%s).", reason)
        return

    if active_role != "writer":
        raise RuntimeError(f"Rol no soportado: {active_role}")

    lock_path = _acquire_writer_lock(settings["remote_db"])
    log.info("Lock writer adquirido en %s", lock_path)

    pattern = os.path.join(CACHE_DIR, PARQUET_PATTERN)
    files = sorted(glob.glob(pattern))

    if not files:
        _release_writer_lock(lock_path)
        raise RuntimeError(f"No se encontraron archivos en {pattern}")

    if date_filter:
        files = [f for f in files if date_filter in os.path.basename(f)]
        if not files:
            _release_writer_lock(lock_path)
            raise RuntimeError(f"No se encontro archivo para fecha {date_filter}")

    log.info("Modo writer. DB maestra: %s", settings["remote_db"])

    conn = sqlite3.connect(settings["remote_db"])
    try:
        _init_db(conn)

        if not force:
            already = _get_processed_files(conn)
            before = len(files)
            files = [f for f in files if os.path.basename(f) not in already]
            skipped = before - len(files)
            if skipped:
                log.info("Archivos ya procesados (omitidos): %d", skipped)

        if not files:
            log.info("No hay archivos nuevos por procesar.")
            # Igual dejamos sidecar consistente
            _update_remote_version(conn, date_filter)
            return

        log.info("Archivos a procesar: %d", len(files))

        totals = {"inserted": 0, "replaced": 0, "unchanged": 0}
        for f in files:
            s = process_parquet(conn, f)
            _mark_processed(conn, os.path.basename(f))
            totals["inserted"] += s["inserted"]
            totals["replaced"] += s["replaced"]
            totals["unchanged"] += s["unchanged"]

        export_tcrc_csv(conn, settings["csv_tcrc"])
        _update_remote_version(conn, date_filter)

        count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_PRECIOS}").fetchone()[0]
        fechas = conn.execute(f"SELECT MIN(Fecha), MAX(Fecha) FROM {TABLE_PRECIOS}").fetchone()
        n_fechas = conn.execute(f"SELECT COUNT(DISTINCT Fecha) FROM {TABLE_PRECIOS}").fetchone()[0]
        n_cambios = conn.execute(f"SELECT COUNT(*) FROM {TABLE_CAMBIOS}").fetchone()[0]

        log.info("=" * 60)
        log.info("RESUMEN")
        log.info("  Filas totales en DB: %d", count)
        log.info("  Fechas distintas:    %d", n_fechas)
        log.info("  Rango de fechas:     %s a %s", fechas[0], fechas[1])
        log.info("  Cambios registrados: %d", n_cambios)
        log.info(
            "  Insertados=%d | Reemplazados=%d | Sin cambio=%d",
            totals["inserted"],
            totals["replaced"],
            totals["unchanged"],
        )
    finally:
        conn.close()
        _release_writer_lock(lock_path)
        log.info("Lock writer liberado.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construir/actualizar DB de precios (writer) o sync local (reader)"
    )
    parser.add_argument(
        "fecha",
        nargs="?",
        default=None,
        help="Fecha YYYYMMDD a procesar (writer). Omitir para procesar todos.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Writer: reprocesar aunque el archivo ya este marcado.",
    )
    parser.add_argument(
        "--role",
        choices=["reader", "writer"],
        default=None,
        help="reader=sync local | writer=actualiza maestra",
    )

    args = parser.parse_args()
    try:
        build_full(date_filter=args.fecha, force=args.force, role=args.role)
    except Exception as e:
        log.error("Fallo build_precios_db: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
