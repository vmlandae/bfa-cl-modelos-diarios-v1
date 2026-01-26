import pandas as pd
import numpy as np
from typing import Dict, Any
import datetime
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut

# # Para una ejecucion directa del script
# BASE_DIR = Path(__file__).resolve().parent.parent
# if str(BASE_BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importar configuraciones
from config import config_rutas as cr

# Cargar configuración de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r') as file:
    config_ext = yaml.safe_load(file)

# Configuración de rutas
ARCHIVO_INPUT = Path(config_ext['modelos']['mr_prepago_cmr']['ms_access_input'])
TABLA_INPUT = config_ext['modelos']['mr_prepago_cmr']['ms_access_tabla_input']
ARCHIVO_OUTPUT_MODELO = Path(config_ext['modelos']['mr_prepago_cmr']['excel_output'])
ARCHIVO_PARAMETROS = Path(config_ext['modelos']['mr_prepago_cmr']['excel_parametros_input'])



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
    nombre_subproductos = ["SAV", "NO_SAV"]
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


def lectura_interfaz_de_datos(fecha_t: datetime.datetime) -> pd.DataFrame:
    """
    Lee los datos de la interfaz desde la base de datos MS Access para una fecha específica.
    
    Args:
        fecha_t (datetime.datetime): Fecha de proceso para filtrar los datos
        
    Returns:
        pd.DataFrame: DataFrame con los datos de tarjetas de crédito CMR filtrados y renombrados
    """
    
    query="""
        SELECT  
            RF_BD_Gestion_RM.Fec_Pro,
            RF_BD_Gestion_RM.Fec_Vcto,
            RF_BD_Gestion_RM.Cod_Sub_Pro,
            RF_BD_Gestion_RM.Cap_Amort,
            RF_BD_Gestion_RM.Int_Total_Cont
        FROM RF_BD_Gestion_RM
        WHERE Cod_Pro = 'TARJETA DE CREDITO'
        AND RF_BD_Gestion_RM.Fec_Pro = #{}#;
    """.format(fecha_t.strftime('%Y-%m-%d'))

    interfaz_t = ut.lectura_datos_ms_access(ruta=ARCHIVO_INPUT, query=query)
    interfaz_t = interfaz_t.rename(columns={
                                            'Fec_Pro': 'FECHA_PROCESO',
                                            'Fec_Vcto': 'FECHA_VENCIMIENTO_CUOTA',
                                            'Cod_Sub_Pro': 'CODIGO_SUBPRODUCTO',
                                            'Cap_Amort': 'AMORTIZACION',
                                            'Int_Total_Cont': 'INTERES'})

    return interfaz_t


def procesamiento_y_guardado(fecha_t: datetime.datetime, 
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
    
    
    # Mapeo de códigos de subproducto a categorías de modelo
    # SAV: Super Avance, NO_SAV: Productos que no son Super Avance
    map_glosa_origen = {
        "AVANCE": "NO_SAV",
        "AVANCE RENEGOCIADO": "NO_SAV",
        "AVANCE RENEGOCIADO-INCUMPLIMIENTO": "NO_SAV",
        "AVANCE RENEGOCIADO-MORA": "NO_SAV",
        "AVANCE-INCUMPLIMIENTO": "NO_SAV",
        "AVANCE-INCUMPLIMIENTO-MORA": "NO_SAV",
        "AVANCE-MORA": "NO_SAV",

        "COMPRA": "NO_SAV",
        "COMPRA RENEGOCIADO": "NO_SAV",
        "COMPRA RENEGOCIADO-INCUMPLIMIENTO": "NO_SAV",
        "COMPRA RENEGOCIADO-INCUMPLIMIENTO-MORA": "NO_SAV",
        "COMPRA RENEGOCIADO-MORA": "NO_SAV",
        "COMPRA-INCUMPLIMIENTO": "NO_SAV",
        "COMPRA-INCUMPLIMIENTO-MORA": "NO_SAV",
        "COMPRA-MORA": "NO_SAV",

        "REVOLVING": "NO_SAV",
        "REVOLVING RENEGOCIADO-INCUMPLIMIENTO": "NO_SAV",
        "REVOLVING RENEGOCIADO-INCUMPLIMIENTO-MORA": "NO_SAV",
        "REVOLVING RENEGOCIADO-MORA": "NO_SAV",
        "REVOLVING-INCUMPLIMIENTO-MORA": "NO_SAV",

        "SUPER AVANCE": "SAV",
        "SUPER AVANCE RENEGOCIADO": "SAV",
        'SUPER AVANCE RENEGOCIADO-MORA': "NO_SAV",
        "SUPER AVANCE-INCUMPLIMIENTO": "SAV",
        'SUPER AVANCE-INCUMPLIMIENTO-MORA': "NO_SAV",
        "SUPER AVANCE MORA": "NO_SAV",
        "SUPER AVANCE-MORA": "NO_SAV",

    }

    # Procesamiento y limpieza de códigos de subproducto
    print("      • Procesando y mapeando códigos de subproducto...")
    interfaz_de_datos_t["CODIGO_SUBPRODUCTO"] = interfaz_de_datos_t["CODIGO_SUBPRODUCTO"].astype(str).str.strip().str.upper()

    interfaz_de_datos_t["GLOSA_CODIGO_SUBPRODUCTO"] = interfaz_de_datos_t["CODIGO_SUBPRODUCTO"].map(map_glosa_origen)

    if interfaz_de_datos_t["GLOSA_CODIGO_SUBPRODUCTO"].isnull().any():
        productos_no_mapeados = interfaz_de_datos_t[interfaz_de_datos_t["GLOSA_CODIGO_SUBPRODUCTO"].isnull()]["CODIGO_SUBPRODUCTO"].unique()
        raise ValueError(f"Se encontraron subproductos no mapeados: {productos_no_mapeados}")

    tabla_desarrollo = pd.DataFrame()
    
    # Validación de días de vencimiento permitidos para tarjetas CMR
    # Se permiten días específicos de facturación según las reglas de negocio
    dias_permitidos = {(fecha_t + pd.Timedelta(days=1)).day, (fecha_t + pd.Timedelta(days=20)).day, 5, 10, 15, 20, 25,28 ,30}
    dias_vencimiento = set(interfaz_de_datos_t['FECHA_VENCIMIENTO_CUOTA'].dt.day.unique())
    if not dias_vencimiento.issubset(dias_permitidos):
        raise ValueError(f"Existen fechas de vencimiento con días no esperados: {dias_vencimiento - dias_permitidos}")
    
    interfaz_de_datos_t['DIA_FACTURACION_AJUSTADO'] = interfaz_de_datos_t['FECHA_VENCIMIENTO_CUOTA'].dt.day

    # Ajuste especial para productos SAV en febrero
    # En febrero, se cambia el día 28 al 30 para estandarizar el procesamiento
    mask_sav_febrero = (
        (interfaz_de_datos_t['GLOSA_CODIGO_SUBPRODUCTO'] == 'SAV') & 
        (interfaz_de_datos_t['FECHA_VENCIMIENTO_CUOTA'].dt.month == 2)
    )

    # Cambiar el día a 28 para SAV en febrero (o el día que necesites)
    interfaz_de_datos_t.loc[mask_sav_febrero, 'DIA_FACTURACION_AJUSTADO'] = interfaz_de_datos_t.loc[mask_sav_febrero, 'DIA_FACTURACION_AJUSTADO'].replace({28:30})

    # Procesamiento por cada tipo de subproducto (SAV / NO_SAV)
    for sub_producto in interfaz_de_datos_t["GLOSA_CODIGO_SUBPRODUCTO"].unique():
        df_filtrado_subproducto = interfaz_de_datos_t[interfaz_de_datos_t["GLOSA_CODIGO_SUBPRODUCTO"] == sub_producto]
        # print(f"\n    • Procesando producto: {sub_producto} - Registros: {len(df_filtrado_subproducto):,}")
        # Procesamiento por cada día de facturación dentro del subproducto
        for fecha_facturacion in df_filtrado_subproducto['DIA_FACTURACION_AJUSTADO'].unique():
            if fecha_facturacion == 30 and sub_producto == 'SAV':
                print(f"\n      • Procesando subproducto: {sub_producto} - Fecha Vencimiento Día: {fecha_facturacion} (incluye día 28)")
            else:
                print(f"\n      • Procesando subproducto: {sub_producto} - Fecha Vencimiento Día: {fecha_facturacion}")
            
            # Filtrar datos por día de facturación específico
            df_filtrado = df_filtrado_subproducto[df_filtrado_subproducto['DIA_FACTURACION_AJUSTADO'] == fecha_facturacion]
            # Agrupar y sumarizar los datos por fecha de vencimiento
            df_filtrado = df_filtrado.groupby(["FECHA_PROCESO", 'FECHA_VENCIMIENTO_CUOTA', 'GLOSA_CODIGO_SUBPRODUCTO', 'DIA_FACTURACION_AJUSTADO'], as_index=False).agg({"AMORTIZACION": "sum",
                                                                                            "INTERES": "sum"})


            # Construcción del vector de fechas del modelo
            fecha_ini = datetime.datetime(fecha_t.year,fecha_t.month,fecha_facturacion)

            # Este cálculo de fechas considera que siempre en febrero la fecha de facturación es el 28 (caso años bisiestos)
            # Se generan 200 periodos mensuales para cubrir toda la vida útil potencial de las operaciones
            fechas_vector_smm = pd.DataFrame([
                    (fecha_ini + pd.DateOffset(months=i)).replace(day=min((fecha_ini + pd.DateOffset(months=i)).day, 28)) 
                    if (fecha_ini + pd.DateOffset(months=i)).month == 2 
                    else fecha_ini + pd.DateOffset(months=i) 
                    for i in range(200)
                ], columns=["FECHA_VENCIMIENTO_CUOTA_MODELO"])
            # Filtrar solo fechas futuras respecto a la fecha de proceso
            fechas_vector_smm = fechas_vector_smm[fechas_vector_smm['FECHA_VENCIMIENTO_CUOTA_MODELO'] > fecha_t]
            # Hacer merge con los datos reales y completar con ceros donde no hay datos
            df_iter = fechas_vector_smm.merge(df_filtrado, left_on='FECHA_VENCIMIENTO_CUOTA_MODELO', right_on='FECHA_VENCIMIENTO_CUOTA', how='left')
            
            # Rellenar valores faltantes con cero (para fechas sin operaciones)
            df_iter["AMORTIZACION"] = df_iter["AMORTIZACION"].fillna(0)
            df_iter["INTERES"] = df_iter["INTERES"].fillna(0)

            # Agrupar por fecha en caso de duplicados y ordenar cronológicamente
            df_iter = df_iter.groupby(["FECHA_VENCIMIENTO_CUOTA_MODELO"], as_index=False).agg({"AMORTIZACION": "sum",
                                                                                            "INTERES": "sum"})
            df_iter = df_iter.sort_values("FECHA_VENCIMIENTO_CUOTA_MODELO", ascending=True).reset_index(drop=True)

            # Limitar a 90 periodos máximo (consolidando exceso en el periodo 90)
            if len(df_iter) > 90:
                extra = df_iter.iloc[90:]
                suma_amort = extra["AMORTIZACION"].sum()
                suma_interes = extra["INTERES"].sum()
                df_iter = df_iter.iloc[:90].copy()
                df_iter.loc[89, "AMORTIZACION"] += suma_amort
                df_iter.loc[89, "INTERES"] += suma_interes
                # Para eliminar solo las filas con ceros al final del vector (pero conservar los ceros que estén entre valores no ceros)
                mask_no_cero = (df_iter["AMORTIZACION"] != 0) | (df_iter["INTERES"] != 0)
                if mask_no_cero.any():
                    ultimo_indice = mask_no_cero[::-1].idxmax()
                    df_iter = df_iter.iloc[:ultimo_indice + 1].reset_index(drop=True)
                else:
                    df_iter = df_iter.iloc[0:0].reset_index(drop=True)


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
                    "CODIGO_PRODUCTO": ["MT_R13_TC_CMR_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                    "CODIGO_SUBPRODUCTO": ["MT_R13_TC_CMR_"+str(sub_producto) + "_" + str(escenarios[esc]["DESCRIPCION"])] * registros,
                    "FECHA_CREACION": [np.nan] * registros,
                    "NUMERO_CUOTA": [np.nan] * registros,
                    "FECHA_INICIO_CUOTA": [np.nan] * registros,
                    "FECHA_VENCIMIENTO_CUOTA": df_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
                    "FECHA_PAGO":  df_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
                    "FECHA_REPRICING":  df_iter["FECHA_VENCIMIENTO_CUOTA_MODELO"],
                    "AMORTIZACION": resultados['FLUJOS']['AMORTIZACION'],
                    "INTERES": resultados['FLUJOS']['INTERES'],
                    "INTERES_DEVENGADO": [np.nan] * registros,
                    "VP_AMORTIZACION": [np.nan] * registros,
                    "VP_INTERES": [np.nan] * registros,
                    "FACTOR_DE_RIESGO": [np.nan] * registros,
                    "TIPO_CUOTA": [1] * registros,
                    "AREA_NEGOCIO": ["CMR_BKG"] * registros,
                    "CODIGO_EJECUTIVO": [np.nan] * registros,
                    "CODIGO_ESTRATEGIA": ["CMR_BKG"] * registros,
                    "CLASIFICACION_CONTABLE": ["HTM"] * registros,
                    "TIPO_TASA": [1] * registros,
                    "INDEXADOR": [np.nan] * registros,
                    "TASA": [np.nan] * registros,
                    "TASA_CF": [np.nan] * registros,
                    "SPREAD": [np.nan] * registros,
                }
                tabla_desarrollo = pd.concat(
                    [tabla_desarrollo, pd.DataFrame(tabla_desarrollo_tmp)],ignore_index=True)


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


def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo de prepago CMR.
    Esta función es llamada por el orquestador y encapsula toda la lógica necesaria.
    
    Args:
        fecha_proceso (datetime.datetime): Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa, False en caso de error
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO PREPAGO CMR")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")

        print("[1/4] Cargando parámetros del modelo...")
        parametros = lectura_parametros_modelo()
        SMM_MODELO = parametros['SMM_MODELO']
        ESCENARIOS = parametros['ESCENARIOS']
        print("      Parámetros cargados correctamente\n")

        print("[2/4] Leyendo datos de interfaz...")
        interfaz_de_datos_cmr_t = lectura_interfaz_de_datos(fecha_proceso)

        # Validar que los datos no estén vacíos
        if interfaz_de_datos_cmr_t.empty:
            raise ValueError(f"No se encontraron datos para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                            f"Verifique que existan registros en la base de datos para esta fecha.")

        print(f"      Datos leídos exitosamente - {len(interfaz_de_datos_cmr_t):,} registros encontrados")

        print("\n[3/4] Procesando información y calculando prepagos...")
        procesamiento_y_guardado(fecha_proceso, interfaz_de_datos_cmr_t, SMM_MODELO, ESCENARIOS)
        
        print("\n[4/4] Proceso completado:")
        print("      Cálculos realizados")
        print("      Archivos guardados")
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO PREPAGO CMR:")
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
    # fecha_proceso_str = "2025-12-16"

    try:
        fecha_proceso = datetime.datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    # Usar la nueva función ejecutar_modelo
    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)

