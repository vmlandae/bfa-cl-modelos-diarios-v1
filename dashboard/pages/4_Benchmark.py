"""
Página: Benchmark — Tendencias de performance.

Gráficos de duración total y por modelo, box plots, tabla resumen.
BQ-first con fallback local.  Agrupa ejecuciones del mismo día.
"""

import json
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery

from core.sync_benchmark import cargar_benchmark_desde_bq
from dashboard.utils.bq_client import get_bq_client, PROJECT_ID, DATASET_DLY
from dashboard.utils.local_data import cargar_benchmark_historial
from dashboard.utils.theme import MODELOS_CANONICOS

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120)
def _cargar_benchmarks_bq(dias: int = 90) -> list[dict]:
    """Lee benchmarks desde tabla dedicada; fallback a reportes_ejecucion."""
    # --- Tabla dedicada reportes_benchmark ---
    entries = cargar_benchmark_desde_bq(dias)
    if entries:
        return entries

    # --- Fallback: parsear reporte_json de reportes_ejecucion ---
    try:
        client = get_bq_client()
        sql = f"""
            SELECT fecha_proceso, timestamp, reporte_json, status_global
            FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
            WHERE fecha_proceso >= DATE_SUB(CURRENT_DATE(), INTERVAL @dias DAY)
            ORDER BY fecha_proceso, timestamp
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("dias", "INT64", dias),
            ]
        )
        df = client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
        if df.empty:
            return []

        entries = []
        for _, row in df.iterrows():
            raw = row.get("reporte_json")
            if not raw:
                continue
            try:
                rep = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            bench = rep.get("benchmark", {})
            por_modelo = bench.get("por_modelo", {})
            if not por_modelo:
                modelos = rep.get("modelos", {})
                por_modelo = {k: v.get("duracion_seg", 0) for k, v in modelos.items()}
            entries.append({
                "fecha": str(row["fecha_proceso"]),
                "total_seg": rep.get("duracion_total_seg", 0),
                "por_modelo": por_modelo,
                "hostname": rep.get("hostname", "?"),
                "status": row.get("status_global", rep.get("status_global", "?")),
            })
        return entries
    except Exception:
        return []


def _cargar_datos() -> tuple[list[dict], str]:
    """Intenta BQ primero, fallback local."""
    entries = _cargar_benchmarks_bq()
    if entries:
        return entries, "BigQuery"
    entries = cargar_benchmark_historial()
    if entries:
        return entries, "Local"
    return [], "ninguna"


def _entries_a_df(entries: list[dict]) -> pd.DataFrame:
    """Convierte entradas benchmark a DataFrame plano.

    Solo incluye modelos canónicos; descarta entradas de prueba.
    """
    _canonicos = set(MODELOS_CANONICOS)
    rows = []
    for e in entries:
        base = {
            "fecha": e["fecha"],
            "total_seg": e["total_seg"],
            "hostname": e.get("hostname", "?"),
            "status": e.get("status", "?"),
        }
        for modelo, dur in e.get("por_modelo", {}).items():
            if modelo not in _canonicos:
                continue
            rows.append({**base, "modelo": modelo, "duracion_seg": dur})
    return pd.DataFrame(rows)


def _agregar_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    """Suma duraciones de todas las ejecuciones del mismo día."""
    if df.empty:
        return df

    # Total por día = suma de total_seg de cada ejecución
    df_totales = (
        df.drop_duplicates(subset=["fecha", "total_seg"])
        .groupby("fecha", as_index=False)
        .agg(total_dia_seg=("total_seg", "sum"))
    )

    # Por modelo: sumar duraciones del mismo modelo en el mismo día
    df_modelos = (
        df.groupby(["fecha", "modelo"], as_index=False)
        .agg(duracion_dia_seg=("duracion_seg", "sum"))
    )

    return df_totales, df_modelos


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📈 Benchmark de Performance")

entries, fuente = _cargar_datos()
if not entries:
    st.warning("No hay datos de benchmark disponibles.")
    st.stop()

st.caption(f"Fuente: {fuente} — {len(entries)} ejecuciones")

df_raw = _entries_a_df(entries)
if df_raw.empty:
    st.warning("No se pudieron parsear los datos de benchmark.")
    st.stop()

df_totales, df_modelos = _agregar_por_dia(df_raw)

# --- Duración total por día ---
st.subheader("Duración total del pipeline por día")

fig_total = px.bar(
    df_totales.sort_values("fecha"),
    x="fecha",
    y="total_dia_seg",
    labels={"fecha": "Fecha", "total_dia_seg": "Duración (s)"},
    text_auto=".0f",
)
fig_total.update_layout(height=350, xaxis_tickangle=-45)
st.plotly_chart(fig_total, use_container_width=True)

# --- Duración por modelo (stacked bar) ---
st.subheader("Duración por modelo (agregado por día)")

df_modelos_sorted = df_modelos.sort_values(["fecha", "modelo"])
# Traducir ids a nombres legibles
nombre_map = {k: v["nombre"] for k, v in MODELOS_CANONICOS.items()}
df_modelos_sorted["modelo_nombre"] = df_modelos_sorted["modelo"].map(
    lambda m: nombre_map.get(m, m)
)

fig_modelos = px.bar(
    df_modelos_sorted,
    x="fecha",
    y="duracion_dia_seg",
    color="modelo_nombre",
    labels={
        "fecha": "Fecha",
        "duracion_dia_seg": "Duración (s)",
        "modelo_nombre": "Modelo",
    },
    barmode="stack",
)
fig_modelos.update_layout(height=450, xaxis_tickangle=-45)
st.plotly_chart(fig_modelos, use_container_width=True)

# --- Line chart por modelo ---
st.subheader("Evolución por modelo")

modelos_disponibles = sorted(df_modelos["modelo"].unique())
modelos_sel = st.multiselect(
    "Modelos a mostrar",
    modelos_disponibles,
    default=modelos_disponibles,
    format_func=lambda m: nombre_map.get(m, m),
)

if modelos_sel:
    df_line = df_modelos[df_modelos["modelo"].isin(modelos_sel)].copy()
    df_line["modelo_nombre"] = df_line["modelo"].map(lambda m: nombre_map.get(m, m))

    fig_line = px.line(
        df_line.sort_values("fecha"),
        x="fecha",
        y="duracion_dia_seg",
        color="modelo_nombre",
        markers=True,
        labels={
            "fecha": "Fecha",
            "duracion_dia_seg": "Duración (s)",
            "modelo_nombre": "Modelo",
        },
    )
    fig_line.update_layout(height=400)
    st.plotly_chart(fig_line, use_container_width=True)

# --- Box plot ---
st.subheader("Distribución de tiempos por modelo")

n_puntos = len(df_modelos)
if n_puntos < 10:
    st.info(
        f"⚠️ Solo {n_puntos} puntos de datos. Se requieren más ejecuciones "
        "para estadísticas robustas."
    )

df_box = df_modelos.copy()
df_box["modelo_nombre"] = df_box["modelo"].map(lambda m: nombre_map.get(m, m))

fig_box = px.box(
    df_box,
    x="modelo_nombre",
    y="duracion_dia_seg",
    labels={"modelo_nombre": "Modelo", "duracion_dia_seg": "Duración (s)"},
    points="all",
)
fig_box.update_layout(height=400, xaxis_tickangle=-30)
st.plotly_chart(fig_box, use_container_width=True)

# --- Tabla resumen ---
st.subheader("Tabla resumen")

if not df_modelos.empty:
    resumen = (
        df_modelos.groupby("modelo")["duracion_dia_seg"]
        .agg(["mean", "median", "min", "max", "count", "last"])
        .reset_index()
    )
    resumen.columns = ["Modelo", "Media (s)", "Mediana (s)", "Mín (s)",
                        "Máx (s)", "Ejecuciones", "Último (s)"]
    resumen["Modelo"] = resumen["Modelo"].map(lambda m: nombre_map.get(m, m))
    resumen = resumen.sort_values("Media (s)", ascending=False)

    st.dataframe(
        resumen.style.format({
            "Media (s)": "{:.1f}",
            "Mediana (s)": "{:.1f}",
            "Mín (s)": "{:.1f}",
            "Máx (s)": "{:.1f}",
            "Último (s)": "{:.1f}",
        }),
        use_container_width=True,
    )

    # Detección simple de anomalías
    for _, row in resumen.iterrows():
        if row["Ejecuciones"] >= 3 and row["Último (s)"] > row["Mediana (s)"] * 2:
            st.warning(
                f"⚠️ **{row['Modelo']}** — última ejecución ({row['Último (s)']:.1f}s) "
                f"es {row['Último (s)'] / row['Mediana (s)']:.1f}x su mediana "
                f"({row['Mediana (s)']:.1f}s)"
            )

# --- Descarga ---
st.divider()
csv = df_raw.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar historial CSV",
    data=csv,
    file_name="benchmark_historial.csv",
    mime="text/csv",
)
