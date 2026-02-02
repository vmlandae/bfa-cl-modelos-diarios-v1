import bfa_cl_utilidades as ut
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

# Importar configuraciones
from config import config_rutas as cr

# Número máximo de tablas a procesar simultáneamente
MAX_WORKERS = 5
RUTA_CUENTA_SERVICIO_GCP = cr.obtener_ruta_credenciales_gcp()
PROJECT_ID = "bfa-cl-trade-price-report-dev"

lector_trade_dev = ut.LectorBigQuery(tipo_conexion="cuenta_servicio",
                                     archivo_credenciales_json=RUTA_CUENTA_SERVICIO_GCP,
                                     proyecto_id=PROJECT_ID)

def verificar_datos_existentes(ruta_servicio: str, tabla_completa: str, columna_fecha: str, fecha: str) -> bool:
    """
    Verifica si ya existen datos en la tabla de destino para la fecha especificada
    
    Args:
        ruta_servicio: Ruta al archivo de credenciales de GCP
        tabla_completa: Nombre completo de la tabla (proyecto.dataset.tabla)
        columna_fecha: Nombre de la columna de fecha para filtrar
        fecha: Fecha en formato 'YYYY-MM-DD'
    
    Returns:
        bool: True si existen datos, False si no existen
    """
    sql_verificacion = f"""
    SELECT COUNT(*) as total_registros
    FROM `{PROJECT_ID}.{tabla_completa}`
    WHERE DATE({columna_fecha}) = DATE('{fecha}')
    """
    
    try:
        # resultado = ut.ejecutar_query_bigquery(ruta_servicio, sql_verificacion)
        resultado = lector_trade_dev.leer_a_dataframe(sql_verificacion)
        resultado = resultado['total_registros'].iloc[0]
        
        # Si el resultado es mayor a 0, ya existen datos
        return resultado > 0
    except Exception as e:
        print(f"ADVERTENCIA: Excepción al verificar datos existentes: {e}")
        return True  # Por seguridad, asumimos que existen datos

# Definición de la estructura de configuración para cada par de tablas (diario -> histórico)
CONFIGURACION_CONSOLIDACION = [
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_mr_prepago_hipotecario_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_mr_prepago_hipotecario_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_mr_prepago_consumo_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_mr_prepago_consumo_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_mr_prepago_cmr_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_mr_prepago_cmr_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_mora_consumo_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_mora_consumo_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_mora_consumo_renegociado_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_mora_consumo_renegociado_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_mora_cae_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_mora_cae_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_mora_hipotecario_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_mora_hipotecario_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
        {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_mora_comercial_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_mora_comercial_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
        {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_nmd_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_nmd_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    
    
]


def consolidar_historico_por_tabla(fecha_a_procesar: datetime.datetime,
                           ruta_servicio: str,
                           config: dict):

    # 1. Extraer configuración
    origen_dataset = config["ORIGEN_DATASET"]
    origen_tabla = config["ORIGEN_TABLA"]
    destino_dataset = config["DESTINO_DATASET"]
    destino_tabla = config["DESTINO_TABLA"]
    columna_fecha = config["COLUMNA_FECHA_PARTICION"]

    # Nombres completos
    NOMBRE_COMPLETO_DIARIO = f"{origen_dataset}.{origen_tabla}"
    NOMBRE_COMPLETO_HISTORICO = f"{destino_dataset}.{destino_tabla}"

    fecha_str = fecha_a_procesar.strftime('%Y-%m-%d')
    print(f"\n--- Procesando {NOMBRE_COMPLETO_DIARIO} para la fecha: {fecha_str} ---")

    # 1. Verificar si ya existen datos en la tabla de destino
    print(f"1. Verificando si ya existen datos en {destino_tabla} para la fecha {fecha_str}...")
    datos_existentes = verificar_datos_existentes(
        ruta_servicio, 
        NOMBRE_COMPLETO_HISTORICO, 
        columna_fecha, 
        fecha_str
    )
    
    if datos_existentes:
        print(f"DATOS YA EXISTEN en {destino_tabla} para la fecha {fecha_str}")
        print("SUSPENDIENDO inserción para evitar duplicados")
        print(f"--- {origen_tabla} OMITIDO ---\n")
        return
    
    print("No hay datos existentes. Procediendo con la inserción...")

    # 2. Query de INSERCIÓN (Mover datos)
    sql_insert = f"""
    INSERT INTO `{PROJECT_ID}.{NOMBRE_COMPLETO_HISTORICO}`
    SELECT * 
    FROM `{PROJECT_ID}.{NOMBRE_COMPLETO_DIARIO}`
    WHERE DATE({columna_fecha}) = DATE('{fecha_str}');
    """

    print(f"2. Insertando datos en {destino_tabla}...")
    registros_insertados = ut.ejecutar_query_bigquery(ruta_servicio, sql_insert)

    if registros_insertados == -1:
        print("Falla crítica durante la inserción")
        return

    print(f"Registros insertados: {registros_insertados}")


    print(f"--- {origen_tabla} Terminado ---\n")
    return True


def consolidar_historico_bigquery(fecha_proceso: datetime.datetime, modelos_a_consolidar: List[str] = None) -> Dict[str, bool]:
    """
    Función principal para consolidar datos diarios en tablas históricas de BigQuery
    
    Args:
        fecha_proceso: Fecha de proceso en formato datetime
        modelos_a_consolidar: Lista de códigos de modelos a consolidar. Si es None, consolida todos.
        
    Returns:
        dict: Diccionario con los resultados de cada consolidación {tabla: bool}
    """
    print("\n" + "="*70)
    print("CONSOLIDACION HISTORICA EN BIGQUERY")
    print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
    print("="*70 + "\n")

    # Mapeo de modelos a sus tablas de configuración
    MODELO_A_TABLAS = {
        'mr_prepago_hipotecario': ['report_mr_prepago_hipotecario_dly'],
        'mr_prepago_consumo': ['report_mr_prepago_consumo_dly'],
        'mr_prepago_cmr': ['report_mr_prepago_cmr_dly'],
        'ml_mora_consumo': ['report_ml_mora_consumo_dly', 'report_ml_mora_consumo_renegociado_dly'],
        'ml_mora_cae': ['report_ml_mora_cae_dly'],
        'ml_mora_hipotecario': ['report_ml_mora_hipotecario_dly'],
        'ml_mora_comercial': ['report_ml_mora_comercial_dly'],
        'ml_nmd': ['report_ml_nmd_dly'],
    }

    # Filtrar configuraciones según los modelos solicitados
    if modelos_a_consolidar:
        configs_a_ejecutar = []
        for modelo in modelos_a_consolidar:
            if modelo in MODELO_A_TABLAS:
                tablas_modelo = MODELO_A_TABLAS[modelo]
                for config in CONFIGURACION_CONSOLIDACION:
                    if config['ORIGEN_TABLA'] in tablas_modelo:
                        configs_a_ejecutar.append(config)
        
        if not configs_a_ejecutar:
            print("ADVERTENCIA: Ninguno de los modelos especificados tiene configuración de consolidación")
            return {}
    else:
        configs_a_ejecutar = CONFIGURACION_CONSOLIDACION

    print(f"Total de tablas a consolidar: {len(configs_a_ejecutar)}")
    print(f"Usando {MAX_WORKERS} hilos de trabajo simultáneos.")
    print("Iniciando procesamiento paralelo...\n")
    
    resultados = {}

    # Utilizamos ThreadPoolExecutor para gestionar los hilos
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_config = {}

        # Enviar todas las tareas al ejecutor
        for config in configs_a_ejecutar:
            future = executor.submit(
                consolidar_historico_por_tabla,
                fecha_proceso,
                RUTA_CUENTA_SERVICIO_GCP,
                config
            )
            future_to_config[future] = config['DESTINO_TABLA']

        # Esperar y recolectar los resultados
        for future in as_completed(future_to_config):
            tabla_nombre = future_to_config[future]
            try:
                resultado = future.result()
                resultados[tabla_nombre] = resultado if resultado is not None else True
                print(f"[{tabla_nombre}] Finalizado exitosamente.")
            except Exception as exc:
                print(f"[{tabla_nombre}] ERROR: {exc}")
                resultados[tabla_nombre] = False

    print("\n" + "="*70)
    print("CONSOLIDACION FINALIZADA")
    print(f"Exitosos: {sum(1 for v in resultados.values() if v)}/{len(resultados)}")
    print("="*70)
    
    return resultados


# --- EJECUCIÓN STANDALONE ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python cargar_output_modelos_bigquery_hist.py YYYY-MM-DD [modelo1 modelo2 ...]")
        sys.exit(1)

    fecha_proceso_str = sys.argv[1]

    try:
        fecha_proceso_t = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Obtener modelos opcionales desde argumentos
    modelos = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Ejecutar consolidación
    resultados = consolidar_historico_bigquery(fecha_proceso_t, modelos)
    
    # Mostrar resumen
    print("\n=== RESUMEN DE CONSOLIDACION ===")
    for tabla, exito in resultados.items():
        estado = "EXITO" if exito else "ERROR"
        print(f"{tabla}: {estado}")
    
    sys.exit(0 if all(resultados.values()) else 1)
