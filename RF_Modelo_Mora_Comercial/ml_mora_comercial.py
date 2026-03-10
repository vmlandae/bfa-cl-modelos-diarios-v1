
import pandas as pd
import numpy as np
import os
import datetime
import yaml
from pathlib import Path
import sys
from core.excel_output import guardar_excel


# #  # Para una ejecucion directa del script
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr  # Configuración de rutas del proyecto

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)



# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
RUTA_INTERFAZ_DE_DATOS = cr.resolver_ruta(config_ext['modelos']['ml_mora_comercial']['interfaz_datos_input'])
RUTA_PARAMETOS_MORA_COMERCIAL = cr.resolver_ruta(config_ext['modelos']['ml_mora_comercial']['excel_parametros_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_mora_comercial']['excel_output'])


def lectura_parametros_modelo():
    factores_mora = pd.read_excel(RUTA_PARAMETOS_MORA_COMERCIAL, sheet_name="FACTORES_MORA", dtype={"FACTOR_MORA_COMERCIAL": "float"})
    matriz_mora_comercial = pd.read_excel(RUTA_PARAMETOS_MORA_COMERCIAL, sheet_name="MATRIZ_COMERCIAL")
    factores_globales_mora = pd.read_excel(RUTA_PARAMETOS_MORA_COMERCIAL, sheet_name="FACTORES_GLOBALES").iloc[0,0]
    return factores_mora, matriz_mora_comercial.iloc[:366,:366], factores_globales_mora

def lectura_interfaz_de_datos(fecha_t: datetime.datetime)-> pd.DataFrame:
    from procesamiento_datos_input.cache_tablas import leer_interfaz_con_cache

    interfaz_t = leer_interfaz_con_cache(
        ruta_red=RUTA_INTERFAZ_DE_DATOS,
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
    )

    subproductos_validos_sel = [
        "80", "82"
    ]

    return interfaz_t[((interfaz_t['SISTEMA'] == "SEL") & (interfaz_t['CODIGO_PRODUCTO'] == "150001") & 
                       (interfaz_t['CODIGO_SUBPRODUCTO'].isin(subproductos_validos_sel)))].reset_index(drop=True).copy()


def calcular_flujos_estimados_mora(data: pd.DataFrame,
                           fecha_t: datetime.datetime,
                           matriz_mora: pd.DataFrame,
                           factor_mora: float,
                           factor_global: float) -> pd.DataFrame:
    """
    Calcula estimaciones de flujos de caja considerando probabilidades de mora.
    
    Esta función procesa los flujos de amortización e interés de una cartera de créditos,
    aplicando modelos de mora basados en matrices de transición y factores de ajuste
    para generar proyecciones de flujos futuros.
    
    Args:
        data (pd.DataFrame): DataFrame con información de créditos que debe incluir las columnas:
                           'AMORTIZACION', 'INTERES', 'FECHA_VENCIMIENTO_CUOTA'
        fecha_t (datetime.datetime): Fecha base de proceso para los cálculos (fecha T)
        matriz_mora (pd.DataFrame): Matriz de transición de mora (366x366) con probabilidades
                                  de pago por día. Cada fila representa un día después de T,
                                  cada columna representa la probabilidad de pago en ese día.
        factor_mora (float): Factor multiplicador para ajustar flujos de mora vigente
                           (aplicado sobre flujos vencidos en los últimos 180 días)
        factor_global (float): Factor multiplicador global aplicado a todos los flujos
                             proyectados (factor de garantía/cobertura)
    
    Returns:
        pd.DataFrame: DataFrame con flujos estimados que incluye las siguientes columnas:
                     - FECHA_VENCIMIENTO_CUOTA_MODELO: Fechas de proyección (T+1 a T+366)
                     - FECHA_VENCIMIENTO_CUOTA: Fecha original de vencimiento (si aplica)
                     - FLUJO_MO, AMORTIZACION_MO, INTERES_MO: Flujos originales agrupados
                     - FLUJO_MODELO_MO, AMORTIZACION_MODELO_MO, INTERES_MODELO_MO: Flujos ajustados por matriz de mora
                     - FLUJO_MORA_VIGENTE_MO, AMORTIZACION_MORA_VIGENTE_MO, INTERES_MORA_VIGENTE_MO: Ajustes por mora vigente
    
    Notes:
        - Los flujos vencidos se consideran hasta 180 días hacia atrás desde fecha_t
        - Los flujos posteriores al horizonte de proyección se consolidan en el último día
        - Se aplica factor_global a las proyecciones y factor_mora a los vencidos
    
    """
    # Procesar amortización
    data_amort = data.copy()
    data_amort['AMORTIZACION_MO'] = data_amort['AMORTIZACION']
    data_amort_grouped = data_amort.groupby(['FECHA_VENCIMIENTO_CUOTA'], as_index=False)["AMORTIZACION_MO"].sum()
    
    # Procesar interés
    data_int = data.copy()
    data_int['INTERES_MO'] = data_int['INTERES']
    data_int_grouped = data_int.groupby(['FECHA_VENCIMIENTO_CUOTA'], as_index=False)["INTERES_MO"].sum()
    
    # Crear fechas modelo
    lst_fechas_venc = [fecha_t + datetime.timedelta(days=i) for i in range(1, len(matriz_mora) + 1)]
    df_fechas_venc = pd.DataFrame(lst_fechas_venc, columns=['FECHA_VENCIMIENTO_CUOTA_MODELO'])
    
    # Merge con amortización
    df_fechas_amort = df_fechas_venc.merge(data_amort_grouped, how='left',
                                          left_on='FECHA_VENCIMIENTO_CUOTA_MODELO',
                                          right_on='FECHA_VENCIMIENTO_CUOTA')
    df_fechas_amort['AMORTIZACION_MO'] = df_fechas_amort['AMORTIZACION_MO'].fillna(0)
    
    # Merge con interés
    df_fechas_int = df_fechas_venc.merge(data_int_grouped, how='left',
                                        left_on='FECHA_VENCIMIENTO_CUOTA_MODELO',
                                        right_on='FECHA_VENCIMIENTO_CUOTA')
    df_fechas_int['INTERES_MO'] = df_fechas_int['INTERES_MO'].fillna(0)
    
    # Combinar ambos DataFrames
    flujo_estimado = df_fechas_amort.merge(df_fechas_int[['FECHA_VENCIMIENTO_CUOTA_MODELO', 'INTERES_MO']], 
                                          on='FECHA_VENCIMIENTO_CUOTA_MODELO')
    
    # Cálculos para amortización
    suma_amortizacion_mo = data_amort_grouped[
        data_amort_grouped['FECHA_VENCIMIENTO_CUOTA'] > df_fechas_venc["FECHA_VENCIMIENTO_CUOTA_MODELO"].iloc[-1]
    ]["AMORTIZACION_MO"].sum()
    
    suma_amortizacion_mo_vencido = data_amort_grouped[
        (data_amort_grouped['FECHA_VENCIMIENTO_CUOTA'] < fecha_t) &
        ((data_amort_grouped['FECHA_VENCIMIENTO_CUOTA'] - fecha_t).dt.days >= -180)
    ]['AMORTIZACION_MO'].sum()
    
    # Cálculos para interés
    suma_interes_mo = data_int_grouped[
        data_int_grouped['FECHA_VENCIMIENTO_CUOTA'] > df_fechas_venc["FECHA_VENCIMIENTO_CUOTA_MODELO"].iloc[-1]
    ]["INTERES_MO"].sum()
    
    suma_interes_mo_vencido = data_int_grouped[
        (data_int_grouped['FECHA_VENCIMIENTO_CUOTA'] < fecha_t) &
        ((data_int_grouped['FECHA_VENCIMIENTO_CUOTA'] - fecha_t).dt.days >= -180)
    ]['INTERES_MO'].sum()
    
    # Aplicar matriz de mora
    flujo_estimado['AMORTIZACION_MODELO_MO'] = np.dot(flujo_estimado['AMORTIZACION_MO'].values, matriz_mora.values) * factor_global
    flujo_estimado['INTERES_MODELO_MO'] = np.dot(flujo_estimado['INTERES_MO'].values, matriz_mora.values) * factor_global
    
    # Agregar fila final
    nueva_fila = pd.DataFrame({
        'FECHA_VENCIMIENTO_CUOTA_MODELO': [df_fechas_venc["FECHA_VENCIMIENTO_CUOTA_MODELO"].iloc[-1] + datetime.timedelta(days=1)],
        'AMORTIZACION_MO': [suma_amortizacion_mo],
        'INTERES_MO': [suma_interes_mo],
        'AMORTIZACION_MODELO_MO': [suma_amortizacion_mo * factor_global],
        'INTERES_MODELO_MO': [suma_interes_mo * factor_global],
    })
    
    flujo_estimado = pd.concat([flujo_estimado, nueva_fila], ignore_index=True)
    
    # Calcular mora vigente
    flujo_estimado['AMORTIZACION_MORA_VIGENTE_MO'] = factor_mora * suma_amortizacion_mo_vencido
    flujo_estimado['INTERES_MORA_VIGENTE_MO'] = factor_mora * suma_interes_mo_vencido

    flujo_estimado['FLUJO_MO'] = flujo_estimado['AMORTIZACION_MO'] + flujo_estimado['INTERES_MO']
    flujo_estimado['FLUJO_MODELO_MO'] = flujo_estimado['AMORTIZACION_MODELO_MO'] + flujo_estimado['INTERES_MODELO_MO']
    flujo_estimado['FLUJO_MORA_VIGENTE_MO'] = flujo_estimado['AMORTIZACION_MORA_VIGENTE_MO'] + flujo_estimado['INTERES_MORA_VIGENTE_MO']
    flujo_estimado = flujo_estimado[['FECHA_VENCIMIENTO_CUOTA_MODELO', 'FECHA_VENCIMIENTO_CUOTA', 
                                               'FLUJO_MO','AMORTIZACION_MO', 'INTERES_MO', 
                                               'FLUJO_MODELO_MO','AMORTIZACION_MODELO_MO', 'INTERES_MODELO_MO', 'FLUJO_MORA_VIGENTE_MO','AMORTIZACION_MORA_VIGENTE_MO', 'INTERES_MORA_VIGENTE_MO']]
    
    return flujo_estimado


def procesamiento_y_guardado(fecha_t: datetime.datetime,
                             interfaz_de_datos_t: pd.DataFrame
                             )-> None:

    print("      • Preparando datos comerciales...")
    comercial = interfaz_de_datos_t
    
    print("      • Cargando parámetros del modelo...")
    factor_mora_comercial, matriz_mora_comercial, fg_comercial = lectura_parametros_modelo()
    print(f"        - Factor Global Comercial: {fg_comercial:.4f}")

    print("      • Calculando flujos estimados de mora...")
    flujo_estimado_iter = calcular_flujos_estimados_mora(
        data=comercial,
        fecha_t=fecha_t,
        matriz_mora=matriz_mora_comercial,
        factor_mora=factor_mora_comercial,
        factor_global=fg_comercial)

    registros = len(flujo_estimado_iter)

    tabla_desarrollo_tmp = {
        "FECHA_PROCESO": [fecha_t] * registros,
        "CODIGO_EMPRESA": [np.nan] * registros,
        "OPERACION": [np.nan] * registros,
        "COD_ACT/PAS": ["ACT"] * registros,
        "MONEDA_ORIGEN": ["CLP"] * registros,
        "MONEDA_COMPENSACION": ["CLP"] * registros,
        "COMPENSACION": [np.nan] * registros,
        "CODIGO_PRODUCTO": ["ML_C46_MORA_CREDITO_COMERCIAL"] * registros,
        "CODIGO_SUBPRODUCTO": ["ML_C46_MORA_CREDITO_COMERCIAL_SELLERS"] * registros,
        "FECHA_CREACION": [np.nan] * registros,
        "NUMERO_CUOTA": [np.nan] * registros,
        "FECHA_INICIO_CUOTA": [np.nan] * registros,
        "FECHA_VENCIMIENTO_CUOTA": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "FECHA_PAGO": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "FECHA_REPRICING": flujo_estimado_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
        "AMORTIZACION": flujo_estimado_iter['AMORTIZACION_MODELO_MO'] + flujo_estimado_iter['AMORTIZACION_MORA_VIGENTE_MO'],
        "INTERES": flujo_estimado_iter['INTERES_MODELO_MO'] + flujo_estimado_iter['INTERES_MORA_VIGENTE_MO'],
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


    flujo_estimado_iter["PRODUCTO"] = "COMERCIAL"
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
    print(f"        - Guardando hoja 'DETALLE_FLUJOS' con {len(flujo_estimado_iter):,} registros")
    guardar_excel(
        ruta_archivo=RUTA_OUTPUT_MODELO,
        hojas={
            "DESARROLLO": tabla_desarrollo,
            "DETALLE_FLUJOS": flujo_estimado_iter[["FECHA_PROCESO","PRODUCTO",'FECHA_VENCIMIENTO_CUOTA_MODELO', 'FECHA_VENCIMIENTO_CUOTA', 
                                                'FLUJO_MO','AMORTIZACION_MO', 'INTERES_MO', 
                                                'FLUJO_MODELO_MO','AMORTIZACION_MODELO_MO', 'INTERES_MODELO_MO', 
                                                'FLUJO_MORA_VIGENTE_MO','AMORTIZACION_MORA_VIGENTE_MO', 'INTERES_MORA_VIGENTE_MO']],
        },
        formatos_columnas=formatos_excel,
    )

    # print("      • Respaldando archivo en carpeta de ejecuciones...")
    # ut.copia_archivo_en_ruta(RUTA_OUTPUT_MODELO,
    #                          cr.EJECUCIONES_ML_MORA_COMERCIAL,
    #                          Path(RUTA_OUTPUT_MODELO).stem + ".xlsm",
    #                          agregar_fecha=True)


def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo de mora comercial.
    Esta función es llamada por el orquestador y encapsula toda la lógica necesaria.
    
    Args:
        fecha_proceso (datetime.datetime): Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso de error
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO MORA COMERCIAL")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")

        print("[1/3] Leyendo datos de interfaz...")
        interfaz_de_datos_comercial_t = lectura_interfaz_de_datos(fecha_proceso)
        
        # Validar que los datos no estén vacíos
        if interfaz_de_datos_comercial_t.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros en la interfaz de datos para esta fecha.")
        
        print(f"      ✓ Datos leídos exitosamente - {len(interfaz_de_datos_comercial_t):,} registros encontrados")

        print("\n[2/3] Procesando información y calculando estimaciones...")
        procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_comercial_t)
        
        print("\n[3/3] Proceso completado:")
        print("      ✓ Cálculos realizados")
        print("      ✓ Archivos guardados")
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO MORA COMERCIAL:")
        print(f"   {str(e)}")
        print("\n" + "="*50)
        print("PROCESO TERMINADO CON ERRORES")
        print("="*50)
        return False


# --- Bloque de Ejemplo de Uso ---
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
        sys.exit(1)
    
    fecha_proceso_str = sys.argv[1]

    # fecha_proceso_str = "2025-12-24"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Usar la nueva función ejecutar_modelo
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)







