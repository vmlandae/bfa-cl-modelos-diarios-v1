"""Motor de controles de output post-carga BQ (F29).

Valida los outputs de los modelos diarios después de que se cargan a
BigQuery, generando alertas con severidad ``OK | WARNING | CRITICAL`` que
se persisten en la tabla ``controles_diarios``. El email y la página
``7_Controles`` del dashboard consumen estos resultados.

Catálogo de checks (los de cuadratura input↔output viven en
``core.controles_cuadratura``):

    n_filas_zero               tabla vacía hoy
    n_filas_ratio              ratio filas(t)/filas(t-1) fuera de banda
    nulls_required             NULL en columnas REQUIRED
    invariante_codigo_empresa  CODIGO_EMPRESA único valor = 1
    invariante_monedas         MONEDA_ORIGEN/COMPENSACION válidas
    delta_amort_<moneda>       Δ% SUM(AMORTIZACION) vs día anterior
    delta_interes_<moneda>     Δ% SUM(INTERES) vs día anterior
    productos_desaparecidos    productos en t-1 ausentes en t
    freshness_fecha            FECHA_PROCESO de las filas == @fecha

Política CRITICAL (decisión 2026-05-13): **no degrada `status_global`**.
Los CRITICAL se reportan en email + dashboard + log; no detienen la
ejecución diaria.

CLI::

    python -m core.controles_outputs --fecha 2026-05-12
    python -m core.controles_outputs --fecha 2026-05-12 --modelos ml_mora_consumo
    python -m core.controles_outputs --fecha 2026-05-12 --no-persist --export-json out.json
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import socket
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from google.cloud import bigquery

from config.config_rutas import BASE_DIR
from core.modelos_registry import (
    listar_modelos,
    nombre_legible,
    tabla_dly,
    tabla_hist,
    tablas_extra_dly,
    tablas_extra_hist,
)

logger = logging.getLogger("bfa_modelos.controles_outputs")

_PROJECT_ID = "bfa-cl-trade-price-report-dev"
_DATASET_DLY = "bfa_cl_prd_financial_risk_dly_proc_models"
_DATASET_HIST = "bfa_cl_prd_financial_risk_dly_proc_models_hist"
_CONFIG_PATH = BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"
_VERSION_MOTOR = "1.0"


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------


@dataclass
class CheckResultado:
    """Resultado individual de un check sobre un modelo."""

    modelo: str
    tabla: str
    check_id: str
    nivel: str  # OK | WARNING | CRITICAL | INFO
    mensaje: str
    fecha_proceso: str  # ISO YYYY-MM-DD
    fecha_anterior: Optional[str] = None
    evidencia: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    hostname: str = field(default_factory=socket.gethostname)
    version_motor: str = _VERSION_MOTOR


@dataclass
class ResultadoControles:
    """Agregado de resultados de un día (todos los modelos)."""

    fecha_proceso: str
    fecha_anterior: Optional[str]
    por_modelo: dict[str, list[CheckResultado]] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def todos(self) -> list[CheckResultado]:
        out: list[CheckResultado] = []
        for checks in self.por_modelo.values():
            out.extend(checks)
        return out

    @property
    def n_por_nivel(self) -> dict[str, int]:
        salida = {"OK": 0, "WARNING": 0, "CRITICAL": 0, "INFO": 0}
        for c in self.todos:
            salida[c.nivel] = salida.get(c.nivel, 0) + 1
        return salida

    @property
    def nivel_global(self) -> str:
        n = self.n_por_nivel
        if n.get("CRITICAL", 0) > 0:
            return "CRITICAL"
        if n.get("WARNING", 0) > 0:
            return "WARNING"
        return "OK"

    @property
    def modelos_criticos(self) -> list[str]:
        return sorted({c.modelo for c in self.todos if c.nivel == "CRITICAL"})


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


def cargar_config(config_path: Optional[Path] = None) -> dict:
    """Lee la sección ``controles:`` del YAML. Retorna dict vacío si no existe."""
    ruta = config_path or _CONFIG_PATH
    with open(ruta, "r", encoding="utf-8") as f:
        cfg_full = yaml.safe_load(f) or {}
    return cfg_full.get("controles", {})


def umbrales_para(cfg: dict, modelo: str) -> dict:
    """Resuelve umbrales aplicables a un modelo: defaults + override por modelo."""
    defaults = cfg.get("defaults", {})
    por_modelo = cfg.get("por_modelo", {}).get(modelo, {})
    return _deep_merge(defaults, por_modelo)


def _deep_merge(a: dict, b: dict) -> dict:
    """Merge recursivo: b override a. Sin mutar inputs."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Cliente BQ
# ---------------------------------------------------------------------------


def _get_bq_client() -> bigquery.Client:
    """Cliente BQ con credenciales del proyecto."""
    from config.config_rutas import obtener_ruta_credenciales_gcp
    cred_path = obtener_ruta_credenciales_gcp()
    return bigquery.Client.from_service_account_json(str(cred_path))


def _fecha_anterior_disponible(
    client: bigquery.Client, modelo: str, fecha: str
) -> Optional[str]:
    """Resuelve la fecha previa con datos para un modelo en la tabla hist."""
    tabla = tabla_hist(modelo)
    sql = f"""
        SELECT MAX(FECHA_PROCESO) AS fecha
        FROM `{_PROJECT_ID}.{_DATASET_HIST}.{tabla}`
        WHERE FECHA_PROCESO < @fecha
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("fecha", "DATE", fecha)]
    )
    try:
        df = client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
    except Exception as exc:
        logger.warning("No se pudo leer fecha anterior de %s: %s", tabla, exc)
        return None
    if df.empty or df["fecha"].iloc[0] is None:
        return None
    return str(df["fecha"].iloc[0])


# ---------------------------------------------------------------------------
# Recolección de métricas por modelo (una query por modelo)
# ---------------------------------------------------------------------------


def _query_metricas_modelo(modelo: str, fecha_t: str, fecha_t1: Optional[str]) -> str:
    """Construye SQL consolidada para todas las métricas del modelo en una sola query."""
    tabla_d = tabla_dly(modelo)
    tabla_h = tabla_hist(modelo)
    fecha_t1_sql = "DATE '1900-01-01'" if fecha_t1 is None else "@fecha_t1"

    return f"""
    WITH dia AS (
        SELECT * FROM `{_PROJECT_ID}.{_DATASET_DLY}.{tabla_d}`
        WHERE FECHA_PROCESO = @fecha_t
    ),
    ayer AS (
        SELECT * FROM `{_PROJECT_ID}.{_DATASET_HIST}.{tabla_h}`
        WHERE FECHA_PROCESO = {fecha_t1_sql}
    )
    SELECT
        (SELECT COUNT(*) FROM dia)  AS n_filas_t,
        (SELECT COUNT(*) FROM ayer) AS n_filas_t1,

        (SELECT COUNTIF(CODIGO_EMPRESA IS NULL) FROM dia)     AS nulls_codigo_empresa,
        (SELECT COUNTIF(CODIGO_PRODUCTO IS NULL) FROM dia)    AS nulls_codigo_producto,
        (SELECT COUNTIF(CODIGO_SUBPRODUCTO IS NULL) FROM dia) AS nulls_codigo_subproducto,
        (SELECT COUNTIF(FECHA_PROCESO IS NULL) FROM dia)      AS nulls_fecha_proceso,

        (SELECT ARRAY_AGG(DISTINCT IFNULL(CAST(CODIGO_EMPRESA AS STRING), 'NULL'))
         FROM dia) AS distinct_codigo_empresa,

        (SELECT ARRAY_AGG(DISTINCT IFNULL(MONEDA_ORIGEN, 'NULL'))
         FROM dia) AS distinct_monedas_origen,
        (SELECT ARRAY_AGG(DISTINCT IFNULL(MONEDA_COMPENSACION, 'NULL'))
         FROM dia) AS distinct_monedas_comp,

        (SELECT ARRAY_AGG(STRUCT(MONEDA_ORIGEN AS moneda, suma)) FROM (
            SELECT MONEDA_ORIGEN, SUM(AMORTIZACION) AS suma
            FROM dia WHERE MONEDA_ORIGEN IS NOT NULL
            GROUP BY MONEDA_ORIGEN
        )) AS suma_amort_t,
        (SELECT ARRAY_AGG(STRUCT(MONEDA_ORIGEN AS moneda, suma)) FROM (
            SELECT MONEDA_ORIGEN, SUM(AMORTIZACION) AS suma
            FROM ayer WHERE MONEDA_ORIGEN IS NOT NULL
            GROUP BY MONEDA_ORIGEN
        )) AS suma_amort_t1,

        (SELECT ARRAY_AGG(STRUCT(MONEDA_ORIGEN AS moneda, suma)) FROM (
            SELECT MONEDA_ORIGEN, SUM(INTERES) AS suma
            FROM dia WHERE MONEDA_ORIGEN IS NOT NULL
            GROUP BY MONEDA_ORIGEN
        )) AS suma_interes_t,
        (SELECT ARRAY_AGG(STRUCT(MONEDA_ORIGEN AS moneda, suma)) FROM (
            SELECT MONEDA_ORIGEN, SUM(INTERES) AS suma
            FROM ayer WHERE MONEDA_ORIGEN IS NOT NULL
            GROUP BY MONEDA_ORIGEN
        )) AS suma_interes_t1,

        (SELECT ARRAY_AGG(DISTINCT CODIGO_PRODUCTO IGNORE NULLS) FROM dia)  AS productos_t,
        (SELECT ARRAY_AGG(DISTINCT CODIGO_PRODUCTO IGNORE NULLS) FROM ayer) AS productos_t1,

        (SELECT COUNTIF(FECHA_PROCESO != @fecha_t) FROM dia) AS freshness_violations
    """


def _leer_metricas_modelo(
    client: bigquery.Client, modelo: str, fecha_t: str, fecha_t1: Optional[str]
) -> dict[str, Any]:
    """Ejecuta la query y retorna dict de métricas. Maneja error de tabla inexistente."""
    sql = _query_metricas_modelo(modelo, fecha_t, fecha_t1)
    params = [bigquery.ScalarQueryParameter("fecha_t", "DATE", fecha_t)]
    if fecha_t1:
        params.append(bigquery.ScalarQueryParameter("fecha_t1", "DATE", fecha_t1))
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    try:
        df = client.query(sql, job_config=job_config).to_dataframe(
            create_bqstorage_client=False
        )
    except Exception as exc:
        logger.error("Falla al leer métricas de %s: %s", modelo, exc)
        return {"_error": str(exc)}
    if df.empty:
        return {"_error": "Query retornó df vacío"}
    return df.iloc[0].to_dict()


# ---------------------------------------------------------------------------
# Checks individuales
# ---------------------------------------------------------------------------


def _ok(modelo: str, tabla: str, check_id: str, mensaje: str, fecha_t: str,
        fecha_t1: Optional[str] = None, evidencia: Optional[dict] = None) -> CheckResultado:
    return CheckResultado(
        modelo=modelo, tabla=tabla, check_id=check_id, nivel="OK",
        mensaje=mensaje, fecha_proceso=fecha_t, fecha_anterior=fecha_t1,
        evidencia=evidencia or {},
    )


def _alerta(nivel: str, modelo: str, tabla: str, check_id: str, mensaje: str,
            fecha_t: str, fecha_t1: Optional[str] = None,
            evidencia: Optional[dict] = None) -> CheckResultado:
    return CheckResultado(
        modelo=modelo, tabla=tabla, check_id=check_id, nivel=nivel,
        mensaje=mensaje, fecha_proceso=fecha_t, fecha_anterior=fecha_t1,
        evidencia=evidencia or {},
    )


def check_n_filas(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """Detecta tabla vacía y ratios anómalos vs día anterior."""
    tabla = tabla_dly(modelo)
    n_t = int(metricas.get("n_filas_t", 0) or 0)
    n_t1 = int(metricas.get("n_filas_t1", 0) or 0)
    cfg = umbrales.get("n_filas", {})
    warn_lo, warn_hi = cfg.get("warning_ratio", [0.5, 2.0])
    crit_lo, crit_hi = cfg.get("critical_ratio", [0.3, 3.0])
    out: list[CheckResultado] = []

    if n_t == 0:
        out.append(_alerta("CRITICAL", modelo, tabla, "n_filas_zero",
                           f"La tabla {tabla} no tiene filas para {fecha_t}",
                           fecha_t, fecha_t1, evidencia={"n_filas_t": 0, "n_filas_t1": n_t1}))
        return out

    if n_t1 == 0:
        out.append(_alerta("INFO", modelo, tabla, "n_filas_ratio",
                           f"Sin t-1 disponible para comparar n_filas",
                           fecha_t, fecha_t1, evidencia={"n_filas_t": n_t, "n_filas_t1": n_t1}))
        return out

    ratio = n_t / n_t1
    ev = {"n_filas_t": n_t, "n_filas_t1": n_t1, "ratio": round(ratio, 4)}
    if ratio < crit_lo or ratio > crit_hi:
        out.append(_alerta("CRITICAL", modelo, tabla, "n_filas_ratio",
                           f"n_filas ratio {ratio:.2f} fuera de banda crítica [{crit_lo}, {crit_hi}]",
                           fecha_t, fecha_t1, evidencia=ev))
    elif ratio < warn_lo or ratio > warn_hi:
        out.append(_alerta("WARNING", modelo, tabla, "n_filas_ratio",
                           f"n_filas ratio {ratio:.2f} fuera de banda warning [{warn_lo}, {warn_hi}]",
                           fecha_t, fecha_t1, evidencia=ev))
    else:
        out.append(_ok(modelo, tabla, "n_filas_ratio",
                       f"n_filas ratio {ratio:.2f} dentro de banda",
                       fecha_t, fecha_t1, evidencia=ev))
    return out


def check_nulls_required(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """Cualquier NULL en CODIGO_PRODUCTO, CODIGO_SUBPRODUCTO, FECHA_PROCESO → CRITICAL."""
    tabla = tabla_dly(modelo)
    campos = umbrales.get("nulls_required", {}).get(
        "campos", ["FECHA_PROCESO", "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO"]
    )
    nivel_si_hay = umbrales.get("nulls_required", {}).get("nivel", "CRITICAL")
    map_campo = {
        "FECHA_PROCESO": "nulls_fecha_proceso",
        "CODIGO_PRODUCTO": "nulls_codigo_producto",
        "CODIGO_SUBPRODUCTO": "nulls_codigo_subproducto",
        "CODIGO_EMPRESA": "nulls_codigo_empresa",
    }
    out: list[CheckResultado] = []
    for campo in campos:
        key = map_campo.get(campo)
        if key is None:
            continue
        n = int(metricas.get(key, 0) or 0)
        ev = {"campo": campo, "n_nulls": n}
        if n > 0:
            out.append(_alerta(nivel_si_hay, modelo, tabla, f"nulls_{campo.lower()}",
                               f"{n} filas con {campo} NULL",
                               fecha_t, fecha_t1, evidencia=ev))
        else:
            out.append(_ok(modelo, tabla, f"nulls_{campo.lower()}",
                           f"{campo} sin NULLs",
                           fecha_t, fecha_t1, evidencia=ev))
    return out


def check_invariante_codigo_empresa(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """CODIGO_EMPRESA debe ser único valor configurado (default {1})."""
    tabla = tabla_dly(modelo)
    valores_validos = umbrales.get("invariantes", {}).get("codigo_empresa", [1])
    valores_validos_str = {str(v) for v in valores_validos}
    presentes = list(metricas.get("distinct_codigo_empresa") or [])
    presentes_set = set(presentes)
    ev = {
        "esperado": sorted(valores_validos_str),
        "encontrado": sorted(presentes_set),
    }
    if not presentes_set:
        return [_alerta("WARNING", modelo, tabla, "invariante_codigo_empresa",
                        "CODIGO_EMPRESA no tiene valores (tabla vacía o todos NULL)",
                        fecha_t, fecha_t1, evidencia=ev)]
    fuera = presentes_set - valores_validos_str
    if fuera:
        return [_alerta("CRITICAL", modelo, tabla, "invariante_codigo_empresa",
                        f"CODIGO_EMPRESA inválido: {sorted(fuera)}",
                        fecha_t, fecha_t1, evidencia=ev)]
    return [_ok(modelo, tabla, "invariante_codigo_empresa",
                f"CODIGO_EMPRESA = {sorted(presentes_set)}",
                fecha_t, fecha_t1, evidencia=ev)]


def check_invariante_monedas(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """MONEDA_ORIGEN y MONEDA_COMPENSACION ∈ set válido."""
    tabla = tabla_dly(modelo)
    validas = set(umbrales.get("invariantes", {}).get(
        "monedas_validas", ["CLP", "CLF", "USD"]
    ))
    # Algunos modelos guardan códigos numéricos en MONEDA_ORIGEN (999, 998, 13).
    # Si la config lista códigos numéricos, sumarlos.
    numericas_ok = set(str(v) for v in
                      umbrales.get("invariantes", {}).get("monedas_origen_numericas_validas", []))
    validas_origen = validas | numericas_ok

    out: list[CheckResultado] = []
    for campo, presentes_key, validas_set in [
        ("MONEDA_ORIGEN", "distinct_monedas_origen", validas_origen),
        ("MONEDA_COMPENSACION", "distinct_monedas_comp", validas),
    ]:
        presentes = set(metricas.get(presentes_key) or [])
        # Filtrar el placeholder 'NULL'
        nulls_presentes = "NULL" in presentes
        presentes_no_null = presentes - {"NULL"}
        ev = {"campo": campo, "validas": sorted(validas_set), "encontradas": sorted(presentes)}
        if not presentes_no_null:
            out.append(_alerta("WARNING", modelo, tabla, f"invariante_{campo.lower()}",
                               f"{campo} no tiene valores (tabla vacía o todos NULL)",
                               fecha_t, fecha_t1, evidencia=ev))
            continue
        fuera = presentes_no_null - validas_set
        if fuera:
            out.append(_alerta("CRITICAL", modelo, tabla, f"invariante_{campo.lower()}",
                               f"{campo} con valores fuera de set válido: {sorted(fuera)}",
                               fecha_t, fecha_t1, evidencia=ev))
        elif nulls_presentes:
            out.append(_alerta("WARNING", modelo, tabla, f"invariante_{campo.lower()}",
                               f"{campo} con algunos NULL (set válido: {sorted(presentes_no_null)})",
                               fecha_t, fecha_t1, evidencia=ev))
        else:
            out.append(_ok(modelo, tabla, f"invariante_{campo.lower()}",
                           f"{campo} ∈ {sorted(presentes_no_null)}",
                           fecha_t, fecha_t1, evidencia=ev))
    return out


def check_delta(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """Δ% por moneda para AMORTIZACION e INTERES."""
    tabla = tabla_dly(modelo)
    cfg = umbrales.get("delta", {})
    warn_pct = cfg.get("warning_pct", 5.0)
    crit_pct = cfg.get("critical_pct", 15.0)
    out: list[CheckResultado] = []

    for metrica, key_t, key_t1 in [
        ("amort", "suma_amort_t", "suma_amort_t1"),
        ("interes", "suma_interes_t", "suma_interes_t1"),
    ]:
        sumas_t = {item["moneda"]: item["suma"] for item in (metricas.get(key_t) or [])}
        sumas_t1 = {item["moneda"]: item["suma"] for item in (metricas.get(key_t1) or [])}
        monedas = sorted(set(sumas_t) | set(sumas_t1))
        if not monedas:
            continue
        for moneda in monedas:
            v_t = float(sumas_t.get(moneda) or 0)
            v_t1 = float(sumas_t1.get(moneda) or 0)
            check_id = f"delta_{metrica}_{(moneda or 'na').lower()}"
            ev = {"moneda": moneda, "valor_t": v_t, "valor_t1": v_t1}
            if v_t1 == 0:
                if v_t == 0:
                    out.append(_ok(modelo, tabla, check_id,
                                   f"{metrica} {moneda}: ambos en 0",
                                   fecha_t, fecha_t1, evidencia=ev))
                else:
                    out.append(_alerta("INFO", modelo, tabla, check_id,
                                       f"{metrica} {moneda}: t-1 = 0, Δ% no calculable",
                                       fecha_t, fecha_t1, evidencia=ev))
                continue
            delta_pct = (v_t - v_t1) / abs(v_t1) * 100.0
            ev["delta_pct"] = round(delta_pct, 4)
            abs_pct = abs(delta_pct)
            if abs_pct >= crit_pct:
                nivel = "CRITICAL"
            elif abs_pct >= warn_pct:
                nivel = "WARNING"
            else:
                nivel = "OK"
            msg = f"{metrica} {moneda} Δ% = {delta_pct:+.2f}%"
            out.append(_alerta(nivel, modelo, tabla, check_id,
                               msg, fecha_t, fecha_t1, evidencia=ev) if nivel != "OK"
                       else _ok(modelo, tabla, check_id, msg, fecha_t, fecha_t1, evidencia=ev))
    return out


def check_productos_desaparecidos(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """Productos en t-1 ausentes en t."""
    tabla = tabla_dly(modelo)
    productos_t = set(metricas.get("productos_t") or [])
    productos_t1 = set(metricas.get("productos_t1") or [])
    if not productos_t1:
        return []
    desaparecidos = sorted(productos_t1 - productos_t)
    if not desaparecidos:
        return [_ok(modelo, tabla, "productos_desaparecidos",
                    f"Todos los productos de t-1 presentes en t ({len(productos_t)})",
                    fecha_t, fecha_t1,
                    evidencia={"n_productos_t": len(productos_t),
                               "n_productos_t1": len(productos_t1)})]
    return [_alerta("CRITICAL", modelo, tabla, "productos_desaparecidos",
                    f"{len(desaparecidos)} productos desaparecidos: {desaparecidos[:5]}"
                    + ("..." if len(desaparecidos) > 5 else ""),
                    fecha_t, fecha_t1,
                    evidencia={"desaparecidos": desaparecidos,
                               "n_productos_t": len(productos_t),
                               "n_productos_t1": len(productos_t1)})]


def check_freshness(
    modelo: str, metricas: dict, umbrales: dict, fecha_t: str, fecha_t1: Optional[str]
) -> list[CheckResultado]:
    """Todas las filas deben tener FECHA_PROCESO = @fecha_t."""
    tabla = tabla_dly(modelo)
    viol = int(metricas.get("freshness_violations", 0) or 0)
    ev = {"freshness_violations": viol}
    if viol > 0:
        return [_alerta("CRITICAL", modelo, tabla, "freshness_fecha",
                        f"{viol} filas con FECHA_PROCESO != {fecha_t}",
                        fecha_t, fecha_t1, evidencia=ev)]
    return [_ok(modelo, tabla, "freshness_fecha",
                f"FECHA_PROCESO consistente",
                fecha_t, fecha_t1, evidencia=ev)]


# Lista ordenada de checks (excluye cuadratura que vive en controles_cuadratura).
_CHECKS_REGISTRY = [
    check_n_filas,
    check_nulls_required,
    check_invariante_codigo_empresa,
    check_invariante_monedas,
    check_freshness,
    check_productos_desaparecidos,
    check_delta,
]


# ---------------------------------------------------------------------------
# Ejecutor
# ---------------------------------------------------------------------------


def ejecutar_controles(
    fecha: "date | str",
    modelos: Optional[list[str]] = None,
    persistir: bool = True,
    config_path: Optional[Path] = None,
    incluir_cuadratura: bool = True,
) -> ResultadoControles:
    """Corre los checks de output sobre los modelos para una fecha.

    Args:
        fecha: ISO YYYY-MM-DD o date.
        modelos: lista de keys o None = todos los modelos activos.
        persistir: si True escribe a BQ ``controles_diarios``.
        config_path: path al YAML (default config/config_rutas_ext_y_archivos.yaml).
        incluir_cuadratura: si True intenta correr ``controles_cuadratura``
                            si está disponible.
    """
    fecha_str = fecha.isoformat() if isinstance(fecha, date) else str(fecha)
    cfg = cargar_config(config_path)
    if not cfg.get("enabled", True):
        logger.info("Controles deshabilitados por config.")
        return ResultadoControles(fecha_proceso=fecha_str, fecha_anterior=None)

    modelos = modelos or listar_modelos(activos=True)
    client = _get_bq_client()
    resultado = ResultadoControles(fecha_proceso=fecha_str, fecha_anterior=None)

    for modelo in modelos:
        fecha_ant = _fecha_anterior_disponible(client, modelo, fecha_str)
        umbrales = umbrales_para(cfg, modelo)
        metricas = _leer_metricas_modelo(client, modelo, fecha_str, fecha_ant)
        checks: list[CheckResultado] = []

        if "_error" in metricas:
            checks.append(_alerta(
                "CRITICAL", modelo, tabla_dly(modelo), "lectura_bq",
                f"No se pudo leer métricas: {metricas['_error']}",
                fecha_str, fecha_ant, evidencia={"error": metricas["_error"]},
            ))
            resultado.por_modelo[modelo] = checks
            continue

        for fn in _CHECKS_REGISTRY:
            try:
                checks.extend(fn(modelo, metricas, umbrales, fecha_str, fecha_ant))
            except Exception as exc:  # check individual no debe romper todo
                logger.exception("Check %s falló para %s: %s", fn.__name__, modelo, exc)
                checks.append(_alerta(
                    "WARNING", modelo, tabla_dly(modelo), fn.__name__,
                    f"Excepción ejecutando check: {exc}",
                    fecha_str, fecha_ant, evidencia={"exception": repr(exc)},
                ))

        # Cuadratura (delegada a módulo separado, opcional)
        if incluir_cuadratura:
            try:
                from core.controles_cuadratura import check_cuadratura
                checks.extend(check_cuadratura(modelo, fecha_str, cfg, bq_client=client))
            except ImportError:
                pass
            except Exception as exc:
                logger.exception("Cuadratura falló para %s: %s", modelo, exc)
                checks.append(_alerta(
                    "WARNING", modelo, tabla_dly(modelo), "cuadratura",
                    f"Excepción ejecutando cuadratura: {exc}",
                    fecha_str, fecha_ant, evidencia={"exception": repr(exc)},
                ))

        resultado.por_modelo[modelo] = checks

    if persistir and resultado.por_modelo:
        try:
            from core.controles_persistence import escribir
            escribir(resultado)
        except Exception as exc:
            logger.exception("No se pudo persistir resultado: %s", exc)

    return resultado


# ---------------------------------------------------------------------------
# Helpers de presentación
# ---------------------------------------------------------------------------


def resumir_consola(resultado: ResultadoControles) -> str:
    """Texto compacto para imprimir en consola/log."""
    lineas = [
        f"Controles {resultado.fecha_proceso} — nivel global: {resultado.nivel_global}",
        f"  Total: {resultado.n_por_nivel}",
    ]
    for modelo in sorted(resultado.por_modelo):
        checks = resultado.por_modelo[modelo]
        crit = sum(1 for c in checks if c.nivel == "CRITICAL")
        warn = sum(1 for c in checks if c.nivel == "WARNING")
        ok = sum(1 for c in checks if c.nivel == "OK")
        lineas.append(f"    {nombre_legible(modelo):28s}  OK={ok}  WARN={warn}  CRIT={crit}")
        for c in checks:
            if c.nivel in ("CRITICAL", "WARNING"):
                lineas.append(f"      [{c.nivel:8s}] {c.check_id}: {c.mensaje}")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Motor de controles de output post-carga BQ (F29)."
    )
    parser.add_argument("--fecha", required=True, help="ISO YYYY-MM-DD")
    parser.add_argument("--modelos", nargs="*", default=None,
                        help="Lista de keys de modelos. Default = todos activos.")
    parser.add_argument("--no-persist", action="store_true",
                        help="No escribir resultado a BQ controles_diarios.")
    parser.add_argument("--sin-cuadratura", action="store_true",
                        help="Saltar core.controles_cuadratura.")
    parser.add_argument("--export-json", type=Path, default=None,
                        help="Volcar el resultado a un JSON local.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    resultado = ejecutar_controles(
        fecha=args.fecha,
        modelos=args.modelos,
        persistir=not args.no_persist,
        incluir_cuadratura=not args.sin_cuadratura,
    )

    print(resumir_consola(resultado))

    if args.export_json:
        payload = {
            "fecha_proceso": resultado.fecha_proceso,
            "nivel_global": resultado.nivel_global,
            "n_por_nivel": resultado.n_por_nivel,
            "modelos_criticos": resultado.modelos_criticos,
            "checks": [asdict(c) for c in resultado.todos],
        }
        args.export_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"Resultado exportado a {args.export_json}")

    return 0 if resultado.nivel_global != "CRITICAL" else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli())
