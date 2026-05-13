"""Cuadratura input ↔ output (F29 — fase 4).

Reconcilia el ``CAPITAL`` / ``INTERES`` del INPUT del modelo (PML, Access,
Excel) con el ``SUM(AMORTIZACION)`` / ``SUM(INTERES)`` del OUTPUT cargado
a BQ. Este es el check que habría detectado el "error grueso" reciente
de desbalance entre lo que entra y lo que sale.

Tipos soportados (vía ``cuadratura_inputs.{modelo}.tipo`` en YAML):

- ``pml_gcp``  — lee ``ProductosMercadoLiquidezGCP{fecha}.txt`` (UNC),
  filtra por ``SISTEMA`` (y opcionalmente ``CODIGO_PRODUCTO``) según YAML,
  suma ``AMORTIZACION`` e ``INTERES``.
- ``pml_cmr``  — análogo con el archivo CMR.
- ``access``   — TODO: requiere lector ODBC. Emite INFO hasta que se
  implemente (sprint S7 candidato).
- ``manual``   — modelos cuya entrada se sube a BQ manualmente (SSV,
  Prepago CMR hoy). Emite INFO.
- ``no_configurado`` — modelo sin entrada en YAML. Emite INFO.

Resultado por modelo: dos ``CheckResultado`` con ``check_id`` =
``cuadratura_capital`` y ``cuadratura_interes``. Nivel según
``|delta_pct|`` y ``cfg.cuadratura.tolerancia_pct.{warning,critical}``.

Tolerancia laxa por defecto (warning 10%, critical 50%): mora aplica
factores que cambian el monto agregado de forma sistemática, por lo que
la cuadratura captura *roturas gruesas* (output cero, factor invertido,
filtro caído), no exactitud matemática. El usuario calibra por modelo
en YAML iterando con datos reales.
"""

from __future__ import annotations

import logging
import socket
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from core.modelos_registry import tabla_dly

if TYPE_CHECKING:  # pragma: no cover
    from google.cloud import bigquery

    from core.controles_outputs import CheckResultado

logger = logging.getLogger("bfa_modelos.controles_cuadratura")


# ---------------------------------------------------------------------------
# Lector PML (reutiliza core.control_interfaces)
# ---------------------------------------------------------------------------


def _leer_pml(
    modelo: str,
    fecha: str,
    cfg_input: dict,
    *,
    tipo_pml: str,
) -> dict[str, float]:
    """Lee el archivo PML del día y devuelve sumas filtradas.

    Args:
        modelo: clave del modelo (informativo).
        fecha: ISO YYYY-MM-DD.
        cfg_input: entry de ``cuadratura_inputs.{modelo}`` del YAML.
            Puede traer ``sistemas`` (lista) y ``codigo_producto``.
        tipo_pml: ``"gcp"`` o ``"cmr"``.

    Returns:
        Dict con ``capital``, ``interes`` y ``n_filas``.

    Raises:
        FileNotFoundError / OSError: si el archivo no se encuentra
            en la ruta UNC ni en cache local.
        KeyError: si la sección ``control_interfaces`` falta en YAML.
    """
    # Imports diferidos: evita cargar pandas/yaml cuando el módulo
    # se importa solo para acceder a check_cuadratura desde el motor.
    from core.control_interfaces import (
        _copiar_un_archivo,
        _leer_interfaz,
        cargar_config_interfaces,
        obtener_rutas_archivos,
    )

    cfg_intf = cargar_config_interfaces()
    fecha_d = date.fromisoformat(fecha)
    ruta_unc_t, _, ruta_local_t, _ = obtener_rutas_archivos(tipo_pml, fecha_d, cfg_intf)
    ruta_t = _copiar_un_archivo(ruta_unc_t, ruta_local_t, "t", tipo_pml)
    df = _leer_interfaz(ruta_t, cfg_intf.interfaces[tipo_pml])

    sistemas = cfg_input.get("sistemas") or []
    cod_prod = cfg_input.get("codigo_producto")

    n0 = len(df)
    if sistemas and "SISTEMA" in df.columns:
        df = df[df["SISTEMA"].isin(sistemas)]
    if cod_prod and "CODIGO_PRODUCTO" in df.columns:
        df = df[df["CODIGO_PRODUCTO"] == str(cod_prod)]

    logger.debug(
        "PML %s para %s: %d → %d filas (sistemas=%s, cod_prod=%s)",
        tipo_pml, modelo, n0, len(df), sistemas, cod_prod,
    )

    return {
        "capital": float(df["AMORTIZACION"].sum()),
        "interes": float(df["INTERES"].sum()),
        "n_filas": int(len(df)),
    }


# ---------------------------------------------------------------------------
# Lector Access (placeholder — fase S7)
# ---------------------------------------------------------------------------


def _leer_access(modelo: str, fecha: str, cfg_input: dict) -> dict[str, float]:
    """Stub: lectura Access requiere driver ODBC en PC institucional.

    En lugar de levantar excepción, devolvemos ``NotImplementedError``
    para que el caller emita INFO en vez de WARNING. El usuario activará
    esto cuando se implemente el lector (sprint S7).
    """
    raise NotImplementedError(
        f"Lector access pendiente (sprint S7). tabla={cfg_input.get('ruta_tabla')!r}"
    )


# ---------------------------------------------------------------------------
# Lector output BQ
# ---------------------------------------------------------------------------


def _leer_output_bq(
    modelo: str,
    fecha: str,
    client: Optional["bigquery.Client"] = None,
) -> dict[str, float]:
    """Suma AMORTIZACION e INTERES del output BQ del día."""
    from google.cloud import bigquery

    from core.controles_outputs import (
        _DATASET_DLY,
        _PROJECT_ID,
        _get_bq_client,
    )

    if client is None:
        client = _get_bq_client()
    tabla = tabla_dly(modelo)
    sql = f"""
        SELECT
            COALESCE(SUM(AMORTIZACION), 0) AS capital,
            COALESCE(SUM(INTERES), 0)      AS interes,
            COUNT(*)                       AS n_filas
        FROM `{_PROJECT_ID}.{_DATASET_DLY}.{tabla}`
        WHERE FECHA_PROCESO = @fecha
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("fecha", "DATE", fecha)]
    )
    df = client.query(sql, job_config=job_config).to_dataframe(
        create_bqstorage_client=False
    )
    if df.empty:
        return {"capital": 0.0, "interes": 0.0, "n_filas": 0}
    row = df.iloc[0]
    return {
        "capital": float(row["capital"] or 0),
        "interes": float(row["interes"] or 0),
        "n_filas": int(row["n_filas"] or 0),
    }


# ---------------------------------------------------------------------------
# Resolución de tolerancia
# ---------------------------------------------------------------------------


def _resolver_tolerancia(cfg_controles: dict, modelo: str) -> dict[str, float]:
    """Tolerancia para cuadratura: defaults → por_modelo → cuadratura_inputs.

    Cada nivel posterior sobrescribe al anterior con un merge superficial.
    Estructura final esperada::

        {"warning": float_pct, "critical": float_pct}
    """
    defaults = (cfg_controles.get("defaults") or {}).get("cuadratura", {}).get(
        "tolerancia_pct", {}
    )
    por_modelo = (
        (cfg_controles.get("por_modelo") or {})
        .get(modelo, {})
        .get("cuadratura", {})
        .get("tolerancia_pct", {})
    )
    override = (
        (cfg_controles.get("cuadratura_inputs") or {})
        .get(modelo, {})
        .get("tolerancia_pct", {})
    )
    out: dict[str, float] = {"warning": 10.0, "critical": 50.0}
    for capa in (defaults, por_modelo, override):
        if capa:
            out.update({k: float(v) for k, v in capa.items()})
    return out


# ---------------------------------------------------------------------------
# Construcción de CheckResultado
# ---------------------------------------------------------------------------


def _build_check(
    *,
    modelo: str,
    fecha: str,
    check_id: str,
    nivel: str,
    mensaje: str,
    evidencia: dict[str, Any],
) -> "CheckResultado":
    """Helper para construir un CheckResultado con campos comunes."""
    from core.controles_outputs import CheckResultado, _VERSION_MOTOR

    return CheckResultado(
        modelo=modelo,
        tabla=tabla_dly(modelo),
        check_id=check_id,
        nivel=nivel,
        mensaje=mensaje,
        fecha_proceso=fecha,
        fecha_anterior=None,
        evidencia=evidencia,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        hostname=socket.gethostname(),
        version_motor=_VERSION_MOTOR,
    )


# ---------------------------------------------------------------------------
# Comparador y emisión de resultados
# ---------------------------------------------------------------------------


def _comparar(
    modelo: str,
    fecha: str,
    input_sums: dict[str, float],
    output_sums: dict[str, float],
    tolerancia: dict[str, float],
    tipo_input: str,
) -> "list[CheckResultado]":
    """Emite dos checks (capital, interes) comparando input vs output."""
    warn_pct = tolerancia.get("warning", 10.0)
    crit_pct = tolerancia.get("critical", 50.0)

    out: list["CheckResultado"] = []
    for metrica in ("capital", "interes"):
        check_id = f"cuadratura_{metrica}"
        v_in = float(input_sums.get(metrica, 0.0))
        v_out = float(output_sums.get(metrica, 0.0))
        evidencia: dict[str, Any] = {
            "tipo_input": tipo_input,
            "valor_input": v_in,
            "valor_output": v_out,
            "n_filas_input": input_sums.get("n_filas"),
            "n_filas_output": output_sums.get("n_filas"),
            "tolerancia_warning_pct": warn_pct,
            "tolerancia_critical_pct": crit_pct,
        }

        if v_in == 0 and v_out == 0:
            out.append(_build_check(
                modelo=modelo, fecha=fecha, check_id=check_id, nivel="OK",
                mensaje=f"{metrica}: input y output en 0 (sin cuadratura aplicable)",
                evidencia=evidencia,
            ))
            continue

        if v_in == 0:
            evidencia["delta_pct"] = None
            out.append(_build_check(
                modelo=modelo, fecha=fecha, check_id=check_id, nivel="CRITICAL",
                mensaje=(
                    f"{metrica}: input=0 pero output={v_out:,.0f}. "
                    "Δ% no calculable; revisar filtro de input."
                ),
                evidencia=evidencia,
            ))
            continue

        delta_abs = v_out - v_in
        delta_pct = delta_abs / abs(v_in) * 100.0
        abs_pct = abs(delta_pct)
        evidencia["delta_abs"] = delta_abs
        evidencia["delta_pct"] = round(delta_pct, 4)

        if abs_pct >= crit_pct:
            nivel = "CRITICAL"
        elif abs_pct >= warn_pct:
            nivel = "WARNING"
        else:
            nivel = "OK"

        msg = (
            f"{metrica}: input={v_in:,.0f} output={v_out:,.0f} "
            f"Δ={delta_pct:+.2f}% (warn={warn_pct}%, crit={crit_pct}%)"
        )
        out.append(_build_check(
            modelo=modelo, fecha=fecha, check_id=check_id, nivel=nivel,
            mensaje=msg, evidencia=evidencia,
        ))

    return out


# ---------------------------------------------------------------------------
# Entrada pública: check_cuadratura
# ---------------------------------------------------------------------------


def check_cuadratura(
    modelo: str,
    fecha: str,
    cfg_controles: dict,
    *,
    bq_client: Optional["bigquery.Client"] = None,
) -> "list[CheckResultado]":
    """Ejecuta la cuadratura input↔output para un modelo.

    Args:
        modelo: clave del modelo (ej ``ml_mora_consumo``).
        fecha: ISO YYYY-MM-DD.
        cfg_controles: sección ``controles`` del YAML completo.
        bq_client: cliente BQ opcional (testeable).

    Returns:
        Lista de CheckResultado. Vacía nunca: siempre devuelve al menos
        un INFO si el lector no aplica.
    """
    cfg_input = (cfg_controles.get("cuadratura_inputs") or {}).get(modelo, {})
    tipo = cfg_input.get("tipo", "no_configurado")

    if tipo == "manual":
        nota = cfg_input.get("nota", "")
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="INFO",
            mensaje=f"Cuadratura no aplica: modelo manual. {nota}".strip(),
            evidencia={"tipo_input": tipo, "nota": nota},
        )]

    if tipo == "no_configurado":
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="INFO",
            mensaje="Cuadratura no configurada en YAML para este modelo.",
            evidencia={"tipo_input": tipo},
        )]

    # Lectura del input
    try:
        if tipo == "pml_gcp":
            input_sums = _leer_pml(modelo, fecha, cfg_input, tipo_pml="gcp")
        elif tipo == "pml_cmr":
            input_sums = _leer_pml(modelo, fecha, cfg_input, tipo_pml="cmr")
        elif tipo == "access":
            input_sums = _leer_access(modelo, fecha, cfg_input)
        else:
            return [_build_check(
                modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="INFO",
                mensaje=f"Tipo de input desconocido: {tipo!r}",
                evidencia={"tipo_input": tipo},
            )]
    except NotImplementedError as exc:
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="INFO",
            mensaje=f"Lector pendiente: {exc}",
            evidencia={"tipo_input": tipo, "pendiente": str(exc)},
        )]
    except FileNotFoundError as exc:
        logger.warning("Cuadratura %s: input no encontrado (%s)", modelo, exc)
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="WARNING",
            mensaje=f"Input no accesible: {exc}",
            evidencia={"tipo_input": tipo, "error": str(exc)},
        )]
    except Exception as exc:
        logger.exception("Cuadratura %s: error leyendo input", modelo)
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="WARNING",
            mensaje=f"Error leyendo input ({type(exc).__name__}): {exc}",
            evidencia={"tipo_input": tipo, "error": str(exc), "tipo_error": type(exc).__name__},
        )]

    # Lectura del output BQ
    try:
        output_sums = _leer_output_bq(modelo, fecha, client=bq_client)
    except Exception as exc:
        logger.exception("Cuadratura %s: error leyendo output BQ", modelo)
        return [_build_check(
            modelo=modelo, fecha=fecha, check_id="cuadratura_capital", nivel="WARNING",
            mensaje=f"Error leyendo output BQ ({type(exc).__name__}): {exc}",
            evidencia={"tipo_input": tipo, "error": str(exc), "tipo_error": type(exc).__name__},
        )]

    tolerancia = _resolver_tolerancia(cfg_controles, modelo)
    return _comparar(modelo, fecha, input_sums, output_sums, tolerancia, tipo)
