"""
Página: Comparación Outputs t vs t-1.

Comparativa de SUM(AMORTIZACION) agrupada por MONEDA_ORIGEN, CODIGO_PRODUCTO
y MODELO entre un día procesado (t) y su día procesado anterior (t-1).

Cobertura: todos los modelos del registry (F28). La columna MODELO en el
UNION ALL permite filtrar y agrupar por modelo en el front sin perder los
productos de V2 (NMD, LC, Inversiones, SSV, Prepago) que antes quedaban
excluidos por un filtro CODIGO_PRODUCTOS hardcoded.
"""

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from dashboard.utils.bq_client import get_bq_client, PROJECT_ID, DATASET_HIST
from core.modelos_registry import (
    listar_modelos,
    nombre_legible,
    tabla_hist,
    tablas_extra_hist,
    todas_las_tablas_hist,
    modelo_de_tabla,
)

# ---------------------------------------------------------------------------
# Constantes derivadas del registry (F28) — adios listas hardcoded
# ---------------------------------------------------------------------------
TABLAS_HIST: list[str] = todas_las_tablas_hist()

# Nombre legible visible en UI -> tabla. Tabla principal usa nombre_legible;
# tabla extra usa nombre_legible + sufijo entre paréntesis derivado del nombre.
NOMBRES_TABLAS: dict[str, str] = {}
for m in listar_modelos():
    NOMBRES_TABLAS[nombre_legible(m)] = tabla_hist(m)
    for extra in tablas_extra_hist(m):
        # ej: report_ml_mora_consumo_renegociado_hist -> "Mora Consumo Renegociado"
        sufijo = (
            extra.removeprefix(f"report_{m}_")
                 .removesuffix("_hist")
                 .replace("_", " ")
                 .title()
        )
        NOMBRES_TABLAS[f"{nombre_legible(m)} {sufijo}"] = extra

ETIQUETAS_MONEDA = {"USD": "USD", "CLF": "CLF", "CLP": "CLP"}
MONEDAS_INTERES = list(ETIQUETAS_MONEDA.keys())


# ---------------------------------------------------------------------------
# Helpers SQL
# ---------------------------------------------------------------------------

def _union_all_tablas() -> str:
    """UNION ALL de todas las tablas hist con columna sintética MODELO."""
    selects = []
    for t in TABLAS_HIST:
        modelo = modelo_de_tabla(t) or t
        selects.append(
            f"SELECT *, '{modelo}' AS MODELO "
            f"FROM `{PROJECT_ID}.{DATASET_HIST}.{t}`"
        )
    return "\nUNION ALL\n".join(selects)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def obtener_fechas_disponibles() -> list:
    """Lista descendente de fechas con datos. Cacheada 15 min."""
    client = get_bq_client()
    subquery = _union_all_tablas()
    sql = f"""
        SELECT DISTINCT FECHA_PROCESO
        FROM ({subquery})
        WHERE FECHA_PROCESO < CURRENT_DATE()
        ORDER BY FECHA_PROCESO DESC
        LIMIT 60
    """
    df = client.query(sql).to_dataframe()
    return df["FECHA_PROCESO"].tolist()


@st.cache_data(ttl=600, show_spinner=False)
def obtener_amortizacion(fecha: str) -> pd.DataFrame:
    """SUM(AMORTIZACION) agrupado por MODELO × MONEDA × CODIGO_PRODUCTO.

    Sin filtro de productos: cubre todos los productos presentes en BQ.
    """
    client = get_bq_client()
    subquery = _union_all_tablas()
    sql = f"""
        SELECT
            MODELO,
            CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
            CODIGO_PRODUCTO,
            SUM(AMORTIZACION) AS TOTAL_AMORTIZACION
        FROM ({subquery})
        WHERE FECHA_PROCESO = @fecha
          AND CAST(MONEDA_ORIGEN AS STRING) IN UNNEST(@monedas)
        GROUP BY MODELO, MONEDA_ORIGEN, CODIGO_PRODUCTO
        ORDER BY MODELO, MONEDA_ORIGEN, CODIGO_PRODUCTO
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
            bigquery.ArrayQueryParameter("monedas", "STRING", MONEDAS_INTERES),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def _comparar(fecha_t: str, fecha_t1: str | None) -> pd.DataFrame:
    """Merge t vs t-1 cacheado. Vectorizado para evitar lambda en axis=1."""
    df_actual = obtener_amortizacion(fecha_t)
    if fecha_t1:
        df_anterior = obtener_amortizacion(fecha_t1)
    else:
        df_anterior = pd.DataFrame(
            columns=["MODELO", "MONEDA_ORIGEN", "CODIGO_PRODUCTO", "TOTAL_AMORTIZACION"]
        )

    df_comp = pd.merge(
        df_actual.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T"}),
        df_anterior.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T1"}),
        on=["MODELO", "MONEDA_ORIGEN", "CODIGO_PRODUCTO"],
        how="outer",
    ).fillna(0)

    df_comp["DIFERENCIA"] = df_comp["AMORT_T"] - df_comp["AMORT_T1"]
    denom = df_comp["AMORT_T1"].abs().replace(0, pd.NA)
    df_comp["DIFERENCIA_%"] = (df_comp["DIFERENCIA"] / denom * 100).fillna(0.0)
    return df_comp


@st.cache_data(ttl=1800, show_spinner=False)
def obtener_tabla_completa(tabla: str, fecha: str) -> pd.DataFrame:
    """Lee una tabla histórica completa para una fecha. Cacheada 30 min, LIMIT 50000."""
    client = get_bq_client()
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_HIST}.{tabla}`
        WHERE FECHA_PROCESO = @fecha
        ORDER BY CODIGO_PRODUCTO, MONEDA_ORIGEN
        LIMIT 50000
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def diagnostico(fecha: str) -> pd.DataFrame:
    """Conteos y sumas crudas por MODELO × MONEDA × CODIGO_PRODUCTO."""
    client = get_bq_client()
    subquery = _union_all_tablas()
    sql = f"""
        SELECT
            MODELO,
            CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
            CODIGO_PRODUCTO,
            COUNT(*) AS filas,
            SUM(AMORTIZACION) AS sum_amort
        FROM ({subquery})
        WHERE FECHA_PROCESO = @fecha
        GROUP BY MODELO, MONEDA_ORIGEN, CODIGO_PRODUCTO
        ORDER BY MODELO, MONEDA_ORIGEN, CODIGO_PRODUCTO
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📊 Comparación Outputs — Datos Históricos GCP")

# Sidebar: selección de fecha + filtro de modelo
with st.sidebar:
    st.header("Parámetros de consulta")

    with st.spinner("Cargando fechas disponibles…"):
        fechas = obtener_fechas_disponibles()

    if not fechas:
        st.warning("No hay fechas disponibles.")
        st.stop()

    fecha_seleccionada = st.selectbox(
        "Fecha a consultar (t)",
        options=fechas,
        format_func=lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
    )

    idx = fechas.index(fecha_seleccionada)
    if idx + 1 < len(fechas):
        fecha_anterior = fechas[idx + 1]
        st.info(f"Fecha anterior (t-1): **{fecha_anterior}**")
    else:
        fecha_anterior = None
        st.warning("No existe una fecha procesada anterior.")

    st.divider()
    st.caption("Filtro de modelos (vacío = todos)")
    modelos_disp = listar_modelos()
    modelos_sel = st.multiselect(
        "Modelos",
        options=modelos_disp,
        default=[],
        format_func=nombre_legible,
    )

# Consulta unificada cacheada
with st.spinner("Consultando datos…"):
    df_comp = _comparar(
        str(fecha_seleccionada),
        str(fecha_anterior) if fecha_anterior else None,
    )

if modelos_sel:
    df_comp = df_comp[df_comp["MODELO"].isin(modelos_sel)]

# Métricas resumen
st.subheader(f"Resumen — {fecha_seleccionada}")

total_actual = df_comp["AMORT_T"].sum()
total_anterior = df_comp["AMORT_T1"].sum()

col1, col2, col3 = st.columns(3)
with col1:
    delta_abs = total_actual - total_anterior if fecha_anterior else None
    st.metric(
        label="Total Amortización (t)",
        value=f"{total_actual:,.2f}",
        delta=f"{delta_abs:,.2f}" if delta_abs is not None else None,
    )
with col2:
    st.metric(
        label="Total Amortización (t-1)",
        value=f"{total_anterior:,.2f}" if fecha_anterior else "—",
    )
with col3:
    if fecha_anterior and total_anterior != 0:
        delta_pct = (total_actual - total_anterior) / abs(total_anterior) * 100
        st.metric(label="Variación %", value=f"{delta_pct:+.2f} %")
    else:
        st.metric(label="Variación %", value="—")

# Tabla pivote por modelo (nueva — visible siempre)
st.subheader("Por modelo")
df_por_modelo = (
    df_comp.groupby("MODELO")[["AMORT_T", "AMORT_T1"]]
    .sum()
    .assign(DIFERENCIA=lambda x: x["AMORT_T"] - x["AMORT_T1"])
)
denom_m = df_por_modelo["AMORT_T1"].abs().replace(0, pd.NA)
df_por_modelo["DIFERENCIA_%"] = (df_por_modelo["DIFERENCIA"] / denom_m * 100).fillna(0.0)
df_por_modelo = df_por_modelo.reset_index()
df_por_modelo["MODELO"] = df_por_modelo["MODELO"].map(lambda m: nombre_legible(m) if m in modelos_disp else m)
st.dataframe(
    df_por_modelo.style.format({
        "AMORT_T": "{:,.2f}",
        "AMORT_T1": "{:,.2f}",
        "DIFERENCIA": "{:,.2f}",
        "DIFERENCIA_%": "{:+.2f} %",
    }),
    use_container_width=True,
    height=min(400, 50 + 35 * len(df_por_modelo)),
)

# Gráfico por moneda (lazy plotly)
for cod_moneda, etiqueta_moneda in ETIQUETAS_MONEDA.items():
    st.subheader(f"Moneda: {etiqueta_moneda} ({cod_moneda})")

    df_moneda = df_comp[df_comp["MONEDA_ORIGEN"] == cod_moneda].sort_values(
        ["MODELO", "CODIGO_PRODUCTO"]
    )

    if df_moneda.empty:
        st.info(f"Sin datos para moneda {etiqueta_moneda}.")
        continue

    import plotly.graph_objects as go  # lazy import — perf F32

    fig = go.Figure()

    if fecha_anterior is not None:
        fig.add_trace(go.Bar(
            x=df_moneda["CODIGO_PRODUCTO"],
            y=df_moneda["AMORT_T1"],
            name=f"t-1  ({fecha_anterior})",
            marker_color="#EF553B",
            customdata=df_moneda["MODELO"],
            hovertemplate="<b>%{x}</b><br>Modelo: %{customdata}<br>AMORT_T1: %{y:,.2f}<extra></extra>",
        ))

    fig.add_trace(go.Bar(
        x=df_moneda["CODIGO_PRODUCTO"],
        y=df_moneda["AMORT_T"],
        name=f"t  ({fecha_seleccionada})",
        marker_color="#636EFA",
        customdata=df_moneda["MODELO"],
        hovertemplate="<b>%{x}</b><br>Modelo: %{customdata}<br>AMORT_T: %{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        xaxis_title="Código Producto",
        yaxis_title="Sum Amortización",
        legend_title="Fecha Proceso",
        height=450,
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"Detalle {etiqueta_moneda}"):
        st.dataframe(
            df_moneda[["MODELO", "CODIGO_PRODUCTO", "AMORT_T", "AMORT_T1",
                        "DIFERENCIA", "DIFERENCIA_%"]]
            .reset_index(drop=True)
            .style.format({
                "AMORT_T": "{:,.2f}",
                "AMORT_T1": "{:,.2f}",
                "DIFERENCIA": "{:,.2f}",
                "DIFERENCIA_%": "{:+.2f} %",
            }),
            use_container_width=True,
        )

# Diagnóstico
with st.expander("🔍 Diagnóstico — valores reales en BigQuery"):
    df_diag = diagnostico(str(fecha_seleccionada))
    if df_diag.empty:
        st.warning("La consulta no retornó datos para esta fecha.")
    else:
        st.write(f"**Modelos:** {sorted(df_diag['MODELO'].unique().tolist())}")
        st.write(f"**Valores únicos MONEDA_ORIGEN:** {sorted(df_diag['MONEDA_ORIGEN'].unique().tolist())}")
        st.write(f"**Valores únicos CODIGO_PRODUCTO:** {sorted(df_diag['CODIGO_PRODUCTO'].unique().tolist())}")
        st.dataframe(df_diag, use_container_width=True)

# Exploración de tablas
st.divider()
st.subheader("📋 Explorar tabla completa")

col_tabla, col_fecha_exp = st.columns(2)
with col_tabla:
    nombre_tabla_exp = st.selectbox("Tabla", list(NOMBRES_TABLAS.keys()), key="tabla_exp")
with col_fecha_exp:
    fecha_exp = st.selectbox(
        "Fecha",
        options=fechas,
        format_func=lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
        key="fecha_exp",
    )

tabla_exp = NOMBRES_TABLAS[nombre_tabla_exp]


if st.button("Consultar tabla", key="btn_explorar"):
    with st.spinner("Consultando tabla completa…"):
        df_tabla = obtener_tabla_completa(tabla_exp, str(fecha_exp))

    if df_tabla.empty:
        st.warning("Sin datos para esta tabla y fecha.")
    else:
        st.write(f"**{len(df_tabla):,}** registros encontrados.")
        st.dataframe(df_tabla, use_container_width=True, height=400)

        csv = df_tabla.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name=f"{tabla_exp}_{fecha_exp}.csv",
            mime="text/csv",
        )
