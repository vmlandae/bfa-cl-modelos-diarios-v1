"""
Cuadre de modelos de Segunda Vuelta (BigQuery vs productivo heredado xlsm).

Compara, para una fecha de proceso dada, las tablas BQ `report_*_dly` contra
los Excel productivos historicos en Z:\\ a tres niveles:

  1. Totales globales por columna numerica
  2. Agregado por (CODIGO_PRODUCTO, MONEDA_ORIGEN)
  3. Fila a fila por clave natural (detectada automaticamente)

Salida: reports/cuadre_v2_<fecha>.xlsx con multiples hojas.

Uso:
    python -m tools.cuadre_v2 2026-04-24
    python -m tools.cuadre_v2 2026-04-24 --modelos prepago_cmr nmd

Nota: requiere acceso de lectura a Z:\\ y credenciales BQ configuradas.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from google.cloud import bigquery

# Permitir ejecutar como script suelto: python tools/cuadre_v2.py
_BASE_DIR = Path(__file__).resolve().parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from config import config_rutas as cr  # noqa: E402

# ---------------------------------------------------------------------------
# Configuracion de modelos
# ---------------------------------------------------------------------------

PROYECTO_BQ = "bfa-cl-trade-price-report-dev"
DATASET_BQ = "bfa_cl_prd_financial_risk_dly_proc_models"

# Columnas numericas a comparar (subconjunto del esquema base que es relevante
# para el cuadre financiero). Las demas se usan solo como parte de la clave o
# para inspeccion.
COLUMNAS_NUMERICAS = [
    "AMORTIZACION",
    "INTERES",
    "INTERES_DEVENGADO",
    "VP_AMORTIZACION",
    "VP_INTERES",
    "TASA",
    "TASA_CF",
    "SPREAD",
]

# Candidatos de clave natural, ordenados por preferencia. Se elige el primero
# que sea unico en ambos dataframes (xlsm y BQ) tras los filtros.
CANDIDATOS_CLAVE = [
    ["OPERACION", "CODIGO_SUBPRODUCTO", "NUMERO_CUOTA", "FECHA_VENCIMIENTO_CUOTA"],
    ["OPERACION", "NUMERO_CUOTA", "FECHA_VENCIMIENTO_CUOTA", "MONEDA_ORIGEN"],
    ["CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO", "OPERACION", "NUMERO_CUOTA",
     "FECHA_VENCIMIENTO_CUOTA"],
    ["CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO", "OPERACION", "NUMERO_CUOTA",
     "FECHA_VENCIMIENTO_CUOTA", "MONEDA_ORIGEN", "COD_ACT_PAS"],
    ["CODIGO_EMPRESA", "OPERACION", "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO",
     "NUMERO_CUOTA", "FECHA_VENCIMIENTO_CUOTA", "MONEDA_ORIGEN"],
]

# Codigos de producto que separan NMD vs LC dentro del mismo MLA_NMD.xlsm
CODIGOS_LC = [
    "ML_C46_Linea_de_Credito_Egreso_Ajustado",
    "ML_C46_Linea_de_Credito_Ingreso_Ajustado",
]


@dataclass
class ConfigModelo:
    nombre: str                       # clave corta (inversiones, ssv, ...)
    tabla_bq: str                     # report_*_dly
    ruta_xlsm: Path
    hoja: str
    filtro_codigos_in: list[str] = field(default_factory=list)   # solo estos
    filtro_codigos_out: list[str] = field(default_factory=list)  # excluir estos


def construir_configs() -> list[ConfigModelo]:
    return [
        ConfigModelo(
            nombre="inversiones",
            tabla_bq="report_ml_inversiones_dly",
            ruta_xlsm=Path(r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Inversiones\Modelo de Inversiones.xlsx"),
            hoja="INTERFAZ_MODELO_INVERSIONES",
        ),
        ConfigModelo(
            nombre="ssv",
            tabla_bq="report_mr_ssv_dly",
            ruta_xlsm=Path(r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Saldos_sin_Vencimiento\MT_SSV.XLSM"),
            hoja="DESARROLLO",
        ),
        ConfigModelo(
            nombre="nmd",
            tabla_bq="report_ml_nmd_dly",
            ruta_xlsm=Path(r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_NMD\MLA_NMD.xlsm"),
            hoja="DESARROLLO",
            filtro_codigos_out=CODIGOS_LC,
        ),
        ConfigModelo(
            nombre="lc",
            tabla_bq="report_ml_lc_dly",
            ruta_xlsm=Path(r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_NMD\MLA_NMD.xlsm"),
            hoja="DESARROLLO",
            filtro_codigos_in=CODIGOS_LC,
        ),
        ConfigModelo(
            nombre="prepago_cmr",
            tabla_bq="report_mr_prepago_cmr_dly",
            ruta_xlsm=Path(r"Z:\RF_PROCESOS\RF_Modelos\RF_Modelo_Prepago_CMR\Prepago_CMR_Historia\20260424_Prepago_TC_CMR.xlsx"),
            hoja="DESARROLLO",
        ),
    ]


# ---------------------------------------------------------------------------
# Normalizacion (alineada con cargar_output_modelos_bigquery_dly.py)
# ---------------------------------------------------------------------------

RENOMBRES = {
    "FECHA PROCESO": "FECHA_PROCESO",
    "FECHA CREACION": "FECHA_CREACION",
    "FECHA PAGO": "FECHA_PAGO",
    "FACTOR DE RIESGO": "FACTOR_DE_RIESGO",
    "AREA NEGOCIO": "AREA_NEGOCIO",
    "CODIGO_ EJECUTIVO": "CODIGO_EJECUTIVO",
    "TIPO TASA": "TIPO_TASA",
    "TASA CF": "TASA_CF",
    "COD ACT/PAS": "COD_ACT_PAS",
    "COD_ACT/PAS": "COD_ACT_PAS",
}

COLUMNAS_FECHA = [
    "FECHA_PROCESO",
    "FECHA_CREACION",
    "FECHA_INICIO_CUOTA",
    "FECHA_VENCIMIENTO_CUOTA",
    "FECHA_PAGO",
    "FECHA_REPRICING",
]


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in RENOMBRES.items() if k in df.columns})

    # Reemplazar cadenas vacias por NaN solo en columnas object: hacerlo sobre
    # todo el df rompe con extension arrays (p.ej. dbdate de BigQuery).
    cols_obj = df.select_dtypes(include="object").columns
    if len(cols_obj) > 0:
        df[cols_obj] = df[cols_obj].replace("", np.nan)

    for col in COLUMNAS_FECHA:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce").dt.date

    for col in COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Strings: dejar como object, pero strip
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(
            lambda v: v.strip() if isinstance(v, str) else v
        )

    return df


def leer_excel(cfg: ConfigModelo, fecha: datetime.date) -> pd.DataFrame:
    print(f"  Leyendo Excel: {cfg.ruta_xlsm.name} (hoja={cfg.hoja})...")
    df = pd.read_excel(cfg.ruta_xlsm, sheet_name=cfg.hoja, engine="openpyxl")
    df = _normalizar(df)

    if "FECHA_PROCESO" in df.columns:
        df = df[df["FECHA_PROCESO"] == fecha].reset_index(drop=True).copy()

    if cfg.filtro_codigos_in:
        df = df[df["CODIGO_PRODUCTO"].isin(cfg.filtro_codigos_in)].reset_index(drop=True)
    if cfg.filtro_codigos_out:
        df = df[~df["CODIGO_PRODUCTO"].isin(cfg.filtro_codigos_out)].reset_index(drop=True)

    print(f"    -> {len(df):,} filas")
    return df


def leer_bq(client: bigquery.Client, cfg: ConfigModelo, fecha: datetime.date) -> pd.DataFrame:
    print(f"  Leyendo BQ: {cfg.tabla_bq}...")
    sql = f"""
        SELECT *
        FROM `{PROYECTO_BQ}.{DATASET_BQ}.{cfg.tabla_bq}`
        WHERE FECHA_PROCESO = @fecha
    """
    job = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("fecha", "DATE", fecha)
    ])
    df = client.query(sql, job_config=job).to_dataframe(create_bqstorage_client=False)
    df = _normalizar(df)
    print(f"    -> {len(df):,} filas")
    return df


# ---------------------------------------------------------------------------
# Comparacion
# ---------------------------------------------------------------------------

def _detectar_clave(df_a: pd.DataFrame, df_b: pd.DataFrame) -> list[str]:
    """Elige el primer candidato cuyas columnas existan en ambos dataframes.
    No exige unicidad: los duplicados se reportan en el resumen y se desempatan
    con un seq ordinal en _filas_diff."""
    for cand in CANDIDATOS_CLAVE:
        if all(c in df_a.columns and c in df_b.columns for c in cand):
            return cand
    # Fallback: interseccion de columnas no numericas
    return [c for c in df_a.columns
            if c in df_b.columns and c not in COLUMNAS_NUMERICAS
            and c != "FECHA_ACTUALIZACION"]


def _totales(df_excel: pd.DataFrame, df_bq: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for col in COLUMNAS_NUMERICAS:
        s_e = df_excel[col].sum() if col in df_excel.columns else np.nan
        s_b = df_bq[col].sum() if col in df_bq.columns else np.nan
        diff = s_e - s_b if pd.notna(s_e) and pd.notna(s_b) else np.nan
        diff_rel = (diff / s_b) if pd.notna(diff) and s_b not in (0, np.nan) and s_b != 0 else np.nan
        filas.append({
            "columna": col,
            "suma_excel": s_e,
            "suma_bq": s_b,
            "diff_abs": diff,
            "diff_rel_pct": (diff_rel * 100) if pd.notna(diff_rel) else np.nan,
        })
    return pd.DataFrame(filas)


def _por_producto(df_excel: pd.DataFrame, df_bq: pd.DataFrame) -> pd.DataFrame:
    grupo = ["CODIGO_PRODUCTO", "MONEDA_ORIGEN"]
    grupo = [g for g in grupo
             if g in df_excel.columns and g in df_bq.columns]
    if not grupo:
        return pd.DataFrame()

    cols = [c for c in COLUMNAS_NUMERICAS
            if c in df_excel.columns and c in df_bq.columns]
    if not cols:
        return pd.DataFrame()

    agg_e = df_excel.groupby(grupo, dropna=False)[cols].sum().add_suffix("_excel")
    agg_b = df_bq.groupby(grupo, dropna=False)[cols].sum().add_suffix("_bq")
    out = agg_e.join(agg_b, how="outer").fillna(0)

    for c in cols:
        out[f"{c}_diff_abs"] = out[f"{c}_excel"] - out[f"{c}_bq"]
        denom = out[f"{c}_bq"].replace(0, np.nan)
        out[f"{c}_diff_pct"] = (out[f"{c}_diff_abs"] / denom) * 100

    return out.reset_index()


def _filas_diff(df_excel: pd.DataFrame, df_bq: pd.DataFrame, clave: list[str],
                limite: int = 20000) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna (filas_diff, solo_excel, solo_bq).

    Si la clave no es unica, agrega un `_seq` ordinal por grupo en cada lado
    para emparejar 1:1 dentro del grupo. Castea columnas de clave a string
    para evitar errores de dtype en el merge.
    """
    cols_num = [c for c in COLUMNAS_NUMERICAS
                if c in df_excel.columns and c in df_bq.columns]

    e = df_excel[clave + cols_num].copy()
    b = df_bq[clave + cols_num].copy()

    # Homogeneizar dtype de columnas de clave: todo a string para columnas
    # que no son fecha (las fechas ya son datetime.date en ambos lados).
    cols_fecha_clave = [c for c in clave if c in COLUMNAS_FECHA]
    cols_str_clave = [c for c in clave if c not in cols_fecha_clave]
    for col in cols_str_clave:
        e[col] = e[col].astype(object).where(e[col].notna(), None)
        b[col] = b[col].astype(object).where(b[col].notna(), None)
        e[col] = e[col].map(lambda v: "" if v is None else str(v))
        b[col] = b[col].map(lambda v: "" if v is None else str(v))

    # Desambiguar duplicados con un seq ordinal por grupo
    e["_seq"] = e.groupby(clave, dropna=False).cumcount()
    b["_seq"] = b.groupby(clave, dropna=False).cumcount()
    clave_full = clave + ["_seq"]

    merged = e.merge(b, on=clave_full, how="outer", suffixes=("_excel", "_bq"),
                     indicator=True)

    solo_excel = merged[merged["_merge"] == "left_only"][
        clave_full + [f"{c}_excel" for c in cols_num]]
    solo_bq = merged[merged["_merge"] == "right_only"][
        clave_full + [f"{c}_bq" for c in cols_num]]

    comunes = merged[merged["_merge"] == "both"].copy()

    mask_dif = pd.Series(False, index=comunes.index)
    for c in cols_num:
        e_col = comunes[f"{c}_excel"].fillna(0)
        b_col = comunes[f"{c}_bq"].fillna(0)
        diff = e_col - b_col
        comunes[f"{c}_diff"] = diff
        mask_dif |= diff.abs() > 0.005

    filas_diff = comunes[mask_dif].drop(columns=["_merge"])

    orden = list(clave_full)
    for c in cols_num:
        orden += [f"{c}_excel", f"{c}_bq", f"{c}_diff"]
    filas_diff = filas_diff[orden]

    if len(filas_diff) > limite:
        print(f"    AVISO: truncando filas_diff de {len(filas_diff):,} a {limite:,}")
        filas_diff = filas_diff.head(limite)

    return filas_diff, solo_excel.head(5000), solo_bq.head(5000)


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------

def comparar_modelo(cfg: ConfigModelo, fecha: datetime.date,
                    client: bigquery.Client) -> dict:
    print(f"\n=== {cfg.nombre.upper()} ===")
    df_excel = leer_excel(cfg, fecha)
    df_bq = leer_bq(client, cfg, fecha)

    clave = _detectar_clave(df_excel, df_bq)
    dup_excel = df_excel.duplicated(subset=clave).sum() if clave else -1
    dup_bq = df_bq.duplicated(subset=clave).sum() if clave else -1
    print(f"  Clave: {clave} (dup_excel={dup_excel}, dup_bq={dup_bq})")

    totales = _totales(df_excel, df_bq)
    por_prod = _por_producto(df_excel, df_bq)
    filas_diff, solo_excel, solo_bq = _filas_diff(df_excel, df_bq, clave)

    resumen = {
        "modelo": cfg.nombre,
        "tabla_bq": cfg.tabla_bq,
        "filas_excel": len(df_excel),
        "filas_bq": len(df_bq),
        "clave": " + ".join(clave),
        "dup_clave_excel": dup_excel,
        "dup_clave_bq": dup_bq,
        "filas_solo_excel": len(solo_excel),
        "filas_solo_bq": len(solo_bq),
        "filas_con_diff": len(filas_diff),
    }
    # Agregar totales por columna al resumen
    for _, r in totales.iterrows():
        resumen[f"diff_abs_{r['columna']}"] = r["diff_abs"]

    print(f"  Resumen: {resumen}")

    return {
        "resumen": resumen,
        "totales": totales,
        "por_producto": por_prod,
        "filas_diff": filas_diff,
        "solo_excel": solo_excel,
        "solo_bq": solo_bq,
    }


def _hoja(nombre_modelo: str, sufijo: str) -> str:
    """Nombre de hoja Excel (max 31 chars)."""
    s = f"{nombre_modelo}_{sufijo}"
    return s[:31]


def escribir_reporte(resultados: dict[str, dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nEscribiendo reporte: {destino}")

    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        resumen_df = pd.DataFrame([r["resumen"] for r in resultados.values()])
        resumen_df.to_excel(xw, sheet_name="00_resumen", index=False)

        for modelo, r in resultados.items():
            r["totales"].to_excel(xw, sheet_name=_hoja(modelo, "totales"), index=False)
            if not r["por_producto"].empty:
                r["por_producto"].to_excel(
                    xw, sheet_name=_hoja(modelo, "por_prod"), index=False)
            if not r["filas_diff"].empty:
                r["filas_diff"].to_excel(
                    xw, sheet_name=_hoja(modelo, "filas_diff"), index=False)
            if not r["solo_excel"].empty:
                r["solo_excel"].to_excel(
                    xw, sheet_name=_hoja(modelo, "solo_excel"), index=False)
            if not r["solo_bq"].empty:
                r["solo_bq"].to_excel(
                    xw, sheet_name=_hoja(modelo, "solo_bq"), index=False)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cuadre BQ vs xlsm productivo")
    parser.add_argument("fecha", help="Fecha proceso YYYY-MM-DD")
    parser.add_argument("--modelos", nargs="*",
                        choices=["inversiones", "ssv", "nmd", "lc", "prepago_cmr"],
                        help="Subset de modelos (default: todos)")
    parser.add_argument("--salida", default=None,
                        help="Ruta de salida (default: reports/cuadre_v2_<fecha>.xlsx)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    fecha = datetime.datetime.strptime(args.fecha, "%Y-%m-%d").date()

    configs = construir_configs()
    if args.modelos:
        configs = [c for c in configs if c.nombre in args.modelos]

    cred = cr.obtener_ruta_credenciales_gcp()
    client = bigquery.Client.from_service_account_json(str(cred),
                                                        project=PROYECTO_BQ)

    resultados: dict[str, dict] = {}
    for cfg in configs:
        try:
            resultados[cfg.nombre] = comparar_modelo(cfg, fecha, client)
        except Exception as e:
            import traceback
            print(f"  ERROR en {cfg.nombre}: {e!r}")
            traceback.print_exc()
            resultados[cfg.nombre] = {
                "resumen": {"modelo": cfg.nombre, "error": repr(e)},
                "totales": pd.DataFrame(),
                "por_producto": pd.DataFrame(),
                "filas_diff": pd.DataFrame(),
                "solo_excel": pd.DataFrame(),
                "solo_bq": pd.DataFrame(),
            }

    if args.salida:
        destino = Path(args.salida)
    else:
        destino = _BASE_DIR / "reports" / f"cuadre_v2_{args.fecha.replace('-', '')}.xlsx"

    escribir_reporte(resultados, destino)
    print("\nListo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
