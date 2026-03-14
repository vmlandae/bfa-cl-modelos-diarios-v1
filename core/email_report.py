"""
Reporte de amortización por email — Primera Vuelta.

Genera charts Plotly (exportados a PNG vía kaleido), un Excel resumen
con detalle por moneda/producto, y envía todo vía Outlook COM (pywin32).

Uso desde terminal::

    python -m core.email_report --fecha 2026-03-12

Uso programático::

    from core.email_report import generar_y_enviar_reporte
    generar_y_enviar_reporte("2026-03-12")
"""

import argparse
import logging
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import yaml
from google.cloud import bigquery

from config.config_rutas import BASE_DIR

logger = logging.getLogger("bfa_modelos.email_report")

# ---------------------------------------------------------------------------
# Constantes: scope primera vuelta
# ---------------------------------------------------------------------------

_PROJECT_ID = "bfa-cl-trade-price-report-dev"
_DATASET_HIST = "bfa_cl_prd_financial_risk_dly_proc_models_hist"

TABLAS_PRIMERA_VUELTA = [
    "report_mr_prepago_hipotecario_hist",
    "report_mr_prepago_consumo_hist",
    "report_ml_mora_consumo_hist",
    "report_ml_mora_consumo_renegociado_hist",
    "report_ml_mora_cae_hist",
    "report_ml_mora_hipotecario_hist",
    "report_ml_mora_comercial_hist",
]

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

MONEDAS = ["CLP", "CLF", "USD"]

# Paleta corporativa
_COLOR_T = "#636EFA"    # azul — fecha actual
_COLOR_T1 = "#EF553B"   # rojo — fecha anterior

# ---------------------------------------------------------------------------
# Configuración desde YAML
# ---------------------------------------------------------------------------

_CONFIG_PATH = BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"


def _cargar_config_email() -> dict:
    """Lee la sección ``email_report`` del YAML de configuración."""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("email_report", {})


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------

def _get_bq_client() -> bigquery.Client:
    from config.config_rutas import obtener_ruta_credenciales_gcp
    cred_path = obtener_ruta_credenciales_gcp()
    return bigquery.Client.from_service_account_json(str(cred_path))


def _union_all() -> str:
    selects = [
        f"SELECT * FROM `{_PROJECT_ID}.{_DATASET_HIST}.{t}`"
        for t in TABLAS_PRIMERA_VUELTA
    ]
    return "\nUNION ALL\n".join(selects)


def obtener_fechas_disponibles(client: bigquery.Client) -> list[date]:
    """Retorna las fechas procesadas disponibles, orden desc."""
    sql = f"""
        SELECT DISTINCT FECHA_PROCESO
        FROM ({_union_all()})
        WHERE FECHA_PROCESO < CURRENT_DATE()
        ORDER BY FECHA_PROCESO DESC
    """
    df = client.query(sql).to_dataframe(create_bqstorage_client=False)
    return df["FECHA_PROCESO"].tolist()


def obtener_amortizacion(
    client: bigquery.Client, fecha: str
) -> pd.DataFrame:
    """SUM(AMORTIZACION) agrupado por MONEDA_ORIGEN × CODIGO_PRODUCTO."""
    sql = f"""
        SELECT
            CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
            CODIGO_PRODUCTO,
            SUM(AMORTIZACION) AS TOTAL_AMORTIZACION
        FROM ({_union_all()})
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
            bigquery.ArrayQueryParameter("monedas", "STRING", MONEDAS),
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe(
        create_bqstorage_client=False
    )


# ---------------------------------------------------------------------------
# Comparación t vs t-1
# ---------------------------------------------------------------------------

def _calcular_comparacion(
    client: bigquery.Client, fecha: str
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Retorna (df_comp, fecha_anterior).

    df_comp tiene columnas: MONEDA_ORIGEN, CODIGO_PRODUCTO, AMORT_T,
    AMORT_T1, DIFERENCIA, DIFERENCIA_PCT.
    """
    fechas = obtener_fechas_disponibles(client)

    if not fechas:
        raise RuntimeError("No hay fechas disponibles en BQ hist.")

    fecha_date = datetime.strptime(fecha, "%Y-%m-%d").date()

    # Buscar la fecha anterior disponible
    fecha_anterior = None
    for f in fechas:
        f_date = f if isinstance(f, date) else datetime.strptime(str(f), "%Y-%m-%d").date()
        if f_date < fecha_date:
            fecha_anterior = str(f_date)
            break

    df_actual = obtener_amortizacion(client, fecha)

    if fecha_anterior:
        df_anterior = obtener_amortizacion(client, fecha_anterior)
    else:
        df_anterior = pd.DataFrame(
            columns=["MONEDA_ORIGEN", "CODIGO_PRODUCTO", "TOTAL_AMORTIZACION"]
        )

    df_comp = pd.merge(
        df_actual.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T"}),
        df_anterior.rename(columns={"TOTAL_AMORTIZACION": "AMORT_T1"}),
        on=["MONEDA_ORIGEN", "CODIGO_PRODUCTO"],
        how="outer",
    ).fillna(0)

    df_comp["DIFERENCIA"] = df_comp["AMORT_T"] - df_comp["AMORT_T1"]
    df_comp["DIFERENCIA_PCT"] = df_comp.apply(
        lambda r: (r["DIFERENCIA"] / abs(r["AMORT_T1"]) * 100)
        if r["AMORT_T1"] != 0
        else 0.0,
        axis=1,
    )

    return df_comp, fecha_anterior


# ---------------------------------------------------------------------------
# Charts Plotly → PNG
# ---------------------------------------------------------------------------

def _generar_chart_moneda(
    df_moneda: pd.DataFrame,
    moneda: str,
    fecha: str,
    fecha_anterior: Optional[str],
) -> go.Figure:
    """Crea un chart de barras agrupadas para una moneda."""
    fig = go.Figure()

    if fecha_anterior is not None:
        fig.add_trace(go.Bar(
            x=df_moneda["CODIGO_PRODUCTO"],
            y=df_moneda["AMORT_T1"],
            name=f"t-1  ({fecha_anterior})",
            marker_color=_COLOR_T1,
            text=df_moneda["AMORT_T1"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
            textfont_size=9,
        ))

    fig.add_trace(go.Bar(
        x=df_moneda["CODIGO_PRODUCTO"],
        y=df_moneda["AMORT_T"],
        name=f"t  ({fecha})",
        marker_color=_COLOR_T,
        text=df_moneda["AMORT_T"].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
        textfont_size=9,
    ))

    # Anotaciones de Δ% sobre cada par de barras
    for _, row in df_moneda.iterrows():
        if row["AMORT_T1"] != 0:
            delta_text = f"{row['DIFERENCIA_PCT']:+.1f}%"
            y_max = max(row["AMORT_T"], row["AMORT_T1"])
            fig.add_annotation(
                x=row["CODIGO_PRODUCTO"],
                y=y_max * 1.15,
                text=f"<b>{delta_text}</b>",
                showarrow=False,
                font=dict(
                    size=10,
                    color="green" if row["DIFERENCIA_PCT"] >= 0 else "red",
                ),
            )

    fig.update_layout(
        title=f"Amortización por Producto — {moneda}",
        barmode="group",
        xaxis_title="Código Producto",
        yaxis_title="Sum Amortización",
        legend_title="Fecha Proceso",
        height=500,
        width=800,
        xaxis_tickangle=-30,
        margin=dict(t=80, b=100),
        font=dict(family="Segoe UI, Arial", size=11),
    )

    return fig


def _exportar_charts(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    directorio: Path,
) -> dict[str, Path]:
    """
    Genera PNGs por moneda. Retorna dict {moneda: ruta_png}.
    """
    rutas = {}
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        if df_m.empty:
            continue

        fig = _generar_chart_moneda(df_m, moneda, fecha, fecha_anterior)
        ruta_png = directorio / f"chart_{moneda.lower()}.png"
        fig.write_image(str(ruta_png), format="png", width=800, height=500, scale=2)
        rutas[moneda] = ruta_png
        logger.info("Chart generado: %s", ruta_png.name)

    return rutas


# ---------------------------------------------------------------------------
# Excel adjunto
# ---------------------------------------------------------------------------

def _generar_excel(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    directorio: Path,
) -> Path:
    """Genera un .xlsx con una hoja por moneda + hoja resumen."""
    ruta_excel = directorio / f"reporte_amortizacion_{fecha}.xlsx"

    hojas = {}
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        if df_m.empty:
            continue
        hojas[moneda] = df_m[
            ["CODIGO_PRODUCTO", "AMORT_T", "AMORT_T1", "DIFERENCIA", "DIFERENCIA_PCT"]
        ].copy()

    # Hoja resumen por moneda
    resumen_rows = []
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda]
        total_t = df_m["AMORT_T"].sum()
        total_t1 = df_m["AMORT_T1"].sum()
        diff = total_t - total_t1
        pct = (diff / abs(total_t1) * 100) if total_t1 != 0 else 0.0
        resumen_rows.append({
            "MONEDA": moneda,
            "TOTAL_T": total_t,
            "TOTAL_T1": total_t1,
            "DIFERENCIA": diff,
            "DIFERENCIA_PCT": pct,
        })
    hojas["Resumen"] = pd.DataFrame(resumen_rows)

    from core.excel_output import guardar_excel
    guardar_excel(
        ruta_archivo=ruta_excel,
        hojas=hojas,
        formatos_columnas={
            "AMORT_T": "#,##0.00",
            "AMORT_T1": "#,##0.00",
            "TOTAL_T": "#,##0.00",
            "TOTAL_T1": "#,##0.00",
            "DIFERENCIA": "#,##0.00",
            "DIFERENCIA_PCT": "0.00",
        },
    )
    logger.info("Excel generado: %s", ruta_excel.name)
    return ruta_excel


# ---------------------------------------------------------------------------
# Cuerpo HTML del email
# ---------------------------------------------------------------------------

def _construir_html(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    chart_cids: dict[str, str],
) -> str:
    """Construye el HTML del email con tablas resumen e imágenes CID."""

    # Tabla resumen por moneda
    filas_resumen = []
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda]
        total_t = df_m["AMORT_T"].sum()
        total_t1 = df_m["AMORT_T1"].sum()
        diff = total_t - total_t1
        pct = (diff / abs(total_t1) * 100) if total_t1 != 0 else 0.0
        color = "green" if pct >= 0 else "red"
        filas_resumen.append(
            f"<tr>"
            f"<td style='padding:4px 8px'><b>{moneda}</b></td>"
            f"<td style='padding:4px 8px;text-align:right'>{total_t:,.2f}</td>"
            f"<td style='padding:4px 8px;text-align:right'>{total_t1:,.2f}</td>"
            f"<td style='padding:4px 8px;text-align:right;color:{color}'>{pct:+.2f}%</td>"
            f"</tr>"
        )

    tabla_resumen = "\n".join(filas_resumen)

    # Bloques de charts
    charts_html = ""
    for moneda, cid in chart_cids.items():
        charts_html += f"""
        <h3 style="color:#333;margin-top:20px">{moneda}</h3>
        <img src="cid:{cid}" width="800" style="max-width:100%">
        """

    fecha_ant_str = fecha_anterior or "N/A"

    html = f"""\
<html>
<body style="font-family:Segoe UI,Arial,sans-serif;color:#333;max-width:900px;margin:0 auto">
  <h2 style="color:#1a1a2e;border-bottom:2px solid #636EFA;padding-bottom:8px">
    Reporte Amortización Primera Vuelta &mdash; {fecha}
  </h2>
  <p>Comparación vs día anterior (<b>{fecha_ant_str}</b>)</p>

  <table style="border-collapse:collapse;margin:10px 0" border="1" cellpadding="5">
    <tr style="background:#636EFA;color:white">
      <th>Moneda</th><th>Total t</th><th>Total t-1</th><th>&Delta;%</th>
    </tr>
    {tabla_resumen}
  </table>

  {charts_html}

  <hr style="margin-top:30px">
  <p style="font-size:11px;color:#888">
    Detalle completo en el Excel adjunto.<br>
    Generado automáticamente por <b>bfa-cl-modelos-diarios</b>.
  </p>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Envío vía Outlook COM
# ---------------------------------------------------------------------------

def _enviar_outlook(
    destinatarios: list[str],
    asunto: str,
    cuerpo_html: str,
    adjuntos: list[Path],
    imagenes_cid: dict[str, Path],
    modo: str = "send",
) -> None:
    """
    Crea y envía (o muestra) un email vía Outlook COM.

    Args:
        destinatarios: lista de direcciones email.
        asunto: asunto del email.
        cuerpo_html: HTML body con referencias CID.
        adjuntos: archivos a adjuntar (Excel, etc.).
        imagenes_cid: dict {content_id: ruta_png} para embeber inline.
        modo: "send" para enviar directo, "display" para mostrar en Outlook.
    """
    import win32com.client

    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # olMailItem
    mail.To = "; ".join(destinatarios)
    mail.Subject = asunto

    # Agregar adjuntos (Excel)
    for ruta in adjuntos:
        mail.Attachments.Add(str(ruta))

    # Embeber imágenes CID
    # Outlook COM: agregar como attachment y setear ContentId
    # para que se referencien con cid: en el HTML body
    PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"

    for cid, ruta_img in imagenes_cid.items():
        att = mail.Attachments.Add(str(ruta_img))
        pa = att.PropertyAccessor
        pa.SetProperty(PR_ATTACH_CONTENT_ID, cid)

    mail.HTMLBody = cuerpo_html

    if modo == "display":
        mail.Display()
        logger.info("Email abierto en Outlook para revisión.")
    else:
        mail.Send()
        logger.info("Email enviado a: %s", ", ".join(destinatarios))


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def generar_y_enviar_reporte(
    fecha: str,
    modo: Optional[str] = None,
    destinatarios: Optional[list[str]] = None,
) -> None:
    """
    Genera el reporte completo y lo envía por email.

    Args:
        fecha: fecha de proceso en formato YYYY-MM-DD.
        modo: "send" o "display". Si None, lee del YAML.
        destinatarios: override de destinatarios. Si None, lee del YAML.
    """
    cfg = _cargar_config_email()

    if not cfg.get("enabled", True):
        logger.info("Email report deshabilitado en configuración.")
        return

    destinatarios = destinatarios or cfg.get("destinatarios", [])
    if not destinatarios:
        logger.warning("Sin destinatarios configurados. Abortando envío.")
        return

    modo = modo or cfg.get("modo", "send")
    asunto_template = cfg.get(
        "asunto_template",
        "Reporte Amortización Primera Vuelta — {fecha}",
    )
    asunto = asunto_template.format(fecha=fecha)

    logger.info("Generando reporte de amortización para %s…", fecha)

    # 1. Consultar BQ
    client = _get_bq_client()
    df_comp, fecha_anterior = _calcular_comparacion(client, fecha)

    if df_comp.empty:
        logger.warning("Sin datos de amortización para %s. No se envía email.", fecha)
        return

    # 2. Generar artefactos en directorio temporal
    with tempfile.TemporaryDirectory(prefix="email_report_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Charts PNG
        chart_rutas = _exportar_charts(df_comp, fecha, fecha_anterior, tmpdir_path)

        # Excel
        ruta_excel = _generar_excel(df_comp, fecha, fecha_anterior, tmpdir_path)

        # CIDs para las imágenes
        chart_cids = {}
        imagenes_cid = {}
        for moneda, ruta_png in chart_rutas.items():
            cid = f"chart_{moneda.lower()}"
            chart_cids[moneda] = cid
            imagenes_cid[cid] = ruta_png

        # HTML
        cuerpo_html = _construir_html(df_comp, fecha, fecha_anterior, chart_cids)

        # 3. Enviar
        _enviar_outlook(
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            adjuntos=[ruta_excel],
            imagenes_cid=imagenes_cid,
            modo=modo,
        )

    logger.info("Reporte de amortización %s completado.", fecha)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Genera y envía reporte de amortización primera vuelta por email."
    )
    parser.add_argument(
        "--fecha",
        required=True,
        help="Fecha de proceso (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--modo",
        choices=["send", "display"],
        default=None,
        help="Modo de envío. Default: lee del YAML (send).",
    )
    parser.add_argument(
        "--destinatarios",
        nargs="+",
        default=None,
        help="Override de destinatarios (sepados por espacio).",
    )
    args = parser.parse_args()

    # Setup logging básico si se ejecuta standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    generar_y_enviar_reporte(
        fecha=args.fecha,
        modo=args.modo,
        destinatarios=args.destinatarios,
    )


if __name__ == "__main__":
    main()
