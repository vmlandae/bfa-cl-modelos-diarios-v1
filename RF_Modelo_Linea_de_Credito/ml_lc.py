import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut

# Configuración de importación para ejecución directa
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importación de módulos internos
from config import config_rutas as cr  # Configuración de rutas del proyecto


# Carga de configuración desde archivo YAML
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
ARCHIVO_INPUT = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['ms_access_input'])
ARCHIVO_DAP = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['ms_access_input'])
RUTA_PARAMETROS_NMD = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_parametros_modelo_input'])
RUTA_PARAMETROS_CORE = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_parametros_core_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_output'])