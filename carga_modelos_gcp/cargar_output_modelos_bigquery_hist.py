import bfa_cl_utilidades as ut
import datetime
import os
import sys
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed # Necesario para paralelizar
# ... (otras importaciones y la definición de ejecutar_query_bigquery) ...

# Número máximo de tablas a procesar simultáneamente
MAX_WORKERS = 5
RUTA_CUENTA_SERVICIO_GCP = r"Z:\RF_PROYECTOS\METODOLOGIAS\PROCESOS_DIARIOS_MODELOS\HERRAMIENTAS\bfa-cl-trade-price-report-dev-9d137fc23b7f.json"
PROJECT_ID = "bfa-cl-trade-price-report-dev"

# Definición de la estructura de configuración para cada par de tablas
MIGRATION_CONFIG = [
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
    
    
]


def migrar_datos_por_tabla(fecha_a_procesar: datetime.datetime,
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

    # 2. Query de INSERCIÓN (Mover datos)
    sql_insert = f"""
    INSERT INTO `{PROJECT_ID}.{NOMBRE_COMPLETO_HISTORICO}`
    SELECT * 
    FROM `{PROJECT_ID}.{NOMBRE_COMPLETO_DIARIO}`
    WHERE DATE({columna_fecha}) = DATE('{fecha_str}');
    """

    print(f"1. Insertando datos en {destino_tabla}...")
    registros_insertados = ut.ejecutar_query_bigquery(ruta_servicio, sql_insert)

    if registros_insertados == -1:
        print("Falla crítica durante la inserción")
        return

    print(f"Registros insertados: {registros_insertados}")


    print(f"--- {origen_tabla} Terminado ---\n")


# --- LÓGICA DE EJECUCIÓN ESCALABLE PRINCIPAL ---

if __name__ == "__main__":

    # --- PROCESAMIENTO DE ARGUMENTOS DE LÍNEA DE COMANDOS ---
    # if len(sys.argv) < 2:
    #     print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
    #     sys.exit(1)
    #
    # fecha_proceso_str = sys.argv[1]

    fecha_proceso_str = "2025-12-17"

    try:
        fecha_proceso_t = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)


    # fecha_a_procesar = datetime.now() - timedelta(days=1)

    print(f"Iniciando respaldo historico: {fecha_proceso_t.strftime('%Y-%m-%d')}")
    print(f"Usando {MAX_WORKERS} hilos de trabajo simultáneos.")

    # Utilizamos ThreadPoolExecutor para gestionar los hilos
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        # Almacenar las ejecuciones futuras
        future_to_config = {}

        # 1. Enviar todas las tareas al ejecutor
        for config in MIGRATION_CONFIG:
            # Enviamos la función y sus argumentos
            future = executor.submit(
                migrar_datos_por_tabla,
                fecha_proceso_t,
                RUTA_CUENTA_SERVICIO_GCP,
                config
            )
            # Mantenemos un mapeo del objeto Future a la configuración de la tabla
            future_to_config[future] = config['ORIGEN_TABLA']

        # 2. Esperar y recolectar los resultados a medida que se completan
        for future in as_completed(future_to_config):
            tabla_nombre = future_to_config[future]
            try:
                # El resultado de la función migrar_datos_por_tabla (que no devuelve nada)
                # O simplemente capturamos la excepción si falló.
                future.result()
                print(f"[{tabla_nombre}] Finalizado exitosa.")
            except Exception as exc:
                print(f"[{tabla_nombre}] GENERÓ UNA EXCEPCION: {exc}")

    print("\nProceso Finalizado.")
