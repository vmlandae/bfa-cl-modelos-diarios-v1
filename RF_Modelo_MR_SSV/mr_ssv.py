"""
Modelo SSV (Saldos Sin Vencimiento) — versión productiva.

Genera la tabla de desarrollo de los productos NMD (CTA_CTE, CTA_VTA, AGD, AGI)
bajo dos vistas:

- GESTIÓN:     CORE con cuotas mensuales fijadas por metodología (hoja CUOTAS_SSV)
               + NON_CORE a +1 día con el resto del flujo.
- NORMATIVA R13: CORE distribuido con la curva DISTR_CORE_SSV_R13 (cap por
               FACTOR_CORE_R13 · flujo) + NON_CORE a +1 día + dos filas de
               agregado (CORE y NON_CORE) que replican la convención del
               reporte regulatorio.

Salida: ``RF_Modelo_MR_SSV/mr_ssv.xlsx`` con las hojas DESARROLLO, DATOS y
RESUMEN_HIST. Consumido downstream por ``cargar_output_modelos_bigquery_dly``
(tabla ``report_mr_ssv_dly``).
"""

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
# Configuración de rutas (leídas desde config_rutas_ext_y_archivos.yaml)
# ---------------------------------------------------------------------------
with open(cr.CONFIG / "config_rutas_ext_y_archivos.yaml", "r", encoding="utf-8") as _f:
    _CFG = yaml.safe_load(_f)

ARCHIVO_INPUT = cr.resolver_ruta(_CFG["modelos"]["mr_ssv"]["ms_access_input"])
RUTA_PARAMETROS_CORE = cr.resolver_ruta(_CFG["modelos"]["mr_ssv"]["excel_parametros_core_input"])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(_CFG["modelos"]["mr_ssv"]["excel_output"])

# ---------------------------------------------------------------------------
# Constantes del modelo
# ---------------------------------------------------------------------------
PRODUCTOS_SSV: list[str] = ["CTA_CTE", "CTA_VTA", "AGD", "AGI"]

# Mapeo COD_SUB_PRO (Access) → clave del modelo SSV
_MAPEO_SUB_PRO: dict[str, str] = {
    "CTA. CORRIENTE": "CTA_CTE",
    "CTA. VISTA": "CTA_VTA",
    "CTA. AHORRO GIRO DIFERIDO": "AGD",
    "CTA. AHORRO INCONDICIONAL": "AGI",
}

# Renombres del CORE vigente (Excel transpuesto) hacia las claves del modelo.
# Nota: AGD/AGI llegan con sufijo _UF en el Excel de saldos_core pero el modelo
# los utiliza como CLF.
_RENOMBRES_CORE: dict[str, str] = {
    "CTA_CTE_CLP": "CTA_CTE",
    "CTA_VTA_CLP": "CTA_VTA",
    "AGD_UF": "AGD",
    "AGI_UF": "AGI",
}

# Códigos de CODIGO_PRODUCTO / CODIGO_SUBPRODUCTO esperados por el sistema downstream.
# Se preservan tal cual en la plantilla heredada (incluida la quirk "MT.CTA. VISTA"
# con punto en lugar de guión bajo para CTA_VTA vista gestión).
P_CODIGOS_PRODUCTOS: dict[str, dict[str, str]] = {
    "CTA_CTE": {
        "COD_PRO_R13": "MT_R13_CTA. CORRIENTE",
        "COD_SUB_PRO_R13": "MT_R13_CTA. CORRIENTE PERSONAS_CORE",
        "COD_PRO_GESTION": "MT_CTA. CORRIENTE",
        "COD_SUB_PRO_GESTION": "CTA. CORRIENTE PERSONAS_CORE_CORE",
        "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. CORRIENTE PERSONAS_NONCORE",
        "COD_SUB_PRO_NON_CORE_GESTION": "CTA. CORRIENTE PERSONAS",
    },
    "CTA_VTA": {
        "COD_PRO_R13": "MT_R13_CTA. VISTA",
        "COD_SUB_PRO_R13": "MT_R13_CTA. VISTA_CORE",
        "COD_PRO_GESTION": "MT.CTA. VISTA",
        "COD_SUB_PRO_GESTION": "CTA. VISTA_CORE_CORE",
        "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. VISTA_NONCORE",
        "COD_SUB_PRO_NON_CORE_GESTION": "CTA. VISTA",
    },
    "AGD": {
        "COD_PRO_R13": "MT_R13_CTA. AHORRO",
        "COD_SUB_PRO_R13": "MT_R13_CTA. AHORRO G.DIF_CORE",
        "COD_PRO_GESTION": "MT_CTA. AHORRO",
        "COD_SUB_PRO_GESTION": "CTA. AHORRO G.DIF_CORE_CORE",
        "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. AHORRO G.DIF_NONCORE",
        "COD_SUB_PRO_NON_CORE_GESTION": "CTA. AHORRO G.DIF",
    },
    "AGI": {
        "COD_PRO_R13": "MT_R13_CTA. AHORRO",
        "COD_SUB_PRO_R13": "MT_R13_CTA. AHORRO G.INC_CORE",
        "COD_PRO_GESTION": "MT_CTA. AHORRO",
        "COD_SUB_PRO_GESTION": "CTA. AHORRO G.INC_CORE_CORE",
        "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. AHORRO G.INC_NONCORE",
        "COD_SUB_PRO_NON_CORE_GESTION": "CTA. AHORRO G.INC",
    },
}

# Columnas exactas del DESARROLLO (en el orden esperado por el cargador BQ).
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


# ===========================================================================
# 1. CARGA DE DATOS
# ===========================================================================

def cargar_datos_balance(fecha_t: datetime) -> pd.DataFrame:
    """Lee RF_BD_Gestion_RL filtrando los 4 sub-productos del modelo.

    Usa ``cache_tablas.leer_tabla_con_cache`` → parquet compartido con NMD/LC
    (evita lecturas repetidas a Access dentro de la misma corrida diaria).
    """
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    logger.info("      * Leyendo balance desde Access (o cache parquet)...")
    fecha_access = fecha_t.strftime("%Y-%m-%d")
    query_rl = (
        f"SELECT * FROM [RF_BD_Gestion_RL] "
        f"WHERE [Fec_Pro] = #{fecha_access}#"
    )
    df_rl = leer_tabla_con_cache(
        access_path=ARCHIVO_INPUT,
        nombre_tabla="RF_BD_Gestion_RL",
        fecha_proceso=fecha_t.strftime("%Y%m%d"),
        query=query_rl,
    )

    mask = df_rl["Cod_Sub_Pro"].isin(list(_MAPEO_SUB_PRO.keys()))
    df_filtered = df_rl.loc[mask].copy()

    data = df_filtered.groupby(
        ["Fec_Pro", "Cod_A_P", "Moneda", "Cod_Pro", "Cod_Sub_Pro"],
        as_index=False,
    ).agg(
        AMORTIZACION_MO=("Cap_Amort", "sum"),
        INTERES_MO=("Int_Total_Cont", "sum"),
    )
    data["FLUJO_MO"] = data["AMORTIZACION_MO"] + data["INTERES_MO"]
    data = ut.estandariza_nombre_columnas_dataframe(data)

    data["COD_SUB_PRO_MODELO"] = data["COD_SUB_PRO"].map(_MAPEO_SUB_PRO)
    data = data[data["COD_SUB_PRO_MODELO"].notna()].reset_index(drop=True)

    logger.info(f"        - Balance cargado: {len(data):,} registros")
    logger.info(
        f"        - Productos en balance: {sorted(data['COD_SUB_PRO_MODELO'].unique().tolist())}"
    )
    return data


def cargar_parametros() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    """Carga CUOTAS_SSV, DISTR_CORE_SSV_R13 y FACTORES (JSON preferido), más el
    CORE vigente desde Excel de red.

    Returns:
        (base_cuotas, base_distr_r13, parametros_core, factor_core_r13)
    """
    from procesamiento_datos_input.cargador_parametros import cargar_hojas_parametros

    logger.info("      • Leyendo parámetros del modelo...")
    hojas = cargar_hojas_parametros("mr_ssv")
    base_cuotas = hojas["CUOTAS_SSV"].copy()
    base_distr_r13 = hojas["DISTR_CORE_SSV_R13"].copy()
    factores = hojas.get("FACTORES")

    # Cuando la fuente es JSON, las fechas llegan como strings ISO; re-casteamos.
    for col in ("FECHA_VENCIMIENTO_CUOTA", "FECHA_ACTUALIZACION"):
        if col in base_cuotas.columns:
            base_cuotas[col] = pd.to_datetime(base_cuotas[col], errors="coerce")

    # FACTOR_CORE_R13: default 0.70 para compatibilidad con ejecuciones antiguas.
    factor_core_r13 = 0.70
    if factores is not None and "PARAMETRO" in factores.columns:
        fila = factores.loc[factores["PARAMETRO"] == "FACTOR_CORE_R13"]
        if not fila.empty:
            factor_core_r13 = float(fila["VALOR"].iloc[0])
    logger.info(f"        - FACTOR_CORE_R13 = {factor_core_r13}")

    # CORE vigente (Excel en red compartido con NMD).
    parametros_core = pd.read_excel(RUTA_PARAMETROS_CORE, sheet_name="CORE_VIGENTE")
    parametros_core = parametros_core.rename(columns=_RENOMBRES_CORE)
    parametros_core = (
        parametros_core.T.reset_index(drop=False)
        .rename(columns={0: "MONTO_CORE_GESTION_MO", "index": "COD_SUB_PRO_MODELO"})
    )
    parametros_core = parametros_core[
        ~parametros_core["COD_SUB_PRO_MODELO"].isin(["FECHA", "FECHA_ACTUALIZACION"])
    ]
    parametros_core = parametros_core[
        parametros_core["COD_SUB_PRO_MODELO"].isin(PRODUCTOS_SSV)
    ].reset_index(drop=True)

    logger.info(f"        - CORE vigente: {len(parametros_core)} productos")
    logger.info(
        f"        - CUOTAS_SSV: {len(base_cuotas)} filas / "
        f"DISTR_CORE_SSV_R13: {len(base_distr_r13)} filas"
    )
    return base_cuotas, base_distr_r13, parametros_core, factor_core_r13


# ===========================================================================
# 2. VALIDACIÓN
# ===========================================================================

def validar_datos_iniciales(
    balance: pd.DataFrame,
    cuotas: pd.DataFrame,
    distr_r13: pd.DataFrame,
    core: pd.DataFrame,
    fecha_proceso: datetime,
) -> None:
    """Falla temprano si faltan insumos para los 4 productos."""
    if balance.empty:
        raise ValueError(
            f"No se encontraron datos de balance para {fecha_proceso:%Y-%m-%d}. "
            "Verifique RF_BD_Gestion_RL."
        )

    productos_balance = set(balance["COD_SUB_PRO_MODELO"].unique())
    faltantes = set(PRODUCTOS_SSV) - productos_balance
    if faltantes:
        raise ValueError(f"Productos SSV ausentes en balance: {sorted(faltantes)}")

    for prod in PRODUCTOS_SSV:
        if cuotas[cuotas["COD_SUB_PRO_MODELO"] == prod].empty:
            raise ValueError(f"CUOTAS_SSV sin filas para {prod}")
        sub_r13 = distr_r13[distr_r13["COD_SUB_PRO_MODELO"] == prod]
        if sub_r13.empty:
            raise ValueError(f"DISTR_CORE_SSV_R13 sin filas para {prod}")
        suma = sub_r13["DISTR_CORE_R13"].sum()
        if abs(suma - 1.0) > 1e-6:
            raise ValueError(
                f"DISTR_CORE_SSV_R13[{prod}] no suma 1 (suma={suma:.6f})"
            )

    if core.empty:
        raise ValueError("CORE vigente vacío (saldos_core.xlsx / hoja CORE_VIGENTE).")
    productos_core = set(core["COD_SUB_PRO_MODELO"].unique())
    faltantes_core = set(PRODUCTOS_SSV) - productos_core
    if faltantes_core:
        raise ValueError(f"CORE vigente sin filas para: {sorted(faltantes_core)}")


# ===========================================================================
# 3. CONSTRUCCIÓN DE LA TABLA DE DESARROLLO
# ===========================================================================

def _generar_fechas_cuotas_r13(fecha_proceso: datetime, n_cuotas: int) -> list[datetime]:
    """Genera ``n_cuotas`` fin-de-mes consecutivos, partiendo del mes siguiente.

    Equivalente a la lógica heredada: la primera cuota siempre cae en el último
    día del mes posterior a ``fecha_proceso``. Las cuotas siguientes avanzan
    mes a mes.
    """
    fechas: list[datetime] = []
    # Primera cuota: último día del mes siguiente al de fecha_proceso
    fecha = ut.ultimo_dia_del_mes(
        ut.agrega_meses_a_fecha(ut.ultimo_dia_del_mes(fecha_proceso), 1)
    )
    fechas.append(fecha)
    for _ in range(1, n_cuotas):
        fecha = ut.ultimo_dia_del_mes(ut.agrega_meses_a_fecha(fecha, 1))
        fechas.append(fecha)
    return fechas


def _bloque_filas(
    fecha_proceso: datetime,
    moneda: str,
    cod_pro: str,
    cod_sub: str,
    amortizacion,          # escalar o array-like
    fecha_venc,            # escalar, Timestamp o array-like
    numero_cuota=None,     # None | array-like
    n: int = 1,
) -> pd.DataFrame:
    """Template para construir N filas homogéneas con la estructura DESARROLLO."""

    def _tile(val):
        """Replica un escalar a longitud n, o deja pasar array-like."""
        if hasattr(val, "__len__") and not isinstance(val, str):
            return list(val)
        return [val] * n

    return pd.DataFrame({
        "FECHA_PROCESO":            [fecha_proceso] * n,
        "CODIGO_EMPRESA":           [1] * n,
        "OPERACION":                [np.nan] * n,
        "COD_ACT/PAS":              ["PAS"] * n,
        "MONEDA_ORIGEN":            [moneda] * n,
        "MONEDA_COMPENSACION":      [moneda] * n,
        "COMPENSACION":             [np.nan] * n,
        "CODIGO_PRODUCTO":          [cod_pro] * n,
        "CODIGO_SUBPRODUCTO":       [cod_sub] * n,
        "FECHA_CREACION":           [np.nan] * n,
        "NUMERO_CUOTA":             [np.nan] * n if numero_cuota is None else _tile(numero_cuota),
        "FECHA_INICIO_CUOTA":       [np.nan] * n,
        "FECHA_VENCIMIENTO_CUOTA":  _tile(fecha_venc),
        "FECHA_PAGO":               _tile(fecha_venc),
        "FECHA_REPRICING":          _tile(fecha_venc),
        "AMORTIZACION":             _tile(amortizacion),
        "INTERES":                  [np.nan] * n,
        "INTERES_DEVENGADO":        [np.nan] * n,
        "VP_AMORTIZACION":          [np.nan] * n,
        "VP_INTERES":               [np.nan] * n,
        "FACTOR_DE_RIESGO":         [np.nan] * n,
        "TIPO_CUOTA":               [1] * n,
        "AREA_NEGOCIO":             ["BALANCE TASAS"] * n,
        "CODIGO_EJECUTIVO":         [np.nan] * n,
        "CODIGO_ESTRATEGIA":        ["BALANCE TASAS"] * n,
        "CLASIFICACION_CONTABLE":   ["HTM"] * n,
        "TIPO_TASA":                [1] * n,
        "INDEXADOR":                [np.nan] * n,
        "TASA":                     [np.nan] * n,
        "TASA_CF":                  [np.nan] * n,
        "SPREAD":                   [np.nan] * n,
    })


def construir_tabla_desarrollo(
    datos: pd.DataFrame,
    base_cuotas: pd.DataFrame,
    base_distr_r13: pd.DataFrame,
    fecha_proceso: datetime,
) -> pd.DataFrame:
    """Construye el DESARROLLO combinando GESTIÓN y R13 para los 4 productos.

    Por producto genera 6 bloques de filas (preserva la convención heredada):

    GESTIÓN:
      1. CORE: N filas con cuotas fijas de ``CUOTAS_SSV``
         (product=COD_PRO_GESTION, subproduct=COD_SUB_PRO_GESTION).
      2. NON_CORE agregado: 1 fila a +1 día
         (product=COD_PRO_GESTION, subproduct=COD_SUB_PRO_NON_CORE_GESTION,
         monto = FLUJO − CORE).

    R13:
      3. CORE distribuido: N filas fin-de-mes con ``DISTR_CORE_R13 · monto_core``
         (product=COD_PRO_R13, subproduct=COD_SUB_PRO_R13).
      4. CORE agregado 1-día (product=COD_SUB_PRO_R13, subproduct=COD_SUB_PRO_R13,
         monto = monto_core).
      5. NON_CORE bajo umbrella R13 a +1 día
         (product=COD_PRO_R13, subproduct=COD_SUB_PRO_NON_CORE_R13).
      6. NON_CORE agregado 1-día (product=COD_SUB_PRO_NON_CORE_R13 = subproduct).
    """
    frames: list[pd.DataFrame] = []
    dia_siguiente = fecha_proceso + timedelta(days=1)

    for prod in PRODUCTOS_SSV:
        codigos = P_CODIGOS_PRODUCTOS[prod]

        # Moneda tomada desde CUOTAS_SSV (canonical por producto), no desde balance.
        cuotas_prod = (
            base_cuotas[base_cuotas["COD_SUB_PRO_MODELO"] == prod]
            .reset_index(drop=True)
        )
        moneda = str(cuotas_prod["MONEDA"].iloc[0])

        fila_datos = datos[datos["COD_SUB_PRO_MODELO"] == prod].iloc[0]
        flujo = float(fila_datos["FLUJO_MO"])
        monto_core_gestion = float(cuotas_prod["AMORTIZACION"].sum())
        monto_core_r13 = float(fila_datos["MONTO_CORE_R13_MO"])
        monto_non_core_gestion = max(flujo - monto_core_gestion, 0.0)
        monto_non_core_r13 = max(flujo - monto_core_r13, 0.0)

        # --- GESTIÓN ---
        core_gestion = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_PRO_GESTION"], codigos["COD_SUB_PRO_GESTION"],
            amortizacion=cuotas_prod["AMORTIZACION"].astype(float).values,
            fecha_venc=cuotas_prod["FECHA_VENCIMIENTO_CUOTA"].values,
            numero_cuota=cuotas_prod["N_CUOTA"].values,
            n=len(cuotas_prod),
        )
        non_core_gestion = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_PRO_GESTION"], codigos["COD_SUB_PRO_NON_CORE_GESTION"],
            amortizacion=monto_non_core_gestion, fecha_venc=dia_siguiente, n=1,
        )

        # --- R13 ---
        distr_prod = (
            base_distr_r13[base_distr_r13["COD_SUB_PRO_MODELO"] == prod]
            .reset_index(drop=True)
        )
        n_cuotas_r13 = int(distr_prod["N_CUOTA"].max())
        fechas_r13 = _generar_fechas_cuotas_r13(fecha_proceso, n_cuotas_r13)
        core_r13 = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_PRO_R13"], codigos["COD_SUB_PRO_R13"],
            amortizacion=(distr_prod["DISTR_CORE_R13"].astype(float).values * monto_core_r13),
            fecha_venc=fechas_r13,
            numero_cuota=distr_prod["N_CUOTA"].values,
            n=n_cuotas_r13,
        )
        core_r13_agr = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_SUB_PRO_R13"], codigos["COD_SUB_PRO_R13"],
            amortizacion=monto_core_r13, fecha_venc=dia_siguiente, n=1,
        )
        non_core_r13 = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_PRO_R13"], codigos["COD_SUB_PRO_NON_CORE_R13"],
            amortizacion=monto_non_core_r13, fecha_venc=dia_siguiente, n=1,
        )
        non_core_r13_agr = _bloque_filas(
            fecha_proceso, moneda,
            codigos["COD_SUB_PRO_NON_CORE_R13"], codigos["COD_SUB_PRO_NON_CORE_R13"],
            amortizacion=monto_non_core_r13, fecha_venc=dia_siguiente, n=1,
        )

        # Orden heredado: primero R13, luego GESTIÓN.
        frames.extend([
            core_r13, core_r13_agr, non_core_r13, non_core_r13_agr,
            core_gestion, non_core_gestion,
        ])

    tabla = pd.concat(frames, ignore_index=True)
    # Forzar orden de columnas
    tabla = tabla[_COLS_DESARROLLO]
    return tabla


# ===========================================================================
# 4. CONTROL / RESUMEN
# ===========================================================================

def calcular_resumen_control(tabla_desarrollo: pd.DataFrame) -> pd.DataFrame:
    """Resumen por (CODIGO_PRODUCTO × CODIGO_SUBPRODUCTO): flujo, PMP, min/max fecha_pago."""
    df = tabla_desarrollo.copy()
    df["FECHA_PAGO"] = pd.to_datetime(df["FECHA_PAGO"], errors="coerce")

    resumen: list[dict] = []
    for cp in df["CODIGO_PRODUCTO"].dropna().unique():
        sub_cp = df[df["CODIGO_PRODUCTO"] == cp]
        for cs in sub_cp["CODIGO_SUBPRODUCTO"].dropna().unique():
            grp = sub_cp[sub_cp["CODIGO_SUBPRODUCTO"] == cs]
            pmp = ut.calculo_plazo_medio_permanencia(
                grp["NUMERO_CUOTA"], grp["AMORTIZACION"], 12
            )
            resumen.append({
                "CODIGO_PRODUCTO": f"MDL_{cp}",
                "COD_SUB_PRO":     f"MDL_{cs}",
                "FLUJO_MO":        float(grp["AMORTIZACION"].sum()),
                "PMP":             pmp,
                "MIN_FECHA_PAGO":  grp["FECHA_PAGO"].min(),
                "MAX_FECHA_PAGO":  grp["FECHA_PAGO"].max(),
            })
    return pd.DataFrame(resumen)


# ===========================================================================
# 5. EJECUCIÓN PRINCIPAL
# ===========================================================================

def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """Entry point estándar del orquestador. Retorna True/False según éxito."""
    try:
        print("\n" + "=" * 60)
        print("INICIO DEL PROCESO - MODELO SSV")
        print(f"Fecha de proceso: {fecha_proceso:%d-%m-%Y}")
        print("=" * 60 + "\n")

        print("[1/4] Cargando balance y parámetros...")
        balance = cargar_datos_balance(fecha_proceso)
        cuotas, distr_r13, core, factor_core_r13 = cargar_parametros()
        print("      ✓ Datos cargados\n")

        print("[2/4] Validando insumos...")
        validar_datos_iniciales(balance, cuotas, distr_r13, core, fecha_proceso)
        print("      ✓ Validación completada\n")

        print("[3/4] Construyendo tabla de desarrollo...")
        # Agregado de balance por producto (una fila por COD_SUB_PRO_MODELO).
        balance_agg = (
            balance.groupby("COD_SUB_PRO_MODELO", as_index=False)
            .agg(
                FLUJO_MO=("FLUJO_MO", "sum"),
                AMORTIZACION_MO=("AMORTIZACION_MO", "sum"),
                INTERES_MO=("INTERES_MO", "sum"),
            )
        )
        datos = balance_agg.merge(core, on="COD_SUB_PRO_MODELO", how="inner")
        datos["MONTO_CORE_R13_MO"] = np.minimum(
            datos["FLUJO_MO"] * factor_core_r13,
            datos["MONTO_CORE_GESTION_MO"],
        )
        tabla_desarrollo = construir_tabla_desarrollo(
            datos, cuotas, distr_r13, fecha_proceso
        )
        resumen_control = calcular_resumen_control(tabla_desarrollo)
        print(f"      ✓ DESARROLLO: {len(tabla_desarrollo):,} filas | "
              f"RESUMEN: {len(resumen_control)} grupos\n")

        # Hoja DATOS: resumen + inputs del modelo (prefijados INPT_ como en heredado).
        df_inputs = datos.copy()
        df_inputs["COD_SUB_PRO_MODELO"] = "INPT_" + df_inputs["COD_SUB_PRO_MODELO"].astype(str)
        hoja_datos = pd.concat([resumen_control, df_inputs], ignore_index=True)

        print("[4/4] Guardando resultados en xlsx...")
        formatos_excel = {
            "FECHA_PROCESO":           "dd-mm-yyyy",
            "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
            "FECHA_PAGO":              "dd-mm-yyyy",
            "FECHA_REPRICING":         "dd-mm-yyyy",
            "MIN_FECHA_PAGO":          "dd-mm-yyyy",
            "MAX_FECHA_PAGO":          "dd-mm-yyyy",
        }
        guardar_excel(
            ruta_archivo=RUTA_OUTPUT_MODELO,
            hojas={
                "DESARROLLO":   tabla_desarrollo,
                "DATOS":        hoja_datos,
                "RESUMEN_HIST": resumen_control,
            },
            formatos_columnas=formatos_excel,
        )
        print(f"      ✓ Archivo guardado en: {RUTA_OUTPUT_MODELO}\n")

        print("=" * 60)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("=" * 60)
        return True

    except Exception as exc:  # noqa: BLE001 - entry point del orquestador
        print("\nERROR EN EL MODELO SSV:")
        print(f"   {exc}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        print("PROCESO TERMINADO CON ERRORES")
        print("=" * 60)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Uso: python -m RF_Modelo_MR_SSV.mr_ssv YYYY-MM-DD")
        sys.exit(1)
    try:
        _fecha = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{sys.argv[1]}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)
    _exito = ejecutar_modelo(_fecha)
    sys.exit(0 if _exito else 1)
