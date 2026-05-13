"""
Reporte de amortizacion por email -- Sistema multi-tipo (F26).

Soporta multiples tipos de reporte:
- ``primera_vuelta``: amortizacion modelos V1 (prepago consumo/hipotecario, mora)
- ``segunda_vuelta``: amortizacion modelos V2 (CMR, NMD, LC, inversiones)
- ``chequeo_interfaces``: sumas de control PML GCP/CMR (pendiente)

Genera charts Plotly (exportados a PNG via kaleido), un Excel resumen
con detalle por moneda/producto, y envía todo vía Outlook COM (pywin32).

Uso desde terminal::

    python -m core.email_report --fecha 2026-03-12
    python -m core.email_report --fecha 2026-03-12 --tipo segunda_vuelta

Uso programático::

    from core.email_report import generar_y_enviar_reporte
    generar_y_enviar_reporte("2026-03-12", tipo_reporte="primera_vuelta")
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
from core.modelos_registry import todas_las_tablas_hist

logger = logging.getLogger("bfa_modelos.email_report")

# ---------------------------------------------------------------------------
# Constantes: tablas por tipo de reporte
# ---------------------------------------------------------------------------

_PROJECT_ID = "bfa-cl-trade-price-report-dev"
_DATASET_HIST = "bfa_cl_prd_financial_risk_dly_proc_models_hist"

# Derivado del registry (F28). Antes de F28 las listas estaban hardcoded y
# se desincronizaron varias veces con el orquestador.
TABLAS_PRIMERA_VUELTA = todas_las_tablas_hist(vuelta=1)
TABLAS_SEGUNDA_VUELTA = todas_las_tablas_hist(vuelta=2)
# F30: tipo unificado = todas las tablas (V1 + V2).
TABLAS_UNIFICADO = TABLAS_PRIMERA_VUELTA + TABLAS_SEGUNDA_VUELTA

_TABLAS_POR_TIPO = {
    "primera_vuelta": TABLAS_PRIMERA_VUELTA,
    "segunda_vuelta": TABLAS_SEGUNDA_VUELTA,
    "unificado": TABLAS_UNIFICADO,
}

_TITULO_POR_TIPO = {
    "primera_vuelta": "Primera Vuelta",
    "segunda_vuelta": "Segunda Vuelta",
    "unificado": "Unificado (V1 + V2)",
}

# CODIGO_PRODUCTOS eliminado (F28): la comparativa pasa de 8 productos
# hardcoded a TODOS los productos presentes en BQ por modelo×moneda.
# La query agrupa por MODELO también para no perder cobertura.

MONEDAS = ["CLP", "CLF", "USD"]

# Paleta corporativa
_COLOR_T = "#4CAF50"    # verde -- fecha actual
_COLOR_T1 = "#90CAF9"   # celeste -- fecha anterior

# ---------------------------------------------------------------------------
# Configuración desde YAML
# ---------------------------------------------------------------------------

_CONFIG_PATH = BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"


def _cargar_config_email(tipo_reporte: str = "primera_vuelta") -> dict:
    """Lee la sección ``email_report`` del YAML, mergeando config del tipo.

    Retorna dict con claves: enabled, destinatarios, modo,
    auto_post_ejecucion, asunto_template (del tipo específico).
    """
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base = cfg.get("email_report", {})

    # Config del tipo específico
    reportes = base.get("reportes", {})
    tipo_cfg = reportes.get(tipo_reporte, {})

    # Merge: base + tipo (tipo sobreescribe)
    resultado = {
        "enabled": base.get("enabled", True) and tipo_cfg.get("enabled", True),
        "destinatarios": base.get("destinatarios", []),
        "modo": base.get("modo", "send"),
        "auto_post_ejecucion": base.get("auto_post_ejecucion", False),
        "asunto_template": tipo_cfg.get(
            "asunto_template",
            f"Reporte Amortizacion -- {{fecha}}",
        ),
    }
    return resultado


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------

def _get_bq_client() -> bigquery.Client:
    from config.config_rutas import obtener_ruta_credenciales_gcp
    cred_path = obtener_ruta_credenciales_gcp()
    return bigquery.Client.from_service_account_json(str(cred_path))


def _union_all(tablas: list[str] | None = None) -> str:
    if tablas is None:
        tablas = TABLAS_PRIMERA_VUELTA
    selects = [
        f"SELECT * FROM `{_PROJECT_ID}.{_DATASET_HIST}.{t}`"
        for t in tablas
    ]
    return "\nUNION ALL\n".join(selects)


def obtener_fechas_disponibles(
    client: bigquery.Client,
    tablas: list[str] | None = None,
) -> list[date]:
    """Retorna las fechas procesadas disponibles, orden desc."""
    sql = f"""
        SELECT DISTINCT FECHA_PROCESO
        FROM ({_union_all(tablas)})
        WHERE FECHA_PROCESO < CURRENT_DATE()
        ORDER BY FECHA_PROCESO DESC
    """
    df = client.query(sql).to_dataframe(create_bqstorage_client=False)
    return df["FECHA_PROCESO"].tolist()


def obtener_amortizacion(
    client: bigquery.Client,
    fecha: str,
    tablas: list[str] | None = None,
) -> pd.DataFrame:
    """SUM(AMORTIZACION) agrupado por MONEDA_ORIGEN × CODIGO_PRODUCTO.

    F28: sin filtro de CODIGO_PRODUCTOS hardcoded. Cubre todos los productos
    presentes en BQ por modelo×moneda.
    """
    sql = f"""
        SELECT
            CAST(MONEDA_ORIGEN AS STRING) AS MONEDA_ORIGEN,
            CODIGO_PRODUCTO,
            SUM(AMORTIZACION) AS TOTAL_AMORTIZACION
        FROM ({_union_all(tablas)})
        WHERE FECHA_PROCESO = @fecha
          AND CAST(MONEDA_ORIGEN AS STRING) IN UNNEST(@monedas)
        GROUP BY MONEDA_ORIGEN, CODIGO_PRODUCTO
        ORDER BY MONEDA_ORIGEN, CODIGO_PRODUCTO
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fecha", "DATE", fecha),
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
    client: bigquery.Client,
    fecha: str,
    tablas: list[str] | None = None,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Retorna (df_comp, fecha_anterior).

    df_comp tiene columnas: MONEDA_ORIGEN, CODIGO_PRODUCTO, AMORT_T,
    AMORT_T1, DIFERENCIA, DIFERENCIA_PCT.
    """
    fechas = obtener_fechas_disponibles(client, tablas)

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

    df_actual = obtener_amortizacion(client, fecha, tablas)

    if fecha_anterior:
        df_anterior = obtener_amortizacion(client, fecha_anterior, tablas)
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
# Charts Plotly -> PNG
# ---------------------------------------------------------------------------

def _escala_eje(max_val: float) -> tuple[float, str]:
    """Retorna (divisor, sufijo) para escalar el eje Y de forma legible."""
    abs_max = abs(max_val) if max_val else 1
    if abs_max >= 1_000_000_000:
        return 1_000_000_000, "Miles de MM"
    if abs_max >= 1_000_000:
        return 1_000_000, "Millones"
    if abs_max >= 1_000:
        return 1_000, "Miles"
    return 1, ""


def _generar_chart_modelo(
    producto: str,
    amort_t: float,
    amort_t1: float,
    fecha: str,
    fecha_anterior: Optional[str],
    moneda: str,
) -> go.Figure:
    """Crea un chart de 2 barras (t-1, t) para un modelo individual."""
    fig = go.Figure()

    labels = []
    values = []
    colors = []

    if fecha_anterior is not None:
        labels.append(fecha_anterior)
        values.append(amort_t1)
        colors.append(_COLOR_T1)

    labels.append(fecha)
    values.append(amort_t)
    colors.append(_COLOR_T)

    # Escala inteligente del eje Y
    raw_max = max(abs(v) for v in values) if values else 1
    divisor, sufijo_y = _escala_eje(raw_max)
    scaled_values = [v / divisor for v in values]

    fig.add_trace(go.Bar(
        x=labels,
        y=scaled_values,
        marker_color=colors,
        width=0.35,
    ))

    # Delta % como anotacion centrada arriba
    if fecha_anterior is not None and amort_t1 != 0:
        delta_pct = (amort_t - amort_t1) / abs(amort_t1) * 100
        delta_color = "#2E7D32" if delta_pct >= 0 else "#C62828"
        delta_text = f"{delta_pct:+.2f}%"
        y_annot = max(scaled_values) * 1.05
        fig.add_annotation(
            x=0.5, xref="paper",
            y=y_annot, yref="y",
            text=f"<b>{delta_text}</b>",
            showarrow=False,
            font=dict(size=13, color=delta_color),
        )

    y_label = f"{sufijo_y} ({moneda})" if sufijo_y else moneda
    y_top = max(scaled_values) * 1.20 if scaled_values else 1

    fig.update_layout(
        title=dict(text=producto, font=dict(size=12, color="#333")),
        yaxis_title=y_label,
        showlegend=False,
        height=320,
        width=340,
        margin=dict(t=45, b=35, l=55, r=15),
        font=dict(family="Segoe UI, Arial", size=10),
        xaxis=dict(type="category", tickfont=dict(size=10)),
        yaxis=dict(range=[0, y_top], tickformat=",.1f",
                   gridcolor="#eee", zeroline=False),
        plot_bgcolor="white",
    )

    return fig


def _exportar_charts(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    directorio: Path,
) -> dict[str, Path]:
    """
    Genera PNGs por modelo y moneda. Retorna dict {cid_key: ruta_png}.
    cid_key = "moneda__producto" (ej: "clp__MT_R13_CONSUMO_BASE").
    """
    rutas = {}
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        if df_m.empty:
            continue
        for _, row in df_m.iterrows():
            producto = row["CODIGO_PRODUCTO"]
            fig = _generar_chart_modelo(
                producto, row["AMORT_T"], row["AMORT_T1"],
                fecha, fecha_anterior, moneda,
            )
            safe_prod = producto.replace(" ", "_")
            cid_key = f"{moneda.lower()}__{safe_prod}"
            ruta_png = directorio / f"chart_{cid_key}.png"
            fig.write_image(str(ruta_png), format="png", width=340, height=320, scale=2)
            rutas[cid_key] = ruta_png
        logger.info("Charts %s: %d modelos exportados.", moneda, len(df_m))

    return rutas


# ---------------------------------------------------------------------------
# Excel adjunto
# ---------------------------------------------------------------------------

def _generar_excel(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    directorio: Path,
    tipo_reporte: str = "primera_vuelta",
) -> Path:
    """Genera un .xlsx con una hoja por moneda + hoja resumen."""
    sufijo = tipo_reporte.replace("_", "-")
    ruta_excel = directorio / f"reporte_amortizacion_{sufijo}_{fecha}.xlsx"

    fecha_ant_str = fecha_anterior or "N/A"
    col_t = f"AMORT_{fecha}"
    col_t1 = f"AMORT_{fecha_ant_str}"

    hojas = {}
    for moneda in MONEDAS:
        df_m = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        if df_m.empty:
            continue
        hoja = df_m[
            ["CODIGO_PRODUCTO", "AMORT_T", "AMORT_T1", "DIFERENCIA", "DIFERENCIA_PCT"]
        ].copy()
        hoja = hoja.rename(columns={"AMORT_T": col_t, "AMORT_T1": col_t1})
        hojas[moneda] = hoja

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
            f"TOTAL_{fecha}": total_t,
            f"TOTAL_{fecha_ant_str}": total_t1,
            "DIFERENCIA": diff,
            "DIFERENCIA_PCT": pct,
        })
    hojas["Resumen"] = pd.DataFrame(resumen_rows)

    from core.excel_output import guardar_excel
    guardar_excel(
        ruta_archivo=ruta_excel,
        hojas=hojas,
        formatos_columnas={
            col_t: "#,##0.00",
            col_t1: "#,##0.00",
            f"TOTAL_{fecha}": "#,##0.00",
            f"TOTAL_{fecha_ant_str}": "#,##0.00",
            "DIFERENCIA": "#,##0.00",
            "DIFERENCIA_PCT": "0.00",
        },
    )
    logger.info("Excel generado: %s", ruta_excel.name)
    return ruta_excel


# ---------------------------------------------------------------------------
# Cuerpo HTML del email
# ---------------------------------------------------------------------------

def _leer_controles_dia(client: bigquery.Client, fecha: str) -> pd.DataFrame:
    """Lee controles_diarios para una fecha. Vacío si tabla no existe (F30)."""
    sql = f"""
        SELECT modelo, tabla, check_id, nivel, mensaje, evidencia_json
        FROM `{_PROJECT_ID}.bfa_cl_prd_financial_risk_dly_proc_models.controles_diarios`
        WHERE fecha_proceso = @fecha
        ORDER BY modelo, nivel DESC, check_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("fecha", "DATE", fecha)]
    )
    try:
        return client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
    except Exception as exc:
        logger.warning("No se pudieron leer controles del día: %s", exc)
        return pd.DataFrame()


def _construir_seccion_salud(df_ctrl: pd.DataFrame, fecha: str) -> tuple[str, str]:
    """Construye sección de salud (banner + anexo CRITICAL) y devuelve nivel_global.

    Returns:
        (html_seccion, nivel_global) — nivel_global es 'OK', 'WARNING' o 'CRITICAL'.
    """
    if df_ctrl.empty:
        return (
            f'<div style="padding:10px 14px;border-radius:6px;background:#f0f0f0;'
            f'border-left:4px solid #999;margin-bottom:16px;font-size:13px;color:#555">'
            f'<b>ℹ️ Controles del día</b><br>'
            f'No hay registros en <code>controles_diarios</code> para {fecha} todavía.'
            f'</div>',
            "OK",
        )

    counts = df_ctrl["nivel"].value_counts().to_dict()
    n_crit = int(counts.get("CRITICAL", 0))
    n_warn = int(counts.get("WARNING", 0))
    n_ok = int(counts.get("OK", 0))
    n_info = int(counts.get("INFO", 0))

    if n_crit:
        color, label, nivel_global = "#dc3545", "🔴 CRITICAL", "CRITICAL"
    elif n_warn:
        color, label, nivel_global = "#ffc107", "🟡 WARNING", "WARNING"
    else:
        color, label, nivel_global = "#28a745", "🟢 OK", "OK"

    banner = (
        f'<div style="padding:12px 16px;border-radius:6px;background:{color}22;'
        f'border-left:4px solid {color};margin-bottom:16px;">'
        f'<div style="font-size:16px;font-weight:600;color:#1a1a2e">'
        f'Salud de los modelos &mdash; {fecha}: {label}</div>'
        f'<div style="font-size:13px;color:#555;margin-top:4px">'
        f'CRITICAL = <b>{n_crit}</b> · WARNING = <b>{n_warn}</b> · '
        f'OK = <b>{n_ok}</b> · INFO = <b>{n_info}</b></div>'
        f'</div>'
    )

    if n_crit == 0:
        return banner, nivel_global

    # Anexo de CRITICAL
    criticos = df_ctrl[df_ctrl["nivel"] == "CRITICAL"]
    filas = []
    for _, r in criticos.iterrows():
        filas.append(
            f'<tr style="background:#fff5f5">'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f0d0d0">'
            f'<b>{r["modelo"]}</b></td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f0d0d0">'
            f'<code>{r["check_id"]}</code></td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #f0d0d0">'
            f'{r["mensaje"]}</td>'
            f'</tr>'
        )
    anexo = (
        f'<div style="margin-bottom:20px;">'
        f'<h3 style="color:#dc3545;margin-bottom:8px;font-size:15px">'
        f'⚠️ Anexo: alertas CRITICAL</h3>'
        f'<table style="border-collapse:collapse;width:100%;font-size:12px;'
        f'border:1px solid #f0d0d0">'
        f'<tr style="background:#dc3545;color:#fff">'
        f'<th style="padding:6px 10px;text-align:left">Modelo</th>'
        f'<th style="padding:6px 10px;text-align:left">Check</th>'
        f'<th style="padding:6px 10px;text-align:left">Mensaje</th></tr>'
        f'{"".join(filas)}</table></div>'
    )

    return banner + anexo, nivel_global


def _construir_html(
    df_comp: pd.DataFrame,
    fecha: str,
    fecha_anterior: Optional[str],
    chart_cids: dict[str, str],
    titulo_vuelta: str = "Primera Vuelta",
    seccion_salud_html: str = "",
) -> str:
    """Construye el HTML del email con tabla resumen por modelo e imagenes CID."""

    fecha_ant_str = fecha_anterior or "N/A"

    # Tabla resumen: una fila por modelo (producto) con delta% por moneda
    # Agrupar productos unicos
    productos = sorted(df_comp["CODIGO_PRODUCTO"].unique())
    monedas_presentes = [m for m in MONEDAS if m in df_comp["MONEDA_ORIGEN"].values]

    filas_resumen = []
    for prod in productos:
        df_p = df_comp[df_comp["CODIGO_PRODUCTO"] == prod]
        celdas_delta = ""
        for mon in monedas_presentes:
            df_pm = df_p[df_p["MONEDA_ORIGEN"] == mon]
            if df_pm.empty:
                celdas_delta += "<td style='padding:4px 8px;text-align:center;color:#999'>--</td>"
            else:
                row = df_pm.iloc[0]
                pct = row["DIFERENCIA_PCT"]
                color = "#2E7D32" if pct >= 0 else "#C62828"
                arrow = "&#9650;" if pct > 0 else ("&#9660;" if pct < 0 else "")
                celdas_delta += (
                    f"<td style='padding:4px 8px;text-align:right;color:{color}'>"
                    f"{arrow} {pct:+.2f}%</td>"
                )
        filas_resumen.append(
            f"<tr><td style='padding:4px 8px'>{prod}</td>{celdas_delta}</tr>"
        )

    th_monedas = "".join(
        f"<th style='padding:4px 8px'>Delta% {m}</th>" for m in monedas_presentes
    )
    tabla_resumen = "\n".join(filas_resumen)

    # Bloques de charts: agrupados por moneda, chart + data card por modelo
    charts_html = ""
    for moneda in monedas_presentes:
        charts_html += (
            f'<h3 style="color:#1a1a2e;margin-top:28px;border-bottom:2px solid #e0e0e0;'
            f'padding-bottom:6px;font-size:16px">{moneda}</h3>'
        )
        df_mon = df_comp[df_comp["MONEDA_ORIGEN"] == moneda].sort_values("CODIGO_PRODUCTO")
        for _, r in df_mon.iterrows():
            prod = r["CODIGO_PRODUCTO"]
            safe_prod = prod.replace(" ", "_")
            cid_key = f"{moneda.lower()}__{safe_prod}"
            cid_val = chart_cids.get(cid_key, "")
            # Delta
            pct = r["DIFERENCIA_PCT"]
            delta_color = "#2E7D32" if pct >= 0 else "#C62828"
            delta_arrow = "&#9650;" if pct > 0 else ("&#9660;" if pct < 0 else "")
            diff_fmt = f"{r['DIFERENCIA']:,.0f}"
            # Data card
            card = (
                f'<table style="border-collapse:collapse;font-size:12px;margin-top:8px" cellpadding="4">'
                f'<tr style="background:#f5f5f5"><td style="color:#666">{fecha_ant_str}</td>'
                f'<td style="text-align:right;font-weight:600">{r["AMORT_T1"]:,.0f}</td></tr>'
                f'<tr style="background:#e8f5e9"><td style="color:#333">{fecha}</td>'
                f'<td style="text-align:right;font-weight:600">{r["AMORT_T"]:,.0f}</td></tr>'
                f'<tr><td style="color:#666">Diferencia</td>'
                f'<td style="text-align:right;color:{delta_color};font-weight:600">{diff_fmt}</td></tr>'
                f'<tr><td style="color:#666">Variacion</td>'
                f'<td style="text-align:right;color:{delta_color};font-weight:700;font-size:14px">'
                f'{delta_arrow} {pct:+.2f}%</td></tr>'
                f'</table>'
            )
            charts_html += (
                f'<div style="display:flex;align-items:center;gap:12px;'
                f'margin:10px 0;padding:8px;border:1px solid #eee;border-radius:6px;background:#fafafa">'
                f'<div style="flex:0 0 340px"><img src="cid:{cid_val}" width="340" style="max-width:100%"></div>'
                f'<div style="flex:1;min-width:160px">{card}</div>'
                f'</div>'
            )

    html = f"""\
<html>
<body style="font-family:Segoe UI,Arial,sans-serif;color:#333;max-width:950px;margin:0 auto">
  <h2 style="color:#1a1a2e;border-bottom:2px solid #4CAF50;padding-bottom:8px">
    Reporte Amortizacion {titulo_vuelta} &mdash; {fecha}
  </h2>
  {seccion_salud_html}
  <p>Comparacion: <b>{fecha}</b> vs <b>{fecha_ant_str}</b></p>

  <table style="border-collapse:collapse;margin:10px 0" border="1" cellpadding="5">
    <tr style="background:#37474F;color:white">
      <th style="padding:4px 8px">Modelo</th>{th_monedas}
    </tr>
    {tabla_resumen}
  </table>

  {charts_html}

  <hr style="margin-top:30px">
  <p style="font-size:11px;color:#888">
    Detalle completo en el Excel adjunto.<br>
    Generado automaticamente por <b>bfa-cl-modelos-diarios</b>.
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
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # olMailItem
        mail.To = "; ".join(destinatarios)
        mail.Subject = asunto

        # Agregar adjuntos (Excel)
        for ruta in adjuntos:
            mail.Attachments.Add(str(ruta))

        # Embeber imagenes CID
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
            logger.info("Email abierto en Outlook para revision.")
        else:
            mail.Send()
            logger.info("Email enviado a: %s", ", ".join(destinatarios))
    finally:
        pythoncom.CoUninitialize()


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def generar_y_enviar_reporte(
    fecha: str,
    tipo_reporte: str = "primera_vuelta",
    modo: Optional[str] = None,
    destinatarios: Optional[list[str]] = None,
    preview_html: bool = False,
) -> Optional[Path]:
    """
    Genera el reporte completo y lo envía por email.

    Args:
        fecha: fecha de proceso en formato YYYY-MM-DD.
        tipo_reporte: ``primera_vuelta``, ``segunda_vuelta`` o ``unificado``.
        modo: ``send`` o ``display``. Si None, lee del YAML.
        destinatarios: override de destinatarios. Si None, lee del YAML.
        preview_html: si True, no envía nada y vuelca el HTML + adjuntos a
            ``reports/{YYYYMMDD}/email_preview_{tipo}/`` para revisión local
            (F30). Las imágenes CID se reemplazan por rutas relativas en el
            preview standalone.

    Returns:
        Ruta al directorio del preview si ``preview_html=True``, else None.
    """
    tablas = _TABLAS_POR_TIPO.get(tipo_reporte)
    if tablas is None:
        logger.error("Tipo de reporte no soportado: %s", tipo_reporte)
        return None

    titulo_vuelta = _TITULO_POR_TIPO.get(tipo_reporte, tipo_reporte)
    cfg = _cargar_config_email(tipo_reporte)

    if not preview_html and not cfg.get("enabled", True):
        logger.info("Reporte '%s' deshabilitado en configuración.", tipo_reporte)
        return None

    destinatarios = destinatarios or cfg.get("destinatarios", [])
    if not preview_html and not destinatarios:
        logger.warning("Sin destinatarios configurados. Abortando envío.")
        return None

    modo = modo or cfg.get("modo", "send")

    logger.info("Generando reporte de amortizacion %s para %s...", titulo_vuelta, fecha)

    # 1. Consultar BQ
    client = _get_bq_client()
    df_comp, fecha_anterior = _calcular_comparacion(client, fecha, tablas)

    if df_comp.empty:
        logger.warning("Sin datos de amortizacion para %s. No se envia email.", fecha)
        return None

    # 1b. Leer controles (F30) y construir sección de salud
    df_ctrl = _leer_controles_dia(client, fecha)
    seccion_salud_html, nivel_global_ctrl = _construir_seccion_salud(df_ctrl, fecha)

    # Resolver asunto con fechas reales + prefijo [CRITICO] si aplica
    asunto_template = cfg.get("asunto_template", "Reporte Amortizacion -- {fecha}")
    asunto = asunto_template.format(
        fecha=fecha,
        fecha_anterior=fecha_anterior or "N/A",
    )
    if nivel_global_ctrl == "CRITICAL" and not asunto.startswith("[CRITICO]"):
        asunto = f"[CRITICO] {asunto}"

    # Directorio de trabajo: temporal si envío real, persistente si preview
    if preview_html:
        fecha_compact = fecha.replace("-", "")
        preview_dir = BASE_DIR / "reports" / fecha_compact / f"email_preview_{tipo_reporte}"
        preview_dir.mkdir(parents=True, exist_ok=True)
        tmpdir_path = preview_dir
        cleanup = lambda: None
    else:
        import tempfile as _tempfile
        _ctx = _tempfile.TemporaryDirectory(prefix="email_report_")
        tmpdir_path = Path(_ctx.name)
        cleanup = _ctx.cleanup

    try:
        # 2. Generar artefactos
        chart_rutas = _exportar_charts(df_comp, fecha, fecha_anterior, tmpdir_path)
        ruta_excel = _generar_excel(
            df_comp, fecha, fecha_anterior, tmpdir_path,
            tipo_reporte=tipo_reporte,
        )

        # CIDs para las imagenes (cid_key -> cid_value, cid_value -> ruta)
        chart_cids = {}   # cid_key -> cid_value (para HTML)
        imagenes_cid = {} # cid_value -> ruta_png (para Outlook)
        for cid_key, ruta_png in chart_rutas.items():
            cid_val = f"chart_{cid_key}"
            chart_cids[cid_key] = cid_val
            imagenes_cid[cid_val] = ruta_png

        # HTML
        cuerpo_html = _construir_html(
            df_comp, fecha, fecha_anterior, chart_cids,
            titulo_vuelta=titulo_vuelta,
            seccion_salud_html=seccion_salud_html,
        )

        # 3. Enviar o generar preview standalone
        if preview_html:
            # Reemplazar `cid:chart_*` por rutas relativas a los PNG
            html_standalone = cuerpo_html
            for cid_val, ruta_png in imagenes_cid.items():
                html_standalone = html_standalone.replace(
                    f"cid:{cid_val}", ruta_png.name
                )
            (tmpdir_path / "index.html").write_text(html_standalone, encoding="utf-8")
            (tmpdir_path / "subject.txt").write_text(asunto, encoding="utf-8")
            logger.info(
                "Preview HTML generado en %s (subject: %s, nivel_ctrl: %s).",
                tmpdir_path, asunto, nivel_global_ctrl,
            )
            return tmpdir_path

        _enviar_outlook(
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            adjuntos=[ruta_excel],
            imagenes_cid=imagenes_cid,
            modo=modo,
        )
    finally:
        cleanup()

    logger.info("Reporte de amortizacion %s (%s) completado.", titulo_vuelta, fecha)
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Genera y envia reporte de amortizacion por email.",
    )
    parser.add_argument(
        "--fecha",
        required=True,
        help="Fecha de proceso (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--tipo",
        choices=list(_TABLAS_POR_TIPO.keys()),
        default="primera_vuelta",
        help="Tipo de reporte (default: primera_vuelta).",
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
        help="Override de destinatarios (separados por espacio).",
    )
    parser.add_argument(
        "--preview-html",
        action="store_true",
        help="No envía nada; genera HTML+adjuntos en "
             "reports/{YYYYMMDD}/email_preview_{tipo}/ (F30).",
    )
    args = parser.parse_args()

    # Setup logging básico si se ejecuta standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    )

    salida = generar_y_enviar_reporte(
        fecha=args.fecha,
        tipo_reporte=args.tipo,
        modo=args.modo,
        destinatarios=args.destinatarios,
        preview_html=args.preview_html,
    )
    if args.preview_html and salida is not None:
        print(f"Preview generado en: {salida}")
        print(f"Abrir: file://{salida}/index.html")


if __name__ == "__main__":
    main()
