"""
Pagina: Envio de Reporte Email.

Permite generar y enviar (o previsualizar) el reporte de amortizacion
via Outlook COM directamente desde el dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.utils.bq_client import get_bq_client

from core.email_report import (
    _TABLAS_POR_TIPO,
    _TITULO_POR_TIPO,
    _cargar_config_email,
    _calcular_comparacion,
    obtener_fechas_disponibles,
    generar_y_enviar_reporte,
    MONEDAS,
    _COLOR_T,
    _COLOR_T1,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIPO_OPCIONES = {
    "Primera Vuelta": "primera_vuelta",
    "Segunda Vuelta": "segunda_vuelta",
}


@st.cache_data(ttl=300)
def _fechas_por_tipo(tipo_key: str) -> list:
    """Fechas disponibles en BQ para el tipo de reporte."""
    client = get_bq_client()
    tablas = _TABLAS_POR_TIPO[tipo_key]
    return obtener_fechas_disponibles(client, tablas)


def _preview_comparacion(tipo_key: str, fecha: str):
    """Consulta BQ y retorna (df_comp, fecha_anterior)."""
    client = get_bq_client()
    tablas = _TABLAS_POR_TIPO[tipo_key]
    return _calcular_comparacion(client, fecha, tablas)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("Envio de Reporte Email")
st.caption("Genera y envia el reporte de amortizacion via Outlook COM.")

# --- Sidebar: parametros --------------------------------------------------

with st.sidebar:
    st.header("Configuracion del reporte")

    tipo_label = st.radio(
        "Tipo de reporte",
        options=list(TIPO_OPCIONES.keys()),
        index=0,
    )
    tipo_key = TIPO_OPCIONES[tipo_label]

    # Fechas disponibles
    with st.spinner("Cargando fechas..."):
        fechas = _fechas_por_tipo(tipo_key)

    if not fechas:
        st.warning("No hay fechas disponibles en BQ para este tipo.")
        st.stop()

    fecha_seleccionada = st.selectbox(
        "Fecha de proceso",
        options=fechas,
        format_func=lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
    )

    st.divider()

    # Config desde YAML como defaults
    cfg = _cargar_config_email(tipo_key)

    modo = st.radio(
        "Modo de envio",
        options=["send", "display"],
        index=0 if cfg.get("modo", "send") == "send" else 1,
        format_func=lambda m: "Enviar directo" if m == "send" else "Abrir en Outlook",
    )

    destinatarios_default = ", ".join(cfg.get("destinatarios", []))
    destinatarios_input = st.text_area(
        "Destinatarios (separados por coma)",
        value=destinatarios_default,
        height=68,
    )

    # Parse destinatarios
    destinatarios_list = [
        d.strip() for d in destinatarios_input.split(",")
        if d.strip()
    ]

# --- Preview de datos -----------------------------------------------------

st.subheader(f"Preview -- {tipo_label} -- {fecha_seleccionada}")

with st.spinner("Consultando datos de comparacion..."):
    df_comp, fecha_anterior = _preview_comparacion(tipo_key, str(fecha_seleccionada))

if df_comp.empty:
    st.warning(
        f"Sin datos de amortizacion para {fecha_seleccionada}. "
        "No se puede generar el reporte."
    )
    st.stop()

# Mostrar fecha anterior
fecha_ant_str = str(fecha_anterior) if fecha_anterior else "N/A"
st.info(f"Comparando **{fecha_seleccionada}** vs **{fecha_ant_str}**")

# Tabla resumen: modelos ejecutados y delta % por moneda
monedas_presentes = [m for m in MONEDAS if m in df_comp["MONEDA_ORIGEN"].values]
productos = sorted(df_comp["CODIGO_PRODUCTO"].unique())

resumen_rows = []
for prod in productos:
    row_dict = {"Modelo": prod}
    for mon in monedas_presentes:
        df_pm = df_comp[
            (df_comp["CODIGO_PRODUCTO"] == prod)
            & (df_comp["MONEDA_ORIGEN"] == mon)
        ]
        if df_pm.empty:
            row_dict[f"Delta% {mon}"] = None
        else:
            row_dict[f"Delta% {mon}"] = df_pm.iloc[0]["DIFERENCIA_PCT"]
    resumen_rows.append(row_dict)

df_resumen = pd.DataFrame(resumen_rows)
st.dataframe(
    df_resumen.style.format(
        {f"Delta% {m}": "{:+.2f}%" for m in monedas_presentes},
        na_rep="--",
    ).applymap(
        lambda v: "color: #2E7D32" if isinstance(v, (int, float)) and v >= 0
        else "color: #C62828" if isinstance(v, (int, float)) else "",
        subset=[f"Delta% {m}" for m in monedas_presentes],
    ),
    use_container_width=True,
    hide_index=True,
)

def _escala_eje_dash(max_val: float) -> tuple[float, str]:
    """Retorna (divisor, sufijo) para escalar el eje Y."""
    abs_max = abs(max_val) if max_val else 1
    if abs_max >= 1_000_000_000:
        return 1_000_000_000, "Miles de MM"
    if abs_max >= 1_000_000:
        return 1_000_000, "Millones"
    if abs_max >= 1_000:
        return 1_000, "Miles"
    return 1, ""


# Charts por moneda (tabs) -- un chart + data card por modelo
tabs = st.tabs(monedas_presentes)
for tab, moneda in zip(tabs, monedas_presentes):
    with tab:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        if df_m.empty:
            st.info(f"Sin datos para {moneda}.")
            continue

        for _, row in df_m.iterrows():
            col_chart, col_card = st.columns([3, 2])

            with col_chart:
                raw_values = []
                labels, colors = [], []
                if fecha_anterior:
                    raw_values.append(row["AMORT_T1"])
                    labels.append(str(fecha_anterior))
                    colors.append(_COLOR_T1)
                raw_values.append(row["AMORT_T"])
                labels.append(str(fecha_seleccionada))
                colors.append(_COLOR_T)

                raw_max = max(abs(v) for v in raw_values) if raw_values else 1
                divisor, sufijo_y = _escala_eje_dash(raw_max)
                scaled = [v / divisor for v in raw_values]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=labels, y=scaled, marker_color=colors, width=0.35,
                ))

                # Delta annotation
                if fecha_anterior and row["AMORT_T1"] != 0:
                    dpct = row["DIFERENCIA_PCT"]
                    dcol = "#2E7D32" if dpct >= 0 else "#C62828"
                    fig.add_annotation(
                        x=0.5, xref="paper",
                        y=max(scaled) * 1.05, yref="y",
                        text=f"<b>{dpct:+.2f}%</b>",
                        showarrow=False,
                        font=dict(size=13, color=dcol),
                    )

                y_label = f"{sufijo_y} ({moneda})" if sufijo_y else moneda
                y_top = max(scaled) * 1.20 if scaled else 1
                fig.update_layout(
                    title=dict(text=row["CODIGO_PRODUCTO"], font=dict(size=12)),
                    yaxis_title=y_label,
                    showlegend=False,
                    height=320,
                    margin=dict(t=45, b=35, l=55, r=15),
                    xaxis=dict(type="category", tickfont=dict(size=10)),
                    yaxis=dict(range=[0, y_top], tickformat=",.1f",
                               gridcolor="#eee", zeroline=False),
                    plot_bgcolor="white",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_card:
                st.markdown(f"**{row['CODIGO_PRODUCTO']}**")
                card_data = {
                    "Fecha": [str(fecha_anterior) if fecha_anterior else "--",
                              str(fecha_seleccionada)],
                    "Amortizacion": [f"{row['AMORT_T1']:,.0f}",
                                     f"{row['AMORT_T']:,.0f}"],
                }
                st.table(pd.DataFrame(card_data))
                pct = row["DIFERENCIA_PCT"]
                diff = row["DIFERENCIA"]
                dcol = "green" if pct >= 0 else "red"
                st.markdown(
                    f"Diferencia: **{diff:,.0f}** &nbsp; "
                    f"Variacion: :{dcol}[**{pct:+.2f}%**]"
                )
            st.divider()

# --- Boton de envio --------------------------------------------------------

st.divider()

col_send, col_info = st.columns([1, 2])
with col_send:
    enviar = st.button(
        "Enviar reporte" if modo == "send" else "Abrir en Outlook",
        type="primary",
        use_container_width=True,
    )
with col_info:
    st.markdown(
        f"**Tipo:** {tipo_label} | "
        f"**Modo:** {'Envio directo' if modo == 'send' else 'Preview en Outlook'} | "
        f"**Destinatarios:** {', '.join(destinatarios_list)}"
    )

if enviar:
    if not destinatarios_list:
        st.error("Debe ingresar al menos un destinatario.")
    else:
        with st.spinner("Generando reporte y enviando..."):
            try:
                generar_y_enviar_reporte(
                    fecha=str(fecha_seleccionada),
                    tipo_reporte=tipo_key,
                    modo=modo,
                    destinatarios=destinatarios_list,
                )
                if modo == "send":
                    st.success(
                        f"Reporte {tipo_label} enviado exitosamente "
                        f"para {fecha_seleccionada}."
                    )
                else:
                    st.success(
                        f"Reporte {tipo_label} abierto en Outlook "
                        f"para revision ({fecha_seleccionada})."
                    )
            except Exception as e:
                st.error(f"Error al generar/enviar reporte: {e}")
