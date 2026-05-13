"""
Página: Controles diarios — semáforos y drill-down (F31).

Lee la tabla BQ ``controles_diarios`` que produce ``core.controles_outputs``
y muestra matriz pivote modelo×check con severidades, KPI tiles y detalle
de evidencia.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

import pandas as pd
import streamlit as st

from core.modelos_registry import listar_modelos, nombre_legible
from dashboard.utils.controles_helpers import (
    NIVEL_COLORS,
    NIVEL_EMOJI,
    NIVEL_RANK,
    cargar_controles_bq,
    cargar_umbrales,
    fechas_con_controles,
    parsear_evidencia,
    resumen_por_nivel,
)

st.title("🛡️ Controles diarios")
st.caption(
    "Validación post-carga de outputs BQ (motor `core.controles_outputs`, F29). "
    "Política CRITICAL: no degrada `status_global`."
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Parámetros")
    fechas_disp = fechas_con_controles(30)
    if fechas_disp:
        fecha_iso = st.selectbox("Fecha de proceso", options=fechas_disp, index=0)
    else:
        # Fallback: date_input cuando no hay datos en BQ todavía
        fecha_iso = str(st.date_input("Fecha de proceso",
                                       value=date.today(), max_value=date.today()))

    st.divider()
    todos_modelos = listar_modelos()
    modelos_filtro = st.multiselect(
        "Filtrar modelos (vacío = todos)",
        options=todos_modelos,
        default=[],
        format_func=nombre_legible,
    )
    niveles_filtro = st.multiselect(
        "Filtrar niveles",
        options=["CRITICAL", "WARNING", "OK", "INFO"],
        default=["CRITICAL", "WARNING"],
    )

    st.divider()
    if st.button("🔄 Re-ejecutar controles", help="Invoca python -m core.controles_outputs"):
        with st.spinner("Re-ejecutando motor de controles…"):
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "core.controles_outputs",
                     "--fecha", fecha_iso],
                    capture_output=True, text=True, timeout=600,
                )
                if proc.returncode == 0:
                    st.success("Motor re-ejecutado OK.")
                else:
                    st.error(f"Motor falló (returncode={proc.returncode}).")
                if proc.stdout:
                    st.code(proc.stdout[-2000:])
                if proc.stderr:
                    st.code(proc.stderr[-1000:])
                cargar_controles_bq.clear()
                fechas_con_controles.clear()
            except subprocess.TimeoutExpired:
                st.error("Timeout al re-ejecutar (>10 min).")
            except Exception as exc:
                st.error(f"Error: {exc}")

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
with st.spinner("Consultando controles…"):
    df = cargar_controles_bq(fecha_iso)

if df.empty:
    st.warning(
        f"No hay controles registrados para **{fecha_iso}**. "
        "Ejecuta el pipeline o corre `python -m core.controles_outputs --fecha "
        f"{fecha_iso}` para poblar la tabla."
    )
    st.stop()

# Aplicar filtros
df_view = df.copy()
if modelos_filtro:
    df_view = df_view[df_view["modelo"].isin(modelos_filtro)]
if niveles_filtro:
    df_view = df_view[df_view["nivel"].isin(niveles_filtro)]

# ---------------------------------------------------------------------------
# KPI tiles
# ---------------------------------------------------------------------------
r_total = resumen_por_nivel(df)
r_view = resumen_por_nivel(df_view)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("CRITICAL", r_view["CRITICAL"], delta=None)
with col2:
    st.metric("WARNING", r_view["WARNING"])
with col3:
    st.metric("OK", r_view["OK"])
with col4:
    st.metric("INFO", r_view["INFO"])
with col5:
    n_modelos = df["modelo"].nunique()
    st.metric("Modelos evaluados", n_modelos)

# Banner global (sobre todos, no filtrado)
nivel_global = (
    "CRITICAL" if r_total["CRITICAL"] else
    ("WARNING" if r_total["WARNING"] else "OK")
)
color = NIVEL_COLORS[nivel_global]
emoji = NIVEL_EMOJI[nivel_global]
st.markdown(
    f'<div style="padding:.5rem 1rem;border-radius:8px;background:{color}22;'
    f'border-left:4px solid {color};margin:.5rem 0;font-weight:600;">'
    f'{emoji} Nivel global del día: <b>{nivel_global}</b> · '
    f"CRITICAL={r_total['CRITICAL']} · WARNING={r_total['WARNING']} · "
    f"OK={r_total['OK']} · INFO={r_total['INFO']}</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Matriz pivote modelo × check_id
# ---------------------------------------------------------------------------
st.subheader("Matriz modelo × check")

# Mapear nivel a rank para que el max funcione
df_view["nivel_rank"] = df_view["nivel"].map(NIVEL_RANK).fillna(-1).astype(int)
pivote = (
    df_view.pivot_table(
        index="modelo",
        columns="check_id",
        values="nivel_rank",
        aggfunc="max",
        fill_value=-1,
    )
)
rank_a_nivel = {v: k for k, v in NIVEL_RANK.items()}


def _fmt_celda(v):
    if v == -1:
        return ""
    return NIVEL_EMOJI.get(rank_a_nivel.get(v, ""), "")


def _style_celda(v):
    color = NIVEL_COLORS.get(rank_a_nivel.get(v, ""), "transparent")
    if v == -1:
        return ""
    return f"background-color: {color}33;"


if not pivote.empty:
    pivote_idx_legible = pivote.copy()
    pivote_idx_legible.index = pivote_idx_legible.index.map(
        lambda m: nombre_legible(m) if m in listar_modelos() else m
    )
    st.dataframe(
        pivote_idx_legible.style
            .format(_fmt_celda)
            .applymap(_style_celda),
        use_container_width=True,
        height=min(450, 50 + 35 * len(pivote_idx_legible)),
    )
else:
    st.info("No hay datos filtrados.")

# ---------------------------------------------------------------------------
# Detalle expandible
# ---------------------------------------------------------------------------
st.subheader("Detalle (drill-down)")

# Solo niveles WARN/CRIT/INFO por defecto, OK arriba se controla por filtro de sidebar
df_detalle = df_view.sort_values(
    by=["nivel_rank", "modelo", "check_id"], ascending=[False, True, True]
)

if df_detalle.empty:
    st.info("Sin filas que mostrar con los filtros actuales.")
else:
    for _, row in df_detalle.iterrows():
        nivel = row["nivel"]
        color = NIVEL_COLORS.get(nivel, "#999")
        emoji = NIVEL_EMOJI.get(nivel, "⚪")
        modelo_legible = nombre_legible(row["modelo"]) if row["modelo"] in listar_modelos() else row["modelo"]
        header = f"{emoji} **{modelo_legible}** · `{row['check_id']}` · {nivel}"
        with st.expander(header, expanded=(nivel == "CRITICAL")):
            st.markdown(
                f'<div style="padding:.4rem .8rem;background:{color}11;'
                f'border-left:3px solid {color};border-radius:4px;">'
                f"<b>{row['mensaje']}</b></div>",
                unsafe_allow_html=True,
            )
            evidencia = parsear_evidencia(row.get("evidencia_json"))
            cols = st.columns(2)
            with cols[0]:
                st.caption("Evidencia")
                st.json(evidencia, expanded=False)
            with cols[1]:
                st.caption("Metadata")
                st.write({
                    "tabla": row.get("tabla"),
                    "fecha_proceso": str(row.get("fecha_proceso")),
                    "fecha_anterior": str(row.get("fecha_anterior")) if row.get("fecha_anterior") else None,
                    "hostname": row.get("hostname"),
                    "timestamp": str(row.get("timestamp")),
                    "version_motor": row.get("version_motor"),
                })

# ---------------------------------------------------------------------------
# Configuración aplicada (umbrales)
# ---------------------------------------------------------------------------
with st.expander("⚙️ Configuración de umbrales aplicada"):
    cfg = cargar_umbrales()
    if not cfg:
        st.info("No se pudo leer la sección `controles:` del YAML.")
    else:
        st.json(cfg)
