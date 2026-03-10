"""
Dashboard de control para datos históricos en GCP BigQuery.

Comparativa de SUM(AMORTIZACION) agrupada por MONEDA_ORIGEN y CODIGO_PRODUCTO
entre un día procesado (t) y su día procesado anterior (t-1).  Se muestran
todos los modelos consolidados en una sola página, con un gráfico por moneda.

Ejecución:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar config
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account

from config import config_rutas as cr

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PROJECT_ID = "bfa-cl-trade-price-report-dev"
DATASET_HIST = "bfa_cl_prd_financial_risk_dly_proc_models_hist"

TABLAS_HIST = [
    "report_mr_prepago_hipotecario_hist",
    "report_mr_prepago_consumo_hist",
    "report_mr_prepago_cmr_hist",
    "report_ml_mora_consumo_hist",
    "report_ml_mora_consumo_renegociado_hist",
    "report_ml_mora_cae_hist",
    "report_ml_mora_hipotecario_hist",
    "report_ml_mora_comercial_hist",
    "report_ml_nmd_hist",
    "report_ml_lc_hist",
    "report_ml_inversiones_hist",
]

# Productos a incluir en el dashboard
CODIGO_PRODUCTOS = [
    "ML_C46_MORA_CREDITO_CONSUMO",
    "ML_C46_MORA_CREDITO_RENEGOCIADO",
    "ML_SCSA_Contingente_Derivados",
    "ML_C46_MORA_CREDITO_COMERCIAL",
    "ML_C46_MORA_CREDITO_HIPOTECARIO",
    "ML_Contingente_Derivados",
    "MT_R13_HIPOTECARIO_BASE",
    "MT_R13_CONSUMO_BASE",
]

# Etiquetas legibles para MONEDA_ORIGEN (los valores en BQ ya son strings)
ETIQUETAS_MONEDA = {"USD": "USD", "CLF": "CLF", "CLP": "CLP"}
MONEDAS_INTERES = list(ETIQUETAS_MONEDA.keys())


# ---------------------------------------------------------------------------
# Conexión BigQuery (cacheada por sesión)
# ---------------------------------------------------------------------------

@st.cache_resource
def obtener_cliente_bq() -> bigquery.Client:
    """Crea y cachea el cliente de BigQuery usando la cuenta de servicio."""
    ruta_credenciales = cr.obtener_ruta_credenciales_gcp()
    credentials = service_account.Credentials.from_service_account_file(
        str(ruta_credenciales),
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=credentials)

# ---------------------------------------------------------------------------
# Helpers SQL
# ---------------------------------------------------------------------------

def _union_all_tablas() -> str:
    """Genera un UNION ALL de todas las tablas históricas."""
    selects = [
        f"SELECT * FROM `{PROJECT_ID}.{DATASET_HIST}.{t}`"
        for t in TABLAS_HIST
    ]
    return "\nUNION ALL\n".join(selects)

# ---------------------------------------------------------------------------
# Funciones de consulta
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def obtener_fechas_disponibles() -> list:
    """Retorna las FECHA_PROCESO distintas (de todas las tablas), ordenadas desc."""
    client = obtener_cliente_bq()
    subquery = _union_all_tablas()
    sql = f"""
        SELECT DISTINCT FECHA_PROCESO
        FROM ({subquery})
        WHERE FECHA_PROCESO < CURRENT_DATE()
        ORDER BY FECHA_PROCESO DESC
    """
    df = client.query(sql).to_dataframe()
    return df["FECHA_PROCESO"].tolist()


@st.cache_data(ttl=300)
def obtener_amortizacion(fecha: str) -> pd.DataFrame:
    """SUM(AMORTIZACION) agrupada por MONEDA_ORIGEN y CODIGO_PRODUCTO para una fecha."""
    client = obtener_cliente_bq()
    subquery = _union_all_tablas()
    sql = f"""
        SELECT
            CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
            CODIGO_PRODUCTO,
            SUM(AMORTIZACION) AS TOTAL_AMORTIZACION
        FROM ({subquery})
        WHERE FECHA_PROCESO = @fecha
          AND CODIGO_PRODUCTO IN UNNEST(@productos)
          AND CAST(MONEDA_ORIGEN AS STRING) IN UNNEST(@monedas)
        GROUP BY MONEDA_ORIGEN, CODIGO_PRODUCTO
        ORDER BY MONEDA_ORIGEN, CODIGO_PRODUCTO
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
            bigquery.ArrayQueryParameter("productos", "STRING", CODIGO_PRODUCTOS),
            bigquery.ArrayQueryParameter("monedas", "STRING", MONEDAS_INTERES),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Control Histórico GCP",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard de Control — Datos Históricos GCP")

# ---------------------------------------------------------------------------
# Sidebar: selección de fecha
# ---------------------------------------------------------------------------
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

    # Determinar fecha anterior (t-1)
    idx = fechas.index(fecha_seleccionada)
    if idx + 1 < len(fechas):
        fecha_anterior = fechas[idx + 1]
        st.info(f"Fecha anterior (t-1): **{fecha_anterior}**")
    else:
        fecha_anterior = None
        st.warning("No existe una fecha procesada anterior.")

# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
with st.spinner("Consultando datos…"):
    df_actual = obtener_amortizacion(str(fecha_seleccionada))

    if fecha_anterior is not None:
        df_anterior = obtener_amortizacion(str(fecha_anterior))
    else:
        df_anterior = pd.DataFrame(
            columns=["MONEDA_ORIGEN", "CODIGO_PRODUCTO", "TOTAL_AMORTIZACION"]
        )

# ---------------------------------------------------------------------------
# Preparar datos comparativos
# ---------------------------------------------------------------------------
df_comp = pd.merge(
    df_actual.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T"}),
    df_anterior.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T1"}),
    on=["MONEDA_ORIGEN", "CODIGO_PRODUCTO"],
    how="outer",
).fillna(0)

df_comp["DIFERENCIA"] = df_comp["AMORT_T"] - df_comp["AMORT_T1"]
df_comp["DIFERENCIA_%"] = df_comp.apply(
    lambda r: (r["DIFERENCIA"] / abs(r["AMORT_T1"]) * 100)
    if r["AMORT_T1"] != 0 else 0.0,
    axis=1,
)

# ---------------------------------------------------------------------------
# Métricas resumen globales
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Un gráfico por moneda (3 gráficos)
# ---------------------------------------------------------------------------
for cod_moneda, etiqueta_moneda in ETIQUETAS_MONEDA.items():
    st.subheader(f"Moneda: {etiqueta_moneda} ({cod_moneda})")

    df_moneda = df_comp[df_comp["MONEDA_ORIGEN"] == cod_moneda].sort_values(
        "CODIGO_PRODUCTO"
    )

    if df_moneda.empty:
        st.info(f"Sin datos para moneda {etiqueta_moneda}.")
        continue

    fig = go.Figure()

    # Barra izquierda: t-1
    if fecha_anterior is not None:
        fig.add_trace(go.Bar(
            x=df_moneda["CODIGO_PRODUCTO"],
            y=df_moneda["AMORT_T1"],
            name=f"t-1  ({fecha_anterior})",
            marker_color="#EF553B",
        ))

    # Barra derecha: t
    fig.add_trace(go.Bar(
        x=df_moneda["CODIGO_PRODUCTO"],
        y=df_moneda["AMORT_T"],
        name=f"t  ({fecha_seleccionada})",
        marker_color="#636EFA",
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

    # Tabla detalle por moneda
    with st.expander(f"Detalle {etiqueta_moneda}"):
        st.dataframe(
            df_moneda[["CODIGO_PRODUCTO", "AMORT_T", "AMORT_T1",
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

# ---------------------------------------------------------------------------
# Diagnóstico (temporal)
# ---------------------------------------------------------------------------
with st.expander("🔍 Diagnóstico — valores reales en BigQuery"):
    @st.cache_data(ttl=300)
    def diagnostico(fecha: str) -> pd.DataFrame:
        client = obtener_cliente_bq()
        subquery = _union_all_tablas()
        sql = f"""
            SELECT
                CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
                CODIGO_PRODUCTO,
                COUNT(*) AS filas,
                SUM(AMORTIZACION) AS sum_amort
            FROM ({subquery})
            WHERE FECHA_PROCESO = @fecha
            GROUP BY MONEDA_ORIGEN, CODIGO_PRODUCTO
            ORDER BY MONEDA_ORIGEN, CODIGO_PRODUCTO
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
            ]
        )
        return client.query(sql, job_config=job_config).to_dataframe()

    df_diag = diagnostico(str(fecha_seleccionada))
    if df_diag.empty:
        st.warning("La consulta no retornó datos para esta fecha. Verificar que existan registros.")
    else:
        st.write(f"**Valores únicos MONEDA_ORIGEN:** {sorted(df_diag['MONEDA_ORIGEN'].unique().tolist())}")
        st.write(f"**Valores únicos CODIGO_PRODUCTO:** {sorted(df_diag['CODIGO_PRODUCTO'].unique().tolist())}")
        st.dataframe(df_diag, use_container_width=True)

# ---------------------------------------------------------------------------
# Exploración de tablas completas con descarga
# ---------------------------------------------------------------------------
st.divider()
st.subheader("📋 Explorar tabla completa")

NOMBRES_TABLAS = {
    "Prepago Hipotecario": "report_mr_prepago_hipotecario_hist",
    "Prepago Consumo": "report_mr_prepago_consumo_hist",
    "Prepago CMR": "report_mr_prepago_cmr_hist",
    "Mora Consumo": "report_ml_mora_consumo_hist",
    "Mora Consumo Renegociado": "report_ml_mora_consumo_renegociado_hist",
    "Mora CAE": "report_ml_mora_cae_hist",
    "Mora Hipotecario": "report_ml_mora_hipotecario_hist",
    "Mora Comercial": "report_ml_mora_comercial_hist",
    "NMD": "report_ml_nmd_hist",
    "Línea de Crédito": "report_ml_lc_hist",
    "Inversiones": "report_ml_inversiones_hist",
}

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

@st.cache_data(ttl=300)
def obtener_tabla_completa(tabla: str, fecha: str) -> pd.DataFrame:
    client = obtener_cliente_bq()
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_HIST}.{tabla}`
        WHERE FECHA_PROCESO = @fecha
        ORDER BY CODIGO_PRODUCTO, MONEDA_ORIGEN
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()

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
