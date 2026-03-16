"""
Página: Home — Mission Control.

Vista consolidada por día de proceso: para cada uno de los 10 modelos
canónicos se toma el resultado de la última ejecución que lo incluyó.
BQ-first con fallback local.
"""

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from dashboard.utils.bq_client import get_bq_client, PROJECT_ID, DATASET_DLY
from dashboard.utils.local_data import cargar_reporte_ejecucion
from dashboard.utils.theme import (
    STATUS_COLORS,
    STATUS_EMOJI,
    MODELOS_CANONICOS,
)


# ---------------------------------------------------------------------------
# Fecha de proceso por defecto (último día laboral ≤ ayer)
# ---------------------------------------------------------------------------

def _fecha_proceso_default() -> date:
    """Retorna el último día laboral anterior a hoy."""
    try:
        from bfa_cl_utilidades import es_dia_laboral
        d = date.today() - timedelta(days=1)
        while not es_dia_laboral(d):
            d -= timedelta(days=1)
        return d
    except ImportError:
        # Fallback: ayer (sin validar feriados)
        return date.today() - timedelta(days=1)

# ---------------------------------------------------------------------------
# Consultas BQ
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120)
def _cargar_reportes_fecha_bq(fecha: str) -> pd.DataFrame:
    """Todas las ejecuciones de una fecha_proceso, ordenadas por timestamp."""
    try:
        client = get_bq_client()
        sql = f"""
            SELECT
                fecha_proceso,
                timestamp,
                hostname,
                status_global,
                duracion_total_seg,
                modelos_ok,
                modelos_error,
                alertas,
                reporte_json
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            WHERE fecha_proceso = @fecha
            ORDER BY timestamp ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
            ]
        )
        return client.query(sql, job_config=job_config).to_dataframe()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def _fechas_disponibles_bq() -> list[str]:
    """Lista de fechas_proceso disponibles en BQ, desc."""
    try:
        client = get_bq_client()
        sql = f"""
            SELECT DISTINCT fecha_proceso
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            ORDER BY fecha_proceso DESC
            LIMIT 60
        """
        df = client.query(sql).to_dataframe()
        return [str(f) for f in df["fecha_proceso"].tolist()]
    except Exception:
        return []


def _parse_reporte_json(raw: str | None) -> dict | None:
    """Parsea un string JSON a dict."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Consolidación: para cada modelo canónico, tomar la última ejecución
# ---------------------------------------------------------------------------

def _consolidar_dia(df: pd.DataFrame) -> dict:
    """Consolida todas las ejecuciones de un día.

    Retorna dict con claves:
        modelos        – dict {modelo_id: {status, duracion_seg, error_msg?, ejecucion_idx}}
        n_ejecuciones  – cantidad de ejecuciones del día
        duracion_total – suma de duracion_total_seg de todas las ejecuciones
        alertas        – lista unificada de alertas (sin duplicar)
        carga_gcp      – merge de carga_gcp (última gana)
        benchmarks     – lista de benchmark dicts
        timestamps     – lista de timestamps (ASC)
    """
    modelos: dict[str, dict] = {}
    alertas_set: list[str] = []
    carga_gcp: dict = {}
    benchmarks: list[dict] = []
    timestamps: list[str] = []
    duracion_total = 0.0

    for idx, row in df.iterrows():
        reporte = _parse_reporte_json(row.get("reporte_json"))
        ts = str(row.get("timestamp", ""))[:19]
        timestamps.append(ts)
        duracion_total += float(row.get("duracion_total_seg", 0) or 0)

        # Alertas: acumular sin duplicar
        raw_al = row.get("alertas")
        if raw_al is not None:
            for a in list(raw_al):
                if a and a not in alertas_set:
                    alertas_set.append(a)

        if reporte is None:
            continue

        # Modelos: la ejecución posterior sobreescribe la anterior
        rep_modelos = reporte.get("modelos", {})
        for modelo_id, resultado in rep_modelos.items():
            modelos[modelo_id] = {**resultado, "ejecucion_ts": ts}

        # Carga GCP: merge (última gana)
        rep_carga = reporte.get("carga_gcp", {})
        carga_gcp.update(rep_carga)

        # Benchmark
        rep_bench = reporte.get("benchmark")
        if rep_bench:
            benchmarks.append(rep_bench)

    return {
        "modelos": modelos,
        "n_ejecuciones": len(df),
        "duracion_total": round(duracion_total, 1),
        "alertas": alertas_set,
        "carga_gcp": carga_gcp,
        "benchmarks": benchmarks,
        "timestamps": timestamps,
    }


def _status_global_consolidado(modelos_consolidados: dict) -> str:
    """Deriva el status global desde los modelos consolidados."""
    if not modelos_consolidados:
        return "SIN_MODELOS"
    statuses = {v.get("status") for v in modelos_consolidados.values()}
    if statuses == {"OK"}:
        return "OK"
    if statuses == {"ERROR"}:
        return "ERROR"
    if "ERROR" in statuses:
        return "PARCIAL"
    return "OK"


# ---------------------------------------------------------------------------
# Fallback local
# ---------------------------------------------------------------------------

def _cargar_reporte_local(fecha_iso: str) -> dict | None:
    """Carga reporte local para una fecha (formato YYYYMMDD)."""
    fecha_yyyymmdd = fecha_iso.replace("-", "")
    return cargar_reporte_ejecucion(fecha_yyyymmdd)


# ---------------------------------------------------------------------------
# Helpers de renderizado
# ---------------------------------------------------------------------------

def _render_semaforo(status: str, fecha: str, info_extra: str):
    emoji = STATUS_EMOJI.get(status, "❓")
    color = STATUS_COLORS.get(status, "#999")
    st.markdown(
        f"""
        <div style="text-align:center; padding:1rem; border-radius:12px;
                    background-color:{color}22; border:2px solid {color};">
            <span style="font-size:3rem;">{emoji}</span>
            <h2 style="margin:0.3rem 0 0 0;">{status}</h2>
            <p style="margin:0; color:#888;"> Fecha Proceso:  {fecha} — {info_extra}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_modelo_card(nombre_id: str, info_canon: dict, resultado: dict | None):
    """Renderiza una tarjeta pequeña para un modelo."""
    nombre_display = info_canon["nombre"]

    if resultado is None:
        st.markdown(
            f'<div style="padding:0.5rem; border-radius:8px; '
            f'background-color:#f0f0f0; border-left:4px solid #ccc; '
            f'margin-bottom:0.4rem;">'
            f'⚪ <strong>{nombre_display}</strong> '
            f'<span style="color:#999; font-size:0.85rem;"> — no ejecutado</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    status = resultado.get("status", "?")
    duracion = resultado.get("duracion_seg", 0)
    ts = resultado.get("ejecucion_ts", "")
    emoji = "🟢" if status == "OK" else "🔴"
    color = "#28a745" if status == "OK" else "#dc3545"
    error_line = ""
    if status == "ERROR" and resultado.get("error_msg"):
        error_line = (
            f'<div style="color:#dc3545; font-size:0.8rem; margin-top:0.2rem;">'
            f'{resultado["error_msg"][:120]}</div>'
        )
    ts_line = (
        f'<span style="font-size:0.75rem; color:#aaa;"> ({ts})</span>' if ts else ""
    )

    st.markdown(
        f'<div style="padding:0.5rem; border-radius:8px; '
        f'background-color:{color}11; border-left:4px solid {color}; '
        f'margin-bottom:0.4rem;">'
        f'{emoji} <strong>{nombre_display}</strong> '
        f'<span style="font-size:0.85rem; color:#666;"> — {duracion:.1f}s</span>'
        f'{ts_line}'
        f'{error_line}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# UI principal
# ---------------------------------------------------------------------------
st.title("🏠 Mission Control")

# --- Sidebar: selector de fecha de proceso ---
with st.sidebar:
    st.header("Fecha de proceso")
    fecha_default = _fecha_proceso_default()
    fecha_sel = st.date_input(
        "Seleccionar fecha",
        value=fecha_default,
        max_value=date.today(),
        key="home_fecha_proceso",
    )

fecha_iso = str(fecha_sel)

# --- Cargar datos ---
df_bq = _cargar_reportes_fecha_bq(fecha_iso)
usando_bq = not df_bq.empty

if usando_bq:
    consolidado = _consolidar_dia(df_bq)
    fuente = "BigQuery"
else:
    # Fallback local (un solo reporte)
    reporte_local = _cargar_reporte_local(fecha_iso)
    if reporte_local is None:
        st.warning(
            f"No se encontraron reportes para **{fecha_iso}** "
            "(ni en BigQuery ni localmente)."
        )
        st.stop()
    # Simular consolidado desde reporte local
    consolidado = {
        "modelos": reporte_local.get("modelos", {}),
        "n_ejecuciones": 1,
        "duracion_total": reporte_local.get("duracion_total_seg", 0),
        "alertas": reporte_local.get("alertas", []),
        "carga_gcp": reporte_local.get("carga_gcp", {}),
        "benchmarks": [reporte_local["benchmark"]] if reporte_local.get("benchmark") else [],
        "timestamps": [reporte_local.get("timestamp", "?")[:19]],
    }
    fuente = "Local"

modelos_consol = consolidado["modelos"]
n_ejec = consolidado["n_ejecuciones"]
duracion_total = consolidado["duracion_total"]
alertas = consolidado["alertas"]
timestamps = consolidado["timestamps"]

# Derivar status global consolidado
status_global = _status_global_consolidado(modelos_consol)
n_ok = sum(1 for v in modelos_consol.values() if v.get("status") == "OK")
n_error = sum(1 for v in modelos_consol.values() if v.get("status") == "ERROR")
n_no_ejec = len(MODELOS_CANONICOS) - len(
    {k for k in modelos_consol if k in MODELOS_CANONICOS}
)

# --- Semáforo ---
info_extra = f"{n_ejec} ejecuci{'ón' if n_ejec == 1 else 'ones'}"
if timestamps:
    info_extra += f" · última: {timestamps[-1]}"
_render_semaforo(status_global, fecha_iso, info_extra)
st.caption(f"Fuente: {fuente}")

# --- Métricas principales ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Duración total", f"{duracion_total:.1f}s")
with col2:
    st.metric("Modelos OK", n_ok)
with col3:
    st.metric("Modelos Error", n_error)
with col4:
    st.metric("No ejecutados", n_no_ejec)

# --- Tarjetas por modelo ---
st.subheader("Modelos")

col_left, col_right = st.columns(2)
for i, (modelo_id, info) in enumerate(MODELOS_CANONICOS.items()):
    resultado = modelos_consol.get(modelo_id)
    target_col = col_left if i % 2 == 0 else col_right
    with target_col:
        _render_modelo_card(modelo_id, info, resultado)

# --- Alertas ---
# Suprimir alertas de benchmark antiguo (pre-2026-03-13, comparaban total
# contra promedio global sin distinguir fase).
_ALERTAS_FIABLES_DESDE = "2026-03-13"
if alertas and fecha_iso >= _ALERTAS_FIABLES_DESDE:
    st.subheader("⚠️ Alertas")
    for alerta in alertas:
        st.warning(alerta)

# --- Carga GCP ---
carga_gcp = consolidado["carga_gcp"]
if carga_gcp:
    st.subheader("Carga GCP")
    ok_count = sum(1 for v in carga_gcp.values() if v is True)
    fail_count = sum(1 for v in carga_gcp.values() if v is not True)
    gc1, gc2 = st.columns(2)
    with gc1:
        st.metric("Tablas subidas", ok_count)
    with gc2:
        st.metric("Tablas fallidas", fail_count)
    if fail_count > 0:
        with st.expander("Detalle cargas fallidas"):
            for tabla, resultado in carga_gcp.items():
                if resultado is not True:
                    st.error(f"❌ {tabla}: {resultado}")

# --- Detalle ejecuciones del día (si hay varias en BQ) ---
if usando_bq and n_ejec > 1:
    st.subheader("Ejecuciones del día")
    df_ejec = df_bq[["timestamp","hostname", "status_global", "duracion_total_seg",
                      "modelos_ok", "modelos_error"]].copy()
    df_ejec.columns = ["Timestamp", "Hostname", "Status", "Duración (s)", "OK", "Error"]

    def _color_status(val):
        c = STATUS_COLORS.get(val, "#999")
        return f"background-color: {c}22; color: {c}; font-weight: bold;"

    st.dataframe(
        df_ejec.style.map(_color_status, subset=["Status"]).format(
            {"Duración (s)": "{:.1f}"}
        ),
        use_container_width=True,
        height=min(35 * len(df_ejec) + 38, 300),
    )
