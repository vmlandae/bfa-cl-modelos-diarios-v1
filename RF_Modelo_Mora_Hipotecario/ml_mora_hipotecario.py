import pandas as pd
import numpy as np
import os
import datetime
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut

# #  # Para una ejecucion directa del script
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr  # Configuración de rutas del proyecto

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)


# Configuración de rutas
RUTA_INTERFAZ_DE_DATOS = Path(config_ext['modelos']['ml_mora_hipotecario']['interfaz_datos_input'])
RUTA_PARAMETOS_MORA_HIPOTECARIO = Path(config_ext['modelos']['ml_mora_hipotecario']['excel_parametros_input'])
RUTA_OUTPUT_MODELO = Path(config_ext['modelos']['ml_mora_hipotecario']['excel_output'])
    

def lectura_parametros_modelo():
    factores_mora = pd.read_excel(RUTA_PARAMETOS_MORA_HIPOTECARIO, sheet_name="FACTORES_MORA", dtype={"FACTOR_MORA_HIPOTECARIO": "float"})
    matriz_mora_hipotecario = pd.read_excel(RUTA_PARAMETOS_MORA_HIPOTECARIO, sheet_name="MATRIZ_HIPOTECARIO")
    factores_globales_mora = pd.read_excel(RUTA_PARAMETOS_MORA_HIPOTECARIO, sheet_name="FACTORES_GLOBALES").iloc[0,0]
    return factores_mora, matriz_mora_hipotecario.iloc[:366,:366], factores_globales_mora

def lectura_interfaz_de_datos(fecha_t: datetime.datetime)-> pd.DataFrame:
    columnas = ["FECHA_PROCESO", "SISTEMA", "CODIGO_SUBPRODUCTO","DESTINOCREDITO", "MONEDA_ORIGEN",
                "AMORTIZACION", "INTERES","FECHA_VENCIMIENTO_CUOTA"]

    tipos_datos = {"FECHA_PROCESO": "str", "SISTEMA": "str", "CODIGO_SUBPRODUCTO": "str", "DESTINOCREDITO": "str",
                   "MONEDA_ORIGEN": "str", "AMORTIZACION": "float",
                   "INTERES": "float","FECHA_VENCIMIENTO_CUOTA": "str",}

    ruta_t = os.path.join(RUTA_INTERFAZ_DE_DATOS, f"ProductosMercadoLiquidezGCP{fecha_t.strftime('%Y%m%d')}.txt")

    interfaz_t = pd.read_csv(ruta_t, sep=';', decimal=',', usecols=columnas, dtype=tipos_datos)

    interfaz_t['FECHA_PROCESO'] = pd.to_datetime(interfaz_t['FECHA_PROCESO'], format='%Y%m%d')
    interfaz_t['FECHA_VENCIMIENTO_CUOTA'] = pd.to_datetime(interfaz_t['FECHA_VENCIMIENTO_CUOTA'], format='%Y%m%d')


    interfaz_t['CODIGO_SUBPRODUCTO'] = interfaz_t['CODIGO_SUBPRODUCTO'].str.strip()
    interfaz_t['DESTINOCREDITO'] = interfaz_t['DESTINOCREDITO'].str.strip()
    interfaz_t['SISTEMA'] = interfaz_t['SISTEMA'].str.strip()
    return interfaz_t[interfaz_t['SISTEMA']=="HIP"].reset_index(drop=True).copy()

def calcular_flujo_estimado_mora(data: pd.DataFrame,
                                fecha_t: datetime.datetime,
                                matriz_mora: pd.DataFrame,
                                factor_mora: float,
                                factor_global: float) -> pd.DataFrame:
    """
    Calcula el flujo estimado para una cartera de créditos.

    Args:
        data: DataFrame con la información de los créditos.
        fecha_t: Fecha de proceso.
        matriz_mora: Matriz de mora para los cálculos.
        factor_mora: Factor de mora a aplicar.
        factor_global: Factor de garantía a aplicar.

    Returns:
        DataFrame con el flujo estimado calculado.
    """
    data['FLUJO_MO'] = data['AMORTIZACION'] + data['INTERES']
    data = data.groupby(['FECHA_VENCIMIENTO_CUOTA'], as_index=False)["FLUJO_MO"].sum()

    lst_fechas_venc = [fecha_t + datetime.timedelta(days=i) for i in range(1, len(matriz_mora) + 1)]
    df_fechas_venc = pd.DataFrame(lst_fechas_venc, columns=['FECHA_VENCIMIENTO_CUOTA_MODELO'])

    df_fechas_venc = df_fechas_venc.merge(data, how='left',
                                          left_on='FECHA_VENCIMIENTO_CUOTA_MODELO',
                                          right_on='FECHA_VENCIMIENTO_CUOTA')
    df_fechas_venc['FLUJO_MO'] = df_fechas_venc['FLUJO_MO'].fillna(0)

    suma_flujo_mo = data[data['FECHA_VENCIMIENTO_CUOTA'] > df_fechas_venc["FECHA_VENCIMIENTO_CUOTA_MODELO"].iloc[-1]][
        "FLUJO_MO"].sum()

    suma_flujo_mo_vencido = data[(data['FECHA_VENCIMIENTO_CUOTA'] < fecha_t) &
                                 ((data['FECHA_VENCIMIENTO_CUOTA'] - fecha_t).dt.days >= -180)]['FLUJO_MO'].sum()

    flujo_estimado = df_fechas_venc.copy()
    flujo_estimado['FLUJO_MODELO_MO'] = np.dot(df_fechas_venc['FLUJO_MO'].values, matriz_mora.values) * factor_global

    nueva_fila = pd.DataFrame({
        'FECHA_VENCIMIENTO_CUOTA_MODELO': [
            df_fechas_venc["FECHA_VENCIMIENTO_CUOTA_MODELO"].iloc[-1] + datetime.timedelta(days=1)],
        'FLUJO_MO': [suma_flujo_mo],
        'FLUJO_MODELO_MO': [suma_flujo_mo * factor_global],
    })
    flujo_estimado = pd.concat([flujo_estimado, nueva_fila], ignore_index=True)
    flujo_estimado['FLUJO_MORA_VIGENTE_MO'] = factor_mora * suma_flujo_mo_vencido

    return flujo_estimado

def procesamiento_y_guardado(fecha_t: datetime.datetime,
                             interfaz_de_datos_t: pd.DataFrame
                             )-> None:

    print("      • Preparando datos hipotecarios...")
    hipotecario = interfaz_de_datos_t
    
    print("      • Cargando parámetros del modelo...")
    factor_mora_hipotecario, matriz_mora_hipotecario, fg_hipotecario = lectura_parametros_modelo()
    print(f"        - Factor Global Hipotecario: {fg_hipotecario:.4f}")

    print("      • Calculando flujos estimados de mora...")
    flujo_estimado_iter = calcular_flujo_estimado_mora(
        data=hipotecario,
        fecha_t=fecha_t,
        matriz_mora=matriz_mora_hipotecario,
        factor_mora=factor_mora_hipotecario,
        factor_global=fg_hipotecario)

    registros = len(flujo_estimado_iter)

    tabla_desarrollo_tmp = {
        "FECHA_PROCESO": [fecha_t] * registros,
        "CODIGO_EMPRESA": [np.nan] * registros,
        "OPERACION": [np.nan] * registros,
        "COD_ACT/PAS": ["ACT"] * registros,
        "MONEDA_ORIGEN": ["CLF"] * registros,
        "MONEDA_COMPENSACION": ["CLF"] * registros,
        "COMPENSACION": [np.nan] * registros,
        "CODIGO_PRODUCTO": ["ML_C46_MORA_CREDITO_HIPOTECARIO"] * registros,
        "CODIGO_SUBPRODUCTO": ["ML_C46_MORA_CREDITO_HIPOTECARIO"] * registros,
        "FECHA_CREACION": [np.nan] * registros,
        "NUMERO_CUOTA": [np.nan] * registros,
        "FECHA_INICIO_CUOTA": [np.nan] * registros,
        "FECHA_VENCIMIENTO_CUOTA": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "FECHA_PAGO": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "FECHA_REPRICING": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "AMORTIZACION": flujo_estimado_iter['FLUJO_MODELO_MO'] + flujo_estimado_iter['FLUJO_MORA_VIGENTE_MO'],
        "INTERES": [np.nan] * registros,
        "INTERES_DEVENGADO": [np.nan] * registros,
        "VP_AMORTIZACION": [np.nan] * registros,
        "VP_INTERES": [np.nan] * registros,
        "FACTOR_DE_RIESGO": [np.nan] * registros,
        "TIPO_CUOTA": [1] * registros,
        "AREA_NEGOCIO": ["BALANCE TASAS"] * registros,
        "CODIGO_EJECUTIVO": [np.nan] * registros,
        "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * registros,
        "CLASIFICACION_CONTABLE": ["HTM"] * registros,
        "TIPO_TASA": [1] * registros,
        "INDEXADOR": [np.nan] * registros,
        "TASA": [np.nan] * registros,
        "TASA_CF": [np.nan] * registros,
        "SPREAD": [np.nan] * registros,
    }


    flujo_estimado_iter["PRODUCTO"] = "HIPOTECARIO"
    flujo_estimado_iter["FECHA_PROCESO"] = fecha_t
    tabla_desarrollo = pd.DataFrame(tabla_desarrollo_tmp)

  
    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy",
        "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy",
        "FECHA_REPRICING": "dd-mm-yyyy"
    }

    print("      • Guardando resultados en archivo Excel...")
    print(f"        - Guardando hoja 'DESARROLLO' con {len(tabla_desarrollo):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                         nombre_hoja="DESARROLLO",
                         datos=tabla_desarrollo,
                         formatos_columnas=formatos_excel
                         )
    
    print(f"        - Guardando hoja 'DETALLE_FLUJOS' con {len(flujo_estimado_iter):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                        nombre_hoja="DETALLE_FLUJOS",
                        datos=flujo_estimado_iter[["FECHA_PROCESO", "PRODUCTO", "FECHA_VENCIMIENTO_CUOTA", 
                        "FECHA_VENCIMIENTO_CUOTA_MODELO","FLUJO_MO", "FLUJO_MODELO_MO", "FLUJO_MORA_VIGENTE_MO"]],
                        formatos_columnas=formatos_excel
                        )

    # print("      • Respaldando archivo en carpeta de ejecuciones...")
    # ut.copia_archivo_en_ruta(RUTA_OUTPUT_MODELO,
    #                          str(cr.EJECUCIONES_ML_MORA_HIPOTECARIO),
    #                          Path(RUTA_OUTPUT_MODELO).stem + ".xlsm",
    #                          agregar_fecha=True)




# --- Bloque de Ejemplo de Uso ---
if __name__ == "__main__":

    # if len(sys.argv) < 2:
    #     print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
    #     sys.exit(1)
    
    # fecha_proceso_str = sys.argv[1]

    fecha_proceso_str = "2025-12-05"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    print("\n" + "="*50)
    print("INICIO DEL PROCESO - MODELO MORA HIPOTECARIO")
    print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
    print("="*50 + "\n")

    print("[1/3] Leyendo datos de interfaz...")
    interfaz_de_datos_hipotecario_t = lectura_interfaz_de_datos(fecha_proceso)
    print(f"      ✓ Datos leídos exitosamente - {len(interfaz_de_datos_hipotecario_t):,} registros encontrados")

    print("\n[2/3] Procesando información y calculando estimaciones...")
    procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_hipotecario_t)
    
    print("\n[3/3] Proceso completado:")
    print("      ✓ Cálculos realizados")
    print("      ✓ Archivos guardados")
    print("\n" + "="*50)
    print("PROCESO FINALIZADO EXITOSAMENTE")
    print("="*50)






