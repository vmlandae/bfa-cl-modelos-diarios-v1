"""Fuente única de verdad del catálogo de modelos diarios.

Centraliza la metadata de los 11 modelos del pipeline para que orquestador,
dashboard, email_report y cargas BQ consuman una sola estructura. Antes de
este módulo la lista vivía duplicada en 4 lugares y producía drift (ej:
mr_ssv quedó fuera de la comparativa del dashboard al agregarse).

Convención de nombres de tabla BQ::

    report_{key_modelo}_dly   -- diario, dataset *_dly_proc_models
    report_{key_modelo}_hist  -- histórico, dataset *_hist

Excepción única: ml_mora_consumo produce además
``report_ml_mora_consumo_renegociado_{dly,hist}``. Se modela vía
``_TABLAS_EXTRA``.

Uso típico::

    from core.modelos_registry import listar_modelos, tabla_hist, nombre_legible

    for m in listar_modelos(vuelta=2):
        print(nombre_legible(m), "->", tabla_hist(m))
"""

from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Catálogo principal de modelos.
#
# Mantener este dict como única fuente. Cuando se agregue un modelo nuevo,
# solo se toca aquí (y, si hay tablas extra, ``_TABLAS_EXTRA``).
# ---------------------------------------------------------------------------

_MODELOS: dict[str, dict[str, Any]] = {
    "mr_prepago_consumo": {
        "nombre": "Modelo Prepago Consumo",
        "nombre_corto": "Prepago Consumo",
        "modulo": "RF_Modelo_Prepago_Consumo.mr_prepago_consumo",
        "activado": True,
        "orden": 1,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "mr_prepago_hipotecario": {
        "nombre": "Modelo Prepago Hipotecario",
        "nombre_corto": "Prepago Hipotecario",
        "modulo": "RF_Modelo_Prepago_Hipotecario.mr_prepago_hipotecario",
        "activado": True,
        "orden": 2,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "mr_prepago_cmr": {
        "nombre": "Modelo Prepago CMR",
        "nombre_corto": "Prepago CMR",
        "modulo": "RF_Modelo_Prepago_CMR.mr_prepago_cmr",
        "activado": True,
        "orden": 3,
        "vuelta": 2,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_mora_consumo": {
        "nombre": "Modelo Mora Consumo",
        "nombre_corto": "Mora Consumo",
        "modulo": "RF_Modelo_Mora_Consumo.ml_mora_consumo",
        "activado": True,
        "orden": 4,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_mora_cae": {
        "nombre": "Modelo Mora CAE",
        "nombre_corto": "Mora CAE",
        "modulo": "RF_Modelo_Mora_CAE.ml_mora_cae",
        "activado": True,
        "orden": 5,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_mora_hipotecario": {
        "nombre": "Modelo Mora Hipotecario",
        "nombre_corto": "Mora Hipotecario",
        "modulo": "RF_Modelo_Mora_Hipotecario.ml_mora_hipotecario",
        "activado": True,
        "orden": 6,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_mora_comercial": {
        "nombre": "Modelo Mora Comercial",
        "nombre_corto": "Mora Comercial",
        "modulo": "RF_Modelo_Mora_Comercial.ml_mora_comercial",
        "activado": True,
        "orden": 7,
        "vuelta": 1,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_nmd": {
        "nombre": "Modelo NMD",
        "nombre_corto": "NMD",
        "modulo": "RF_Modelo_NMD.ml_nmd",
        "activado": True,
        "orden": 8,
        "vuelta": 2,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_lc": {
        "nombre": "Modelo Linea de Credito",
        "nombre_corto": "Línea de Crédito",
        "modulo": "RF_Modelo_Linea_de_Credito.ml_lc",
        "activado": True,
        "orden": 8,
        "vuelta": 2,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "ml_inversiones": {
        "nombre": "Modelo Inversiones",
        "nombre_corto": "Inversiones",
        "modulo": "RF_Modelo_Inversiones.ml_inversiones",
        "activado": True,
        "orden": 9,
        "vuelta": 2,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
    "mr_ssv": {
        "nombre": "Modelo SSV (Saldos Sin Vencimiento)",
        "nombre_corto": "SSV (EOM)",
        "modulo": "RF_Modelo_MR_SSV.mr_ssv",
        "activado": True,
        "orden": 10,
        "vuelta": 2,
        "tiene_carga_gcp": True,
        "tiene_carga_gcp_historica": True,
    },
}

# Tablas extra que un modelo carga además de la principal ``report_{key}_{tipo}``.
# Solo ml_mora_consumo tiene esta excepción.
_TABLAS_EXTRA: dict[str, list[str]] = {
    "ml_mora_consumo": ["report_ml_mora_consumo_renegociado"],
}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def listar_modelos(
    vuelta: Optional[int] = None,
    activos: bool = True,
    con_carga_gcp: bool = False,
    con_carga_gcp_historica: bool = False,
) -> list[str]:
    """Retorna las claves de los modelos que cumplen los filtros."""
    salida = []
    for key, cfg in _MODELOS.items():
        if activos and not cfg.get("activado", True):
            continue
        if vuelta is not None and cfg.get("vuelta") != vuelta:
            continue
        if con_carga_gcp and not cfg.get("tiene_carga_gcp", False):
            continue
        if con_carga_gcp_historica and not cfg.get("tiene_carga_gcp_historica", False):
            continue
        salida.append(key)
    return salida


def metadata(modelo: str) -> dict[str, Any]:
    """Retorna la metadata completa de un modelo. Copia para evitar mutación."""
    cfg = _MODELOS.get(modelo)
    if cfg is None:
        raise KeyError(f"Modelo desconocido: {modelo}")
    return dict(cfg)


def vuelta(modelo: str) -> int:
    return _MODELOS[modelo].get("vuelta", 0)


def nombre_legible(modelo: str) -> str:
    """Nombre corto para UI/email (ej ``"Mora Consumo"``)."""
    cfg = _MODELOS.get(modelo, {})
    return cfg.get("nombre_corto") or cfg.get("nombre") or modelo


def tabla_dly(modelo: str) -> str:
    """Tabla BQ diaria principal del modelo."""
    return f"report_{modelo}_dly"


def tabla_hist(modelo: str) -> str:
    """Tabla BQ histórica principal del modelo."""
    return f"report_{modelo}_hist"


def tablas_extra_dly(modelo: str) -> list[str]:
    """Tablas extra diarias de un modelo (lista vacía si no aplica)."""
    return [f"{base}_dly" for base in _TABLAS_EXTRA.get(modelo, [])]


def tablas_extra_hist(modelo: str) -> list[str]:
    """Tablas extra históricas de un modelo (lista vacía si no aplica)."""
    return [f"{base}_hist" for base in _TABLAS_EXTRA.get(modelo, [])]


def todas_las_tablas_dly(vuelta: Optional[int] = None) -> list[str]:
    """Todas las tablas dly (principal + extras) de los modelos filtrados."""
    salida: list[str] = []
    for m in listar_modelos(vuelta=vuelta):
        salida.append(tabla_dly(m))
        salida.extend(tablas_extra_dly(m))
    return salida


def todas_las_tablas_hist(vuelta: Optional[int] = None) -> list[str]:
    """Todas las tablas hist (principal + extras) de los modelos filtrados."""
    salida: list[str] = []
    for m in listar_modelos(vuelta=vuelta):
        salida.append(tabla_hist(m))
        salida.extend(tablas_extra_hist(m))
    return salida


def modelo_de_tabla(tabla: str) -> Optional[str]:
    """Resuelve a qué modelo pertenece una tabla BQ (principal o extra).

    Útil cuando se etiqueta resultado de un UNION ALL con la columna MODELO.
    """
    sin_sufijo = tabla.removesuffix("_dly").removesuffix("_hist")
    base = sin_sufijo.removeprefix("report_")
    if base in _MODELOS:
        return base
    for modelo, extras in _TABLAS_EXTRA.items():
        for extra in extras:
            extra_base = extra.removeprefix("report_")
            if base == extra_base:
                return modelo
    return None


# ---------------------------------------------------------------------------
# CLI de inspección
# ---------------------------------------------------------------------------

def _cli() -> None:  # pragma: no cover
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Inspecciona el registry de modelos.")
    parser.add_argument("--vuelta", type=int, choices=[1, 2], default=None)
    parser.add_argument("--solo-tablas", action="store_true", help="Imprime tablas hist y dly.")
    parser.add_argument("--json", action="store_true", help="Salida JSON.")
    args = parser.parse_args()

    modelos = listar_modelos(vuelta=args.vuelta)

    if args.solo_tablas:
        salida = {
            "tablas_hist": todas_las_tablas_hist(vuelta=args.vuelta),
            "tablas_dly": todas_las_tablas_dly(vuelta=args.vuelta),
        }
    else:
        salida = {m: {**metadata(m),
                      "tabla_dly": tabla_dly(m),
                      "tabla_hist": tabla_hist(m),
                      "tablas_extra_hist": tablas_extra_hist(m)}
                  for m in modelos}

    if args.json:
        print(json.dumps(salida, indent=2, ensure_ascii=False))
    else:
        for k, v in salida.items() if isinstance(salida, dict) else [(None, salida)]:
            print(k, "->", v)


if __name__ == "__main__":  # pragma: no cover
    _cli()
