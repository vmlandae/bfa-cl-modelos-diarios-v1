"""
Cargador unificado de parámetros: JSON (preferido) con fallback a Excel.

Flujo de carga:
    1. Si existe .json → carga desde JSON.
       - Si también existe .xlsx → valida equivalencia (con caché).
    2. Si solo existe .xlsx → carga desde Excel (modo legacy, warning).
    3. Si no existe ninguno → FileNotFoundError.

Validación eficiente con caché de metadata:
    - Primera vez: compara contenido completo, guarda checksums + metadata.
    - Ejecuciones siguientes: si size/mtime no cambiaron → skip.
    - Si metadata cambió → re-compara; si hay diferencia → error bloqueante.

Uso:
    from procesamiento_datos_input.cargador_parametros import cargar_hojas_parametros

    hojas = cargar_hojas_parametros("mr_prepago_consumo")
    df_smm = hojas["SMM_PREPAGO"]
    df_esc = hojas["ESCENARIO"]
"""

import hashlib
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Raíz del proyecto
_BASE_DIR = Path(__file__).resolve().parent.parent
_CACHE_DIR = _BASE_DIR / "data" / "cache"

# Catálogo: modelo → ruta relativa del Excel de parámetros
_CATALOGO: Dict[str, str] = {
    "mr_prepago_consumo": "RF_Modelo_Prepago_Consumo/parametros/parametros_mr_prepago_consumo.xlsx",
    "mr_prepago_hipotecario": "RF_Modelo_Prepago_Hipotecario/parametros/parametros_mr_prepago_hipotecario.xlsx",
    "mr_prepago_cmr": "RF_Modelo_Prepago_CMR/parametros/parametros_mr_prepago_cmr.xlsx",
    "ml_mora_consumo": "RF_Modelo_Mora_Consumo/parametros/parametros_ml_mora_consumo.xlsx",
    "ml_mora_cae": "RF_Modelo_Mora_CAE/parametros/parametros_ml_mora_cae.xlsx",
    "ml_mora_hipotecario": "RF_Modelo_Mora_Hipotecario/parametros/parametros_ml_mora_hipotecario.xlsx",
    "ml_mora_comercial": "RF_Modelo_Mora_Comercial/parametros/parametros_ml_mora_comercial.xlsx",
    "ml_nmd": "RF_Modelo_NMD/parametros/parametros_ml_nmd.xlsx",
    "ml_lc": "RF_Modelo_Linea_de_Credito/parametros/parametros_ml_lc.xlsx",
    "mr_ssv": "RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.xlsx",
}


# ─────────────────────────── utilidades ───────────────────────────


def _sha256(path: Path) -> str:
    """Calcula SHA-256 de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_meta(path: Path) -> dict:
    """Retorna metadata liviana de un archivo (size + mtime)."""
    st = path.stat()
    return {"size": st.st_size, "mtime": st.st_mtime}


# ─────────────────────────── lectura JSON ───────────────────────────


def _leer_json(ruta_json: Path) -> Dict[str, pd.DataFrame]:
    """Lee un JSON de parámetros y retorna dict {nombre_hoja: DataFrame}."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    hojas = {}
    for nombre_hoja, contenido in data["hojas"].items():
        hojas[nombre_hoja] = pd.DataFrame(
            data=contenido["data"],
            columns=contenido["columns"],
        )
    return hojas


# ─────────────────────────── lectura Excel ───────────────────────────


def _leer_excel(ruta_excel: Path) -> Dict[str, pd.DataFrame]:
    """Lee un Excel de parámetros y retorna dict {nombre_hoja: DataFrame}."""
    xls = pd.ExcelFile(ruta_excel)
    return {s: pd.read_excel(ruta_excel, sheet_name=s) for s in xls.sheet_names}


# ─────────────────────── validación con caché ───────────────────────


def _ruta_cache_validacion(modelo: str) -> Path:
    return _CACHE_DIR / f"param_check_{modelo}.json"


def _comparar_hojas(
    hojas_json: Dict[str, pd.DataFrame],
    hojas_excel: Dict[str, pd.DataFrame],
) -> list:
    """
    Compara hoja por hoja. Retorna lista de diferencias (vacía = idénticos).
    """
    diffs = []

    solo_json = set(hojas_json) - set(hojas_excel)
    solo_excel = set(hojas_excel) - set(hojas_json)
    if solo_json:
        diffs.append(f"Hojas solo en JSON: {solo_json}")
    if solo_excel:
        diffs.append(f"Hojas solo en Excel: {solo_excel}")

    for nombre in sorted(set(hojas_json) & set(hojas_excel)):
        df_j = hojas_json[nombre]
        df_e = hojas_excel[nombre]

        if list(df_j.columns) != list(df_e.columns):
            diffs.append(
                f"[{nombre}] Columnas difieren: "
                f"JSON={list(df_j.columns)[:5]}… Excel={list(df_e.columns)[:5]}…"
            )
            continue

        if df_j.shape != df_e.shape:
            diffs.append(f"[{nombre}] Shape difiere: JSON={df_j.shape} Excel={df_e.shape}")
            continue

        for col in df_j.columns:
            sj, se = df_j[col], df_e[col]
            if pd.api.types.is_numeric_dtype(sj) and pd.api.types.is_numeric_dtype(se):
                if not np.allclose(
                    sj.fillna(0).values, se.fillna(0).values,
                    atol=1e-10, rtol=1e-10,
                ):
                    max_diff = float(np.max(np.abs(sj.fillna(0).values - se.fillna(0).values)))
                    diffs.append(f"[{nombre}] Col '{col}' difiere (max_diff={max_diff:.2e})")
            else:
                mask = sj.astype(str).fillna("") != se.astype(str).fillna("")
                if mask.any():
                    diffs.append(f"[{nombre}] Col '{col}' difiere en {mask.sum()} valor(es)")

    return diffs


def _validar_con_cache(
    modelo: str,
    ruta_json: Path,
    ruta_excel: Path,
) -> None:
    """
    Valida equivalencia JSON↔Excel con caché de metadata.

    - Si metadata (size + mtime) no cambió desde la última validación → skip.
    - Si cambió → comparación completa; error bloqueante si hay diferencias.
    """
    cache_path = _ruta_cache_validacion(modelo)
    meta_json = _file_meta(ruta_json)
    meta_excel = _file_meta(ruta_excel)

    # Intentar caché previo
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)

        cj = cached.get("json", {})
        ce = cached.get("excel", {})

        if (
            cj.get("size") == meta_json["size"]
            and cj.get("mtime") == meta_json["mtime"]
            and ce.get("size") == meta_excel["size"]
            and ce.get("mtime") == meta_excel["mtime"]
        ):
            logger.info(
                "[%s] Validación parámetros: caché vigente (validado %s)",
                modelo, cached.get("validated_at", "?"),
            )
            return

        logger.info("[%s] Metadata cambió — forzando re-validación completa", modelo)

    # Comparación completa
    logger.info("[%s] Validando equivalencia JSON vs Excel...", modelo)
    hojas_json = _leer_json(ruta_json)
    hojas_excel = _leer_excel(ruta_excel)
    diffs = _comparar_hojas(hojas_json, hojas_excel)

    if diffs:
        detalle = "\n  ".join(diffs)
        raise RuntimeError(
            f"Parámetros desincronizados para '{modelo}'.\n"
            f"Diferencias encontradas:\n  {detalle}\n\n"
            f"Ejecutar: python -m tools.excel_a_json {modelo}\n"
            f"para re-generar el JSON desde el Excel actualizado."
        )

    # Guardar caché
    sha_j = _sha256(ruta_json)
    sha_e = _sha256(ruta_excel)
    cache_data = {
        "modelo": modelo,
        "validated_at": datetime.now().isoformat(timespec="seconds"),
        "result": "ok",
        "json": {"path": ruta_json.name, "size": meta_json["size"],
                 "mtime": meta_json["mtime"], "sha256": sha_j},
        "excel": {"path": ruta_excel.name, "size": meta_excel["size"],
                  "mtime": meta_excel["mtime"], "sha256": sha_e},
        "hojas_validadas": sorted(hojas_json.keys()),
    }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "[%s] Validación OK — %d hojas idénticas "
        "(sha256_json=%s… sha256_excel=%s…)",
        modelo, len(hojas_json), sha_j[:12], sha_e[:12],
    )


# ───────────────────── API pública: cargador unificado ─────────────────────


def resolver_rutas_parametros(modelo: str) -> tuple:
    """Resuelve (ruta_excel, ruta_json) para un modelo dado."""
    ruta_rel = _CATALOGO.get(modelo)
    if not ruta_rel:
        raise ValueError(f"Modelo '{modelo}' no está en el catálogo de parámetros")
    ruta_excel = _BASE_DIR / ruta_rel
    return ruta_excel, ruta_excel.with_suffix(".json")


def cargar_hojas_parametros(
    modelo: str,
    ruta_excel_override: Optional[Path] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Carga parámetros de un modelo como dict de DataFrames.

    Prioridad:
        1. JSON si existe (más rápido, sin dependencia binaria).
        2. Excel como fallback (modo legacy).

    Si ambos existen, valida equivalencia con caché de metadata.

    Args:
        modelo: Nombre del modelo (ej: "mr_prepago_consumo").
        ruta_excel_override: Ruta alternativa al Excel (ej: parámetros en red).

    Returns:
        Dict {nombre_hoja: DataFrame}.

    Raises:
        FileNotFoundError: Si no existe ni JSON ni Excel.
        RuntimeError: Si JSON y Excel están desincronizados.
    """
    ruta_excel, ruta_json = resolver_rutas_parametros(modelo)
    if ruta_excel_override:
        ruta_excel = Path(ruta_excel_override)
        ruta_json = ruta_excel.with_suffix(".json")

    tiene_json = ruta_json.exists()
    tiene_excel = ruta_excel.exists()

    if not tiene_json and not tiene_excel:
        raise FileNotFoundError(
            f"No se encontró archivo de parámetros para '{modelo}'.\n"
            f"  Buscado JSON: {ruta_json}\n"
            f"  Buscado Excel: {ruta_excel}"
        )

    if tiene_json and tiene_excel:
        _validar_con_cache(modelo, ruta_json, ruta_excel)
        logger.debug("[%s] Cargando parámetros desde JSON", modelo)
        return _leer_json(ruta_json)

    if tiene_json:
        logger.debug("[%s] Cargando parámetros desde JSON (sin Excel)", modelo)
        return _leer_json(ruta_json)

    # Solo Excel — modo legacy
    warnings.warn(
        f"[{modelo}] Cargando parámetros desde Excel (fallback). "
        f"Generar JSON: python -m tools.excel_a_json {modelo}",
        stacklevel=2,
    )
    return _leer_excel(ruta_excel)