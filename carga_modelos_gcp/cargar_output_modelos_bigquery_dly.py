import os
import sys
import yaml
import pandas as pd
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from google.cloud import bigquery
from pathlib import Path

# Agregar el directorio raíz al path de Python
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr

# Importar configuraciones y utilidades
import bfa_cl_utilidades as ut

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r', encoding='utf-8') as file:
    config_ext = yaml.safe_load(file)

# Rutas
RUTA_CUENTA_SERVICIO_GCP = cr.obtener_ruta_credenciales_gcp()
def crear_esquema_base():
        return [
            bigquery.SchemaField("FECHA_PROCESO", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("CODIGO_EMPRESA", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("OPERACION", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("COD_ACT_PAS", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("MONEDA_ORIGEN", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("MONEDA_COMPENSACION", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("COMPENSACION", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("CODIGO_PRODUCTO", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("CODIGO_SUBPRODUCTO", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("FECHA_CREACION", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("NUMERO_CUOTA", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("FECHA_INICIO_CUOTA", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("FECHA_VENCIMIENTO_CUOTA", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("FECHA_PAGO", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("FECHA_REPRICING", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("AMORTIZACION", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("INTERES", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("INTERES_DEVENGADO", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("VP_AMORTIZACION", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("VP_INTERES", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("FACTOR_DE_RIESGO", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("TIPO_CUOTA", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("AREA_NEGOCIO", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("CODIGO_EJECUTIVO", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("CODIGO_ESTRATEGIA", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("CLASIFICACION_CONTABLE", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("TIPO_TASA", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("INDEXADOR", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("TASA", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("TASA_CF", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("SPREAD", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("FECHA_ACTUALIZACION", "DATETIME", mode="NULLABLE"),
        ]


def cargar_tablas_bigquery(fecha_t, ruta_archivo, hoja_archivo, tabla_respaldo, esquema_tabla=None, tipo_carga=None):
    pid = os.getpid()  # Obtener el ID del proceso actual
    print(f'[{pid}] Iniciando carga de: {ruta_archivo} (hoja: {hoja_archivo}) para la fecha: {fecha_t.strftime("%Y-%m-%d")}')

    try:

        dtype_excel = {
            "FECHA_PROCESO": "str",  # Convertir a string para procesar como fecha después
            "CODIGO_EMPRESA": "Int64",
            "OPERACION": "Int64",
            "COD_ACT/PAS": "str",
            "MONEDA_ORIGEN": "str",
            "MONEDA_COMPENSACION": "str",
            "COMPENSACION": "Int64",
            "CODIGO_PRODUCTO": "str",
            "CODIGO_SUBPRODUCTO": "str",
            "FECHA_CREACION": "str",  # Convertir a string para procesar como fecha después
            "NUMERO_CUOTA": "Int64",
            "FECHA_INICIO_CUOTA": "str",  # Convertir a string para procesar como fecha después
            "FECHA_VENCIMIENTO_CUOTA": "str",
            "FECHA_PAGO": "str",
            "FECHA_REPRICING": "str",
            "AMORTIZACION": "float",
            "INTERES": "float",
            "INTERES_DEVENGADO": "float",
            "VP_AMORTIZACION": "float",
            "VP_INTERES": "float",
            "FACTOR_DE_RIESGO": "str",
            "TIPO_CUOTA": "Int64",
            "AREA_NEGOCIO": "str",
            "CODIGO_EJECUTIVO": "str",
            "CODIGO_ESTRATEGIA": "str",
            "CLASIFICACION_CONTABLE": "str",
            "TIPO_TASA": "Int64",
            "INDEXADOR": "str",
            "TASA": "float",
            "TASA_CF": "float",
            "SPREAD": "float"
        }

        # ── Normalizar columnas con espacios (ml_inversiones) ──────────
        # El Excel de inversiones usa nombres con espacios/slash que
        # difieren del estándar con guiones bajos.  Se renombran aquí
        # para que el resto del pipeline funcione sin cambios.
        # Solo aplica a columnas que efectivamente existan en el DataFrame.
        _normalizacion_cols = {
            "FECHA PROCESO":    "FECHA_PROCESO",
            "FECHA CREACION":   "FECHA_CREACION",
            "FECHA PAGO":       "FECHA_PAGO",
            "FACTOR DE RIESGO": "FACTOR_DE_RIESGO",
            "AREA NEGOCIO":     "AREA_NEGOCIO",
            "CODIGO_ EJECUTIVO":"CODIGO_EJECUTIVO",
            "TIPO TASA":        "TIPO_TASA",
            "TASA CF":          "TASA_CF",
            "COD ACT/PAS":      "COD_ACT/PAS",
        }

        # Lectura: detectar si las columnas del Excel coinciden con dtype_excel.
        # Si no (p.ej. ml_inversiones con espacios), leer sin dtype y
        # recastear después del rename.
        df_peek = pd.read_excel(ruta_archivo, sheet_name=hoja_archivo,
                                engine='openpyxl', nrows=0)
        cols_excel = set(df_peek.columns)
        necesita_normalizacion = bool(cols_excel & set(_normalizacion_cols.keys()))

        if necesita_normalizacion:
            # Leer sin dtype forzado (los nombres aún no coinciden)
            df = pd.read_excel(ruta_archivo, sheet_name=hoja_archivo, engine='openpyxl')
            # Renombrar primero
            cols_a_renombrar = {k: v for k, v in _normalizacion_cols.items()
                               if k in df.columns}
            df = df.rename(columns=cols_a_renombrar)
            # Reemplazar cadenas vacías por NaN para que la conversión de tipos funcione
            import numpy as np
            df = df.replace('', np.nan)
            # Ahora re-castear a los tipos esperados
            for col, tipo in dtype_excel.items():
                if col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce') \
                            if tipo in ('Int64', 'float') \
                            else df[col].astype(tipo)
                    except (ValueError, TypeError):
                        pass  # Dejar tipo inferido si no convierte
        else:
            df = pd.read_excel(ruta_archivo, sheet_name=hoja_archivo,
                               engine='openpyxl', dtype=dtype_excel)

        # Convertir columnas de fecha a datetime.date.
        # Cuando se lee sin dtype (inversiones), openpyxl devuelve objetos
        # datetime nativos; cuando se lee con dtype str (otros modelos),
        # llegan como cadenas '2026-02-20 00:00:00'.  Usar format='mixed'
        # maneja ambos casos de forma robusta.
        _cols_fecha = ['FECHA_PROCESO', 'FECHA_CREACION', 'FECHA_INICIO_CUOTA',
                       'FECHA_VENCIMIENTO_CUOTA', 'FECHA_PAGO', 'FECHA_REPRICING']
        for _cf in _cols_fecha:
            df[_cf] = pd.to_datetime(df[_cf], format='mixed').dt.date

        ajuste_nombres_cols = {
            "COD_ACT/PAS": "COD_ACT_PAS",
            "COD ACT/PAS": "COD_ACT_PAS",
        }
        df = df.rename(columns=ajuste_nombres_cols)
        df["FECHA_ACTUALIZACION"] = datetime.datetime.now().replace(second=0, microsecond=0)

        df = df[df['FECHA_PROCESO'] == fecha_t.date()].reset_index(drop=True).copy()
        
        ut.cargar_dataframe_bigquery(
            data=df,
            ruta_cuenta_servicio=str(RUTA_CUENTA_SERVICIO_GCP),
            proyecto_id="bfa-cl-trade-price-report-dev",
            dataset_id="bfa_cl_prd_financial_risk_dly_proc_models",
            tabla_id=tabla_respaldo,
            esquema_tabla=esquema_tabla,
            tipo_escritura=tipo_carga
        )
        
        return f"[{pid}] ✓ Carga exitosa: {tabla_respaldo}"

    except Exception as e:
        return f"[{pid}] ✗ ERROR al procesar {ruta_archivo} (hoja: {hoja_archivo}). Error: {e}"

def cargar_modelos_a_bigquery(fecha_proceso: datetime, modelos_a_cargar: list = None) -> dict:
    """
    Función principal para cargar modelos a BigQuery
    
    Args:
        fecha_proceso: Fecha de proceso en formato datetime
        modelos_a_cargar: Lista de códigos de modelos a cargar. Si es None, carga todos.
        
    Returns:
        dict: Diccionario con los resultados de cada carga {tabla: bool}
    """
    print("\n" + "="*70)
    print("INICIO DE CARGA A BIGQUERY")
    print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
    print("="*70 + "\n")

    # Diccionario con todas las tareas disponibles
    todas_las_tareas = {
        'mr_prepago_hipotecario': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['mr_prepago_hipotecario']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_mr_prepago_hipotecario_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'mr_prepago_hipotecario'
        },
        'mr_prepago_consumo': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['mr_prepago_consumo']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_mr_prepago_consumo_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'mr_prepago_consumo'
        },
        'mr_prepago_cmr': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['mr_prepago_cmr']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_mr_prepago_cmr_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'mr_prepago_cmr'
        },
        'ml_mora_consumo': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_mora_consumo']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_mora_consumo_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_mora_consumo'
        },
        'ml_mora_consumo_renegociado': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_mora_consumo']['excel_output_2']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_mora_consumo_renegociado_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_mora_consumo'  # Mismo modelo origen
        },
        'ml_mora_cae': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_mora_cae']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_mora_cae_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_mora_cae'  # Mismo modelo origen
        },
        'ml_mora_hipotecario': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_mora_hipotecario']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_mora_hipotecario_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_mora_hipotecario'  # Mismo modelo origen
        },
        'ml_mora_comercial': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_mora_comercial']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_mora_comercial_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_mora_comercial'  # Mismo modelo origen
        },
        'ml_nmd': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_nmd']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_nmd_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_nmd'  # Mismo modelo origen
        },
        'ml_lc': {  # Clave única
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_lc']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_ml_lc_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_lc'  # Mismo modelo origen
        },
        'ml_inversiones': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['ml_inversiones']['excel_output']),
            'hoja_archivo': "INTERFAZ_MODELO_INVERSIONES",
            'tabla_respaldo': "report_ml_inversiones_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'ml_inversiones'
        },
        'mr_ssv': {
            'fecha_t': fecha_proceso,
            'ruta_archivo': Path(config_ext['modelos']['mr_ssv']['excel_output']),
            'hoja_archivo': "DESARROLLO",
            'tabla_respaldo': "report_mr_ssv_dly",
            'esquema_tabla': crear_esquema_base(),
            'tipo_carga': "TRUNCATE",
            'modelo_origen': 'mr_ssv',
        },
    }

    # Filtrar tareas según los modelos solicitados
    if modelos_a_cargar:
        tareas_a_ejecutar = []
        
        # Para cada modelo solicitado, buscar todas sus tareas asociadas
        for modelo in modelos_a_cargar:
            for llave, tarea in todas_las_tareas.items():
                # Incluir si la clave coincide directamente O si el modelo_origen coincide
                if llave == modelo or tarea.get('modelo_origen') == modelo:
                    tareas_a_ejecutar.append(tarea)
        
        if not tareas_a_ejecutar:
            print(f"Ninguno de los modelos especificados tiene configuración de carga: {modelos_a_cargar}")
            return {}
        
        # Mostrar qué tablas se cargarán
        tablas_a_cargar = [t['tabla_respaldo'] for t in tareas_a_ejecutar]
        print(f"Tablas a cargar: {', '.join(tablas_a_cargar)}")
    else:
        tareas_a_ejecutar = list(todas_las_tareas.values())

    print(f"Total de tareas: {len(tareas_a_ejecutar)}")
    print("Iniciando procesamiento paralelo de archivos...\n")
    
    resultados = {}

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {}
        
        for task_config in tareas_a_ejecutar:
            # Crear una copia del diccionario sin 'modelo_origen'
            task_args = {k: v for k, v in task_config.items() if k != 'modelo_origen'}
            
            # Enviar la tarea
            future = executor.submit(cargar_tablas_bigquery, **task_args)
            futures[future] = task_config  # Guardar la config completa para referencia

        for future in as_completed(futures):
            task_info = futures[future]
            try:
                result = future.result()
                print(result)
                resultados[task_info['tabla_respaldo']] = True
            except Exception as exc:
                error_msg = f"✗ ERROR en {task_info['tabla_respaldo']}: {exc}"
                print(error_msg)
                resultados[task_info['tabla_respaldo']] = False

    print("\n" + "="*70)
    print("PROCESAMIENTO FINALIZADO")
    print(f"Exitosos: {sum(1 for v in resultados.values() if v)}/{len(resultados)}")
    print("="*70)
    
    return resultados


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python cargar_output_modelos_bigquery_dly.py YYYY-MM-DD [modelo1 modelo2 ...]")
        sys.exit(1)

    fecha_proceso_str = sys.argv[1]

    try:
        fecha_proceso_t = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Obtener modelos opcionales desde argumentos
    modelos = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Ejecutar carga
    resultados = cargar_modelos_a_bigquery(fecha_proceso_t, modelos)
    
    # Mostrar resumen
    print("\n=== RESUMEN DE CARGAS ===")
    for tabla, exito in resultados.items():
        estado = "ÉXITO" if exito else "ERROR"
        print(f"{tabla}: {estado}")
    
    sys.exit(0 if all(resultados.values()) else 1)
