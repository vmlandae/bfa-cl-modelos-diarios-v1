import pandas as pd
import numpy as np
import os
import datetime
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut

### Para una ejecucion directa del script
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Importar utilidades


# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
RUTA_INTERFAZ_DE_DATOS = cr.resolver_ruta(config_ext['modelos']['ml_mora_consumo']['interfaz_datos_input'])
RUTA_PARAMETOS_MORA_CONSUMO = cr.resolver_ruta(config_ext['modelos']['ml_mora_consumo']['excel_parametros_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_mora_consumo']['excel_output'])
RUTA_OUTPUT_MODELO_RENEGOCIADO = cr.resolver_ruta(config_ext['modelos']['ml_mora_consumo']['excel_output_2'])



def lectura_parametros_modelo():
    factores_mora = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="FACTORES_MORA")
    factores_globales_mora = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="FACTORES_GLOBALES")
    matriz_mora_consumo = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="MATRIZ_CONSUMO")
    matriz_mora_automotriz =  pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="MATRIZ_AUTOMOTRIZ")
    matriz_mora_refinanciado = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="MATRIZ_REFINANCIADO")
    matriz_mora_renegociado = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="MATRIZ_RENEGOCIADO")
    matriz_mora_consolidado = pd.read_excel(RUTA_PARAMETOS_MORA_CONSUMO, sheet_name="MATRIZ_CONSOLIDADO")


    lst_matrices_mora = [matriz_mora_consumo.iloc[:366,:366],
                         matriz_mora_automotriz.iloc[:366,:366],
                         matriz_mora_refinanciado.iloc[:366,:366],
                         matriz_mora_renegociado.iloc[:366,:366],
                         matriz_mora_consolidado.iloc[:366,:366]]
    lst_factores_mora = [factores_mora.iloc[:, 0],
                         factores_mora.iloc[:, 1],
                         factores_mora.iloc[:, 2],
                         factores_mora.iloc[:, 3],
                         factores_mora.iloc[:, 4]]
    lst_factores_globales_mora = [factores_globales_mora.iloc[0, 0],
                                factores_globales_mora.iloc[0, 1],
                                factores_globales_mora.iloc[0, 2],
                                factores_globales_mora.iloc[0, 3],
                                factores_globales_mora.iloc[0, 4]]
    return lst_factores_mora, lst_matrices_mora, lst_factores_globales_mora

def lectura_interfaz_de_datos(fecha_t: datetime.datetime)-> pd.DataFrame:
    from procesamiento_datos_input.cache_tablas import leer_interfaz_con_cache

    interfaz_t = leer_interfaz_con_cache(
        ruta_red=RUTA_INTERFAZ_DE_DATOS,
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
    )

    subproductos_validos_crc = [
        #"38", "80",
        #Automotriz
        "16", 
        # Consolidacion
        "27", "32", "34", "37", "42", "46",
        #Consumo
        "1", "4", "31", "33", "35", "68", "69", "71", "73", 
        "78", "81", 
        #Refinanciado
        "24", "36", "43", "75"
    ]

    subproductos_validos_rec = ["1", "4", "16", "23", 
                                "24", "27", "31", "32", 
                                "35", "37", "42", "43", 
                                "46", "100"
                                ]
    return interfaz_t[
            ((interfaz_t['SISTEMA'] == "CRC") & (interfaz_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_t['CODIGO_SUBPRODUCTO'].isin(subproductos_validos_crc))) |
            ((interfaz_t['SISTEMA'] == "REC") & (interfaz_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_t['CODIGO_SUBPRODUCTO'].isin(subproductos_validos_rec)))].reset_index(drop=True).copy()


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

    print("      • Segmentando datos por tipo de crédito...")

    subproducto_consumo_consumo = ["1", "4", "31", "33", "35", "68", "69", "71", "73", "78", "81",]
    subproducto_consumo_automotriz = ["16"]
    subproducto_consumo_refinanciado = ["24", "36", "43", "75"]
    subproducto_consumo_consolidado = ["27", "32", "34", "37", "42", "46"]
    subproducto_renegociado = ["1", "4", "16", "23", "24", "27", "31", "32", 
                               "35", "37", "42", "43", "46", "100"]

    consumo = interfaz_de_datos_t[(interfaz_de_datos_t['SISTEMA'] == "CRC")
                                  & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_consumo))].copy().reset_index(drop=True)
    automotriz = interfaz_de_datos_t[(interfaz_de_datos_t['SISTEMA'] == "CRC")
                                  & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_automotriz))].copy().reset_index(drop=True)
    refinanciado = interfaz_de_datos_t[(interfaz_de_datos_t['SISTEMA'] == "CRC")
                                  & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_refinanciado))].copy().reset_index(drop=True)
    renegociado = interfaz_de_datos_t[(interfaz_de_datos_t['SISTEMA'] == "REC")
                                  & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_renegociado))].copy().reset_index(drop=True)
    consolidado = interfaz_de_datos_t[(interfaz_de_datos_t['SISTEMA'] == "CRC")
                                  & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_consolidado))].copy().reset_index(drop=True)
    
    print(f"        - Consumo: {len(consumo):,} registros")
    print(f"        - Automotriz: {len(automotriz):,} registros")
    print(f"        - Refinanciado: {len(refinanciado):,} registros")
    print(f"        - Renegociado: {len(renegociado):,} registros")
    print(f"        - Consolidado: {len(consolidado):,} registros")
    
    print("\n      • Cargando parámetros del modelo...")
    lst_factores_mora, lst_matrices_mora, lst_factores_globales_mora = lectura_parametros_modelo()

    sub_productos_creditos_consumo = {
        0: {
            "DESCRIPCION": "CONSUMO",
            "DATA": consumo,
            "MATRIZ_MORA": lst_matrices_mora[0],
            "FACTOR_MORA": lst_factores_mora[0],
            "FG": lst_factores_globales_mora[0],
            "SUB_PRODUCTO": "CONSUMO"
        },
        1: {
            "DESCRIPCION": "AUTOMOTRIZ",
            "DATA": automotriz,
            "MATRIZ_MORA": lst_matrices_mora[1],
            "FACTOR_MORA": lst_factores_mora[1],
            "FG": lst_factores_globales_mora[1],
            "SUB_PRODUCTO": "AUTOMOTRIZ"
        },
        2: {
            "DESCRIPCION": "REFINANCIADO",
            "DATA": refinanciado,
            "MATRIZ_MORA": lst_matrices_mora[2],
            "FACTOR_MORA": lst_factores_mora[2],
            "FG": lst_factores_globales_mora[2],
            "SUB_PRODUCTO": "REFINANCIADO"
        },
        3: {
            "DESCRIPCION": "RENEGOCIADO",
            "DATA": renegociado,
            "MATRIZ_MORA": lst_matrices_mora[3],
            "FACTOR_MORA": lst_factores_mora[3],
            "FG": lst_factores_globales_mora[3],
            "SUB_PRODUCTO": "RENEGOCIADO"
        },
        4: {
            "DESCRIPCION": "CONSOLIDADO",
            "DATA": consolidado,
            "MATRIZ_MORA": lst_matrices_mora[4],
            "FACTOR_MORA": lst_factores_mora[4],
            "FG": lst_factores_globales_mora[4],
            "SUB_PRODUCTO": "CONSOLIDADO"
        },
    }

    tabla_desarrollo = pd.DataFrame()
    flujo_estimado_agrupado = pd.DataFrame()
    
    print("\n      • Procesando por tipo de crédito...")
    for sub_pord in sub_productos_creditos_consumo.keys():
        desc_producto = sub_productos_creditos_consumo[sub_pord]["DESCRIPCION"]
        print(f"        - Calculando flujos para {desc_producto}...")
        
        df_iter = sub_productos_creditos_consumo[sub_pord]["DATA"]
        matriz_mora_iter = sub_productos_creditos_consumo[sub_pord]["MATRIZ_MORA"]
        factor_mora_iter = sub_productos_creditos_consumo[sub_pord]["FACTOR_MORA"]
        fg_iter = sub_productos_creditos_consumo[sub_pord]["FG"]
        sub_producto_iter = sub_productos_creditos_consumo[sub_pord]["SUB_PRODUCTO"]
        print(f"          Factor Global {desc_producto}: {fg_iter:.4f}")

        flujo_estimado_iter = calcular_flujos_estimados_mora(
            data=df_iter,
            fecha_t=fecha_t,
            matriz_mora=matriz_mora_iter,
            factor_mora=factor_mora_iter,
            factor_global=fg_iter)
        registros = len(flujo_estimado_iter)

        tabla_desarrollo_tmp = {
            "FECHA_PROCESO": [fecha_t] * registros,
            "CODIGO_EMPRESA": [np.nan] * registros,
            "OPERACION": [np.nan] * registros,
            "COD_ACT/PAS": ["ACT"] * registros,
            "MONEDA_ORIGEN": ["CLP"] * registros,
            "MONEDA_COMPENSACION": ["CLP"] * registros,
            "COMPENSACION": [np.nan] * registros,
            "CODIGO_PRODUCTO": ["ML_C46_MORA_CREDITO_" + str(sub_producto_iter)] * registros,
            "CODIGO_SUBPRODUCTO": ["ML_C46_MORA_CREDITO_" + str(sub_producto_iter)] * registros,
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


        flujo_estimado_iter["PRODUCTO"] = str(sub_producto_iter)
        flujo_estimado_iter["FECHA_PROCESO"] = fecha_t
        flujo_estimado_agrupado = pd.concat([flujo_estimado_agrupado, flujo_estimado_iter], ignore_index=True)
        tabla_desarrollo = pd.concat([tabla_desarrollo, pd.DataFrame(tabla_desarrollo_tmp)], ignore_index=True)




    tabla_desarrollo_output = tabla_desarrollo[tabla_desarrollo["CODIGO_SUBPRODUCTO"] != "ML_C46_MORA_CREDITO_RENEGOCIADO"].copy()
    tabla_desarrollo_output["CODIGO_PRODUCTO"] = "ML_C46_MORA_CREDITO_CONSUMO"
    tabla_desarrollo_output["CODIGO_SUBPRODUCTO"] = "ML_C46_MORA_CREDITO_CONSUMO"

    tabla_desarrollo_renegociado_output = tabla_desarrollo[tabla_desarrollo["CODIGO_SUBPRODUCTO"] == "ML_C46_MORA_CREDITO_RENEGOCIADO"].copy()

    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy",
        "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy",
        "FECHA_REPRICING": "dd-mm-yyyy"
    }

    print("\n      • Guardando resultados en archivo Excel...")

    print(f"        - Guardando hoja 'DESARROLLO_MODELO' con {len(tabla_desarrollo):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                         nombre_hoja="DESARROLLO_MODELO",
                         datos=tabla_desarrollo[tabla_desarrollo["CODIGO_SUBPRODUCTO"] != "ML_C46_MORA_CREDITO_RENEGOCIADO"],
                         formatos_columnas=formatos_excel
                         )
    print(f"        - Guardando hoja 'DESARROLLO_MODELO_RENEGOCIADO' con {len(tabla_desarrollo):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO_RENEGOCIADO,
                         nombre_hoja="DESARROLLO_MODELO",
                         datos=tabla_desarrollo[tabla_desarrollo["CODIGO_SUBPRODUCTO"] == "ML_C46_MORA_CREDITO_RENEGOCIADO"],
                         formatos_columnas=formatos_excel
                         )

    print(f"        - Guardando hoja 'DESARROLLO' con {len(tabla_desarrollo_output):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                        nombre_hoja="DESARROLLO",
                        datos=tabla_desarrollo_output,
                        formatos_columnas=formatos_excel
                        )

    print(f"        - Guardando hoja 'DESARROLLO_RENEGOCIADO' con {len(tabla_desarrollo_renegociado_output):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO_RENEGOCIADO,
                        nombre_hoja="DESARROLLO",
                        datos=tabla_desarrollo_renegociado_output,
                        formatos_columnas=formatos_excel
                        )
                        
    print(f"        - Guardando hoja 'DETALLE_FLUJOS' con {len(flujo_estimado_agrupado):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO,
                        nombre_hoja="DETALLE_FLUJOS",
                        datos=flujo_estimado_agrupado[flujo_estimado_agrupado['PRODUCTO']!='RENEGOCIADO'][["FECHA_PROCESO","PRODUCTO",'FECHA_VENCIMIENTO_CUOTA_MODELO', 'FECHA_VENCIMIENTO_CUOTA', 
                                               'FLUJO_MO','AMORTIZACION_MO', 'INTERES_MO', 
                                               'FLUJO_MODELO_MO','AMORTIZACION_MODELO_MO', 'INTERES_MODELO_MO', 
                                               'FLUJO_MORA_VIGENTE_MO','AMORTIZACION_MORA_VIGENTE_MO', 'INTERES_MORA_VIGENTE_MO']],
                        formatos_columnas=formatos_excel
                        )

    print(f"        - Guardando hoja 'DETALLE_FLUJOS_RENEGOCIADO' con {len(flujo_estimado_agrupado):,} registros")
    ut.cargar_datos_xlsm(ruta_archivo=RUTA_OUTPUT_MODELO_RENEGOCIADO,
                        nombre_hoja="DETALLE_FLUJOS",
                        datos=flujo_estimado_agrupado[flujo_estimado_agrupado['PRODUCTO']=='RENEGOCIADO'][["FECHA_PROCESO","PRODUCTO",'FECHA_VENCIMIENTO_CUOTA_MODELO', 'FECHA_VENCIMIENTO_CUOTA', 
                                                'FLUJO_MO','AMORTIZACION_MO', 'INTERES_MO', 
                                                'FLUJO_MODELO_MO','AMORTIZACION_MODELO_MO', 'INTERES_MODELO_MO', 
                                                'FLUJO_MORA_VIGENTE_MO','AMORTIZACION_MORA_VIGENTE_MO', 'INTERES_MORA_VIGENTE_MO']],
                        formatos_columnas=formatos_excel
                        )


    # print("\n      • Respaldando archivo en carpeta de ejecuciones...")
    # ut.copia_archivo_en_ruta(RUTA_OUTPUT_MODELO,
    #                          cr.EJECUCIONES_ML_MORA_CONSUMO,
    #                          Path(RUTA_OUTPUT_MODELO).stem + ".xlsm",
    #                          agregar_fecha=True)


def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo de mora consumo.
    Esta función es llamada por el orquestador y encapsula toda la lógica necesaria.
    
    Args:
        fecha_proceso (datetime.datetime): Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso de error
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO MORA CONSUMO")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")

        print("[1/3] Leyendo datos de interfaz...")
        interfaz_de_datos_consumo_t = lectura_interfaz_de_datos(fecha_proceso)
        
        # Validar que los datos no estén vacíos
        if interfaz_de_datos_consumo_t.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros en la interfaz de datos para esta fecha.")
        
        print(f"      ✓ Datos leídos exitosamente - {len(interfaz_de_datos_consumo_t):,} registros encontrados")

        print("\n[2/3] Procesando información y calculando estimaciones...")
        procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_consumo_t)
        
        print("\n[3/3] Proceso completado:")
        print("      ✓ Cálculos realizados")
        print("      ✓ Archivos guardados")
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO MORA CONSUMO:")
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

    # fecha_proceso_str = "2025-12-30"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Usar la nueva función ejecutar_modelo
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)





