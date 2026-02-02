import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml
import sys
import bfa_cl_utilidades as ut
import math
from scipy.stats import norm
from pathlib import Path

# Configuración de importación para ejecución directa
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importación de módulos internos
from config import config_rutas as cr  # Configuración de rutas del proyecto


# Carga de configuración desde archivo YAML
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
ARCHIVO_INPUT = cr.resolver_ruta(config_ext['modelos']['ml_lc']['ms_access_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_lc']['excel_output'])
RUTA_PARAMETROS_LC = cr.resolver_ruta(config_ext['modelos']['ml_lc']['excel_parametros_modelo_input'])

def cargar_datos_balance(fecha_t: datetime) -> pd.DataFrame:
    """
    Carga los datos de balance desde la base de datos de gestión.
    """
    print("      • Ejecutando consulta de datos de balance...")
    
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
        AND RF_BD_Gestion_RL.Fec_Pro = #{}#
    GROUP BY
        RF_BD_Gestion_RL.Fec_Pro,
        RF_BD_Gestion_RL.Cod_A_P,
        RF_BD_Gestion_RL.Moneda,
        RF_BD_Gestion_RL.Cod_Pro,
        RF_BD_Gestion_RL.Cod_Sub_Pro
    HAVING
        1 = 1
        AND RF_BD_Gestion_RL.Cod_Sub_Pro = 'LINEA DE CREDITO'
    ORDER BY
        RF_BD_Gestion_RL.Cod_Sub_Pro DESC
    """.format(fecha_t.strftime('%Y-%m-%d'))
    
    data = ut.lectura_datos_ms_access(ARCHIVO_INPUT, query)
    data = ut.estandariza_nombre_columnas_dataframe(data)

    # Mapear códigos de producto del modelo
    data["COD_PRO_MODELO"] = np.where((data["COD_SUB_PRO"] == "LINEA DE CREDITO") & (data["MONEDA"] == "CLP"), "LC_CLP", None)
    
    print(f"        - Datos de balance cargados: {len(data):,} registros")
    print(f"        - Productos encontrados: {data['COD_PRO_MODELO'].value_counts().to_dict()}")
    print("          ✓ Datos de balance procesados exitosamente")

    return data

def cargar_parametros() -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """
    Carga los parámetros del modelo desde archivos Excel.
    Incluye factores de decay rate y parámetros de core vigente.
    """
    print("      • Leyendo parámetros del modelo...")
    
    # Cargar parámetros de decay rate
    parametros_modelo = pd.read_excel(RUTA_PARAMETROS_LC, sheet_name="FACTORES")
    

    return parametros_modelo


def cargar_ml_lc_egreso(fecha_proceso: datetime):
    print("      • Cargando datos de egresos LC...")
    ml_lc_egreso = pd.read_excel(RUTA_PARAMETROS_LC, sheet_name="LC_EGRESO")
    ml_lc_egreso
    ml_lc_egreso['FECHA_PROCESO'] = fecha_proceso
    ml_lc_egreso['FECHA_VENCIMIENTO_CUOTA'] = ml_lc_egreso['FECHA_PROCESO'] + pd.to_timedelta(ml_lc_egreso['FECHA_INICIO_CUOTA'], unit='D')
    ml_lc_egreso['FECHA_PAGO'] = ml_lc_egreso['FECHA_VENCIMIENTO_CUOTA']
    ml_lc_egreso['FECHA_REPRICING'] = ml_lc_egreso['FECHA_VENCIMIENTO_CUOTA']
    print(f"        - {len(ml_lc_egreso):,} registros de egreso procesados")
    print("          ✓ Datos de egreso LC procesados exitosamente")
    return ml_lc_egreso
    

def procesar_datos_iniciales(fecha_proceso: datetime) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Carga y procesa los datos iniciales del modelo.
    Combina datos de balance con parámetros del modelo.
    
    Args:
        fecha_proceso: Fecha de procesamiento
        
    Returns:
        Tuple con (datos_modelo, dap_contractual, dap_contractual_agrupado)
    """
    
    # Cargar datos base
    balance_input = cargar_datos_balance(fecha_proceso)

    # Cargar parámetros y hacer merge
    parametros_modelo = cargar_parametros()
    
    
    datos_modelo = balance_input.merge(
        parametros_modelo[['COD_PRO_MODELO','GAMMA_1','DELTA_1', 'GAMMA_2', 'DELTA_2', 'DECAY_RATE','DECAY_RATE_ACURRACY']],
        on='COD_PRO_MODELO',
        how='left'
    )
    
    
    return datos_modelo



def calculadora_mu_tenor(fecha: datetime):
    """
    Crea una función wrapper para calcular mu_tenor con fecha_proceso fija.
    
    Args:
        fecha_proceso: Fecha base que permanece constante
        
    Returns:
        Función que calcula mu_tenor solo variando fecha_tenor
    """
    primer_dia_mes = fecha.replace(day=1)
    ultimo_dia_mes = ut.ultimo_dia_del_mes(fecha)

    
    numerador = (fecha - primer_dia_mes).days
    denominador = (ultimo_dia_mes - primer_dia_mes).days

    return numerador / denominador
    

def calculo_estimacion_modelo(datos_modelo: pd.DataFrame, fecha_proceso: datetime, n_iteraciones: int = 1095) -> pd.DataFrame:
    print("      • Iniciando cálculo de estimaciones del modelo...")
    print(f"        - Número de iteraciones configurado: {n_iteraciones:,}")

    for producto in datos_modelo['COD_PRO_MODELO'].unique():
        print(f"\n        - Procesando producto: {producto}")
        datos_producto = datos_modelo[datos_modelo['COD_PRO_MODELO'] == producto].copy()
        
        if datos_producto.empty:
            raise ValueError(f"No hay datos para {producto} en los datos del modelo.")

        gamma_1 = datos_producto['GAMMA_1'].values[0]
        delta_1 = datos_producto['DELTA_1'].values[0]
        gamma_2 = datos_producto['GAMMA_2'].values[0]
        delta_2 = datos_producto['DELTA_2'].values[0] 
        decay_rate = datos_producto['DECAY_RATE'].values[0]
        decay_rate_acurracy = datos_producto['DECAY_RATE_ACURRACY'].values[0]
        flujo_total_mo = datos_producto['FLUJO_MO'].values[0]
        z_95 = norm.ppf(0.95)

        print(f"          • Parámetros del modelo cargados:")
        print(f"            - Flujo total MO: {flujo_total_mo:,.2f}")
        print(f"            - Gamma_1: {gamma_1:.6f}, Delta_1: {delta_1:.6f}")
        print(f"            - Gamma_2: {gamma_2:.6f}, Delta_2: {delta_2:.6f}")
        print(f"            - Decay Rate: {decay_rate:.6f}")


        mu_hoy = calculadora_mu_tenor(fecha_proceso)
        factor_mensual_hoy = np.exp(gamma_1 * math.cos(2 * math.pi * 1 * mu_hoy)+ delta_1 * math.sin(2 * math.pi * 1 * mu_hoy))
        factor_bisemanal_hoy = np.exp(gamma_2 * math.cos(2 * math.pi * 2 * mu_hoy)+ delta_2 * math.sin(2 * math.pi * 2 * mu_hoy))

        factor_decaimiento = np.maximum(0, decay_rate + z_95 * decay_rate_acurracy)
        
        print(f"          • Factores base calculados:")
        print(f"            - Factor mensual hoy: {factor_mensual_hoy:.6f}")
        print(f"            - Factor bisemanal hoy: {factor_bisemanal_hoy:.6f}")
        print(f"            - Factor decaimiento: {factor_decaimiento:.6f}")
        
        proyeccion_modelo_lst = []
        tenor_lst = []
        # tenor_lst.append(fecha_proceso)
        for i in range(1, n_iteraciones + 1):
            fecha_tenor = fecha_proceso + timedelta(days=i)
            mu_tenor = calculadora_mu_tenor(fecha_tenor)
            factor_mensual_tenor = np.exp(gamma_1 * math.cos(2 * math.pi * 1 * mu_tenor) + delta_1 * math.sin(2 * math.pi * 1 * mu_tenor))
            factor_bisemanal_tenor = np.exp(gamma_2 * math.cos(2 * math.pi * 2 * mu_tenor) + delta_2 * math.sin(2 * math.pi * 2 * mu_tenor))

            factor_mensual = factor_mensual_tenor / factor_mensual_hoy
            factor_bisemanal = factor_bisemanal_tenor / factor_bisemanal_hoy

            ratio_dinamicas = factor_mensual * factor_bisemanal
            ratio_vintage = np.exp(-factor_decaimiento * i)

            ratio_modelo = ratio_dinamicas * ratio_vintage

            proyeccion_modelo_lst.append(ratio_modelo * flujo_total_mo)
            tenor_lst.append(fecha_tenor)
        
        print(f"          ✓ Proyecciones calculadas para {len(proyeccion_modelo_lst):,} períodos")
        
        print("          • Calculando saldos del modelo...")
        saldos_modelo = []
        for j in range(len(proyeccion_modelo_lst)):
            if j == 0:
                saldo = flujo_total_mo - proyeccion_modelo_lst[j]
            else:
                # Resto: diferencia con el elemento anterior
                saldo = proyeccion_modelo_lst[j-1] - proyeccion_modelo_lst[j]
            saldos_modelo.append(saldo)
        
        # Agregar el último valor: diferencia entre suma del vector y flujo_total_mo
        suma_saldos = sum(saldos_modelo)
        diferencia_final = flujo_total_mo - suma_saldos
        saldos_modelo.append(diferencia_final)
        tenor_lst.append(fecha_proceso + timedelta(days=n_iteraciones + 1))
        
        print(f"          ✓ {len(saldos_modelo):,} saldos calculados")
        print(f"          ✓ Producto {producto} procesado exitosamente")
                     
    return pd.DataFrame({
        "FECHA_VENCIMIENTO": tenor_lst,
        "SALDO_MODELO_POS": saldos_modelo},
        columns=["FECHA_VENCIMIENTO","SALDO_MODELO_POS",])


def tabla_desarrollo_modelo(datos_modelo: pd.DataFrame, fecha_proceso: datetime) -> pd.DataFrame:
    """
    Genera la tabla de desarrollo del modelo.
    
    Args:
        datos_modelo: Datos procesados del modelo
        fecha_proceso: Fecha de procesamiento
        
    Returns:
        DataFrame con la tabla de desarrollo del modelo
    """
    print("      • Generando tabla de desarrollo del modelo...")
    
    saldos_modelo = calculo_estimacion_modelo(datos_modelo, fecha_proceso)
    
    print("      • Aplicando clasificaciones y códigos...")
    saldos_modelo["COD_ACT/PAS"] =np.where(saldos_modelo["SALDO_MODELO_POS"] >= 0, "ACT", "PAS")
    saldos_modelo["CODIGO_PRODUCTO"] =np.where(saldos_modelo["SALDO_MODELO_POS"] >= 0, "ML_C46_Linea_de_Credito_Ingreso_Ajustado", "ML_C46_Linea_de_Credito_Egreso_Ajustado")
    saldos_modelo["CODIGO_SUBPRODUCTO"] =np.where(saldos_modelo["SALDO_MODELO_POS"] >= 0, "ML_C46_Linea_de_Credito_Ingreso_Ajustado", "ML_C46_Linea_de_Credito_Egreso_Ajustado")
    saldos_modelo["AMORTIZACION"] = saldos_modelo["SALDO_MODELO_POS"].abs()
    num_registros = len(saldos_modelo)

    print(f"        - Registros de ingreso (ACT): {len(saldos_modelo[saldos_modelo['COD_ACT/PAS'] == 'ACT']):,}")
    print(f"        - Registros de egreso (PAS): {len(saldos_modelo[saldos_modelo['COD_ACT/PAS'] == 'PAS']):,}")

    tabla_desarrollo_ml_egreso = cargar_ml_lc_egreso(fecha_proceso)

    print("      • Construyendo tabla final de desarrollo...")
    tabla_desarrollo = pd.DataFrame({
    "FECHA_PROCESO": [fecha_proceso] * num_registros,
    "CODIGO_EMPRESA": [1] * num_registros,
    "OPERACION": [np.nan] * num_registros,
    "COD_ACT/PAS": saldos_modelo["COD_ACT/PAS"],
    "MONEDA_ORIGEN": ['CLP']* num_registros,
    "MONEDA_COMPENSACION": ["CLP"] * num_registros,
    "COMPENSACION": ["E"] * num_registros,
    "CODIGO_PRODUCTO": saldos_modelo["CODIGO_PRODUCTO"],
    "CODIGO_SUBPRODUCTO": saldos_modelo["CODIGO_SUBPRODUCTO"],
    "FECHA_CREACION": [np.nan] * num_registros,
    "NUMERO_CUOTA": [np.nan] * num_registros,
    "FECHA_INICIO_CUOTA": [np.nan] * num_registros,
    "FECHA_VENCIMIENTO_CUOTA": saldos_modelo["FECHA_VENCIMIENTO"],
    "FECHA_PAGO": saldos_modelo["FECHA_VENCIMIENTO"],
    "FECHA_REPRICING": saldos_modelo["FECHA_VENCIMIENTO"],
    "AMORTIZACION": saldos_modelo["AMORTIZACION"],
    "INTERES": [np.nan] * num_registros,
    "INTERES_DEVENGADO": [np.nan] * num_registros,
    "VP_AMORTIZACION": [np.nan] * num_registros,
    "VP_INTERES": [np.nan] * num_registros,
    "FACTOR_DE_RIESGO": [np.nan] * num_registros,
    "TIPO_CUOTA": [1] * num_registros,
    "AREA_NEGOCIO": ["BALANCE TASAS"] * num_registros,
    "CODIGO_EJECUTIVO": [np.nan] * num_registros,
    "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * num_registros,
    "CLASIFICACION_CONTABLE": ["HTM"] * num_registros,
    "TIPO_TASA": [1] * num_registros,
    "INDEXADOR": [np.nan] * num_registros,
    "TASA": [np.nan] * num_registros,
    "TASA_CF": [np.nan] * num_registros,
    "SPREAD": [np.nan] * num_registros,
    })

    tabla_desarrollo_final= pd.concat([tabla_desarrollo_ml_egreso, tabla_desarrollo], ignore_index=True)
    
    print(f"        - Tabla final generada con {len(tabla_desarrollo_final):,} registros")
    print("          ✓ Tabla de desarrollo completada exitosamente")
    
    return tabla_desarrollo_final


def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """
    Ejecuta el modelo de línea de crédito.
    
    Args:
        fecha_proceso: Fecha de procesamiento
        
    Returns:
        bool: Indica si la ejecución fue exitosa
    """
    try:
        print("\n" + "="*60)
        print("INICIO DEL PROCESO - MODELO LÍNEA DE CRÉDITO")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*60 + "\n")

        print("[1/3] Procesando datos iniciales del modelo...")
        datos_modelo = procesar_datos_iniciales(fecha_proceso)
        
        # Validar que los datos no estén vacíos
        if datos_modelo.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros de líneas de crédito para esta fecha.")
        
        print("      ✓ Datos iniciales procesados correctamente\n")

        print("[2/3] Generando tabla de desarrollo del modelo...")
        tabla_desarrollo = tabla_desarrollo_modelo(datos_modelo, fecha_proceso)
        print("      ✓ Tabla de desarrollo generada exitosamente\n")

        print("[3/3] Guardando resultados en Excel...")
        formatos_excel = {
            "FECHA_PROCESO": "dd-mm-yyyy",
            "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
            "FECHA_PAGO": "dd-mm-yyyy",
            "FECHA_REPRICING": "dd-mm-yyyy"
        }
        
        print("        - Actualizando archivo principal...")
        ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                             nombre_hoja="DESARROLLO",
                             datos=tabla_desarrollo,
                             formatos_columnas=formatos_excel
                             )
        print("          ✓ Archivo principal actualizado")
        
        print("\n" + "="*60)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print(f"Total de registros procesados: {len(tabla_desarrollo):,}")
        print("="*60)
        
        return True

    except Exception as e:
        print("\nERROR EN EL MODELO LÍNEA DE CRÉDITO:")
        print(f"   {str(e)}")
        print("\n" + "="*60)
        print("PROCESO TERMINADO CON ERRORES")
        print("="*60)
        return False

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
        sys.exit(1)
    
    fecha_proceso_str = sys.argv[1]

    # fecha_proceso_str = "2026-01-30"

    try:
        fecha_proceso = datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)