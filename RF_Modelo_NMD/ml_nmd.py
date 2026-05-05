import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import sys
import bfa_cl_utilidades as ut
from core.excel_output import guardar_excel

# Configuración de importación para ejecución directa
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importación de módulos internos
from config import config_rutas as cr  # Configuración de rutas del proyecto


# Carga de configuración desde archivo YAML
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r', encoding='utf-8') as file:
    config_ext = yaml.safe_load(file)

# Configuración de rutas (resolver_ruta maneja rutas relativas y absolutas)
ARCHIVO_INPUT = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['ms_access_input'])
ARCHIVO_DAP = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['ms_access_input'])
RUTA_PARAMETROS_NMD = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_parametros_modelo_input'])
RUTA_PARAMETROS_CORE = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_parametros_core_input'])
RUTA_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['ml_nmd']['excel_output'])


def cargar_datos_balance(fecha_t: datetime) -> pd.DataFrame:
    """
    Carga los datos de balance desde la base de datos de gestion.
    Incluye productos: DAP, Cuenta Corriente, Cuenta Vista y Cuentas de Ahorro.
    Usa cache parquet compartido (RF_BD_Gestion_RL) para evitar lecturas
    repetidas de Access y compartir datos con otros modelos (ej: LC).
    """
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    print("      * Ejecutando consulta de datos de balance...")

    # Leer tabla completa RL desde cache compartido
    fecha_access = fecha_t.strftime('%Y-%m-%d')
    query_rl = (
        f"SELECT * FROM [RF_BD_Gestion_RL] "
        f"WHERE [Fec_Pro] = #{fecha_access}#"
    )
    df_rl = leer_tabla_con_cache(
        access_path=ARCHIVO_INPUT,
        nombre_tabla='RF_BD_Gestion_RL',
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
        query=query_rl,
    )

    # Filtro equivalente al HAVING del SQL original
    mask = (
        (df_rl['Cod_Sub_Pro'] == 'DAP')
        | (df_rl['Cod_Sub_Pro'] == 'CTA. CORRIENTE')
        | (df_rl['Cod_Sub_Pro'] == 'CTA. VISTA')
        | (df_rl['Cod_Pro'] == 'CTA. AHORRO')
    )
    df_filtered = df_rl[mask]

    # GROUP BY + SUM equivalente
    data = df_filtered.groupby(
        ['Fec_Pro', 'Cod_A_P', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro'],
        as_index=False,
    ).agg(
        AMORTIZACION_MO=('Cap_Amort', 'sum'),
        INTERES_MO=('Int_Total_Cont', 'sum'),
    )
    data['FLUJO_MO'] = data['AMORTIZACION_MO'] + data['INTERES_MO']

    # ORDER BY Cod_Sub_Pro DESC
    data = data.sort_values('Cod_Sub_Pro', ascending=False).reset_index(drop=True)

    data = ut.estandariza_nombre_columnas_dataframe(data)

    # Mapear códigos de producto del modelo
    condiciones = [
        (data["COD_SUB_PRO"] == "CTA. VISTA") & (data["MONEDA"] == "CLP"),
        (data["COD_SUB_PRO"] == "CTA. CORRIENTE") & (data["MONEDA"] == "CLP"),
        (data["COD_SUB_PRO"] == "CTA. AHORRO GIRO DIFERIDO") & (data["MONEDA"] == "CLF"),
        (data["COD_SUB_PRO"] == "CTA. AHORRO INCONDICIONAL") & (data["MONEDA"] == "CLF"),

        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "CLP"),
        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "CLF"),
        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "USD")
    ]
    asignacion = ["CTA_VTA_CLP", "CTA_CTE_CLP", "AGD_CLF", "AGI_CLF", "DAP_CLP", "DAP_CLF", "DAP_USD"]
    data["COD_PRO_MODELO"] = np.select(condiciones, asignacion, default=None)
    data = data[data["COD_PRO_MODELO"].notna()].reset_index(drop=True)
    
    print(f"        - Datos de balance cargados: {len(data):,} registros")
    print(f"        - Productos encontrados: {data['COD_PRO_MODELO'].value_counts().to_dict()}")
    print("          ✓ Datos de balance procesados exitosamente")

    return data

def cargar_dap_contractual(fecha_t: datetime) -> pd.DataFrame:
    """
    Carga los datos contractuales de DAP con informacion detallada de flujos.
    Incluye amortizacion, intereses y fechas de pago programadas.
    Usa cache parquet compartido (RF_BD_Gestion_RL).
    """
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    print("      * Ejecutando consulta de datos contractuales DAP...")

    # Leer tabla completa RL desde cache compartido (reutiliza si ya fue cacheada)
    fecha_access = fecha_t.strftime('%Y-%m-%d')
    query_rl = (
        f"SELECT * FROM [RF_BD_Gestion_RL] "
        f"WHERE [Fec_Pro] = #{fecha_access}#"
    )
    df_rl = leer_tabla_con_cache(
        access_path=ARCHIVO_DAP,
        nombre_tabla='RF_BD_Gestion_RL',
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
        query=query_rl,
    )

    # Filtro equivalente al WHERE del SQL original
    mask = (
        df_rl['Moneda'].isin(['CLP', 'CLF', 'USD'])
        & (df_rl['Cod_Pro'] == 'DAP')
        & (df_rl['Cod_Sub_Pro'] == 'DAP')
    )
    data = df_rl.loc[mask].copy()

    # Renombrar columnas (equivalente a los alias AS del SQL)
    data = data.rename(columns={
        'Cap_Amort': 'AMORTIZACION_MO',
        'Int_Total_Cont': 'INTERES_MO',
        'Int_Devengado': 'INT_DEVENGADO_MO',
        'VP_Cap_Amort': 'VP_AMORTIZACION_MO',
        'VP_Int_Total_Cont': 'VP_INTERES_MO',
    })

    # Columnas calculadas
    data['FLUJO_MO'] = data['AMORTIZACION_MO'] + data['INTERES_MO']
    data['VP_FLUJO_MO'] = data['VP_AMORTIZACION_MO'] + data['VP_INTERES_MO']

    # Seleccionar solo las columnas del SQL original
    output_columns = [
        'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P', 'Cod_Pro', 'Cod_Sub_Pro',
        'Fec_Pago', 'Dias_Pago',
        'AMORTIZACION_MO', 'INTERES_MO', 'FLUJO_MO',
        'INT_DEVENGADO_MO', 'VP_AMORTIZACION_MO', 'VP_INTERES_MO', 'VP_FLUJO_MO',
        'Cod_Estrategia', 'Clasificacion_Contable', 'Empresa_Relacionada', 'Pais',
    ]
    data = data[output_columns]

    data = ut.estandariza_nombre_columnas_dataframe(data)

    # Mapear códigos de producto DAP por moneda
    condiciones = [
        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "CLP"),
        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "CLF"),
        (data["COD_SUB_PRO"] == "DAP") & (data["MONEDA"] == "USD")
    ]
    asignacion = ["DAP_CLP", "DAP_CLF", "DAP_USD"]
    data["COD_PRO_MODELO"] = np.select(condiciones, asignacion, default=None)
    
    print(f"        - Datos contractuales DAP cargados: {len(data):,} registros")
    print(f"        - Distribución por moneda: {data['MONEDA'].value_counts().to_dict()}")
    print("          ✓ Datos contractuales DAP procesados exitosamente")

    return data


def cargar_parametros() -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """
    Carga los parámetros del modelo.
    FACTORES: JSON preferido, fallback Excel.
    CORE_VIGENTE: siempre desde Excel de red (archivo externo, no migrado).
    """
    from procesamiento_datos_input.cargador_parametros import cargar_hojas_parametros

    print("      • Leyendo parámetros del modelo...")
    
    # FACTORES desde JSON/Excel local
    hojas = cargar_hojas_parametros("ml_nmd")
    parametros_modelo = hojas["FACTORES"]
    print(f"        - Factores de decay rate cargados: {len(parametros_modelo)} productos")
    
    # CORE_VIGENTE desde Excel de red (no migrado a JSON)
    parametros_core = pd.read_excel(RUTA_PARAMETROS_CORE, sheet_name="CORE_VIGENTE")
    
    # Transponer parámetros core para formato largo
    parametros_core = parametros_core.melt(
        id_vars=['FECHA','FECHA_ACTUALIZACION'], 
        var_name='COD_PRO_MODELO', 
        value_name='CORE_VIGENTE'
    )
    parametros_core = parametros_core[['FECHA','COD_PRO_MODELO','CORE_VIGENTE','FECHA_ACTUALIZACION']]
    print(f"        - Parámetros de core vigente cargados: {len(parametros_core)} registros")
    print("          ✓ Parámetros del modelo cargados exitosamente")

    return parametros_modelo, parametros_core

def calculo_flujos_modelo(datos_modelo: pd.DataFrame, fecha_proceso: datetime, productos_decay_rate: list, n_iteraciones: int = 1095) -> pd.DataFrame:
    """
    Calcula los flujos del modelo para productos con decay rate.
    Aplica función exponencial de decay para proyectar flujos futuros.
    
    Args:
        datos_modelo: DataFrame con los datos del modelo (incluye DECAY_RATE, CORE_VIGENTE, etc.)
        fecha_proceso: Fecha base para el cálculo
        productos_decay_rate: Lista de productos que usan decay rate
        n_iteraciones: Número de iteraciones para el cálculo (por defecto 1095)
    
    Returns:
        DataFrame con los flujos calculados para todos los productos
    """
    print("      • Calculando flujos del modelo con decay rate...")
    tabla_procesamiento_tmp = pd.DataFrame()

    for producto in productos_decay_rate:
        print(f"        - Procesando producto: {producto}")
        datos_producto = datos_modelo[datos_modelo['COD_PRO_MODELO'] == producto].copy()
        
        if datos_producto.empty:
            # print(f"           No hay datos para {producto}, omitiendo...")
            raise ValueError(f"No hay datos para {producto} en los datos del modelo.")
            
        decay_rate = datos_producto['DECAY_RATE'].values[0]
        flujo_total_mo = datos_producto['FLUJO_MO'].values[0]
        core = datos_producto['CORE_VIGENTE'].values[0]
        non_core = datos_producto['NON_CORE'].values[0]
        print(f"          Decay rate: {decay_rate:.6f}, Flujo total: {flujo_total_mo:,.0f} MM")

        for i in range(1, n_iteraciones + 1):
            factor_decay_ant = np.exp(-decay_rate * (i - 1))
            factor_decay = np.exp(-decay_rate * i)

            flujo_modelo_mo_ant = core * factor_decay_ant
            flujo_modelo_mo = core * factor_decay
            
            if i == 1:
                flujo_neto_modelo = (core - flujo_modelo_mo) + non_core
            else:
                flujo_neto_modelo = flujo_modelo_mo_ant - flujo_modelo_mo

            fila = {
                'COD_PRO_MODELO': producto,
                'DIA': i,
                'FECHA_VENCIMIENTO_CUOTA': fecha_proceso + timedelta(days=i),
                'FLUJO_MODELO_MO': flujo_modelo_mo,
                'FLUJO_NETO_MODELO_MO': flujo_neto_modelo
            }
            tabla_procesamiento_tmp = pd.concat([tabla_procesamiento_tmp, pd.DataFrame([fila])], ignore_index=True)
        
        # Agregar última fila con el residual
        i = i + 1
        ultima_fila = {
            'COD_PRO_MODELO': producto,
            'DIA': i,
            'FECHA_VENCIMIENTO_CUOTA': fecha_proceso + timedelta(days=i),
            'FLUJO_MODELO_MO': np.nan,
            'FLUJO_NETO_MODELO_MO': flujo_total_mo - tabla_procesamiento_tmp[tabla_procesamiento_tmp['COD_PRO_MODELO']==producto]['FLUJO_NETO_MODELO_MO'].sum()
        }
        tabla_procesamiento_tmp = pd.concat([tabla_procesamiento_tmp, pd.DataFrame([ultima_fila])], ignore_index=True)
        print(f"          ✓ Producto {producto} procesado - {n_iteraciones + 1} períodos generados")

    print(f"        - Total de flujos generados: {len(tabla_procesamiento_tmp):,} registros")
    print("          ✓ Cálculo de flujos del modelo completado")
    return tabla_procesamiento_tmp

def ajuste_norm_primera_banda(tabla_flujos: pd.DataFrame, producto: str) -> pd.DataFrame:
    """
    Aplica ajuste normativo de primera banda a los flujos de un producto específico.
    Redistribuye flujos para cumplir con el 25% en primera banda según normativa.
    
    Args:
        tabla_flujos: DataFrame con los flujos generados
        producto: Código del producto a procesar
    
    Returns:
        DataFrame con los flujos ajustados para el producto
    """
    print(f"        - Aplicando ajuste normativo primera banda para {producto}")
    
    # Filtrar datos del producto específico
    tabla_procesamiento_ajuste_norm = tabla_flujos[tabla_flujos['COD_PRO_MODELO'] == producto].copy()
    tabla_procesamiento_ajuste_norm = tabla_procesamiento_ajuste_norm.sort_values(by='DIA').reset_index(drop=True)
    
    # Calcular montos necesarios para el ajuste (25% en primera banda)
    monto_total = tabla_procesamiento_ajuste_norm['FLUJO_NETO_MODELO_MO'].sum()
    monto_primera_banda_normativo = monto_total * 0.250
    monto_primera_banda_normativo_actual = tabla_procesamiento_ajuste_norm['FLUJO_NETO_MODELO_MO'].iloc[0]
    print(f"          Monto total: {monto_total:,.0f}, Objetivo primera banda: {monto_primera_banda_normativo:,.0f}")
    
    # Calcular pesos para redistribución
    tabla_procesamiento_ajuste_norm["W_I"] = tabla_procesamiento_ajuste_norm['FLUJO_NETO_MODELO_MO'] / (monto_total - monto_primera_banda_normativo_actual)
    tabla_procesamiento_ajuste_norm.loc[0, 'W_I'] = 0.0
    
    # Aplicar ajuste normativo
    diferencia_banda = max(0.0, monto_primera_banda_normativo - monto_primera_banda_normativo_actual)
    
    tabla_procesamiento_ajuste_norm['FLUJO_NETO_MODELO_NORM_MO'] = 0.0
    tabla_procesamiento_ajuste_norm.loc[0, 'FLUJO_NETO_MODELO_NORM_MO'] = (
        tabla_procesamiento_ajuste_norm.loc[0, 'FLUJO_NETO_MODELO_MO'] + diferencia_banda
    )
    tabla_procesamiento_ajuste_norm.loc[1:, 'FLUJO_NETO_MODELO_NORM_MO'] = (
        tabla_procesamiento_ajuste_norm.loc[1:, 'FLUJO_NETO_MODELO_MO'] - 
        tabla_procesamiento_ajuste_norm.loc[1:, 'W_I'] * diferencia_banda
    )
    
    # Validar que la suma se mantiene
    suma_final = tabla_procesamiento_ajuste_norm['FLUJO_NETO_MODELO_NORM_MO'].sum()
    print(f"          ✓ Ajuste completado - Diferencia aplicada: {diferencia_banda:,.0f}")
    print(f"          Verificación: Suma final {suma_final:,.0f} = Suma original {monto_total:,.0f}")
    
    return tabla_procesamiento_ajuste_norm

# def ajuste_norm_dap_90_dias_v2(datos_producto: pd.DataFrame) -> pd.DataFrame:
#     """
#     Ajusta los flujos DAP tomando el máximo entre flujo contractual y modelo 
#     para los primeros 90 días, aplicando factor de ajuste después del día 90.
#     ES UN AJUSTE PROPORCIONAL (PROPUESTA)
    
#     Args:
#         datos_producto: DataFrame con flujos modelo y contractuales de DAP
    
#     Returns:
#         DataFrame con los flujos ajustados
#     """
#     datos_ajustados = datos_producto.copy()
    
#     # Filtrar primeros 90 días y después de 90 días
#     primeros_90_dias = datos_ajustados['DIA'] <= 90
#     despues_90_dias = datos_ajustados['DIA'] > 90
    
#     # Calcular suma total del flujo modelo para no excederla
#     suma_total_flujo_modelo = datos_ajustados['FLUJO_NETO_MODELO_MO'].sum()
    
#     # Para los primeros 90 días, tomar el máximo entre contractual y modelo
#     datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_NORM_MO'] = np.maximum(
#         datos_ajustados.loc[primeros_90_dias, 'FLUJO_CONTRACTUAL_MO'] * 0.25,
#         datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_MO']
#     )
    
#     # Calcular cuánto se usó en los primeros 90 días
#     suma_primeros_90 = datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_NORM_MO'].sum()

#     # suma_modelo_primeros_90 = datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_MO'].sum()
    
#     # Lo que queda disponible para después de 90 días
#     restante_disponible = suma_total_flujo_modelo - suma_primeros_90
#     suma_modelo_despues_90 = datos_ajustados.loc[despues_90_dias, 'FLUJO_NETO_MODELO_MO'].sum()
    
#     # Calcular factor de ajuste para después de 90 días
#     if suma_modelo_despues_90 > 0:
#         factor_ajuste = restante_disponible / suma_modelo_despues_90
#         # print(f"Factor de ajuste aplicado después de 90 días: {factor_ajuste}")
#         factor_ajuste = max(0, factor_ajuste)  # No puede ser negativo
#     else:
#         factor_ajuste = 0
    
#     # Aplicar factor de ajuste después de 90 días
#     datos_ajustados.loc[despues_90_dias, 'FLUJO_NETO_MODELO_NORM_MO'] = (
#         datos_ajustados.loc[despues_90_dias, 'FLUJO_NETO_MODELO_MO'] * factor_ajuste
#     )
    
#     return datos_ajustados

def ajuste_norm_dap_90_dias(datos_modelo_dap: pd.DataFrame, data_dap_agrupada: pd.DataFrame) -> pd.DataFrame:
    """
    Ajusta los flujos DAP tomando el máximo entre flujo contractual y modelo 
    para los primeros 90 días, sacando el exceso del último día disponible.
    Implementa lógica especial para DAP que considera información contractual.
    
    Args:
        datos_modelo_dap: DataFrame con flujos modelo de DAP
        data_dap_agrupada: DataFrame con datos contractuales DAP agrupados
    
    Returns:
        DataFrame con los flujos ajustados
    """
    print("        - Aplicando ajuste especial DAP (90 días + contractual)")
    
    # Combinar datos modelo con datos contractuales
    datos_ajustados = datos_modelo_dap.merge(
        data_dap_agrupada[['FEC_PAGO','COD_PRO_MODELO','FLUJO_MO']].rename(columns={'FLUJO_MO':'FLUJO_CONTRACTUAL_MO'}),
        left_on=['COD_PRO_MODELO','FECHA_VENCIMIENTO_CUOTA'],
        right_on=['COD_PRO_MODELO','FEC_PAGO'],
        how='left'
    )
    datos_ajustados['FLUJO_CONTRACTUAL_MO'] = datos_ajustados['FLUJO_CONTRACTUAL_MO'].fillna(0.0).reset_index(drop=True)
    print(f"          Datos contractuales encontrados: {(datos_ajustados['FLUJO_CONTRACTUAL_MO'] > 0).sum()} períodos")

    # datos_ajustados = datos_producto.copy()
    
    # Filtrar primeros 90 días
    primeros_90_dias = datos_ajustados['DIA'] <= 90
    
    # Calcular suma total del flujo modelo para no excederla
    suma_total_flujo_modelo = datos_ajustados['FLUJO_NETO_MODELO_MO'].sum()
    
    # Para los primeros 90 días, tomar el máximo entre contractual y modelo
    datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_NORM_MO'] = np.maximum(
        datos_ajustados.loc[primeros_90_dias, 'FLUJO_CONTRACTUAL_MO'] * 0.25,
        datos_ajustados.loc[primeros_90_dias, 'FLUJO_NETO_MODELO_MO']
    )
    
    # Para después de 90 días, mantener los flujos modelo originales
    despues_90_dias = datos_ajustados['DIA'] > 90
    datos_ajustados.loc[despues_90_dias, 'FLUJO_NETO_MODELO_NORM_MO'] = (
        datos_ajustados.loc[despues_90_dias, 'FLUJO_NETO_MODELO_MO']
    )
    
    # Calcular el exceso total
    suma_ajustada = datos_ajustados['FLUJO_NETO_MODELO_NORM_MO'].sum()
    exceso = suma_ajustada - suma_total_flujo_modelo
    
    if exceso > 0:
        # Encontrar el último día disponible (último día con flujo > 0)
        ultimo_dia_disponible = datos_ajustados[
            datos_ajustados['FLUJO_NETO_MODELO_NORM_MO'] > 0
        ]['DIA'].max()
        
        # Reducir el exceso del último día disponible
        idx_ultimo_dia = datos_ajustados[datos_ajustados['DIA'] == ultimo_dia_disponible].index[0]
        flujo_ultimo_dia = datos_ajustados.loc[idx_ultimo_dia, 'FLUJO_NETO_MODELO_NORM_MO']
        
        # Ajustar el último día, asegurándose de no hacerlo negativo
        nuevo_flujo_ultimo_dia = max(0, flujo_ultimo_dia - exceso)
        datos_ajustados.loc[idx_ultimo_dia, 'FLUJO_NETO_MODELO_NORM_MO'] = nuevo_flujo_ultimo_dia
        print(f"          Exceso de {exceso:,.0f} reducido del día {ultimo_dia_disponible}")
    else:
        print("          No se requiere ajuste por exceso")
    
    suma_final = datos_ajustados['FLUJO_NETO_MODELO_NORM_MO'].sum()
    print(f"          ✓ Ajuste DAP completado - Suma final: {suma_final:,.0f}")
    
    return datos_ajustados

def crea_tabla_desarrollo(tabla_final_flujos: pd.DataFrame) -> pd.DataFrame:
    """
    Crea la tabla de desarrollo con el formato requerido para el output.
    
    Args:
        tabla_final_flujos: DataFrame con los flujos finales procesados
    
    Returns:
        DataFrame con la estructura de tabla de desarrollo
    """
    # Extraer moneda del código de producto
    tabla_final_flujos_procesada = tabla_final_flujos.copy()
    tabla_final_flujos_procesada['MONEDA'] = tabla_final_flujos_procesada['COD_PRO_MODELO'].str.split('_').str[-1]
    
    # Mapeo de códigos de producto
    mapeo_productos = {
        "DAP_CLP": "ML_C46_Deposito_a_Plazo_Ajustado",
        "DAP_CLF": "ML_C46_Deposito_a_Plazo_Ajustado", 
        "DAP_USD": "ML_C46_Deposito_a_Plazo_Ajustado",
        "CTA_CTE_CLP": "ML_C46_Cuenta_Corriente_Ajustado",
        "CTA_VTA_CLP": "ML_C46_Cuenta_Vista_Ajustado",
        "AGD_CLF": "ML_C46_Ahorro_Giro_Diferido_Ajustado",
        "AGI_CLF": "ML_C46_Ahorro_Giro_Incondicional_Ajustado"
    }
    
    tabla_final_flujos_procesada["CODIGO_PRODUCTO"] = tabla_final_flujos_procesada["COD_PRO_MODELO"].map(mapeo_productos)
    tabla_final_flujos_procesada["CODIGO_SUBPRODUCTO"] = tabla_final_flujos_procesada["CODIGO_PRODUCTO"]
    
    tabla_final_flujos_procesada['AMORTIZACION_CALC'] = np.where(
        (tabla_final_flujos_procesada['COD_PRO_MODELO'] == "DAP_CLF") | (tabla_final_flujos_procesada['COD_PRO_MODELO'] == "DAP_USD"),
        tabla_final_flujos_procesada['FLUJO_CONTRACTUAL_MO'],
        tabla_final_flujos_procesada['FLUJO_NETO_MODELO_NORM_MO']
    )
    # Crear diccionario con la estructura final
    tabla_desarrollo = pd.DataFrame()
    for producto in tabla_final_flujos_procesada['COD_PRO_MODELO'].unique():
        tabla_producto = tabla_final_flujos_procesada[tabla_final_flujos_procesada['COD_PRO_MODELO'] == producto]
        num_registros = len(tabla_producto)
        tabla_desarrollo_iter = pd.DataFrame({
            "FECHA_PROCESO": tabla_producto['FECHA_PROCESO'],
            "CODIGO_EMPRESA": [1] * num_registros,
            "OPERACION": [np.nan] * num_registros,
            "COD_ACT/PAS": ["PAS"] * num_registros,
            "MONEDA_ORIGEN": tabla_producto['MONEDA'],
            "MONEDA_COMPENSACION": tabla_producto['MONEDA'],
            "COMPENSACION": [np.nan] * num_registros,
            "CODIGO_PRODUCTO": tabla_producto["CODIGO_PRODUCTO"],
            "CODIGO_SUBPRODUCTO": tabla_producto["CODIGO_SUBPRODUCTO"],
            "FECHA_CREACION": [np.nan] * num_registros,
            "NUMERO_CUOTA": [np.nan] * num_registros,
            "FECHA_INICIO_CUOTA": [np.nan] * num_registros,
            "FECHA_VENCIMIENTO_CUOTA": tabla_producto["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_PAGO": tabla_producto["FECHA_VENCIMIENTO_CUOTA"],
            "FECHA_REPRICING": tabla_producto["FECHA_VENCIMIENTO_CUOTA"],
            "AMORTIZACION": tabla_producto['AMORTIZACION_CALC'],
            "INTERES": [np.nan] * num_registros,
            "INTERES_DEVENGADO": [np.nan] * num_registros,
            "VP_AMORTIZACION": [np.nan] * num_registros,
            "VP_INTERES": [np.nan] * num_registros,
            "FACTOR_DE_RIESGO": [np.nan] * num_registros,
            "TIPO_CUOTA": [1] * num_registros,
            "AREA_NEGOCIO": ["BALANCE TASAS"] * num_registros,
            "CODIGO_EJECUTIVO": [np.nan] * num_registros,
            "CODIGO_ESTRATEGIA": ["BALANCE TASAS"] * num_registros,
            "CLASIFICACION_CONTABLE": ["HTM"] * num_registros,
            "TIPO_TASA": [1] * num_registros,
            "INDEXADOR": [np.nan] * num_registros,
            "TASA": [np.nan] * num_registros,
            "TASA_CF": [np.nan] * num_registros,
            "SPREAD": [np.nan] * num_registros,
        })
        tabla_desarrollo = pd.concat([tabla_desarrollo, tabla_desarrollo_iter], ignore_index=True)
    return tabla_desarrollo

def validar_datos_iniciales(balance_input: pd.DataFrame, dap_contractual: pd.DataFrame, 
                           parametros_modelo: pd.DataFrame, parametros_core: pd.DataFrame, 
                           fecha_proceso: datetime) -> None:
    """
    Valida que todos los datos iniciales necesarios estén disponibles.
    Levanta excepción si algún DataFrame está vacío o no contiene datos válidos.
    
    Args:
        balance_input: DataFrame con datos de balance
        dap_contractual: DataFrame con datos contractuales DAP
        parametros_modelo: DataFrame con parámetros del modelo
        parametros_core: DataFrame con parámetros de core vigente
        fecha_proceso: Fecha de procesamiento
        
    Raises:
        ValueError: Si algún DataFrame está vacío o no contiene datos válidos
    """
    print("      • Validando integridad de datos iniciales...")
    
    # Validar datos de balance
    if balance_input.empty:
        raise ValueError(f"No se encontraron datos de balance para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                        f"Verifique que existan registros en la base de datos para esta fecha.")
    
    # Verificar que haya productos válidos en balance
    productos_validos = balance_input['COD_PRO_MODELO'].notna().sum()
    if productos_validos == 0:
        raise ValueError(f"No se encontraron productos válidos en los datos de balance. "
                        f"Verifique los criterios de filtrado y mapeo de productos.")
    
    print(f"        - Balance: {len(balance_input)} registros, {productos_validos} productos válidos")
    
    # Validar datos contractuales DAP
    if dap_contractual.empty:
        raise ValueError(f"No se encontraron datos contractuales DAP para la fecha {fecha_proceso.strftime('%Y-%m-%d')}. "
                        f"Verifique que existan depósitos a plazo en la base de datos para esta fecha.")
    
    print(f"        - DAP contractual: {len(dap_contractual)} registros")
    
    # Validar parámetros del modelo
    if parametros_modelo.empty:
        raise ValueError(f"No se encontraron parámetros del modelo (factores de decay rate). "
                        f"Verifique el archivo de parámetros: {RUTA_PARAMETROS_NMD}")
    
    # Verificar que haya factores de decay para los productos requeridos
    productos_requeridos = ['CTA_VTA_CLP', 'CTA_CTE_CLP', 'AGD_CLF', 'AGI_CLF', 'DAP_CLP']
    productos_con_parametros = parametros_modelo['COD_PRO_MODELO'].tolist()
    productos_faltantes = [p for p in productos_requeridos if p not in productos_con_parametros]
    
    if productos_faltantes:
        raise ValueError(f"Faltan parámetros de decay rate para los productos: {', '.join(productos_faltantes)}. "
                        f"Verifique la hoja FACTORES en el archivo {RUTA_PARAMETROS_NMD}")
    
    print(f"        - Parámetros modelo: {len(parametros_modelo)} productos con decay rate")
    
    # Validar parámetros core
    if parametros_core.empty:
        raise ValueError(f"No se encontraron parámetros de core vigente. "
                        f"Verifique el archivo de parámetros: {RUTA_PARAMETROS_CORE}")
    
    print(f"        - Parámetros core: {len(parametros_core)} registros")
    
    # Validar que haya flujos positivos en balance
    flujos_positivos = (balance_input['FLUJO_MO'] > 0).sum()
    if flujos_positivos == 0:
        raise ValueError(f"No se encontraron flujos positivos en los datos de balance. "
                        f"Verifique los datos financieros para la fecha {fecha_proceso.strftime('%Y-%m-%d')}")
    
    print(f"        - Validación: {flujos_positivos} productos con flujos positivos")
    print("          ✓ Validación de datos iniciales completada exitosamente")


def procesar_datos_iniciales(fecha_proceso: datetime) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Carga y procesa los datos iniciales del modelo.
    Combina datos de balance con parámetros del modelo.
    
    Args:
        fecha_proceso: Fecha de procesamiento
        
    Returns:
        Tuple con (datos_modelo, dap_contractual, dap_contractual_agrupado)
    """
    print("    • Cargando datos base del modelo...")
    
    # Cargar datos base
    balance_input = cargar_datos_balance(fecha_proceso)
    dap_contractual = cargar_dap_contractual(fecha_proceso)

    # Cargar parámetros y hacer merge
    parametros_modelo, parametros_core = cargar_parametros()
    
    # Validar integridad de todos los datos antes de procesar
    validar_datos_iniciales(balance_input, dap_contractual, parametros_modelo, parametros_core, fecha_proceso)
    
    datos_modelo = balance_input.merge(
        parametros_modelo[['COD_PRO_MODELO','DECAY_RATE']],
        on='COD_PRO_MODELO',
        how='left'
    )
    datos_modelo = datos_modelo.merge(
        parametros_core[['COD_PRO_MODELO','CORE_VIGENTE']],
        on='COD_PRO_MODELO',
        how='left'
    )
    datos_modelo['CORE_VIGENTE'] = datos_modelo['CORE_VIGENTE'].fillna(0)
    datos_modelo['NON_CORE'] = datos_modelo['FLUJO_MO'] - datos_modelo['CORE_VIGENTE']
    
    # Validación post-merge: verificar que no haya productos sin decay rate
    productos_sin_decay = datos_modelo[datos_modelo['DECAY_RATE'].isna()]
    if not productos_sin_decay.empty:
        productos_faltantes = productos_sin_decay['COD_PRO_MODELO'].unique().tolist()
        raise ValueError(f"Los siguientes productos no tienen parámetros de decay rate configurados: {productos_faltantes}. "
                        f"Verifique la configuración de parámetros del modelo.")
    
    print("    • Procesando y combinando datos...")
    
    # Agrupar datos contractuales DAP
    dap_contractual_agrupado = dap_contractual.groupby(['FEC_PRO','COD_PRO_MODELO','FEC_PAGO']).agg({
        'AMORTIZACION_MO':'sum',
        'INTERES_MO':'sum',
        'FLUJO_MO':'sum'
    }).reset_index()
    dap_contractual_agrupado['DIA'] = (dap_contractual_agrupado['FEC_PAGO'] - dap_contractual_agrupado['FEC_PRO']).dt.days
    
    print(f"      ✓ Datos modelo preparados: {len(datos_modelo)} productos")
    print(f"      ✓ Datos contractuales DAP agrupados: {len(dap_contractual_agrupado)} registros")
    
    return datos_modelo, dap_contractual, dap_contractual_agrupado


def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """
    Función principal que ejecuta todo el flujo del modelo NMD.
    Procesa productos de No Madurez Definida con ajustes normativos.
    
    Args:
        fecha_proceso: Fecha de proceso para el modelo
        
    Returns:
        bool: True si la ejecución fue exitosa
    """
    try:
        print("\n" + "="*50)
        print("INICIO DEL PROCESO - MODELO NMD")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("="*50 + "\n")
        
        # Definir productos con decay rate
        PRODUCTOS_DECAY_RATE = ['CTA_VTA_CLP', 'CTA_CTE_CLP', 'AGD_CLF', 'AGI_CLF', 'DAP_CLP']
        print(f"Productos a procesar: {', '.join(PRODUCTOS_DECAY_RATE)}\n")
        
        print("[1/6] Cargando y procesando datos iniciales...")
        # 1. Procesar datos iniciales
        datos_modelo, dap_contractual, dap_contractual_agrupado = procesar_datos_iniciales(fecha_proceso)
        print("      ✓ Datos iniciales cargados correctamente\n")
        
        print("[2/6] Calculando flujos del modelo...")
        tabla_flujos_modelo = calculo_flujos_modelo(datos_modelo, fecha_proceso, PRODUCTOS_DECAY_RATE)
        print("      ✓ Flujos del modelo calculados\n")
        
        print("[3/6] Aplicando ajuste normativo primera banda...")
        PRODUCTOS_DECAY_RATE_ADJ_BANDA = ['CTA_VTA_CLP', 'CTA_CTE_CLP', 'AGD_CLF', 'AGI_CLF']

        tabla_flujos_norm_modelo = pd.DataFrame()
        for producto in PRODUCTOS_DECAY_RATE_ADJ_BANDA:
            tabla_ajustada_tmp = ajuste_norm_primera_banda(tabla_flujos_modelo, producto)
            tabla_flujos_norm_modelo = pd.concat([tabla_flujos_norm_modelo, tabla_ajustada_tmp], ignore_index=True)
        print("      ✓ Ajuste normativo primera banda completado\n")

        print("[4/6] Procesamiento específico para productos DAP...")
        # Procesamiento específico para DAP
        datos_dap = tabla_flujos_modelo[tabla_flujos_modelo['COD_PRO_MODELO'] == "DAP_CLP"].reset_index(drop=True)
        tabla_flujos_norm_dap = ajuste_norm_dap_90_dias(datos_dap, dap_contractual_agrupado)
        print("      ✓ Procesamiento DAP completado\n")

        print("[5/6] Consolidando tabla final de flujos...")
        # Consolidar todas las tablas de flujos
        tabla_final_flujos = pd.concat([tabla_flujos_norm_modelo, tabla_flujos_norm_dap], ignore_index=True)
        tabla_final_flujos['FECHA_PROCESO'] = fecha_proceso

        # Agregar datos contractuales de otros productos DAP
        tabla_final_flujos = pd.concat([tabla_final_flujos, dap_contractual_agrupado[dap_contractual_agrupado["COD_PRO_MODELO"]!='DAP_CLP']
                                        [['FEC_PRO','COD_PRO_MODELO','DIA','FEC_PAGO','FLUJO_MO']].rename(columns={'FEC_PRO':'FECHA_PROCESO',
                                                                                                                 'FEC_PAGO': 'FECHA_VENCIMIENTO_CUOTA',
                                                                                                                'FLUJO_MO':'FLUJO_CONTRACTUAL_MO'})], ignore_index=True)
        
        # Crear tabla de desarrollo
        tabla_desarrollo = crea_tabla_desarrollo(tabla_final_flujos)
        
        # Calcular flujo final para tabla de desarrollo
        tabla_final_flujos['FLUJO_TABLA_DESARROLLO_MO'] = np.where(
            (tabla_final_flujos['COD_PRO_MODELO'] == "DAP_CLF") | (tabla_final_flujos['COD_PRO_MODELO'] == "DAP_USD"),
            tabla_final_flujos['FLUJO_CONTRACTUAL_MO'],
            tabla_final_flujos['FLUJO_NETO_MODELO_NORM_MO']
        )
        
        # Seleccionar columnas finales
        tabla_final_flujos = tabla_final_flujos[['FECHA_PROCESO', 'COD_PRO_MODELO', 'DIA', 'FECHA_VENCIMIENTO_CUOTA','FLUJO_NETO_MODELO_MO','FLUJO_NETO_MODELO_NORM_MO','FLUJO_CONTRACTUAL_MO', 'FLUJO_TABLA_DESARROLLO_MO']]
        print(f"      ✓ Tabla final consolidada: {len(tabla_final_flujos):,} registros\n")

        print("[6/6] Guardando resultados en archivo Excel...")
        formatos_excel = {
            "FECHA_PROCESO": "dd-mm-yyyy",
            "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
            "FECHA_PAGO": "dd-mm-yyyy",
            "FECHA_REPRICING": "dd-mm-yyyy"
        }
        
        print("      • Guardando resultados en archivo Excel...")
        guardar_excel(
            ruta_archivo=RUTA_OUTPUT_MODELO,
            hojas={
                "FLUJOS": tabla_final_flujos,
                "DESARROLLO": tabla_desarrollo,
            },
            formatos_columnas=formatos_excel,
        )
        print("        ✓ Hojas FLUJOS y DESARROLLO actualizadas")
        
        print("\n" + "="*50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print(f"Registros finales generados: {len(tabla_desarrollo):,}")
        print(f"Archivo guardado en: {RUTA_OUTPUT_MODELO}")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\nERROR EN EL MODELO NMD:")
        print(f"   {str(e)}")
        print("\n" + "="*50)
        print("PROCESO TERMINADO CON ERRORES")
        print("="*50)
        return False


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERROR: No se proporcionó fecha. Uso: python tu_script.py YYYY-MM-DD")
        sys.exit(1)
    
    fecha_proceso_str = sys.argv[1]

    # fecha_proceso_str = "2025-12-30"

    try:
        fecha_proceso = datetime.strptime(fecha_proceso_str, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Formato de fecha '{fecha_proceso_str}' incorrecto. Use YYYY-MM-DD.")
        sys.exit(1)

    exito = ejecutar_modelo(fecha_proceso)
    
    if not exito:
        sys.exit(1)