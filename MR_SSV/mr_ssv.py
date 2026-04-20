import datetime
import pandas as pd
import numpy as np
import sys
import os
import pythoncom

# =============================================================================
# BLOQUE DE CONFIGURACIÓN DE RUTAS DEL PROYECTO - NO MODIFICAR
# Este bloque busca la carpeta raíz del proyecto (la que contiene 'HERRAMIENTAS')
# y la añade al path de Python para que los módulos personalizados se encuentren.
# =============================================================================
try:
    # 1. Obtener la ruta del directorio donde se ejecuta este script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Iniciar la búsqueda de la carpeta 'HERRAMIENTAS' subiendo de nivel
    project_root = current_dir
    while not os.path.isdir(os.path.join(project_root, 'HERRAMIENTAS')):
        parent_dir = os.path.dirname(project_root)

        # 3. Condición de seguridad para evitar un bucle infinito si no se encuentra
        if parent_dir == project_root:
            raise FileNotFoundError("No se pudo encontrar la carpeta 'HERRAMIENTAS' en ninguna ruta superior.")

        project_root = parent_dir

    # 4. Añadir la ruta raíz encontrada al path de Python
    if project_root not in sys.path:
        sys.path.insert(0, project_root)  # Usamos insert(0, ...) para darle prioridad

    # 5. Importar las herramientas ahora que la ruta está configurada
    import HERRAMIENTAS.utilidades_bfal as ut

    print(f"Módulos 'HERRAMIENTAS' cargados correctamente desde: {project_root}")

except (FileNotFoundError, ModuleNotFoundError) as e:
    print(f"ERROR CRÍTICO AL CONFIGURAR EL ENTORNO: {e}")
    print("El script no puede continuar. Revisa la estructura de carpetas.")
    sys.exit(1)  # Termina la ejecución si no se puede configurar el entorno


# =============================================================================
# FIN DEL BLOQUE DE CONFIGURACIÓN
# =============================================================================

# --- CONSTANTES DE CONFIGURACIÓN ---
# Mover rutas y valores fijos a constantes mejora la mantenibilidad.
RUTA_BASE_CARTERAS = r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Carteras\INTERFAZ_DATOS\RF_Base_Carteras_Completa.accdb"
RUTA_PARAMETROS_SSV = r"\\vmdvorak\Riesgo Financiero2\RF_PROYECTOS\METODOLOGIAS\PROCESOS_DIARIOS_MODELOS\MANUALES\MODELOS\MR_SSV\parametros_ssv.xlsx"
RUTA_SALDOS_CORE = r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Resultados\Precios de Transferencia\saldos_core.xlsx"
RUTA_OUTPUT_MODELO = r"\\vmdvorak\Riesgo Financiero2\RF_PROYECTOS\METODOLOGIAS\PROCESOS_DIARIOS_MODELOS\MANUALES\MODELOS\MR_SSV\mt_ssv_local_cc.XLSM"
FACTOR_CORE_R13 = 0.70


# --- FUNCIONES DE CARGA DE DATOS ---

def cargar_datos_balance() -> pd.DataFrame:
    """
    Carga y pre-procesa los datos de balance desde la base de datos MS Access.
    La consulta SQL ha sido optimizada
    :return: None
    """
    query = """
    SELECT
        RF_BD_Gestion_RL.Fec_Pro,
        RF_BD_Gestion_RL.Cod_A_P,
        RF_BD_Gestion_RL.Moneda,
        RF_BD_Gestion_RL.Cod_Pro,
        RF_BD_Gestion_RL.Cod_Sub_Pro,
        SUM(RF_BD_Gestion_RL.Cap_Amort + RF_BD_Gestion_RL.Int_Total_Cont) AS FLUJO_MO,
        SUM(RF_BD_Gestion_RL.Cap_Amort) AS AMORTIZACION_MO,
        SUM(RF_BD_Gestion_RL.Int_Total_Cont) AS INTERES_MO
    FROM
        RF_BD_Gestion_RL
    WHERE
        1 = 1
    GROUP BY
        RF_BD_Gestion_RL.Fec_Pro,
        RF_BD_Gestion_RL.Cod_A_P,
        RF_BD_Gestion_RL.Moneda,
        RF_BD_Gestion_RL.Cod_Pro,
        RF_BD_Gestion_RL.Cod_Sub_Pro
    HAVING
        1 = 1
        AND RF_BD_Gestion_RL.Cod_Sub_Pro = 'DAP'
        OR RF_BD_Gestion_RL.Cod_Sub_Pro = 'Cta. Corriente'
        OR RF_BD_Gestion_RL.Cod_Sub_Pro = 'Cta. vista'
        OR RF_BD_Gestion_RL.Cod_Pro = 'Cta. Ahorro'
        OR RF_BD_Gestion_RL.Cod_Sub_Pro = 'LINEA DE CREDITO'
    ORDER BY
        RF_BD_Gestion_RL.Cod_Sub_Pro DESC
    """
    data = ut.lectura_datos_ms_access(RUTA_BASE_CARTERAS, query)
    return ut.estandariza_nombre_columnas_dataframe(data)


def cargar_parametros_modelo() -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """
    Carga todos los parámetros necesarios para el modelo desde archivos Excel.
    :return: None
    """
    base_cuotas_core_gestion_ssv = pd.read_excel(RUTA_PARAMETROS_SSV, sheet_name="CUOTAS_SSV")
    base_distr_core_r13_ssv = pd.read_excel(RUTA_PARAMETROS_SSV, sheet_name="DISTR_CORE_SSV_R13")

    p_modelo_nmd = pd.read_excel(RUTA_SALDOS_CORE, sheet_name="CORE_VIGENTE")

    renombres = {
        'CTA_CTE_CLP': 'CTA_CTE', 'CTA_VTA_CLP': 'CTA_VTA',
        'DAP_CLP': 'DAP', 'AGD_UF': 'AGD', 'AGI_UF': 'AGI'
    }
    p_modelo_nmd.rename(columns=renombres, inplace=True)

    p_modelo_nmd = (
        p_modelo_nmd.T
        .reset_index(drop=False)
        .rename(columns={0: "MONTO_CORE_GESTION_MO", "index": "COD_SUB_PRO_MODELO"})
    )
    excluir = ['FECHA', 'FECHA_ACTUALIZACION']
    p_modelo_nmd = p_modelo_nmd[~p_modelo_nmd['COD_SUB_PRO_MODELO'].isin(excluir)].reset_index(drop=True)
    p_codigos_productos = {
        "CTA_CTE": {
            "COD_PRO_R13": "MT_R13_CTA. CORRIENTE", "COD_SUB_PRO_R13": "MT_R13_CTA. CORRIENTE PERSONAS_CORE",
            "COD_PRO_GESTION": "MT_CTA. CORRIENTE", "COD_SUB_PRO_GESTION": "CTA. CORRIENTE PERSONAS_CORE_CORE",
            "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. CORRIENTE PERSONAS_NONCORE",
            "COD_SUB_PRO_NON_CORE_GESTION": "CTA. CORRIENTE PERSONAS"
        },
        "CTA_VTA": {
            "COD_PRO_R13": "MT_R13_CTA. VISTA", "COD_SUB_PRO_R13": "MT_R13_CTA. VISTA_CORE",
            "COD_PRO_GESTION": "MT.CTA. VISTA", "COD_SUB_PRO_GESTION": "CTA. VISTA_CORE_CORE",
            "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. VISTA_NONCORE", "COD_SUB_PRO_NON_CORE_GESTION": "CTA. VISTA"
        },
        "AGD": {
            "COD_PRO_R13": "MT_R13_CTA. AHORRO", "COD_SUB_PRO_R13": "MT_R13_CTA. AHORRO G.DIF_CORE",
            "COD_PRO_GESTION": "MT_CTA. AHORRO", "COD_SUB_PRO_GESTION": "CTA. AHORRO G.DIF_CORE_CORE",
            "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. AHORRO G.DIF_NONCORE",
            "COD_SUB_PRO_NON_CORE_GESTION": "CTA. AHORRO G.DIF"
        },
        "AGI": {
            "COD_PRO_R13": "MT_R13_CTA. AHORRO", "COD_SUB_PRO_R13": "MT_R13_CTA. AHORRO G.INC_CORE",
            "COD_PRO_GESTION": "MT_CTA. AHORRO", "COD_SUB_PRO_GESTION": "CTA. AHORRO G.INC_CORE_CORE",
            "COD_SUB_PRO_NON_CORE_R13": "MT_R13_CTA. AHORRO G.INC_NONCORE",
            "COD_SUB_PRO_NON_CORE_GESTION": "CTA. AHORRO G.INC"
        }
    }

    return p_modelo_nmd, p_codigos_productos, base_cuotas_core_gestion_ssv, base_distr_core_r13_ssv



def procesar_modelo(fecha_proceso: datetime.datetime) -> None:
    """
    Orquesta el proceso completo: carga, procesamiento, validación y guardado.
    :param fecha_proceso:
    :return:
    """

    # --- 1. CARGA DE DATOS ---
    print("Cargando datos de balance y parámetros...")
    data_balance = cargar_datos_balance()
    p_modelo_nmd, p_codigos_productos, base_cuotas_core_gestion_ssv, base_distr_core_r13_ssv = cargar_parametros_modelo()

    # --- 2. PRE-PROCESAMIENTO ---
    # Mapeo de productos usando np.select para mayor eficiencia y legibilidad
    condiciones = [
        data_balance["COD_SUB_PRO"] == "CTA. VISTA",
        data_balance["COD_SUB_PRO"] == "CTA. CORRIENTE",
        data_balance["COD_SUB_PRO"] == "CTA. AHORRO GIRO DIFERIDO",
        data_balance["COD_SUB_PRO"] == "CTA. AHORRO INCONDICIONAL"
    ]
    asignacion = ["CTA_VTA", "CTA_CTE", "AGD", "AGI"]
    data_balance["COD_SUB_PRO_MODELO"] = np.select(condiciones, asignacion, default=None)

    data_balance.dropna(subset=["COD_SUB_PRO_MODELO"], inplace=True)
    data_balance.reset_index(drop=True, inplace=True)

    # --- 3. PROCESAMIENTO PRINCIPAL (Vectorizado) ---
    print("Procesando modelo...")
    data_fecha_proceso = pd.merge(
        p_modelo_nmd,
        data_balance[["MONEDA", "COD_SUB_PRO_MODELO", "FLUJO_MO", "AMORTIZACION_MO", "INTERES_MO"]],
        on="COD_SUB_PRO_MODELO",
        how="inner"
    )
    data_fecha_proceso["MONTO_CORE_R13_MO"] = np.minimum(data_fecha_proceso["FLUJO_MO"] * FACTOR_CORE_R13,
                                                         data_fecha_proceso["MONTO_CORE_GESTION_MO"])

    tabla_desarrollo_gestion = pd.DataFrame()
    tabla_desarrollo_r13 = pd.DataFrame()
    for i in data_fecha_proceso["COD_SUB_PRO_MODELO"]:

        # GESTION
        cuotas = base_cuotas_core_gestion_ssv[base_cuotas_core_gestion_ssv["COD_SUB_PRO_MODELO"] == i]["N_CUOTA"].max()
        monto_core_gestion = base_cuotas_core_gestion_ssv[base_cuotas_core_gestion_ssv["COD_SUB_PRO_MODELO"] == i][
            "AMORTIZACION"].sum()
        monto_non_core_gestion = np.maximum(
            data_fecha_proceso[data_fecha_proceso["COD_SUB_PRO_MODELO"] == i]["FLUJO_MO"].iloc[0] - monto_core_gestion,
            0)
        moneda_sub_producto = \
            base_cuotas_core_gestion_ssv[base_cuotas_core_gestion_ssv["COD_SUB_PRO_MODELO"] == i]["MONEDA"].iloc[0]
        flujos_core_gestion = base_cuotas_core_gestion_ssv[
            base_cuotas_core_gestion_ssv["COD_SUB_PRO_MODELO"] == i].reset_index(drop=True)

        data_non_core_temp = {
            "FECHA_PROCESO": [fecha_proceso],
            "CODIGO_EMPRESA": [1],
            "OPERACION": [np.nan],
            "COD_ACT/PAS": ["PAS"],
            "MONEDA_ORIGEN": [moneda_sub_producto],
            "MONEDA_COMPENSACION": [moneda_sub_producto],
            "COMPENSACION": [np.nan],
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_PRO_GESTION"]],
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_NON_CORE_GESTION"]],
            "FECHA_CREACION": [np.nan],
            "NUMERO_CUOTA": [np.nan],
            "FECHA_INICIO_CUOTA": [np.nan],
            "FECHA_VENCIMIENTO_CUOTA": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_PAGO": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_REPRICING": [fecha_proceso + datetime.timedelta(days=1)],
            "AMORTIZACION": monto_non_core_gestion,
            "INTERES": [np.nan],
            "INTERES_DEVENGADO": [np.nan],
            "VP_AMORTIZACION": [np.nan],
            "VP_INTERES": [np.nan],
            "FACTOR_DE_RIESGO": [np.nan],
            "TIPO_CUOTA": [1],
            "AREA_NEGOCIO": ["BALANCE TASAS"],
            "CODIGO_EJECUTIVO": [np.nan],
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"],
            "CLASIFICACION_CONTABLE": ["HTM"],
            "TIPO_TASA": [1],
            "INDEXADOR": [np.nan],
            "TASA_CF": [np.nan],
            "SPREAD": [np.nan]
        }
        data_core_temp = {
            "FECHA_PROCESO": [fecha_proceso] * cuotas,
            "CODIGO_EMPRESA": [1] * cuotas,
            "OPERACION": [np.nan] * cuotas,
            "COD_ACT/PAS": ["PAS"] * cuotas,
            "MONEDA_ORIGEN": [moneda_sub_producto] * cuotas,
            "MONEDA_COMPENSACION": [moneda_sub_producto] * cuotas,
            "COMPENSACION": [np.nan] * cuotas,
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_PRO_GESTION"]] * cuotas,
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_GESTION"]] * cuotas,
            "FECHA_CREACION": [np.nan] * cuotas,
            "NUMERO_CUOTA": flujos_core_gestion["N_CUOTA"],
            "FECHA_INICIO_CUOTA": [np.nan] * cuotas,
            "FECHA_VENCIMIENTO_CUOTA": flujos_core_gestion["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_PAGO": flujos_core_gestion["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_REPRICING": flujos_core_gestion["FECHA_VENCIMIENTO_CUOTA"],
            "AMORTIZACION": flujos_core_gestion["AMORTIZACION"],
            "INTERES": [np.nan] * cuotas,
            "INTERES_DEVENGADO": [np.nan] * cuotas,
            "VP_AMORTIZACION": [np.nan] * cuotas,
            "VP_INTERES": [np.nan] * cuotas,
            "FACTOR_DE_RIESGO": [np.nan] * cuotas,
            "TIPO_CUOTA": [1] * cuotas,
            "AREA_NEGOCIO": ["BALANCE TASAS"] * cuotas,
            "CODIGO_EJECUTIVO": [np.nan] * cuotas,
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * cuotas,
            "CLASIFICACION_CONTABLE": ["HTM"] * cuotas,
            "TIPO_TASA": [1] * cuotas,
            "INDEXADOR": [np.nan] * cuotas,
            "TASA_CF": [np.nan] * cuotas,
            "SPREAD": [np.nan] * cuotas
        }

        tabla_desarrollo_gestion = pd.concat(
            [tabla_desarrollo_gestion, pd.DataFrame(data_core_temp), pd.DataFrame(data_non_core_temp)],
            ignore_index=True)

        # NORMATIVO R13
        cuotas_r13 = base_distr_core_r13_ssv[base_distr_core_r13_ssv["COD_SUB_PRO_MODELO"] == i]["N_CUOTA"].max()
        monto_core_r13 = data_fecha_proceso[data_fecha_proceso["COD_SUB_PRO_MODELO"] == i]["MONTO_CORE_R13_MO"].iloc[0]
        monto_non_core_r13 = np.maximum(
            data_fecha_proceso[data_fecha_proceso["COD_SUB_PRO_MODELO"] == i]["FLUJO_MO"].iloc[0] - monto_core_r13, 0)
        # decay_rate_r13 = data_fecha_proceso[data_fecha_proceso["COD_SUB_PRO"] == i]["DECAYRATE"].iloc[0]
        moneda_sub_producto = data_fecha_proceso[data_fecha_proceso["COD_SUB_PRO_MODELO"] == i]["MONEDA"].iloc[0]

        fechas_vencimiento_cuotas = []
        fecha_i = fecha_proceso
        for j in range(1, cuotas_r13 + 1):
            if j == 1:
                fecha_f = ut.ultimo_dia_del_mes(fecha_i.replace(day=1))
                if fecha_f == ut.ultimo_dia_del_mes(fecha_f):
                    fecha_f = ut.ultimo_dia_del_mes(ut.agrega_meses_a_fecha(fecha_f, 1))
            else:
                fecha_f = ut.ultimo_dia_del_mes(ut.agrega_meses_a_fecha(fecha_i, 1))

            fechas_vencimiento_cuotas.append(fecha_f)
            fecha_i = fecha_f

        flujos_core_r13 = base_distr_core_r13_ssv[base_distr_core_r13_ssv["COD_SUB_PRO_MODELO"] == i].reset_index(
            drop=True)

        flujos_core_r13["FECHA_VENCIMIENTO_CUOTA"] = fechas_vencimiento_cuotas

        data_non_core_1_temp = {
            "FECHA_PROCESO": [fecha_proceso],
            "CODIGO_EMPRESA": [1],
            "OPERACION": [np.nan],
            "COD_ACT/PAS": ["PAS"],
            "MONEDA_ORIGEN": [moneda_sub_producto],
            "MONEDA_COMPENSACION": [moneda_sub_producto],
            "COMPENSACION": [np.nan],
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_PRO_R13"]],
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_NON_CORE_R13"]],
            "FECHA_CREACION": [np.nan],
            "NUMERO_CUOTA": [np.nan],
            "FECHA_INICIO_CUOTA": [np.nan],
            "FECHA_VENCIMIENTO_CUOTA": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_PAGO": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_REPRICING": [fecha_proceso + datetime.timedelta(days=1)],
            "AMORTIZACION": monto_non_core_r13,
            "INTERES": [np.nan],
            "INTERES_DEVENGADO": [np.nan],
            "VP_AMORTIZACION": [np.nan],
            "VP_INTERES": [np.nan],
            "FACTOR_DE_RIESGO": [np.nan],
            "TIPO_CUOTA": [1],
            "AREA_NEGOCIO": ["BALANCE TASAS"],
            "CODIGO_EJECUTIVO": [np.nan],
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"],
            "CLASIFICACION_CONTABLE": ["HTM"],
            "TIPO_TASA": [1],
            "INDEXADOR": [np.nan],
            "TASA_CF": [np.nan],
            "SPREAD": [np.nan]
        }
        data_non_core_2_temp = {
            "FECHA_PROCESO": [fecha_proceso],
            "CODIGO_EMPRESA": [1],
            "OPERACION": [np.nan],
            "COD_ACT/PAS": ["PAS"],
            "MONEDA_ORIGEN": [moneda_sub_producto],
            "MONEDA_COMPENSACION": [moneda_sub_producto],
            "COMPENSACION": [np.nan],
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_NON_CORE_R13"]],
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_NON_CORE_R13"]],
            "FECHA_CREACION": [np.nan],
            "NUMERO_CUOTA": [np.nan],
            "FECHA_INICIO_CUOTA": [np.nan],
            "FECHA_VENCIMIENTO_CUOTA": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_PAGO": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_REPRICING": [fecha_proceso + datetime.timedelta(days=1)],
            "AMORTIZACION": monto_non_core_r13,
            "INTERES": [np.nan],
            "INTERES_DEVENGADO": [np.nan],
            "VP_AMORTIZACION": [np.nan],
            "VP_INTERES": [np.nan],
            "FACTOR_DE_RIESGO": [np.nan],
            "TIPO_CUOTA": [1],
            "AREA_NEGOCIO": ["BALANCE TASAS"],
            "CODIGO_EJECUTIVO": [np.nan],
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"],
            "CLASIFICACION_CONTABLE": ["HTM"],
            "TIPO_TASA": [1],
            "INDEXADOR": [np.nan],
            "TASA_CF": [np.nan],
            "SPREAD": [np.nan]
        }

        data_core_2_temp = {
            "FECHA_PROCESO": [fecha_proceso],
            "CODIGO_EMPRESA": [1],
            "OPERACION": [np.nan],
            "COD_ACT/PAS": ["PAS"],
            "MONEDA_ORIGEN": [moneda_sub_producto],
            "MONEDA_COMPENSACION": [moneda_sub_producto],
            "COMPENSACION": [np.nan],
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_R13"]],
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_R13"]],
            "FECHA_CREACION": [np.nan],
            "NUMERO_CUOTA": [np.nan],
            "FECHA_INICIO_CUOTA": [np.nan],
            "FECHA_VENCIMIENTO_CUOTA": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_PAGO": [fecha_proceso + datetime.timedelta(days=1)],
            "FECHA_REPRICING": [fecha_proceso + datetime.timedelta(days=1)],
            "AMORTIZACION": monto_core_r13,
            "INTERES": [np.nan],
            "INTERES_DEVENGADO": [np.nan],
            "VP_AMORTIZACION": [np.nan],
            "VP_INTERES": [np.nan],
            "FACTOR_DE_RIESGO": [np.nan],
            "TIPO_CUOTA": [1],
            "AREA_NEGOCIO": ["BALANCE TASAS"],
            "CODIGO_EJECUTIVO": [np.nan],
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"],
            "CLASIFICACION_CONTABLE": ["HTM"],
            "TIPO_TASA": [1],
            "INDEXADOR": [np.nan],
            "TASA_CF": [np.nan],
            "SPREAD": [np.nan]
        }
        data_core_temp = {
            "FECHA_PROCESO": [fecha_proceso] * cuotas_r13,
            "CODIGO_EMPRESA": [1] * cuotas_r13,
            "OPERACION": [np.nan] * cuotas_r13,
            "COD_ACT/PAS": ["PAS"] * cuotas_r13,
            "MONEDA_ORIGEN": [moneda_sub_producto] * cuotas_r13,
            "MONEDA_COMPENSACION": [moneda_sub_producto] * cuotas_r13,
            "COMPENSACION": [np.nan] * cuotas_r13,
            "CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_PRO_R13"]] * cuotas_r13,
            "CODIGO_SUBPRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_R13"]] * cuotas_r13,
            "FECHA_CREACION": [np.nan] * cuotas_r13,
            "NUMERO_CUOTA": flujos_core_r13["N_CUOTA"],
            "FECHA_INICIO_CUOTA": [np.nan] * cuotas_r13,
            "FECHA_VENCIMIENTO_CUOTA": flujos_core_r13["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_PAGO": flujos_core_r13["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_REPRICING": flujos_core_r13["FECHA_VENCIMIENTO_CUOTA"],
            "AMORTIZACION": flujos_core_r13["DISTR_CORE_R13"] * monto_core_r13,
            "INTERES": [np.nan] * cuotas_r13,
            "INTERES_DEVENGADO": [np.nan] * cuotas_r13,
            "VP_AMORTIZACION": [np.nan] * cuotas_r13,
            "VP_INTERES": [np.nan] * cuotas_r13,
            "FACTOR_DE_RIESGO": [np.nan] * cuotas_r13,
            "TIPO_CUOTA": [1] * cuotas_r13,
            "AREA_NEGOCIO": ["BALANCE TASAS"] * cuotas_r13,
            "CODIGO_EJECUTIVO": [np.nan] * cuotas_r13,
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * cuotas_r13,
            "CLASIFICACION_CONTABLE": ["HTM"] * cuotas_r13,
            "TIPO_TASA": [1] * cuotas_r13,
            "INDEXADOR": [np.nan] * cuotas_r13,
            "TASA_CF": [np.nan] * cuotas_r13,
            "SPREAD": [np.nan] * cuotas_r13
        }
        tabla_desarrollo_r13 = pd.concat([tabla_desarrollo_r13, pd.DataFrame(data_core_temp),
                                          pd.DataFrame(data_core_2_temp),
                                          pd.DataFrame(data_non_core_1_temp),
                                          pd.DataFrame(data_non_core_2_temp)], ignore_index=True)

    tabla_desarrollo_modelo = pd.concat([tabla_desarrollo_r13, tabla_desarrollo_gestion], ignore_index=True)

    # --- 4. GUARDAR RESULTADO DEL MODELO ---
    print("Guardando resultados del modelo...")
    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy", "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy", "FECHA_REPRICING": "dd-mm-yyyy"
    }

    ut.cargar_datos_xlsm(RUTA_OUTPUT_MODELO, "DESARROLLO", tabla_desarrollo_modelo, formatos_excel)


    # --- 5. VALIDACIONES (Optimizadas con GroupBy) ---
    df_tmp = tabla_desarrollo_modelo.copy()
    resumen_control = pd.DataFrame()
    for cod_sub in df_tmp["CODIGO_PRODUCTO"].unique():
        df_filtrado = df_tmp[df_tmp["CODIGO_PRODUCTO"] == cod_sub]
        for cod_sub_pro in df_filtrado["CODIGO_SUBPRODUCTO"].unique():
            df_filtrado_2 = df_filtrado[df_filtrado["CODIGO_SUBPRODUCTO"] == cod_sub_pro]
            resumen_tmp = {
                "CODIGO_PRODUCTO": "MDL_" + str(cod_sub),
                "COD_SUB_PRO": "MDL_" + str(cod_sub_pro),
                "FLUJO_MO": df_filtrado_2["AMORTIZACION"].sum(),
                # "PMP": ut.calculo_plazo_medio_permanencia((df_filtrado["FECHA_PAGO"] - fecha_proceso).dt.days,df_filtrado["AMORTIZACION"],365),
                "PMP": ut.calculo_plazo_medio_permanencia(df_filtrado_2["NUMERO_CUOTA"], df_filtrado_2["AMORTIZACION"],
                                                          12),
                "MIN_FECHA_PAGO": df_filtrado_2["FECHA_PAGO"].min(),
                "MAX_FECHA_PAGO": df_filtrado_2["FECHA_PAGO"].max(),
            }

            resumen_control = pd.concat([resumen_control, pd.DataFrame([resumen_tmp])], ignore_index=True)

    ut.cargar_datos_xlsm(RUTA_OUTPUT_MODELO, "RESUMEN_HIST", resumen_control)

    df_tmp = data_fecha_proceso.copy()
    df_tmp["COD_SUB_PRO_MODELO"] = "INPT_" + df_tmp["COD_SUB_PRO_MODELO"]
    resumen_control = pd.concat([resumen_control, df_tmp], ignore_index=True)

    ut.cargar_datos_xlsm(RUTA_OUTPUT_MODELO, "DATOS", resumen_control)

    print("Enviando resultados...")

    ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "control_y_correo_diario")

    # ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "actualiza_dinamica_control")
    # # ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "enviar_correo_Outlook")
    # ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "control_comparacion_dia")

    # #--- PARA EJECUCION EN PARALELO ---#
    # pythoncom.CoInitialize()  # Inicializa COM en el hilo
    #
    # try:
    #     ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "actualiza_dinamica_control")
    #     ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO,"enviar_correo_Outlook")
    #     ut.ejecutar_macro_excel(RUTA_OUTPUT_MODELO, "control_comparacion_dia")
    #     pass
    # finally:
    #     pythoncom.CoUninitialize()  # Libera COM al finalizar


    print("Proceso finalizado.")


def main():
    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
        sys.exit(1)

    fecha_proceso_str = sys.argv[1]
    # fecha_proceso_str = "2025-09-30"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    print(f"Iniciando modelo para la fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
    procesar_modelo(fecha_proceso=fecha_proceso)
    print("Modelo finalizado con éxito desde Python.")


if __name__ == "__main__":
    main()