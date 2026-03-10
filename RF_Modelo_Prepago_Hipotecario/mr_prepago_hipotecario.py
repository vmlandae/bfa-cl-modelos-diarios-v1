import pandas as pd
import numpy as np
from typing import Dict, Any
import os
import datetime
import yaml
from pathlib import Path
import sys
from core.excel_output import guardar_excel

# # Para una ejecucion directa del script
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)


# Importar utilidades
# import HERRAMIENTAS.utilidades_bfal as ut

# Configuración de rutas y archivos (resolver_ruta maneja rutas relativas y absolutas)
RUTA_INTERFAZ_DE_DATOS = cr.resolver_ruta(config_ext['modelos']['mr_prepago_hipotecario']['interfaz_datos_input'])
ARCHIVO_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['mr_prepago_hipotecario']['excel_output'])
ARCHIVO_PARAMETROS = cr.resolver_ruta(config_ext['modelos']['mr_prepago_hipotecario']['excel_parametros_input'])


def lectura_parametros_modelo() -> Dict[str, Any]:
    """
    Lee los parámetros del modelo desde el archivo de configuración Excel.
    
    Returns:
        Dict[str, Any]: Diccionario con las siguientes claves:
            - 'SMM_MODELO': Lista con las tasas SMM de prepago
            - 'ESCENARIOS': Diccionario con la configuración de escenarios
    """
    print("      • Leyendo parámetros del modelo desde Excel...")
    
    
    if not ARCHIVO_PARAMETROS.exists():
        raise FileNotFoundError(f"No se encontró el archivo de parámetros: {ARCHIVO_PARAMETROS}")
    
    # Leer SMM_MODELO desde la hoja SMM_PREPAGO
    df_smm = pd.read_excel(ARCHIVO_PARAMETROS, sheet_name='SMM_PREPAGO')
    smm_lista = df_smm.iloc[:, 0].dropna().tolist()  # Primera columna, eliminar NaN
    print(f"        - {len(smm_lista)} tasas SMM cargadas")
    
    # Leer ESCENARIOS desde la hoja ESCENARIO
    df_escenarios = pd.read_excel(ARCHIVO_PARAMETROS, sheet_name='ESCENARIO')
    
    # Asumiendo que el Excel tiene columnas: ID_ESCENARIO, DESCRIPCION, PHI
    escenarios_dict = {}
    for _, row in df_escenarios.iterrows():
        id_esc = int(row['ID_ESCENARIO'])
        escenarios_dict[id_esc] = {
            "DESCRIPCION": str(row['DESCRIPCION']).strip().upper(),
            "PHI": float(row['PHI'])
        }
    
    print(f"        - {len(escenarios_dict)} escenarios cargados")
    print("          ✓ Parámetros del modelo cargados exitosamente")
    
    return {
        'SMM_MODELO': smm_lista,
        'ESCENARIOS': escenarios_dict
    }

def aplicar_modelo_prepago(
        capital_inicial: pd.Series,
        pagos_interes: pd.Series,
        tasas_smm: pd.Series,
        escenarios: Dict[str, Any],
        id_escenario: int,
        num_periodos: int = 90,
) -> Dict[str, Any]:
    """
    Aplica el modelo de prepago descrito en el documento para construir una matriz
    de flujos y saldos, y luego separa los flujos de caja en capital e interés.
    :param capital_inicial:
    :param pagos_interes:
    :param tasas_smm:
    :param id_escenario:
    :param num_periodos:
    :return: Dict[str, Any]: Un diccionario que contiene:
            - 'matriz_f': Un DataFrame de pandas (num_periodosxnum_periodos) con la matriz de flujos y saldos.
            - 'flujos_de_caja': Un DataFrame con los flujos de caja totales, de capital
                                y de interés para cada periodo.
            - 'info_escenario': Diccionario con la descripción y factor phi del escenario usado.
    """

    # --- 1. Validación y Preparación de Datos ---
    if not (
            len(capital_inicial) == num_periodos
            and len(pagos_interes) == num_periodos
            and len(tasas_smm) == num_periodos
    ):
        raise ValueError(f"Todos los vectores de entrada deben tener una longitud de {num_periodos}.")

    if id_escenario not in escenarios:
        raise ValueError(f"ID de escenario '{id_escenario}' no es válido. Opciones: {list(escenarios.keys())}")

    info_escenario = escenarios[id_escenario]
    phi = info_escenario["PHI"]

    # Convertir a arrays de NumPy para cálculos eficientes
    capital_np = capital_inicial.to_numpy()
    interes_np = pagos_interes.to_numpy()
    smm_np = tasas_smm.to_numpy()

    # Tasa de prepago ajustada por el escenario: Min(1, φ * SMM)
    smm_ajustado = np.minimum(1.0, phi * smm_np)

    # --- 2. CÁLCULO DE LA PRODUCTORIA (Π) ---
    # La productoria ajusta el interés I_i basado en los prepagos de periodos anteriores.
    # El factor para el periodo i es: Π_{l=0 a i-1} (1 - SMM_l_ajustado)
    tasa_perdida_interes = 1 - smm_ajustado

    tasa_perdida_interes_acum = np.cumprod(tasa_perdida_interes)
    # Para el periodo i, necesitamos el producto hasta i-1.
    # El factor para el periodo 0 es 1 (productoria vacía).
    # Para i>0, el factor es factor_supervivencia_acumulado[i-1].
    factor_ajuste_interes = np.insert(tasa_perdida_interes_acum[:-1], 0, 1.0)

    # Inicializar la matriz f . Será triangular inferior.
    f = np.zeros((num_periodos, num_periodos))

    # --- 2. Construcción Iterativa de la Matriz f_ij ---
    for j in range(num_periodos):  # Itera sobre las columnas
        # print("j ----->",j)
        for i in range(j, num_periodos):  # Itera sobre las filas
            # print("i ----->", i)

            # El caso i < j (triángulo superior) ya es 0 por la inicialización.

            if j == 0:
                # Primera columna. El capital K_ij es el capital inicial k_i.
                capital_ij = capital_np[i]
            else:
                # Columnas subsiguientes. El capital K_ij es el saldo del periodo anterior f_{i, j-1}.
                capital_ij = f[i, j - 1]

            # print(f"CAPITAL EN LA ITERACION ({j},{i}) ->{capital_ij}")
            if i > j:
                # Caso: Triángulo inferior (fuera de la diagonal)
                # Saldo remanente después del prepago del periodo j.
                # f_{i,j} = K_{i,j} * (1 – Min(1, φ·SMM_j))
                f[i, j] = capital_ij * (1 - smm_ajustado[j])

            elif i == j:
                # Caso: Diagonal (i = j)
                # Representa el flujo de caja total del periodo i.

                # Componente de flujo programado: K_ii + I_i * Π
                interes_ajustado = interes_np[i] * factor_ajuste_interes[i]
                flujo_programado = capital_ij + interes_ajustado

                # print(f"FLUJO EN LA ITERACION ({j},{i}) ->{flujo_programado}")
                # print(f"CAPITAL EN LA ITERACION ({j},{i}) ->{capital_ij}")
                # print(f"INTERES EN LA ITERACION ({j},{i}) ->{interes_np[i]}")

                # Componente de prepago: se calcula sobre los saldos remanentes de periodos futuros.
                if i < num_periodos - 1:
                    if j == 0:
                        # Para f[0,0], la base del prepago es la suma de los capitales iniciales futuros
                        base_prepago = np.sum(capital_np[i + 1:])
                    else:
                        # Para f[i,i], la base es la suma de saldos de la columna anterior (j-1)
                        base_prepago = np.sum(f[i + 1:, j - 1])

                    monto_prepago = base_prepago * smm_ajustado[i]
                    # print(f"BASE PREPAGO EN LA ITERACION ({j},{i}) ->{base_prepago}")
                    # print(f"SMM ADJ EN LA ITERACION ({j},{i}) ->{smm_ajustado[i]}")
                    # print(f"SMM EN LA ITERACION ({j},{i}) ->{smm_np[i]}")

                else:
                    # En el último periodo no hay saldos futuros para prepagar.
                    monto_prepago = 0

                f[i, i] = flujo_programado + monto_prepago

    # --- 3. Post-procesamiento: Separar Capital e Interes ---
    # Extraemos la diagonal de la matriz f (flujos de caja totales por periodo).
    flujo_total = np.diag(f)

    # El flujo de interés es el interes programado para cada periodo.
    flujo_interes = interes_np * factor_ajuste_interes

    # El flujo de capital es la diferencia (amortización programada + prepagos).
    flujo_capital = flujo_total - flujo_interes

    # Control: Si el interés es negativo, se toma como 0.
    flujo_interes = np.maximum(0, flujo_interes)

    # --- 4. Formateo de la Salida ---
    nombres_columnas = [f"PERIODO_{p + 1}" for p in range(num_periodos)]
    nombres_indices = [f"PERIODO_{p + 1}" for p in range(num_periodos)]

    matriz_f_df = pd.DataFrame(f, index=nombres_indices, columns=nombres_columnas)

    flujos_df = pd.DataFrame({
        "FLUJO": flujo_total,
        "AMORTIZACION": flujo_capital,
        "INTERES": flujo_interes,
    }, index=nombres_columnas)

    return {
        "MATRIZ_F": matriz_f_df,
        "FLUJOS": flujos_df,
        "INFO_ESCENARIO": info_escenario,
    }

def estandariza_vencimiento(row, fecha_t):
    fv = row['FECHA_VENCIMIENTO_CUOTA']
    if fv < fecha_t:
        return fecha_t + pd.Timedelta(days=1)
    elif fv.year == fecha_t.year and fv.month == fecha_t.month:
        return fecha_t + pd.Timedelta(days=1)
    else:
        return fv.replace(day=10)


def lectura_interfaz_de_datos(fecha_t: datetime.datetime)-> pd.DataFrame:
    from procesamiento_datos_input.cache_tablas import leer_interfaz_con_cache

    interfaz_t = leer_interfaz_con_cache(
        ruta_red=RUTA_INTERFAZ_DE_DATOS,
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
    )

    subproductos_validos_hip = [
        "20", "30", "40", "50", "60", "70", "80", "90", "120", "130", 
        "150", "170", "180", "190", "200", "220", "230", "235", "240", "260", 
        "335", "435", "535", "635", "735", "835", "935", "970", "980", "990", 
        "1235", "1335", "1535", "1735", "1835", "1935", "2035", "2235", "2335", 
        "2435", "2635", "9735", "9835", "9935"
    ]

    return interfaz_t[((interfaz_t['SISTEMA'] == "HIP") & (interfaz_t['CODIGO_PRODUCTO'] == "150003") & (interfaz_t['CODIGO_SUBPRODUCTO'].isin(subproductos_validos_hip)))].reset_index(drop=True).copy()


def procesamiento_y_guardado(
    fecha_t: datetime.datetime,
    interfaz_hip_t: pd.DataFrame,
    smm_modelo: list = None,
    escenarios: Dict[str, Any] = None
) -> None:
    """
    Procesa los datos de entrada y genera los resultados del modelo de prepago.
    
    Args:
        fecha_t: Fecha de proceso
        interfaz_hip_t: DataFrame con los datos de entrada
        smm_modelo: Lista con las tasas SMM del modelo
        escenarios: Diccionario con la configuración de escenarios
    """
    
    # Si no se pasan parámetros, cargarlos
    if smm_modelo is None or escenarios is None:
        parametros = lectura_parametros_modelo()
        smm_modelo = parametros['SMM_MODELO']
        escenarios = parametros['ESCENARIOS']
    
    map_glosa_origen = {
        "30": "CREDITOS COMERCIALES",
        "60": "CREDITOS COMERCIALES",
        "90": "CREDITOS COMERCIALES",
        "260": "CREDITOS COMERCIALES",
        "970": "CREDITOS COMERCIALES",
        "335": "CREDITOS COMERCIALES",
        "635": "CREDITOS COMERCIALES",
        "935": "CREDITOS COMERCIALES",
        "2635": "CREDITOS COMERCIALES",
        "9735": "CREDITOS COMERCIALES",

        "220": "CREDITOS CONSUMO",
        "230": "CREDITOS CONSUMO",
        "2235": "CREDITOS CONSUMO",
        "2335": "CREDITOS CONSUMO",

        "20": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",
        "40": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",
        "240": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",
        "235": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",
        "435": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",
        "2435": "CREDITOS HIPOTECARIOS VIVIENDA LETRAS",

        "50": "CREDITOS HIPOTECARIOS VIVIENDA MUTUO",
        "70": "CREDITOS HIPOTECARIOS VIVIENDA MUTUO",
        "535": "CREDITOS HIPOTECARIOS VIVIENDA MUTUO",
        "735": "CREDITOS HIPOTECARIOS VIVIENDA MUTUO",

        "80": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "120": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "130": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "150": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "170": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "180": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "190": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "200": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "980": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "990": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "835": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1235": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1335": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1535": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1735": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1835": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "1935": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "2035": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "9835": "CREDITOS HIPOTECARIOS VIVIENDA OTROS",
        "9935": "CREDITOS HIPOTECARIOS VIVIENDA OTROS"
    }

    # Filtrar solo los códigos válidos
    codigos_validos = set(map_glosa_origen.keys())
    interfaz_hip_t = interfaz_hip_t[interfaz_hip_t["CODIGO_SUBPRODUCTO"].isin(codigos_validos)].copy()

    print("      • Preparando datos para procesamiento...")

    interfaz_hip_t["GLOSA_CODIGO_SUBPRODUCTO"] = interfaz_hip_t["CODIGO_SUBPRODUCTO"].map(map_glosa_origen)
    interfaz_hip_t['FECHA_VENCIMIENTO_AJUSTADA'] = interfaz_hip_t.apply(estandariza_vencimiento, axis=1, fecha_t=fecha_t)

    tabla_desarrollo = pd.DataFrame()
    
    print("\n      • Procesando por tipo de crédito:")
    for sub_producto in interfaz_hip_t["GLOSA_CODIGO_SUBPRODUCTO"].unique():
        print(f"        - Analizando {sub_producto}...")
        df_filtrado = interfaz_hip_t[interfaz_hip_t["GLOSA_CODIGO_SUBPRODUCTO"] == sub_producto]
        print(f"          Registros a procesar: {len(df_filtrado):,}")
        df_iter = df_filtrado.groupby(["FECHA_VENCIMIENTO_AJUSTADA"], as_index=False).agg({"AMORTIZACION": "sum",
                                                                                           "INTERES": "sum"})
        df_iter = df_iter.sort_values("FECHA_VENCIMIENTO_AJUSTADA", ascending=True).reset_index(drop=True)

        if len(df_iter) > 366:
            extra = df_iter.iloc[366:]
            suma_amort = extra["AMORTIZACION"].sum()
            suma_interes = extra["INTERES"].sum()
            df_iter = df_iter.iloc[:366].copy()
            df_iter.loc[365, "AMORTIZACION"] += suma_amort
            df_iter.loc[365, "INTERES"] += suma_interes

        df_iter = df_iter.reset_index(drop=True)
        
        print("\n          • Procesando escenarios:")
        for esc in escenarios.keys():
            print(f"            - Calculando escenario {escenarios[esc]['DESCRIPCION']}...")
            resultados = aplicar_modelo_prepago(
                capital_inicial=df_iter["AMORTIZACION"],
                pagos_interes=df_iter["INTERES"],
                tasas_smm=pd.Series(smm_modelo[:len(df_iter)]),
                escenarios=escenarios,
                id_escenario=esc,
                num_periodos=len(df_iter),
            )
            print(f"              ✓ Escenario {escenarios[esc]['DESCRIPCION']} completado")
            registros = len(resultados['FLUJOS']['AMORTIZACION'])
            resultados['FLUJOS'] = resultados['FLUJOS'].reset_index(drop=True)

            tabla_desarrollo_tmp = {
                "FECHA_PROCESO": [fecha_t] * registros,
                "CODIGO_EMPRESA": [1] * registros,
                "OPERACION": [np.nan] * registros,
                "COD_ACT/PAS": ["ACT"] * registros,
                "MONEDA_ORIGEN": ["CLF"] * registros,
                "MONEDA_COMPENSACION": ["CLF"] * registros,
                "COMPENSACION": [np.nan] * registros,
                "CODIGO_PRODUCTO": ["MT_R13_HIPOTECARIO_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                "CODIGO_SUBPRODUCTO": ["MT_R13_"+str(sub_producto) + "_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                "FECHA_CREACION": [np.nan] * registros,
                "NUMERO_CUOTA": [np.nan] * registros,
                "FECHA_INICIO_CUOTA": [np.nan] * registros,
                "FECHA_VENCIMIENTO_CUOTA": df_iter["FECHA_VENCIMIENTO_AJUSTADA"],
                "FECHA_PAGO": [np.nan] * registros,
                "FECHA_REPRICING": [np.nan] * registros,
                "AMORTIZACION": resultados['FLUJOS']['AMORTIZACION'],
                "INTERES": resultados['FLUJOS']['INTERES'],
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



            tabla_desarrollo = pd.concat(
                [tabla_desarrollo, pd.DataFrame(tabla_desarrollo_tmp)],ignore_index=True)


    print("\n      • Guardando resultados...")
    
    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy",
        "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy",
        "FECHA_REPRICING": "dd-mm-yyyy"
    }

    print("        - Actualizando archivo principal...")
    guardar_excel(
        ruta_archivo=ARCHIVO_OUTPUT_MODELO,
        hojas={"DESARROLLO": tabla_desarrollo},
        formatos_columnas=formatos_excel,
    )
    print("          ✓ Archivo principal actualizado")

    # print("        - Guardando copia en directorio de ejecuciones...")
    # ut.copia_archivo_en_ruta(RUTA_OUTPUT_MODELO,
    #                          cr.EJECUCIONES_MR_PREPAGO_HIPOTECARIO,
    #                          Path(RUTA_OUTPUT_MODELO).stem + ".xlsm",
    #                          agregar_fecha=True)
    # print("          ✓ Copia de respaldo creada")


def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo de prepago hipotecario.
    Esta función es llamada por el orquestador y encapsula toda la lógica necesaria.
    
    Args:
        fecha_proceso (datetime.datetime): Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso de error
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO PREPAGO HIPOTECARIO")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")

        print("[1/4] Cargando parámetros del modelo...")
        parametros = lectura_parametros_modelo()
        SMM_MODELO = parametros['SMM_MODELO']
        ESCENARIOS = parametros['ESCENARIOS']
        print("      ✓ Parámetros cargados correctamente\n")

        print("[2/4] Leyendo datos de interfaz...")
        interfaz_de_datos_hipotecario = lectura_interfaz_de_datos(fecha_proceso)
        
        # Validar que los datos no estén vacíos
        if interfaz_de_datos_hipotecario.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros en la interfaz de datos para esta fecha.")
        
        print(f"      ✓ Datos leídos exitosamente - {len(interfaz_de_datos_hipotecario):,} registros encontrados")

        print("\n[3/4] Procesando información y calculando prepagos...")
        procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_hipotecario, SMM_MODELO, ESCENARIOS)
        
        print("\n[4/4] Proceso completado:")
        print("      ✓ Cálculos realizados")
        print("      ✓ Archivos guardados")
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO PREPAGO HIPOTECARIO:")
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
    # fecha_proceso_str = "2025-11-28"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Usar la nueva función ejecutar_modelo
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)



