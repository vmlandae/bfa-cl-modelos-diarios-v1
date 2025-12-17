from pathlib import Path


# Definición del directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas principales
CONFIG = BASE_DIR / 'config'
CREDENCIALES = BASE_DIR / 'credenciales'
CORE = BASE_DIR / 'core'
GUI = BASE_DIR / 'gui'
CARGA_MODELOS_GCP = BASE_DIR / 'carga_modelos_gcp'

# Rutas específicas de MODELOS
MR_PREPAGO_CONSUMO = BASE_DIR / 'RF_Modelo_Prepago_Consumo'
MR_PREPAGO_HIPOTECARIO = BASE_DIR / 'RF_Modelo_Prepago_Hipotecario'
MR_PREPAGO_CMR = BASE_DIR / 'RF_Modelo_Prepago_CMR'
ML_MORA_CONSUMO = BASE_DIR / 'RF_Modelo_Mora_Consumo'
ML_MORA_CAE = BASE_DIR / 'RF_Modelo_Mora_CAE'
ML_MORA_HIPOTECARIO = BASE_DIR / 'RF_Modelo_Mora_Hipotecario'
ML_MORA_COMERCIAL = BASE_DIR / 'RF_Modelo_Mora_Comercial'

# Funciones
def obtener_ruta_credenciales_gcp():
    return CREDENCIALES / 'bfa-cl-trade-price-report-dev-9d137fc23b7f.json'

# def obtener_modulo_carga_gcp():
#     """
#     Importa y retorna el módulo de carga a GCP
#     """
#     # Agregar la ruta al sys.path si no existe
#     if str(CARGA_MODELOS_GCP) not in sys.path:
#         sys.path.insert(0, str(CARGA_MODELOS_GCP))
    
#     try:
#         from cargar_output_modelos_bigquery_dly import cargar_modelos_a_bigquery
#         return cargar_modelos_a_bigquery
#     except ImportError as e:
#         raise ImportError(f"No se pudo importar el módulo de carga GCP: {e}")

# def obtener_configuracion_modelos():
#     """
#     Retorna la configuración de todos los modelos disponibles
#     """
#     return {
#         "mr_prepago_consumo": {
#             "nombre": "Modelo Prepago Consumo",
#             "ruta_directorio": MR_PREPAGO_CONSUMO,
#             "modulo": "RF_Modelo_Prepago_Consumo.mr_prepago_consumo",
#             "activado": True,
#             "orden": 1,
#             "tiene_carga_gcp": True
#         },
#         "mr_prepago_hipotecario": {
#             "nombre": "Modelo Prepago Hipotecario", 
#             "ruta_directorio": MR_PREPAGO_HIPOTECARIO,
#             "modulo": "RF_Modelo_Prepago_Hipotecario.mr_prepago_hipotecario",
#             "activado": True,
#             "orden": 2,
#             "tiene_carga_gcp": True
#         },
#         "mr_prepago_cmr": {
#             "nombre": "Modelo Prepago CMR",
#             "ruta_directorio": MR_PREPAGO_CMR,
#             "modulo": "RF_Modelo_Prepago_CMR.mr_prepago_cmr",
#             "activado": True,
#             "orden": 3,
#             "tiene_carga_gcp": True
#         },
#         "ml_mora_consumo": {
#             "nombre": "Modelo Mora Consumo",
#             "ruta_directorio": ML_MORA_CONSUMO,
#             "modulo": "RF_Modelo_Mora_Consumo.ml_mora_consumo",
#             "activado": True,
#             "orden": 4,
#             "tiene_carga_gcp": True
#         },
#         "ml_mora_cae": {
#             "nombre": "Modelo Mora CAE",
#             "ruta_directorio": ML_MORA_CAE,
#             "modulo": "RF_Modelo_Mora_CAE.ml_mora_cae",
#             "activado": True,
#             "orden": 5,
#             "tiene_carga_gcp": True
#         },
#         "ml_mora_hipotecario": {
#             "nombre": "Modelo Mora Hipotecario",
#             "ruta_directorio": ML_MORA_HIPOTECARIO,
#             "modulo": "RF_Modelo_Mora_Hipotecario.ml_mora_hipotecario",
#             "activado": True,
#             "orden": 6,
#             "tiene_carga_gcp": True
#         },
#         "ml_mora_comercial": {
#             "nombre": "Modelo Mora Comercial",
#             "ruta_directorio": ML_MORA_COMERCIAL,
#             "modulo": "RF_Modelo_Mora_Comercial.ml_mora_comercial",
#             "activado": True,
#             "orden": 7,
#             "tiene_carga_gcp": True
#         }
#     }

# def agregar_rutas_al_path():
#     """
#     Agrega las rutas de los modelos al sys.path para importación
#     """
#     rutas_modelos = [
#         str(MR_PREPAGO_CONSUMO),
#         str(MR_PREPAGO_HIPOTECARIO),
#         str(MR_PREPAGO_CMR),
#         str(ML_MORA_CONSUMO),
#         str(ML_MORA_CAE),
#         str(ML_MORA_HIPOTECARIO),
#         str(ML_MORA_COMERCIAL),
#         str(CARGA_MODELOS_GCP),
#         str(BASE_DIR)
#     ]
    
#     for ruta in rutas_modelos:
#         if ruta not in sys.path:
#             sys.path.insert(0, ruta)