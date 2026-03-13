"""
Página: Logs — Explorador de logs JSONL.

Lee logs desde BQ (campo log_jsonl) o desde archivos locales.
Filtros por fecha de proceso, fecha de ejecución del código,
ejecución específica, modelo, nivel, texto.
"""

import json
import re
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery

from dashboard.utils.bq_client import get_bq_client, PROJECT_ID, DATASET_DLY
from dashboard.utils.local_data import listar_fechas_con_log, cargar_log_jsonl
from dashboard.utils.theme import LOG_LEVEL_COLORS, LOG_LEVEL_EMOJI

# Regex para limpiar ANSI escape codes
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# Consultas BQ
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120)
def _fechas_ejecucion_disponibles_bq(fecha_proceso: str) -> list[str]:
    """Fechas de ejecución del código (DATE(timestamp)) para una fecha_proceso."""
    try:
        client = get_bq_client()
        sql = f"""
            SELECT DISTINCT DATE(timestamp) AS fecha_ejec
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            WHERE fecha_proceso = @fp
            ORDER BY fecha_ejec DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("fp", "DATE", fecha_proceso),
            ]
        )
        df = client.query(sql, job_config=job_config).to_dataframe()
        return [str(f) for f in df["fecha_ejec"].tolist()]
    except Exception:
        return []


@st.cache_data(ttl=120)
def _listar_ejecuciones_bq(
    fecha_proceso: str, fecha_ejec_codigo: str | None = None,
) -> list[dict]:
    """Lista ejecuciones (timestamp + hostname) con filtros opcionales."""
    try:
        client = get_bq_client()
        params = [
            bigquery.ScalarQueryParameter("fp", "DATE", fecha_proceso),
        ]
        where = "WHERE fecha_proceso = @fp"
        if fecha_ejec_codigo:
            where += " AND DATE(timestamp) = @fe"
            params.append(
                bigquery.ScalarQueryParameter("fe", "DATE", fecha_ejec_codigo),
            )
        sql = f"""
            SELECT timestamp, hostname
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            {where}
            ORDER BY timestamp ASC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = client.query(sql, job_config=job_config).to_dataframe()
        return [
            {"timestamp": str(row["timestamp"])[:19], "hostname": row["hostname"]}
            for _, row in df.iterrows()
        ]
    except Exception:
        return []


@st.cache_data(ttl=120)
def _cargar_log_ejecucion_bq(fecha_proceso: str, ts_filtro: str) -> list[dict]:
    """Carga log_jsonl de UNA ejecución específica (por timestamp)."""
    try:
        client = get_bq_client()
        sql = f"""
            SELECT log_jsonl
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            WHERE fecha_proceso = @fp
              AND CAST(timestamp AS STRING) LIKE @ts_prefix
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("fp", "DATE", fecha_proceso),
                bigquery.ScalarQueryParameter("ts_prefix", "STRING", ts_filtro + "%"),
            ]
        )
        df = client.query(sql, job_config=job_config).to_dataframe()
        if df.empty:
            return []
        raw = df.iloc[0].get("log_jsonl", "")
        if not raw:
            return []
        entries = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except Exception:
        return []


@st.cache_data(ttl=120)
def _cargar_todos_logs_bq(
    fecha_proceso: str, fecha_ejec_codigo: str | None = None,
) -> list[dict]:
    """Carga logs de ejecuciones, opcionalmente filtradas por fecha de código."""
    try:
        client = get_bq_client()
        params = [
            bigquery.ScalarQueryParameter("fp", "DATE", fecha_proceso),
        ]
        where = "WHERE fecha_proceso = @fp"
        if fecha_ejec_codigo:
            where += " AND DATE(timestamp) = @fe"
            params.append(
                bigquery.ScalarQueryParameter("fe", "DATE", fecha_ejec_codigo),
            )
        sql = f"""
            SELECT log_jsonl
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            {where}
            ORDER BY timestamp ASC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = client.query(sql, job_config=job_config).to_dataframe()
        if df.empty:
            return []
        entries = []
        for _, row in df.iterrows():
            raw = row.get("log_jsonl")
            if not raw:
                continue
            for line in raw.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except Exception:
        return []


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📋 Explorador de Logs")

# --- Sidebar: filtros ---
with st.sidebar:
    st.header("Filtros")

    # Fuente de datos
    fuente = st.radio("Fuente", ["BigQuery", "Local"], horizontal=True)

    if fuente == "Local":
        fechas_disponibles = listar_fechas_con_log()
        if not fechas_disponibles:
            st.warning("No hay logs locales disponibles.")
            st.stop()
        fecha_proceso_sel = st.selectbox(
            "Fecha de proceso",
            fechas_disponibles,
            format_func=lambda f: f"{f[:4]}-{f[4:6]}-{f[6:]}",
            help="Fecha del día procesado.",
        )
        fecha_ejec_sel = None
        ejecucion_sel = None
    else:
        # --- Fecha de proceso ---
        fp_date = st.date_input(
            "Fecha de proceso",
            value=date.today(),
            help="Fecha del día procesado (campo fecha_proceso).",
        )
        fecha_proceso_sel = str(fp_date)

        # --- Fecha de ejecución del código ---
        fechas_ejec = _fechas_ejecucion_disponibles_bq(fecha_proceso_sel)
        if not fechas_ejec:
            st.warning(f"Sin datos en BQ para fecha de proceso {fecha_proceso_sel}.")
            st.stop()

        opciones_fe = ["Todas"] + fechas_ejec
        fe_idx = st.selectbox(
            "Fecha ejecución del código",
            range(len(opciones_fe)),
            format_func=lambda i: opciones_fe[i],
            help="Día calendario en que se corrió el código (puede diferir de la fecha de proceso).",
        )
        fecha_ejec_sel = fechas_ejec[fe_idx - 1] if fe_idx > 0 else None

        # --- Ejecución específica (cascada) ---
        ejecuciones = _listar_ejecuciones_bq(fecha_proceso_sel, fecha_ejec_sel)
        if not ejecuciones:
            st.warning("Sin ejecuciones para los filtros seleccionados.")
            st.stop()

        opciones_ejec = ["Todas"] + [
            f"{e['timestamp']} — {e['hostname']}" for e in ejecuciones
        ]
        ejec_idx = st.selectbox(
            "Ejecución",
            range(len(opciones_ejec)),
            format_func=lambda i: opciones_ejec[i],
        )
        ejecucion_sel = ejecuciones[ejec_idx - 1] if ejec_idx > 0 else None

    # Nivel
    niveles = ["Todos", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    default_nivel = st.session_state.pop("log_nivel", "Todos")
    idx_nivel = niveles.index(default_nivel) if default_nivel in niveles else 0
    nivel_sel = st.selectbox("Nivel", niveles, index=idx_nivel)

    # Modelo
    modelo_filter = st.text_input("Modelo (contiene)", placeholder="ej: nmd")

    # Texto
    texto_filter = st.text_input("Buscar en mensaje", placeholder="ej: error")

    # Shortcut: solo errores
    st.divider()
    if st.button("🔴 Solo errores", use_container_width=True):
        st.session_state["log_nivel"] = "ERROR"
        st.rerun()

# --- Cargar datos ---
with st.spinner("Cargando logs…"):
    if fuente == "Local":
        entries = cargar_log_jsonl(fecha_proceso_sel)
    elif ejecucion_sel is not None:
        entries = _cargar_log_ejecucion_bq(
            fecha_proceso_sel, ejecucion_sel["timestamp"],
        )
    else:
        entries = _cargar_todos_logs_bq(fecha_proceso_sel, fecha_ejec_sel)

if not entries:
    st.info("Sin logs para la selección actual.")
    st.stop()

# --- Aplicar filtros ---
filtered = entries

if nivel_sel != "Todos":
    filtered = [e for e in filtered if e.get("level") == nivel_sel]

if modelo_filter:
    modelo_lower = modelo_filter.lower()
    filtered = [
        e for e in filtered
        if e.get("modelo") and modelo_lower in e["modelo"].lower()
    ]

if texto_filter:
    texto_lower = texto_filter.lower()
    filtered = [
        e for e in filtered
        if texto_lower in _strip_ansi(e.get("msg", "")).lower()
    ]

# --- Resumen ---
total = len(entries)
mostrados = len(filtered)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total entradas", f"{total:,}")
with col2:
    st.metric("Filtradas", f"{mostrados:,}")
with col3:
    # Conteo por nivel
    niveles_count = {}
    for e in entries:
        lvl = e.get("level", "?")
        niveles_count[lvl] = niveles_count.get(lvl, 0) + 1
    parts = [f"{LOG_LEVEL_EMOJI.get(k, '❓')} {k}: {v}" for k, v in sorted(niveles_count.items())]
    st.markdown("  \n".join(parts))

# --- Pie chart por nivel ---
if niveles_count:
    df_niveles = pd.DataFrame(
        [{"Nivel": k, "Cantidad": v} for k, v in niveles_count.items()]
    )
    color_map = {k: v for k, v in LOG_LEVEL_COLORS.items() if k in niveles_count}
    fig_pie = px.pie(
        df_niveles, names="Nivel", values="Cantidad",
        color="Nivel", color_discrete_map=color_map,
        hole=0.4,
    )
    fig_pie.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_pie, use_container_width=True)

# --- Tabla ---
if filtered:
    df = pd.DataFrame(filtered)

    # Limpiar ANSI
    if "msg" in df.columns:
        df["msg"] = df["msg"].apply(_strip_ansi)

    # Columnas a mostrar
    cols_display = [c for c in ["ts", "level", "modelo", "msg"] if c in df.columns]
    df_display = df[cols_display].copy()

    if "ts" in df_display.columns:
        df_display = df_display.rename(columns={"ts": "Timestamp"})
    if "level" in df_display.columns:
        df_display = df_display.rename(columns={"level": "Nivel"})
    if "modelo" in df_display.columns:
        df_display = df_display.rename(columns={"modelo": "Modelo"})
    if "msg" in df_display.columns:
        df_display = df_display.rename(columns={"msg": "Mensaje"})

    # Colorear nivel
    def _style_nivel(val):
        color = LOG_LEVEL_COLORS.get(val, "#999")
        return f"color: {color}; font-weight: bold;"

    styled = df_display.style
    if "Nivel" in df_display.columns:
        styled = styled.map(_style_nivel, subset=["Nivel"])

    st.dataframe(styled, use_container_width=True, height=600)

    # Descarga
    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar CSV",
        data=csv,
        file_name=f"logs_{fecha_proceso_sel}.csv",
        mime="text/csv",
    )
else:
    st.info("Sin resultados con los filtros aplicados.")
