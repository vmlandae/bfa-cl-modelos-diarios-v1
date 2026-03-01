import bfa_cl_utilidades as ut
import csv
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

# Importar configuraciones
from config import config_rutas as cr
from core.logger import get_logger

logger = get_logger(__name__)

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
        resultado = lector_trade_dev.leer_a_dataframe(sql_verificacion).iloc[0]['total_registros']
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
        {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_lc_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_lc_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    {
        "ORIGEN_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models",
        "ORIGEN_TABLA": "report_ml_inversiones_dly",
        "DESTINO_DATASET": "bfa_cl_prd_financial_risk_dly_proc_models_hist",
        "DESTINO_TABLA": "report_ml_inversiones_hist",
        "COLUMNA_FECHA_PARTICION": "FECHA_PROCESO"
    },
    
    
]


def _exportar_backup_pre_delete(tabla_completa: str, columna_fecha: str,
                                 fecha_str: str, destino_tabla: str) -> dict:
    """Exporta los registros que serán eliminados a CSV y genera metadata JSON.

    Guarda los archivos en ``backups_historicos/{YYYYMMDD}/{tabla}/``:
    - ``{tabla}_{timestamp}.csv`` — registros completos
    - ``{tabla}_{timestamp}_metadata.json`` — info de la operación

    Args:
        tabla_completa: Nombre completo dataset.tabla del histórico.
        columna_fecha: Columna de partición de fecha.
        fecha_str: Fecha en formato 'YYYY-MM-DD'.
        destino_tabla: Nombre corto de la tabla destino (para paths).

    Returns:
        dict con claves ``csv_path``, ``metadata_path``, ``filas_exportadas``.

    Raises:
        RuntimeError: Si la exportación falla.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fecha_dir = fecha_str.replace("-", "")
    backup_dir = Path(cr.BASE_DIR) / "backups_historicos" / fecha_dir / destino_tabla
    backup_dir.mkdir(parents=True, exist_ok=True)

    csv_path = backup_dir / f"{destino_tabla}_{timestamp}.csv"
    metadata_path = backup_dir / f"{destino_tabla}_{timestamp}_metadata.json"

    # Leer registros que serán eliminados
    sql_select = f"""
    SELECT *
    FROM `{PROJECT_ID}.{tabla_completa}`
    WHERE DATE({columna_fecha}) = DATE('{fecha_str}')
    """

    logger.info(f"📦 Exportando backup de {destino_tabla} para {fecha_str}...")
    try:
        df_backup = lector_trade_dev.leer_a_dataframe(sql_select)
    except Exception as e:
        raise RuntimeError(
            f"No se pudo leer registros para backup de {destino_tabla}: {e}"
        ) from e

    filas = len(df_backup)
    logger.info(f"📦 {filas} filas leídas de {destino_tabla} para backup")

    # Guardar CSV
    df_backup.to_csv(str(csv_path), index=False, quoting=csv.QUOTE_NONNUMERIC)
    logger.info(f"💾 Backup CSV guardado: {csv_path.relative_to(cr.BASE_DIR)}")

    # Guardar metadata
    metadata = {
        "operacion": "DELETE previo a re-inserción (--force-historico)",
        "timestamp": timestamp,
        "tabla_bq": f"{PROJECT_ID}.{tabla_completa}",
        "columna_fecha": columna_fecha,
        "fecha_proceso": fecha_str,
        "filas_exportadas": filas,
        "columnas": list(df_backup.columns),
        "csv_archivo": csv_path.name,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"📋 Metadata guardada: {metadata_path.relative_to(cr.BASE_DIR)}")

    return {
        "csv_path": str(csv_path),
        "metadata_path": str(metadata_path),
        "filas_exportadas": filas,
    }


def consolidar_historico_por_tabla(fecha_a_procesar: datetime.datetime,
                           ruta_servicio: str,
                           config: dict,
                           force: bool = False):
    """Consolida datos diarios en la tabla histórica correspondiente.

    Comportamiento por defecto (``force=False``):
        Si ya existen datos para la fecha, **omite** la inserción para
        evitar duplicados.

    Con ``force=True`` (flag ``--force-historico``):
        1. Exporta los registros existentes a CSV (backup con timestamp).
        2. Genera archivo de metadata JSON con info de la operación.
        3. Ejecuta DELETE de los registros existentes.
        4. Inserta los nuevos registros desde la tabla diaria.
        Todo queda registrado en el logger (JSONL).

    Args:
        fecha_a_procesar: Fecha de proceso.
        ruta_servicio: Ruta al archivo de credenciales GCP.
        config: Dict con ORIGEN_DATASET, ORIGEN_TABLA, DESTINO_DATASET,
                DESTINO_TABLA, COLUMNA_FECHA_PARTICION.
        force: Si True, permite re-inserción con DELETE previo + backup.
    """
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
    logger.info(f"\n--- Procesando {NOMBRE_COMPLETO_DIARIO} para la fecha: {fecha_str} ---")

    # 2. Verificar si ya existen datos en la tabla de destino
    logger.info(f"1. Verificando si ya existen datos en {destino_tabla} para la fecha {fecha_str}...")
    datos_existentes = verificar_datos_existentes(
        ruta_servicio, 
        NOMBRE_COMPLETO_HISTORICO, 
        columna_fecha, 
        fecha_str
    )
    
    if datos_existentes:
        if not force:
            logger.warning(
                f"⚠️ DATOS YA EXISTEN en {destino_tabla} para {fecha_str}. "
                "Omitiendo inserción (use --force-historico para re-insertar)."
            )
            logger.info(f"--- {origen_tabla} OMITIDO ---\n")
            return True  # No es un error, simplemente no re-inserta

        # --- Modo force: backup + DELETE + INSERT ---
        logger.warning(
            f"🔄 FORCE-HISTORICO: Datos existentes en {destino_tabla} para {fecha_str}. "
            "Iniciando proceso de re-inserción..."
        )

        # 2a. Backup CSV + metadata
        try:
            backup_info = _exportar_backup_pre_delete(
                NOMBRE_COMPLETO_HISTORICO, columna_fecha, fecha_str, destino_tabla
            )
            logger.info(
                f"✅ Backup completado: {backup_info['filas_exportadas']} filas → "
                f"{backup_info['csv_path']}"
            )
        except RuntimeError as e:
            logger.error(f"❌ Backup falló para {destino_tabla}: {e}")
            logger.error(f"--- {origen_tabla} ABORTADO (backup fallido, DELETE no ejecutado) ---\n")
            return False

        # 2b. DELETE
        sql_delete = f"""
        DELETE FROM `{PROJECT_ID}.{NOMBRE_COMPLETO_HISTORICO}`
        WHERE DATE({columna_fecha}) = DATE('{fecha_str}');
        """

        try:
            logger.info(f"🗑️ Ejecutando DELETE en {destino_tabla} para {fecha_str}...")
            filas_eliminadas = ut.ejecutar_query_bigquery(ruta_servicio, sql_delete)
            logger.info(f"🗑️ DELETE completado en {destino_tabla}: {filas_eliminadas} filas eliminadas")
        except Exception as e:
            logger.error(f"❌ ERROR CRÍTICO: DELETE falló en {destino_tabla}: {e}")
            logger.error(f"--- {origen_tabla} ABORTADO ---\n")
            return False
    else:
        logger.info("No hay datos existentes. Procediendo con la inserción...")

    # 3. Query de INSERCIÓN
    sql_insert = f"""
    INSERT INTO `{PROJECT_ID}.{NOMBRE_COMPLETO_HISTORICO}`
    SELECT * 
    FROM `{PROJECT_ID}.{NOMBRE_COMPLETO_DIARIO}`
    WHERE DATE({columna_fecha}) = DATE('{fecha_str}');
    """

    logger.info(f"2. Insertando datos en {destino_tabla}...")
    registros_insertados = ut.ejecutar_query_bigquery(ruta_servicio, sql_insert)

    if registros_insertados == -1:
        logger.error(f"❌ Falla crítica durante la inserción en {destino_tabla}")
        return False

    logger.info(f"✅ Registros insertados en {destino_tabla}: {registros_insertados}")

    # 3a. Guardar metadata de INSERT en el mismo directorio de backup (si hubo force)
    if datos_existentes and force:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fecha_dir = fecha_str.replace("-", "")
        metadata_insert_path = (
            Path(cr.BASE_DIR) / "backups_historicos" / fecha_dir / destino_tabla
            / f"{destino_tabla}_{timestamp}_insert_metadata.json"
        )
        metadata_insert = {
            "operacion": "INSERT post-DELETE (--force-historico)",
            "timestamp": timestamp,
            "tabla_bq_origen": f"{PROJECT_ID}.{NOMBRE_COMPLETO_DIARIO}",
            "tabla_bq_destino": f"{PROJECT_ID}.{NOMBRE_COMPLETO_HISTORICO}",
            "fecha_proceso": fecha_str,
            "filas_insertadas": registros_insertados if registros_insertados != -1 else 0,
            "backup_csv": backup_info.get("csv_path", "N/A"),
            "filas_backup_previo": backup_info.get("filas_exportadas", 0),
        }
        metadata_insert_path.write_text(
            json.dumps(metadata_insert, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"📋 Metadata de INSERT guardada: {metadata_insert_path.relative_to(cr.BASE_DIR)}")

    logger.info(f"--- {origen_tabla} Terminado ---\n")
    return True


def consolidar_historico_bigquery(fecha_proceso: datetime.datetime,
                                  modelos_a_consolidar: List[str] = None,
                                  force: bool = False) -> Dict[str, bool]:
    """
    Función principal para consolidar datos diarios en tablas históricas de BigQuery.

    Por defecto omite tablas que ya tienen datos para la fecha.
    Con ``force=True`` hace backup CSV + DELETE + INSERT.
    
    Args:
        fecha_proceso: Fecha de proceso en formato datetime.
        modelos_a_consolidar: Lista de códigos de modelos. Si es None, consolida todos.
        force: Si True, permite re-inserción con DELETE previo + backup.
        
    Returns:
        dict: Diccionario con los resultados de cada consolidación {tabla: bool}
    """
    logger.info("\n" + "="*70)
    logger.info("CONSOLIDACION HISTORICA EN BIGQUERY")
    logger.info(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
    if force:
        logger.warning("⚠️ MODO FORCE-HISTORICO ACTIVADO: se hará backup + DELETE + INSERT si hay datos existentes")
    logger.info("="*70 + "\n")

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
        'ml_lc': ['report_ml_lc_dly'],
        'ml_inversiones': ['report_ml_inversiones_dly'],
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
            logger.warning("Ninguno de los modelos especificados tiene configuración de consolidación")
            return {}
    else:
        configs_a_ejecutar = CONFIGURACION_CONSOLIDACION

    logger.info(f"Total de tablas a consolidar: {len(configs_a_ejecutar)}")
    logger.info(f"Usando {MAX_WORKERS} hilos de trabajo simultáneos.")
    logger.info("Iniciando procesamiento paralelo...\n")
    
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
                config,
                force
            )
            future_to_config[future] = config['DESTINO_TABLA']

        # Esperar y recolectar los resultados
        for future in as_completed(future_to_config):
            tabla_nombre = future_to_config[future]
            try:
                resultado = future.result()
                resultados[tabla_nombre] = resultado if resultado is not None else True
                logger.info(f"[{tabla_nombre}] Finalizado exitosamente.")
            except Exception as exc:
                logger.error(f"[{tabla_nombre}] ERROR: {exc}")
                resultados[tabla_nombre] = False

    logger.info("\n" + "="*70)
    logger.info("CONSOLIDACION FINALIZADA")
    logger.info(f"Exitosos: {sum(1 for v in resultados.values() if v)}/{len(resultados)}")
    logger.info("="*70)
    
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
