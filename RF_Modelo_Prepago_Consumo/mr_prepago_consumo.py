import pandas as pd
import numpy as np
from typing import Dict, Any
import os
import datetime
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut



# Para una ejecucion directa del script
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr


# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)


# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
RUTA_INTERFAZ_DE_DATOS = cr.resolver_ruta(config_ext['modelos']['mr_prepago_consumo']['interfaz_datos_input'])
ARCHIVO_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['mr_prepago_consumo']['excel_output'])
ARCHIVO_PARAMETROS = cr.resolver_ruta(config_ext['modelos']['mr_prepago_consumo']['excel_parametros_input'])



def lectura_parametros_modelo() -> Dict[str, Any]:
    """
    Lee los parámetros del modelo desde el archivo de configuración Excel.
    
    Returns:
        Dict[str, Any]: Diccionario con las siguientes claves:
            - 'SMM_MODELO': Diccionario con las tasas SMM de prepago por subproducto
            - 'ESCENARIOS': Diccionario con la configuración de escenarios
    """
    print("      • Leyendo parámetros del modelo desde Excel...")
    
    if not ARCHIVO_PARAMETROS.exists():
        raise FileNotFoundError(f"No se encontró el archivo de parámetros: {ARCHIVO_PARAMETROS}")
    
    # Leer SMM_MODELO desde la hoja SMM_PREPAGO (ahora con 5 columnas)
    df_smm = pd.read_excel(ARCHIVO_PARAMETROS, sheet_name='SMM_PREPAGO')
    
    # Crear diccionario con cada columna como una lista
    smm_modelo_dict = {}
    nombre_subproductos = ["CONSUMO", "AUTOMOTRIZ", "REFINANCIADO", "RENEGOCIADO", "CONSOLIDADO"]
    count=0
    for columna in df_smm.columns:
        # Eliminar valores NaN y convertir a lista
        smm_modelo_dict[nombre_subproductos[count]] = df_smm[columna].dropna().tolist()
        print(f"        - {len(smm_modelo_dict[nombre_subproductos[count]])} tasas SMM cargadas para {nombre_subproductos[count]}")
        count += 1
    
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
        'SMM_MODELO': smm_modelo_dict,
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
    
    :param capital_inicial: Serie con el capital inicial por periodo
    :param pagos_interes: Serie con los pagos de interés por periodo
    :param tasas_smm: Serie con las tasas SMM por periodo
    :param escenarios: Diccionario con la configuración de escenarios
    :param id_escenario: ID del escenario a aplicar
    :param num_periodos: Número de periodos a procesar
    :return: Dict[str, Any]: Un diccionario que contiene:
            - 'MATRIZ_F': Un DataFrame de pandas (num_periodosxnum_periodos) con la matriz de flujos y saldos.
            - 'FLUJOS': Un DataFrame con los flujos de caja totales, de capital
                        y de interés para cada periodo.
            - 'INFO_ESCENARIO': Diccionario con la descripción y factor phi del escenario usado.
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
        for i in range(j, num_periodos):  # Itera sobre las filas

            # El caso i < j (triángulo superior) ya es 0 por la inicialización.

            if j == 0:
                # Primera columna. El capital K_ij es el capital inicial k_i.
                capital_ij = capital_np[i]
            else:
                # Columnas subsiguientes. El capital K_ij es el saldo del periodo anterior f_{i, j-1}.
                capital_ij = f[i, j - 1]

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

                # Componente de prepago: se calcula sobre los saldos remanentes de periodos futuros.
                if i < num_periodos - 1:
                    if j == 0:
                        # Para f[0,0], la base del prepago es la suma de los capitales iniciales futuros
                        base_prepago = np.sum(capital_np[i + 1:])
                    else:
                        # Para f[i,i], la base es la suma de saldos de la columna anterior (j-1)
                        base_prepago = np.sum(f[i + 1:, j - 1])

                    monto_prepago = base_prepago * smm_ajustado[i]

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
        return fv.replace(day=5)


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


def procesamiento_y_guardado(
    fecha_t: datetime.datetime,
    interfaz_de_datos_t: pd.DataFrame,
    smm_modelo: Dict[str, list] = None,
    escenarios: Dict[str, Any] = None
) -> None:
    """
    Procesa los datos de entrada y genera los resultados del modelo de prepago.
    
    Args:
        fecha_t: Fecha de proceso
        interfaz_de_datos_t: DataFrame con los datos de entrada
        smm_modelo: Diccionario con las tasas SMM por subproducto
        escenarios: Diccionario con la configuración de escenarios
    """
    
    # Si no se pasan parámetros, cargarlos
    if smm_modelo is None or escenarios is None:
        parametros = lectura_parametros_modelo()
        smm_modelo = parametros['SMM_MODELO']
        escenarios = parametros['ESCENARIOS']

    # Definir listas de subproductos por categoría
    subproducto_consumo_consumo = ["1", "4", "31", "33", "35", "68", "69", "71", "73", "78", "81"]
    subproducto_consumo_automotriz = ["16"]
    subproducto_consumo_refinanciado = ["24", "36", "43", "75"]
    subproducto_consumo_consolidado = ["27", "32", "34", "37", "42", "46"]
    subproducto_renegociado = ["1", "4", "16", "23", "24", "27", "31", "32", 
                               "35", "37", "42", "43", "46", "100"]

    print("      • Preparando datos para procesamiento...")
    
    condicion = [
        (interfaz_de_datos_t['SISTEMA'] == "CRC") & (interfaz_de_datos_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_consumo)),
        (interfaz_de_datos_t['SISTEMA'] == "CRC") & (interfaz_de_datos_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_automotriz)),
        (interfaz_de_datos_t['SISTEMA'] == "CRC") & (interfaz_de_datos_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_refinanciado)),
        (interfaz_de_datos_t['SISTEMA'] == "CRC") & (interfaz_de_datos_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_consumo_consolidado)),
        (interfaz_de_datos_t['SISTEMA'] == "REC") & (interfaz_de_datos_t['CODIGO_PRODUCTO'] == "150001") & (interfaz_de_datos_t['CODIGO_SUBPRODUCTO'].isin(subproducto_renegociado)),
    ]
 
    resultado = [
        "CONSUMO", 
        "AUTOMOTRIZ",
        "REFINANCIADO",
        "CONSOLIDADO",
        "RENEGOCIADO"
    ]
    
    interfaz_de_datos_t["GLOSA_CODIGO_DESTINOCREDITO"] = np.select(
        condicion, 
        resultado, 
        default="OTROS"
    )

    registros_otros = interfaz_de_datos_t[interfaz_de_datos_t["GLOSA_CODIGO_DESTINOCREDITO"] == "OTROS"]
    if not registros_otros.empty:
        print("\n      ¡ADVERTENCIA!: Se encontraron registros con subproductos no válidos")
        raise ValueError("Verifique la configuración de subproductos válidos y las condiciones de mapeo.")



    interfaz_de_datos_t['FECHA_VENCIMIENTO_AJUSTADA'] = interfaz_de_datos_t.apply(estandariza_vencimiento, axis=1, fecha_t=fecha_t)

    tabla_desarrollo = pd.DataFrame()
    
    print("\n      • Procesando por tipo de crédito:")
    for sub_producto in interfaz_de_datos_t["GLOSA_CODIGO_DESTINOCREDITO"].unique():
        print(f"        - Analizando {sub_producto}...")
        df_filtrado = interfaz_de_datos_t[interfaz_de_datos_t["GLOSA_CODIGO_DESTINOCREDITO"] == sub_producto]
        print(f"          Registros a procesar: {len(df_filtrado):,}")
        df_iter = df_filtrado.groupby(["FECHA_VENCIMIENTO_AJUSTADA"], as_index=False).agg({"AMORTIZACION": "sum",
                                                                                           "INTERES": "sum"})
        df_iter = df_iter.sort_values("FECHA_VENCIMIENTO_AJUSTADA", ascending=True).reset_index(drop=True)


        if len(df_iter) > 90:
            extra = df_iter.iloc[90:]
            suma_amort = extra["AMORTIZACION"].sum()
            suma_interes = extra["INTERES"].sum()
            df_iter = df_iter.iloc[:90].copy()
            df_iter.loc[89, "AMORTIZACION"] += suma_amort
            df_iter.loc[89, "INTERES"] += suma_interes

        df_iter = df_iter.reset_index(drop=True)
        print("\n          • Procesando escenarios:")
        for esc in escenarios.keys():
            print(f"            - Calculando escenario {escenarios[esc]['DESCRIPCION']}...")
            resultados = aplicar_modelo_prepago(
                capital_inicial=df_iter["AMORTIZACION"],
                pagos_interes=df_iter["INTERES"],
                tasas_smm=pd.Series(smm_modelo[sub_producto][:len(df_iter)]),
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
                "MONEDA_ORIGEN": ["CLP"] * registros,
                "MONEDA_COMPENSACION": ["CLP"] * registros,
                "COMPENSACION": [np.nan] * registros,
                "CODIGO_PRODUCTO": ["MT_R13_CONSUMO_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                "CODIGO_SUBPRODUCTO": ["MT_R13_"+str(sub_producto) + "_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                "FECHA_CREACION": [np.nan] * registros,
                "NUMERO_CUOTA": [np.nan] * registros,
                "FECHA_INICIO_CUOTA": [np.nan] * registros,
                "FECHA_VENCIMIENTO_CUOTA": df_iter["FECHA_VENCIMIENTO_AJUSTADA"],
                "FECHA_PAGO":  df_iter["FECHA_VENCIMIENTO_AJUSTADA"],
                "FECHA_REPRICING":  df_iter["FECHA_VENCIMIENTO_AJUSTADA"],
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

            print("              • Consolidando datos del escenario...")
            tabla_desarrollo = pd.concat(
                [tabla_desarrollo, pd.DataFrame(tabla_desarrollo_tmp)],ignore_index=True)
            print(f"                ✓ Consolidación completada - {len(tabla_desarrollo):,} registros acumulados")


    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy",
        "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy",
        "FECHA_REPRICING": "dd-mm-yyyy"
    }

    print("\n      • Guardando resultados...")
    print("        - Actualizando archivo principal...")
    ut.cargar_datos_xlsm(ruta_archivo=ARCHIVO_OUTPUT_MODELO,
                         nombre_hoja="DESARROLLO",
                         datos=tabla_desarrollo,
                         formatos_columnas=formatos_excel)
    print("          ✓ Archivo principal actualizado")

    # print("        - Guardando copia en directorio de ejecuciones...")
    # ut.copia_archivo_en_ruta(RUTA_OUTPUT_MODELO,
    #                           cr.EJECUCIONES_MR_PREPAGO_CONSUMO,
    #                          Path(RUTA_OUTPUT_MODELO).stem + ".xlsm",
    #                          agregar_fecha=True)
    # print("          ✓ Copia de respaldo creada")


def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo de prepago consumo.
    Esta función es llamada por el orquestador y encapsula toda la lógica necesaria.
    
    Args:
        fecha_proceso (datetime.datetime): Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso de error
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO PREPAGO CONSUMO")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")

        print("[1/4] Cargando parámetros del modelo...")
        parametros = lectura_parametros_modelo()
        SMM_MODELO = parametros['SMM_MODELO']
        ESCENARIOS = parametros['ESCENARIOS']
        print("      ✓ Parámetros cargados correctamente\n")

        print("[2/4] Leyendo datos de interfaz...")
        interfaz_de_datos_consumo_t = lectura_interfaz_de_datos(fecha_proceso)
        
        # Validar que los datos no estén vacíos
        if interfaz_de_datos_consumo_t.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros en la interfaz de datos para esta fecha.")
        
        print(f"      ✓ Datos leídos exitosamente - {len(interfaz_de_datos_consumo_t):,} registros encontrados")


        print("\n[3/4] Procesando información y calculando prepagos...")
        procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_consumo_t, SMM_MODELO, ESCENARIOS)
        
        print("\n[4/4] Proceso completado:")
        print("      ✓ Cálculos realizados")
        print("      ✓ Archivos guardados")
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("="*50)
        
        return True
        
    except Exception as e:
        print("\nERROR EN EL MODELO PREPAGO CONSUMO:")
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
    # fecha_proceso_str = "2026-01-02"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Usar la nueva función ejecutar_modelo
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)



