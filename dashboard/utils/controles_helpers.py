"""Helpers compartidos para la página Controles (F31)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from dashboard.utils.bq_client import get_bq_client, PROJECT_ID, DATASET_DLY

_TABLA_CONTROLES = f"{PROJECT_ID}.{DATASET_DLY}.controles_diarios"
_CFG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "config_rutas_ext_y_archivos.yaml"


NIVEL_COLORS = {
    "OK": "#28a745",
    "WARNING": "#ffc107",
    "CRITICAL": "#dc3545",
    "INFO": "#6c757d",
}
NIVEL_EMOJI = {
    "OK": "🟢",
    "WARNING": "🟡",
    "CRITICAL": "🔴",
    "INFO": "⚪",
}
NIVEL_RANK = {"INFO": 0, "OK": 1, "WARNING": 2, "CRITICAL": 3}


def color_severidad(nivel: str) -> str:
    return NIVEL_COLORS.get(nivel, "#6c757d")


def emoji_severidad(nivel: str) -> str:
    return NIVEL_EMOJI.get(nivel, "⚪")


@st.cache_data(ttl=900, show_spinner=False)
def cargar_umbrales() -> dict:
    """Lee la sección controles del YAML. Cacheado 15 min."""
    import yaml
    try:
        with open(_CFG_PATH, "r", encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("controles", {})
    except Exception:
        return {}


@st.cache_data(ttl=120, show_spinner=False)
def cargar_controles_bq(fecha_iso: str) -> pd.DataFrame:
    """Lee filas de controles_diarios para una fecha. Cacheada 2 min."""
    from google.cloud import bigquery
    try:
        client = get_bq_client()
        sql = f"""
            SELECT
              fecha_proceso, timestamp, hostname, modelo, tabla,
              check_id, nivel, mensaje, evidencia_json, fecha_anterior,
              version_motor
            FROM `{_TABLA_CONTROLES}`
            WHERE fecha_proceso = @fecha
            ORDER BY modelo, nivel DESC, check_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("fecha", "DATE", fecha_iso)]
        )
        return client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def fechas_con_controles(n: int = 30) -> list[str]:
    """Últimas N fechas con datos en controles_diarios."""
    try:
        client = get_bq_client()
        sql = f"""
            SELECT DISTINCT fecha_proceso
            FROM `{_TABLA_CONTROLES}`
            ORDER BY fecha_proceso DESC
            LIMIT {int(n)}
        """
        df = client.query(sql).to_dataframe(create_bqstorage_client=False)
        return [str(f) for f in df["fecha_proceso"].tolist()]
    except Exception:
        return []


def resumen_por_nivel(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {"OK": 0, "WARNING": 0, "CRITICAL": 0, "INFO": 0}
    counts = df["nivel"].value_counts().to_dict()
    return {n: int(counts.get(n, 0)) for n in ("OK", "WARNING", "CRITICAL", "INFO")}


def render_banner_salud(df: pd.DataFrame, fecha_iso: str, link_a: Optional[str] = None) -> None:
    """Mini-banner para Home: cuenta CRITICAL/WARNING/OK y opcionalmente linkea."""
    if df.empty:
        st.info(f"ℹ️ Sin controles registrados para **{fecha_iso}** todavía.")
        return
    r = resumen_por_nivel(df)
    if r["CRITICAL"]:
        color = NIVEL_COLORS["CRITICAL"]
        label = "🔴 Hay CRITICALes en controles del día"
    elif r["WARNING"]:
        color = NIVEL_COLORS["WARNING"]
        label = "🟡 Hay WARNINGs en controles del día"
    else:
        color = NIVEL_COLORS["OK"]
        label = "🟢 Controles del día OK"
    detalle = (f"CRITICAL={r['CRITICAL']} · WARNING={r['WARNING']} "
               f"· OK={r['OK']} · INFO={r['INFO']}")
    link_html = (
        f'<a href="{link_a}" style="float:right;color:#fff;text-decoration:none;'
        f'background:{color};padding:.15rem .5rem;border-radius:6px;">Ver detalle →</a>'
        if link_a else ""
    )
    st.markdown(
        f'<div style="padding:.6rem 1rem;border-radius:8px;background:{color}22;'
        f'border-left:4px solid {color};font-weight:600;display:flex;'
        f'justify-content:space-between;align-items:center;">'
        f'<div><div style="font-size:1rem;">{label}</div>'
        f'<div style="font-size:.85rem;color:#555;font-weight:400;margin-top:.2rem;">'
        f'{detalle}</div></div>{link_html}</div>',
        unsafe_allow_html=True,
    )


def parsear_evidencia(evidencia_json: Optional[str]) -> dict:
    if not evidencia_json:
        return {}
    try:
        return json.loads(evidencia_json)
    except (json.JSONDecodeError, TypeError):
        return {"_raw": str(evidencia_json)[:500]}
