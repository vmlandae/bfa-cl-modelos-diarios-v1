"""
Modelo SSV -- version EOM (replica 1:1 el MT_SSV productivo).

Este modulo implementa el esquema REAL del MT_SSV.XLSM:
- Granularidad mensual end-of-month (EOM), no diaria.
- Plazos fijos por producto extraidos del MT productivo:
    R13_Cta_Cte : 74  meses CORE
    R13_Cta_Vta : 108 meses CORE
    R13_AGD     : 70  meses CORE
    R13_AGI     : 70  meses CORE
    Cta_Cte     : 51  CORE_CORE + 9  CORE_SOFT (amort=0)
    Cta_Vta     : 47  CORE_CORE + 2  CORE_SOFT
    AGD         : 212 CORE_CORE + 82 CORE_SOFT
    AGI         : 216 CORE_CORE + 78 CORE_SOFT
- Factores F_vec extraidos de las amortizaciones historicas del propio MT
  productivo (JSON: factores_eom_mt_ssv.json). Formula:
      I_k = CORE_total * (F[k-1] - F[k])   para k = 1..N
      F[0] = 1

El output DESARROLLO replica el orden exacto producido por la macro VBA
`Consolida_Desarrollo` del XLSM:
    Cta_Cte -> Cta_Vta -> AGD -> AGI -> R13_Cta_Cte -> R13_Cta_Vta -> R13_AGD -> R13_AGI

Cada hoja emite (en este orden):
    - 1 fila MAYORISTAS (solo en Cta_Cte y R13_Cta_Cte; amort=0 actualmente)
    - 1 fila BASE/NONCORE sin cuota (amort = saldo_total - CORE_total)
    - N filas CORE/CORE_CORE con NUMERO_CUOTA 1..N y fechas EOM
    - [GESTION] M filas CORE_SOFT con NUMERO_CUOTA N+1..N+M y amort=0

Entrada: saldo total por producto (FLUJO_MO) extraido del Access de Liquidez.
Salida: DataFrame DESARROLLO identico al del MT_SSV productivo.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import bfa_cl_utilidades as ut
from config import config_rutas as cr
from core.excel_output import guardar_excel
from core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config y rutas
# ---------------------------------------------------------------------------
with open(cr.CONFIG / "config_rutas_ext_y_archivos.yaml", "r", encoding="utf-8") as _f:
    _CFG = yaml.safe_load(_f)

ARCHIVO_INPUT = cr.resolver_ruta(_CFG["modelos"]["mr_ssv"]["ms_access_input"])
TABLA_INPUT = _CFG["modelos"]["mr_ssv"].get("ms_access_tabla_input", "MOD_Saldos_para_Modelos")
RUTA_OUTPUT_MODELO = cr.resolver_ruta(_CFG["modelos"]["mr_ssv"]["excel_output"])

# Ruta del JSON de factores EOM (extraido del MT productivo una sola vez).
RUTA_FACTORES_EOM = Path(__file__).resolve().parent / "parametros" / "factores_eom_mt_ssv.json"

# Mapeo COD_SUB_PRO (Access) -> clave modelo
_MAPEO_SUB_PRO: dict[str, str] = {
    "CTA. CORRIENTE": "CTA_CTE",
    "CTA. VISTA": "CTA_VTA",
    "CTA. AHORRO GIRO DIFERIDO": "AGD",
    "CTA. AHORRO INCONDICIONAL": "AGI",
}

# Orden exacto de las hojas fuente segun Sub Consolida_Desarrollo del XLSM:
# GESTION primero (Cta_Cte, Cta_Vta, AGD, AGI), luego R13.
_HOJAS_ORDEN: list[str] = [
    "Cta_Cte", "Cta_Vta", "AGD", "AGI",
    "R13_Cta_Cte", "R13_Cta_Vta", "R13_AGD", "R13_AGI",
]

# Mapeo hoja -> clave producto modelo + moneda + orden de subproductos dentro
# de la hoja. El orden de subproductos sigue la estructura EXACTA observada en
# el MT productivo fecha 2026-04-21 (ver sandbox/extract_factores_eom.py).
_HOJAS: dict[str, dict] = {
    "Cta_Cte": {
        "producto_modelo": "CTA_CTE",
        "moneda": "CLP",
        "codigo_producto": "MT_CTA. CORRIENTE",
        "orden_subproductos": [
            ("CTA. CORRIENTE-MAYORISTAS",          "MAYORISTAS"),
            ("CTA. CORRIENTE PERSONAS",            "NONCORE"),
            ("CTA. CORRIENTE PERSONAS_CORE_CORE",  "CORE"),
            ("CTA. CORRIENTE PERSONAS_CORE_SOFT",  "SOFT"),
        ],
    },
    "Cta_Vta": {
        "producto_modelo": "CTA_VTA",
        "moneda": "CLP",
        "codigo_producto": "MT.CTA. VISTA",
        "orden_subproductos": [
            ("CTA. VISTA",             "NONCORE"),
            ("CTA. VISTA_CORE_CORE",   "CORE"),
            ("CTA. VISTA_CORE_SOFT",   "SOFT"),
        ],
    },
    "AGD": {
        "producto_modelo": "AGD",
        "moneda": "CLF",
        "codigo_producto": "MT_CTA. AHORRO",
        "orden_subproductos": [
            ("CTA. AHORRO G.DIF",            "NONCORE"),
            ("CTA. AHORRO G.DIF_CORE_CORE",  "CORE"),
            ("CTA. AHORRO G.DIF_CORE_SOFT",  "SOFT"),
        ],
    },
    "AGI": {
        "producto_modelo": "AGI",
        "moneda": "CLF",
        "codigo_producto": "MT_CTA. AHORRO",
        "orden_subproductos": [
            ("CTA. AHORRO G.INC",            "NONCORE"),
            ("CTA. AHORRO G.INC_CORE_CORE",  "CORE"),
            ("CTA. AHORRO G.INC_CORE_SOFT",  "SOFT"),
        ],
    },
    "R13_Cta_Cte": {
        "producto_modelo": "CTA_CTE",
        "moneda": "CLP",
        "codigo_producto": "MT_R13_CTA. CORRIENTE",
        "orden_subproductos": [
            ("MT_R13_CTA. CORRIENTE-MAYORISTAS",        "MAYORISTAS"),
            ("MT_R13_CTA. CORRIENTE PERSONAS_NONCORE",  "NONCORE"),
            ("MT_R13_CTA. CORRIENTE PERSONAS_CORE",     "CORE"),
        ],
    },
    "R13_Cta_Vta": {
        "producto_modelo": "CTA_VTA",
        "moneda": "CLP",
        "codigo_producto": "MT_R13_CTA. VISTA",
        "orden_subproductos": [
            ("MT_R13_CTA. VISTA_NONCORE",  "NONCORE"),
            ("MT_R13_CTA. VISTA_CORE",     "CORE"),
        ],
    },
    "R13_AGD": {
        "producto_modelo": "AGD",
        "moneda": "CLF",
        "codigo_producto": "MT_R13_CTA. AHORRO",
        "orden_subproductos": [
            ("MT_R13_CTA. AHORRO G.DIF_NONCORE",  "NONCORE"),
            ("MT_R13_CTA. AHORRO G.DIF_CORE",     "CORE"),
        ],
    },
    "R13_AGI": {
        "producto_modelo": "AGI",
        "moneda": "CLF",
        "codigo_producto": "MT_R13_CTA. AHORRO",
        "orden_subproductos": [
            ("MT_R13_CTA. AHORRO G.INC_NONCORE",  "NONCORE"),
            ("MT_R13_CTA. AHORRO G.INC_CORE",     "CORE"),
        ],
    },
}

# Columnas finales del DESARROLLO (uso interno con underscores).
_COLS_DESARROLLO: list[str] = [
    "FECHA_PROCESO", "CODIGO_EMPRESA", "OPERACION", "COD_ACT/PAS",
    "MONEDA_ORIGEN", "MONEDA_COMPENSACION", "COMPENSACION",
    "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO",
    "FECHA_CREACION", "NUMERO_CUOTA", "FECHA_INICIO_CUOTA",
    "FECHA_VENCIMIENTO_CUOTA", "FECHA_PAGO", "FECHA_REPRICING",
    "AMORTIZACION", "INTERES", "INTERES_DEVENGADO",
    "VP_AMORTIZACION", "VP_INTERES", "FACTOR_DE_RIESGO",
    "TIPO_CUOTA", "AREA_NEGOCIO", "CODIGO_EJECUTIVO",
    "CODIGO_ESTRATEGIA", "CLASIFICACION_CONTABLE",
    "TIPO_TASA", "INDEXADOR", "TASA", "TASA_CF", "SPREAD",
]

# Renombrado interno -> headers estilo MT productivo (los que espera el
# cargador BQ cuando lee el xlsm heredado). El loader ya reconoce ambos
# estilos, pero emitimos los del MT para que el mapeo a BQ sea identico.
_RENOMBRE_COLS_MT: dict[str, str] = {
    "FECHA_PROCESO":    "FECHA PROCESO",
    "COD_ACT/PAS":      "COD ACT/PAS",
    "FECHA_CREACION":   "FECHA CREACION",
    "FECHA_PAGO":       "FECHA PAGO",
    "FACTOR_DE_RIESGO": "FACTOR DE RIESGO",
    "AREA_NEGOCIO":     "AREA NEGOCIO",
    "CODIGO_EJECUTIVO": "CODIGO_ EJECUTIVO",
    "TIPO_TASA":        "TIPO TASA",
    "TASA_CF":          "TASA CF",
}


# ===========================================================================
# 1. CARGA DE DATOS
# ===========================================================================

def cargar_factores_eom() -> dict:
    """Lee el JSON con los factores EOM extraidos del MT productivo.

    El JSON es estatico (snapshot del MT productivo fecha 2026-04-21). Contiene
    por cada bloque (hoja) la estructura de subproductos con sus vectores
    factores_eom (F[0..N]) y metadatos (core_total, n_con_cuota, etc.).
    """
    with open(RUTA_FACTORES_EOM, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_datos_balance(fecha_t: datetime) -> pd.DataFrame:
    """Lee MOD_Saldos_para_Modelos y agrega por sub-producto del modelo."""
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    logger.info(f"      * Leyendo balance desde Access (tabla {TABLA_INPUT})...")
    fecha_access = fecha_t.strftime("%Y-%m-%d")
    query = (
        f"SELECT * FROM [{TABLA_INPUT}] "
        f"WHERE [Fec_Pro] = #{fecha_access}#"
    )
    df_raw = leer_tabla_con_cache(
        access_path=ARCHIVO_INPUT,
        nombre_tabla=TABLA_INPUT,
        fecha_proceso=fecha_t.strftime("%Y%m%d"),
        query=query,
    )
    mask = df_raw["Cod_Sub_Pro"].isin(list(_MAPEO_SUB_PRO.keys()))
    df = df_raw.loc[mask].copy()
    group_cols = [c for c in ["Fec_Pro", "Cod_A_P", "Moneda", "Cod_Pro", "Cod_Sub_Pro"] if c in df.columns]
    data = df.groupby(group_cols, as_index=False).agg(
        AMORTIZACION_MO=("Cap_Amort", "sum"),
        INTERES_MO=("Int_Total_Cont", "sum"),
    )
    data["FLUJO_MO"] = data["AMORTIZACION_MO"] + data["INTERES_MO"]
    data = ut.estandariza_nombre_columnas_dataframe(data)
    data["COD_SUB_PRO_MODELO"] = data["COD_SUB_PRO"].map(_MAPEO_SUB_PRO)
    data = data[data["COD_SUB_PRO_MODELO"].notna()].reset_index(drop=True)
    # Agregado final: un saldo por producto modelo.
    balance_agg = (
        data.groupby("COD_SUB_PRO_MODELO", as_index=False)
        .agg(FLUJO_MO=("FLUJO_MO", "sum"))
    )
    logger.info(f"        - Balance agregado: {balance_agg.to_dict(orient='records')}")
    return balance_agg


# ===========================================================================
# 2. CONSTRUCCION DEL DESARROLLO (EOM)
# ===========================================================================

def _fecha_eom_mas_k_meses(fecha_proc: datetime, k: int) -> datetime:
    """EOM(fecha_proc + k meses). Usa ut.agrega_meses_a_fecha + ut.ultimo_dia_del_mes."""
    return ut.ultimo_dia_del_mes(ut.agrega_meses_a_fecha(fecha_proc, k))


def _amortizaciones_desde_factores(
    factores: list[float], core_total: float
) -> np.ndarray:
    """I_k = core * (F[k-1] - F[k]) para k = 1..N.

    ``factores`` tiene longitud N+1 (F[0]=1, F[1], ..., F[N]). Retorna array
    de N amortizaciones mensuales EOM.
    """
    f = np.asarray(factores, dtype=float)
    diffs = f[:-1] - f[1:]
    return core_total * diffs


def _fila_desarrollo(
    fecha_proceso: datetime,
    moneda: str,
    cod_producto: str,
    cod_subproducto: str,
    amortizacion: float,
    fecha_venc: datetime,
    numero_cuota=None,
) -> dict:
    """Una fila homogenea con la estructura DESARROLLO."""
    return {
        "FECHA_PROCESO":            fecha_proceso,
        "CODIGO_EMPRESA":           1,
        "OPERACION":                np.nan,
        "COD_ACT/PAS":              "PAS",
        "MONEDA_ORIGEN":            moneda,
        "MONEDA_COMPENSACION":      moneda,
        "COMPENSACION":             np.nan,
        "CODIGO_PRODUCTO":          cod_producto,
        "CODIGO_SUBPRODUCTO":       cod_subproducto,
        "FECHA_CREACION":           np.nan,
        "NUMERO_CUOTA":             np.nan if numero_cuota is None else numero_cuota,
        "FECHA_INICIO_CUOTA":       np.nan,
        "FECHA_VENCIMIENTO_CUOTA":  fecha_venc,
        "FECHA_PAGO":               fecha_venc,
        "FECHA_REPRICING":          fecha_venc,
        "AMORTIZACION":             amortizacion,
        "INTERES":                  np.nan,
        "INTERES_DEVENGADO":        np.nan,
        "VP_AMORTIZACION":          np.nan,
        "VP_INTERES":               np.nan,
        # Columnas STRING: usar None (no np.nan) para que BQ las reciba como NULL;
        # astype('str') sobre NaN produce el literal 'nan'.
        "FACTOR_DE_RIESGO":         None,
        "TIPO_CUOTA":               1,
        "AREA_NEGOCIO":             "BALANCE TASAS",
        "CODIGO_EJECUTIVO":         None,
        "CODIGO_ESTRATEGIA":        "BALANCE TASAS",
        "CLASIFICACION_CONTABLE":   "HTM",
        "TIPO_TASA":                1,
        "INDEXADOR":                None,
        "TASA":                     np.nan,
        "TASA_CF":                  np.nan,
        "SPREAD":                   np.nan,
    }


def construir_desarrollo_eom(
    balance_agg: pd.DataFrame,
    factores_eom: dict,
    fecha_proceso: datetime,
    factor_core_r13: float = 0.70,
) -> pd.DataFrame:
    """Construye el DESARROLLO EOM replicando el MT_SSV productivo.

    Args:
        balance_agg: DataFrame con columnas COD_SUB_PRO_MODELO y FLUJO_MO.
        factores_eom: dict cargado de ``factores_eom_mt_ssv.json``.
        fecha_proceso: fecha de corrida.
        factor_core_r13: factor R13 (default 0.70 = metodologia vigente).

    Return:
        DataFrame con las columnas ``_COLS_DESARROLLO``.
    """
    flujo_por_prod = dict(zip(balance_agg["COD_SUB_PRO_MODELO"], balance_agg["FLUJO_MO"]))
    bloques_params = factores_eom["bloques"]

    dia_siguiente = fecha_proceso + timedelta(days=1)
    filas: list[dict] = []

    for hoja in _HOJAS_ORDEN:
        cfg_hoja = _HOJAS[hoja]
        prod = cfg_hoja["producto_modelo"]
        moneda = cfg_hoja["moneda"]
        cod_producto = cfg_hoja["codigo_producto"]

        saldo_total = float(flujo_por_prod.get(prod, 0.0))

        # --- CORE total por hoja ---
        if hoja.startswith("R13_"):
            # R13: CORE = saldo_total * factor_core_r13 (0.70)
            core_total_hoja = saldo_total * factor_core_r13
            noncore_total_hoja = saldo_total - core_total_hoja
        else:
            # GESTION: CORE_total hardcoded en el JSON (Montos!D3:D6 del XLSM).
            # Lo leemos del bloque CORE_CORE del propio JSON.
            core_total_hoja = None
            for sub, info in bloques_params[hoja]["subproductos"].items():
                if "CORE_CORE" in sub and info.get("core_total"):
                    core_total_hoja = float(info["core_total"])
                    break
            if core_total_hoja is None:
                raise ValueError(f"No se encontro core_total GESTION para hoja {hoja}")
            noncore_total_hoja = saldo_total - core_total_hoja

        # --- Emitir subproductos en el orden de la hoja ---
        for cod_sub, rol in cfg_hoja["orden_subproductos"]:
            info = bloques_params[hoja]["subproductos"].get(cod_sub)
            if info is None:
                # Subproducto no encontrado en el JSON: se omite (ej: hoja sin MAYORISTAS).
                continue

            if rol == "MAYORISTAS":
                # Fila unica sin cuota, amort=0 (convencion del MT).
                filas.append(_fila_desarrollo(
                    fecha_proceso, moneda, cod_producto, cod_sub,
                    amortizacion=0.0, fecha_venc=dia_siguiente, numero_cuota=None,
                ))

            elif rol == "NONCORE":
                # Fila unica sin cuota, amort = saldo_total - core_total_hoja.
                filas.append(_fila_desarrollo(
                    fecha_proceso, moneda, cod_producto, cod_sub,
                    amortizacion=noncore_total_hoja,
                    fecha_venc=dia_siguiente, numero_cuota=None,
                ))

            elif rol == "CORE":
                # Filas 1..N con amortizaciones = core_total_hoja * (F[k-1]-F[k]).
                factores = info.get("factores_eom")
                if not factores:
                    continue
                amort_vec = _amortizaciones_desde_factores(factores, core_total_hoja)
                n = len(amort_vec)
                for k in range(n):
                    # Convencion MT productivo: cuota 1 vence EOM del mes de fecha_proceso.
                    fecha_k = _fecha_eom_mas_k_meses(fecha_proceso, k)
                    filas.append(_fila_desarrollo(
                        fecha_proceso, moneda, cod_producto, cod_sub,
                        amortizacion=float(amort_vec[k]),
                        fecha_venc=fecha_k,
                        numero_cuota=k + 1,
                    ))

            elif rol == "SOFT":
                # Filas con amort=0 (GESTION CORE_SOFT) para rellenar horizonte.
                # El JSON trae el rango de cuotas (cuota_min..cuota_max).
                k_min = info.get("cuota_min")
                k_max = info.get("cuota_max")
                if k_min is None or k_max is None:
                    continue
                for k in range(int(k_min), int(k_max) + 1):
                    fecha_k = _fecha_eom_mas_k_meses(fecha_proceso, k - 1)
                    filas.append(_fila_desarrollo(
                        fecha_proceso, moneda, cod_producto, cod_sub,
                        amortizacion=0.0,
                        fecha_venc=fecha_k,
                        numero_cuota=k,
                    ))
            else:
                raise ValueError(f"Rol desconocido: {rol!r}")

    # --- Filas agregadas R13 al final del DESARROLLO ---
    # Convencion MT productivo: por cada subproducto R13 (_NONCORE y _CORE) de
    # cada producto, se emite una fila donde CODIGO_PRODUCTO == CODIGO_SUBPRODUCTO,
    # con la amortizacion TOTAL del grupo, fecha = fecha_proceso + 1 dia y sin
    # NUMERO_CUOTA. Orden: R13_Cta_Cte -> R13_Cta_Vta -> R13_AGD -> R13_AGI,
    # dentro de cada bloque NONCORE primero, CORE despues.
    for hoja in ["R13_Cta_Cte", "R13_Cta_Vta", "R13_AGD", "R13_AGI"]:
        cfg_hoja = _HOJAS[hoja]
        prod = cfg_hoja["producto_modelo"]
        moneda = cfg_hoja["moneda"]
        saldo_total = float(flujo_por_prod.get(prod, 0.0))
        core_total = saldo_total * factor_core_r13
        noncore_total = saldo_total - core_total

        # NONCORE
        sub_nc = next((s for s, rol in cfg_hoja["orden_subproductos"] if rol == "NONCORE"), None)
        if sub_nc is not None:
            filas.append(_fila_desarrollo(
                fecha_proceso, moneda,
                cod_producto=sub_nc, cod_subproducto=sub_nc,
                amortizacion=noncore_total,
                fecha_venc=dia_siguiente,
                numero_cuota=None,
            ))
        # CORE
        sub_c = next((s for s, rol in cfg_hoja["orden_subproductos"] if rol == "CORE"), None)
        if sub_c is not None:
            filas.append(_fila_desarrollo(
                fecha_proceso, moneda,
                cod_producto=sub_c, cod_subproducto=sub_c,
                amortizacion=core_total,
                fecha_venc=dia_siguiente,
                numero_cuota=None,
            ))

    tabla = pd.DataFrame(filas)
    tabla = tabla[_COLS_DESARROLLO]
    return tabla


# ===========================================================================
# 3. RESUMEN
# ===========================================================================

def calcular_resumen(tabla: pd.DataFrame) -> pd.DataFrame:
    """Resumen por (CODIGO_PRODUCTO x CODIGO_SUBPRODUCTO): flujo, min/max fecha."""
    df = tabla.copy()
    df["FECHA_PAGO"] = pd.to_datetime(df["FECHA_PAGO"], errors="coerce")
    out = (
        df.groupby(["CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO"], as_index=False)
          .agg(
              FLUJO_MO=("AMORTIZACION", "sum"),
              MIN_FECHA_PAGO=("FECHA_PAGO", "min"),
              MAX_FECHA_PAGO=("FECHA_PAGO", "max"),
              N_FILAS=("AMORTIZACION", "size"),
          )
    )
    return out


# ===========================================================================
# 4. EJECUCION
# ===========================================================================

def ejecutar_modelo(fecha_proceso: datetime, factor_core_r13: float = 0.70) -> bool:
    """Entry point estandar. Retorna True/False segun exito."""
    try:
        print("\n" + "=" * 60)
        print("INICIO - MODELO SSV (version EOM)")
        print(f"Fecha de proceso: {fecha_proceso:%d-%m-%Y}")
        print("=" * 60 + "\n")

        print("[1/3] Cargando balance y factores EOM...")
        balance_agg = cargar_datos_balance(fecha_proceso)
        factores_eom = cargar_factores_eom()
        print(f"      OK factores: hoja {list(factores_eom['bloques'].keys())}")

        print("\n[2/3] Construyendo DESARROLLO...")
        tabla = construir_desarrollo_eom(balance_agg, factores_eom, fecha_proceso,
                                         factor_core_r13=factor_core_r13)
        resumen = calcular_resumen(tabla)
        print(f"      OK DESARROLLO: {len(tabla):,} filas | grupos: {len(resumen)}")

        print("\n[3/3] Guardando xlsx...")
        # Renombrar headers al estilo MT productivo (con espacios) para que
        # el mapeo a BigQuery sea identico al del XLSM heredado.
        tabla_out = tabla.rename(columns=_RENOMBRE_COLS_MT)
        formatos = {
            "FECHA PROCESO":           "dd-mm-yyyy",
            "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
            "FECHA PAGO":              "dd-mm-yyyy",
            "FECHA_REPRICING":         "dd-mm-yyyy",
            "MIN_FECHA_PAGO":          "dd-mm-yyyy",
            "MAX_FECHA_PAGO":          "dd-mm-yyyy",
        }
        guardar_excel(
            ruta_archivo=RUTA_OUTPUT_MODELO,
            hojas={
                "DESARROLLO":   tabla_out,
                "RESUMEN_HIST": resumen,
            },
            formatos_columnas=formatos,
        )
        print(f"      OK guardado en: {RUTA_OUTPUT_MODELO}")

        print("\n" + "=" * 60)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("=" * 60)
        return True

    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR EN EL MODELO SSV (EOM): {exc}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Uso: python -m RF_Modelo_MR_SSV.mr_ssv_eom YYYY-MM-DD")
        sys.exit(1)
    try:
        _fecha = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{sys.argv[1]}' incorrecto.")
        sys.exit(1)
    _exito = ejecutar_modelo(_fecha)
    sys.exit(0 if _exito else 1)
