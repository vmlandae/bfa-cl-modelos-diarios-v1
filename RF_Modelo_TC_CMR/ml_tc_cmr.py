"""
Modelo TC CMR (Tarjeta de Credito CMR)

Modulo principal del modelo de Tarjeta de Credito CMR.
Proyecta flujos de caja futuros esperados (ingresos) para la cartera de
tarjetas de credito CMR, dia a dia, usando factores historicos de
probabilidad de pago por perfil de cliente y dia del mes.

Pipeline de 3 fases:
  Fase 1 - MAESTRO: Preparacion de datos (carga cartera TXT, clasificacion N/R/V, perfiles de pago)
  Fase 2 - Calculo de Flujos: Periodos de facturacion, revolventes, pago estimado
  Fase 3 - Tabla de Desarrollo: Formateo al esquema estandar DESARROLLO para BigQuery
"""

import pandas as pd
import numpy as np
from datetime import datetime
import yaml
import sys
import shutil
import bfa_cl_utilidades as ut
from pathlib import Path

from config import config_rutas as cr

from RF_Modelo_TC_CMR.preparacion import ejecutar_maestro
from RF_Modelo_TC_CMR.calculo import ejecutar_calculo_flujos
from RF_Modelo_TC_CMR.postproceso import generar_tabla_desarrollo


# Cargar configuracion de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Configuracion del modelo desde YAML
CONFIG_ML_TC_CMR = config_ext['modelos']['ml_tc_cmr']

# Rutas de input (red)
RUTA_TXT_CARTERA = Path(CONFIG_ML_TC_CMR['txt_cartera_input'])
TXT_CARTERA_PATTERN = CONFIG_ML_TC_CMR['txt_cartera_pattern']
RUTA_PERFIL_FACTOR = Path(CONFIG_ML_TC_CMR['perfil_factor_input'])
RUTA_TABLA_PERFILES_PP = Path(CONFIG_ML_TC_CMR['tabla_perfiles_pp_input'])

# Rutas locales de parametros y output
RUTA_PARAMETROS = cr.resolver_ruta(CONFIG_ML_TC_CMR['excel_parametros_modelo_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(CONFIG_ML_TC_CMR['excel_output'])
RUTA_OUTPUT_FLUJOS = cr.resolver_ruta(CONFIG_ML_TC_CMR['excel_flujos_output'])

# Directorio local de datos (copias desde red, gitignored)
RUTA_DATA_LOCAL = cr.ML_TC_CMR / 'data'


def copiar_archivos_red(fecha_proceso: datetime) -> None:
    """
    Copia archivos necesarios desde la red al directorio local data/.

    Copia:
    - Archivos TXT de cartera (fecha actual + hasta 6 meses atras para T-30)
    - Perfil_Factor.csv
    - tabla_perfiles_pp.csv
    """
    RUTA_DATA_LOCAL.mkdir(parents=True, exist_ok=True)

    # Copiar parametros externos
    for ruta_red, nombre in [
        (RUTA_PERFIL_FACTOR, RUTA_PERFIL_FACTOR.name),
        (RUTA_TABLA_PERFILES_PP, RUTA_TABLA_PERFILES_PP.name),
    ]:
        destino = RUTA_DATA_LOCAL / nombre
        if ruta_red.exists():
            shutil.copy2(str(ruta_red), str(destino))
            print(f"        - Copiado: {nombre}")
        else:
            print(f"        - [WARN] No encontrado: {ruta_red}")

    # Copiar archivos TXT de cartera
    # Necesitamos el archivo de la fecha actual y los de meses anteriores (para T-30)
    from RF_Modelo_TC_CMR.preparacion.cargar_cartera import ajustar_dia_habil, buscar_archivo_cartera
    from dateutil.relativedelta import relativedelta

    # Buscar archivos de hasta 6 meses atras (para cubrir T-30)
    archivos_copiados = 0
    fechas_a_buscar = set()

    # Fecha principal
    fecha_habil = ajustar_dia_habil(fecha_proceso)
    fechas_a_buscar.add(fecha_habil)

    # Fechas T-30 (hasta 6 meses atras, con margen de +5 dias para fallback)
    for meses in range(1, 7):
        fecha_base = fecha_proceso - relativedelta(months=meses)
        for offset in range(6):
            from datetime import timedelta
            fechas_a_buscar.add(fecha_base + timedelta(days=offset))

    for fecha in sorted(fechas_a_buscar):
        fecha_str = fecha.strftime('%Y%m%d')
        for ext in ['.TXT', '.txt']:
            nombre_archivo = f"ProductosMercadoLiquidezCMR{fecha_str}{ext}"
            ruta_origen = RUTA_TXT_CARTERA / nombre_archivo
            destino = RUTA_DATA_LOCAL / nombre_archivo
            if ruta_origen.exists() and not destino.exists():
                shutil.copy2(str(ruta_origen), str(destino))
                archivos_copiados += 1

    print(f"        - Archivos TXT copiados: {archivos_copiados}")


def cargar_parametros() -> tuple:
    """
    Carga parametros del modelo.

    Returns:
        (factor_ajuste, tabla_perfiles_pp_dict)
        - factor_ajuste: float (default 0.9165 si no hay parametros xlsx)
        - tabla_perfiles_pp_dict: dict {perfil: pp} desde CSV
    """
    # Factor de ajuste desde parametros xlsx
    factor_ajuste = 0.9165  # default
    if RUTA_PARAMETROS.exists():
        try:
            params = pd.read_excel(RUTA_PARAMETROS, sheet_name="PARAMETROS")
            if 'FACTOR_AJUSTE' in params.columns:
                factor_ajuste = float(params['FACTOR_AJUSTE'].iloc[0])
        except Exception as e:
            print(f"        - [WARN] Error leyendo parametros xlsx: {e}, usando default={factor_ajuste}")

    # Tabla de perfiles PP desde CSV local
    ruta_pp_local = RUTA_DATA_LOCAL / RUTA_TABLA_PERFILES_PP.name
    if ruta_pp_local.exists():
        df_pp = pd.read_csv(
            ruta_pp_local,
            sep=';',
            encoding='latin-1'
        )
        df_pp.columns = df_pp.columns.str.strip()
        # Buscar columnas: una de perfil y una de PP
        col_perfil = None
        col_pp = None
        for col in df_pp.columns:
            col_upper = col.upper()
            if 'PERFIL' in col_upper and 'PP' not in col_upper:
                col_perfil = col
            elif col_upper == 'PP':
                col_pp = col
        if col_perfil and col_pp:
            tabla_pp = dict(zip(df_pp[col_perfil].astype(str), df_pp[col_pp].astype(str)))
        else:
            # Fallback: asumir primera columna = perfil, segunda = PP
            tabla_pp = dict(zip(df_pp.iloc[:, 0].astype(str), df_pp.iloc[:, 1].astype(str)))
    else:
        raise FileNotFoundError(
            f"No se encontro tabla_perfiles_pp en {ruta_pp_local}. "
            f"Verifique que se copio desde {RUTA_TABLA_PERFILES_PP}"
        )

    print(f"        - Factor ajuste: {factor_ajuste}")
    print(f"        - Perfiles PP cargados: {len(tabla_pp)} mapeos")

    return factor_ajuste, tabla_pp


def guardar_flujos_validacion(flujos: pd.DataFrame, fecha_proceso: datetime) -> None:
    """Guarda flujos detallados en FLUJOS_MODELO_CMR.xlsx para validacion."""
    print(f"        - Guardando flujos de validacion...")
    RUTA_OUTPUT_FLUJOS.parent.mkdir(parents=True, exist_ok=True)
    flujos.to_excel(str(RUTA_OUTPUT_FLUJOS), index=False, engine='openpyxl')
    print(f"          Archivo: {RUTA_OUTPUT_FLUJOS.name} ({len(flujos):,} filas)")


def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """
    Ejecuta el modelo TC CMR completo.

    Pipeline:
    [1/7] Copiar archivos desde red a data/
    [2/7] Cargar parametros (factor_ajuste, tabla_perfiles_pp)
    [3/7] Fase 1 - MAESTRO (preparacion cartera)
    [4/7] Fase 2 - Calculo de flujos
    [5/7] Fase 3 - Tabla de desarrollo
    [6/7] Guardar flujos de validacion (xlsx)
    [7/7] Guardar DESARROLLO en xlsm

    Args:
        fecha_proceso: Fecha de procesamiento

    Returns:
        bool: True si la ejecucion fue exitosa
    """
    try:
        print(f"\n{'='*60}")
        print(f"INICIO DEL PROCESO - MODELO TC CMR")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print(f"{'='*60}\n")

        # [1/7] Copiar archivos desde red
        print("[1/7] Copiando archivos desde red...")
        copiar_archivos_red(fecha_proceso)
        print("      Archivos copiados exitosamente\n")

        # [2/7] Cargar parametros
        print("[2/7] Cargando parametros del modelo...")
        factor_ajuste, tabla_perfiles_pp = cargar_parametros()
        print("      Parametros cargados exitosamente\n")

        # [3/7] Fase 1 - MAESTRO
        print("[3/7] Ejecutando Fase 1 - MAESTRO (preparacion)...")
        resultado_maestro = ejecutar_maestro(
            fecha_proceso=fecha_proceso,
            ruta_data_local=RUTA_DATA_LOCAL,
            tabla_perfiles_pp=tabla_perfiles_pp
        )
        print(f"      Fase 1 completada: {resultado_maestro['total_registros']:,} registros")
        print(f"      MONTO_MORA: {resultado_maestro['monto_mora']:,.0f}")
        print(f"      FACTURACION: {resultado_maestro['facturacion']:,.0f}")
        print(f"      CORTE: {resultado_maestro['corte']}\n")

        # [4/7] Fase 2 - Calculo de flujos
        print("[4/7] Ejecutando Fase 2 - Calculo de flujos...")
        ruta_csv = Path(resultado_maestro['archivo_output'])
        ruta_perfil_local = RUTA_DATA_LOCAL / RUTA_PERFIL_FACTOR.name

        flujos = ejecutar_calculo_flujos(
            ruta_csv=ruta_csv,
            ruta_perfil_factor=ruta_perfil_local,
            fecha_proceso=fecha_proceso,
            factor_ajuste=factor_ajuste
        )
        print(f"      Fase 2 completada: {len(flujos):,} flujos\n")

        # [5/7] Fase 3 - Tabla de desarrollo
        print("[5/7] Ejecutando Fase 3 - Tabla de desarrollo...")
        tabla_desarrollo = generar_tabla_desarrollo(flujos, fecha_proceso)
        print(f"      Fase 3 completada: {len(tabla_desarrollo):,} registros\n")

        # [6/7] Guardar flujos de validacion
        print("[6/7] Guardando flujos de validacion...")
        guardar_flujos_validacion(flujos, fecha_proceso)
        print("      Flujos guardados exitosamente\n")

        # [7/7] Guardar DESARROLLO en xlsm
        print("[7/7] Guardando resultados en Excel...")
        formatos_excel = {
            "FECHA_PROCESO": "dd-mm-yyyy",
            "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
            "FECHA_PAGO": "dd-mm-yyyy",
            "FECHA_REPRICING": "dd-mm-yyyy"
        }

        ut.cargar_datos_xlsm(
            ruta_archivo=RUTA_OUTPUT_MODELO,
            nombre_hoja="DESARROLLO",
            datos=tabla_desarrollo,
            formatos_columnas=formatos_excel
        )
        print(f"      Archivo actualizado: {RUTA_OUTPUT_MODELO.name}")

        print(f"\n{'='*60}")
        print(f"PROCESO FINALIZADO EXITOSAMENTE")
        print(f"Total registros DESARROLLO: {len(tabla_desarrollo):,}")
        print(f"{'='*60}")

        return True

    except Exception as e:
        print(f"\nERROR EN EL MODELO TC CMR:")
        print(f"   {str(e)}")
        print(f"\n{'='*60}")
        print(f"PROCESO TERMINADO CON ERRORES")
        print(f"{'='*60}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ml_tc_cmr.py YYYY-MM-DD")
        sys.exit(1)

    try:
        fecha = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print("Formato de fecha invalido. Use YYYY-MM-DD")
        sys.exit(1)

    exito = ejecutar_modelo(fecha)
    sys.exit(0 if exito else 1)
