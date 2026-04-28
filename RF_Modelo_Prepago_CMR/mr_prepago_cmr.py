"""
Modelo Prepago CMR - Replica fiel del notebook productivo.

Origen: Z:\\RF_PROYECTOS\\METODOLOGIAS\\PROCESOS_DIARIOS_MODELOS\\001_PROCESOS_DIARIOS\\MANUALES
        \\MODELOS\\MR_PREPAGO_CMR\\Generador_Prepago_TC_CMR_Productivo.ipynb

Este modulo reproduce 1:1 la logica del notebook (que se ejecuta a diario
con el conda env "rf"), adaptada al repositorio:
  - Lectura via cache parquet (leer_tabla_con_cache).
  - Rutas via config_rutas / config_rutas_ext_y_archivos.yaml.
  - Output via guardar_excel.
  - Snapshot historico en Prepago_CMR_Historia/{fecha}_Prepago_TC_CMR.xlsx.

Comportamiento clave (igual al notebook productivo):
  - Dia_F.replace({28: 30, 29: 30}) SIEMPRE para todos los productos.
  - Cuotas MORA con vencimiento pasado se incluyen en NO_SAV.
  - Calendario directo (groupby de fechas reales), no vector de 200 meses.
  - SMM se divide por 100 (parametro entra como porcentaje).
  - Escenarios hardcoded: BASE=1.0, UP=0.8, DOWN=1.2.
  - CODIGO_EMPRESA = 3.

La version anterior (parametrizada via Excel, con divergencias funcionales
respecto al notebook) quedo como `mr_prepago_cmr_dev.py` para retomar las
mejoras en una rama de desarrollo. Ver
`docs/feats/cuadre-mr-prepago-cmr/hallazgos.md` para el contexto completo.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import yaml

from config import config_rutas as cr
from core.excel_output import guardar_excel

# Cargar configuracion de rutas externas
with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r', encoding='utf-8') as f:
    config_ext = yaml.safe_load(f)

ARCHIVO_INPUT = cr.resolver_ruta(config_ext['modelos']['mr_prepago_cmr']['ms_access_input'])
ARCHIVO_OUTPUT_MODELO = cr.resolver_ruta(config_ext['modelos']['mr_prepago_cmr']['excel_output'])

# Path historico (snapshot por fecha) a la par del notebook
RUTA_HISTORIA = Path(
    r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Modelos"
    r"\RF_Modelo_Prepago_CMR\Prepago_CMR_Historia"
)

# Parametros hardcoded como en el notebook
SMM_SAV_PCT = 0.7866      # se divide por 100 dentro del modelo
SMM_NO_SAV_PCT = 0.0
FACTORES = [1.0, 0.8, 1.2]


# ---------------------------------------------------------------------------
# 1. Lectura del Access (mismo cache que el resto del repo)
# ---------------------------------------------------------------------------
def lectura_interfaz_de_datos(fecha_t: datetime.datetime) -> pd.DataFrame:
    """Lee RF_BD_Gestion_RM filtrado a TARJETA DE CREDITO desde el cache.

    Replica la query del notebook usando el cache parquet del repo en lugar
    de pyodbc directo.
    """
    from procesamiento_datos_input.cache_tablas import leer_tabla_con_cache

    fecha_access = fecha_t.strftime('%Y-%m-%d')
    query_rm = (
        f"SELECT * FROM [RF_BD_Gestion_RM] "
        f"WHERE [Fec_Pro] = #{fecha_access}#"
    )
    df_rm = leer_tabla_con_cache(
        access_path=ARCHIVO_INPUT,
        nombre_tabla='RF_BD_Gestion_RM',
        fecha_proceso=fecha_t.strftime('%Y%m%d'),
        query=query_rm,
    )

    df = df_rm.loc[
        df_rm['Cod_Pro'] == 'TARJETA DE CREDITO',
        ['Fec_Pro', 'Fec_Vcto', 'Cod_Sub_Pro', 'Cap_Amort', 'Int_Total_Cont'],
    ].copy()

    df = df.rename(columns={
        'Fec_Pro': 'FECHA_PROCESO',
        'Fec_Vcto': 'FECHA_VENCIMIENTO_CUOTA',
        'Cod_Sub_Pro': 'CODIGO_SUBPRODUCTO',
        'Cap_Amort': 'AMORTIZACION',
        'Int_Total_Cont': 'INTERES',
    })
    return df


# ---------------------------------------------------------------------------
# 2. Generador de matriz - copia 1:1 del notebook
# ---------------------------------------------------------------------------
def generador_matriz_SAV(
    df_in: pd.DataFrame,
    dia_f: int,
    plazo_antiguo: str,
    fecha_proceso: pd.Timestamp,
    smm_porcentaje: float = 0.7866,
    factor: float = 1.0,
) -> pd.DataFrame:
    """Replica exacta de `generador_matriz_SAV` del notebook.

    Cambios respecto al notebook:
      - Recibe `fecha_proceso` como parametro (en el notebook venia de un
        `clean_df` global).
      - Nombres de columnas de salida con guion bajo en lugar de espacios,
        para alinearse con el esquema canonico de BQ
        (FECHA_PROCESO en lugar de "FECHA PROCESO", etc.). El cargador BQ
        normaliza ambos formatos, pero conviene salida consistente.
    """
    filtered = df_in[
        (df_in['Dia_F'] == dia_f) &
        (df_in['Plazo_Antiguo'] == plazo_antiguo)
    ]
    grouped = filtered.groupby('FECHA_VENCIMIENTO_CUOTA', as_index=False)[
        ['AMORTIZACION', 'INTERES']
    ].sum()
    grouped = grouped.sort_values('FECHA_VENCIMIENTO_CUOTA')
    flujos_matriz = grouped.to_numpy()

    # Vector SMM (notebook divide por 100)
    SMM = smm_porcentaje / 100
    SMM_Vector = np.full(90, SMM)
    Comp_SMM = np.zeros(90)
    for i in range(Comp_SMM.shape[0]):
        if i == 0:
            Comp_SMM[i] = (1 - factor * SMM_Vector[i])
        else:
            Comp_SMM[i] = Comp_SMM[i - 1] * (1 - factor * SMM_Vector[i])

    N = int(len(flujos_matriz))
    M = 90
    matriz = np.zeros((N, M))

    if N == 0:
        return pd.DataFrame()

    for j in range(M):
        for i in range(N):
            if i == 0 and j == 0:
                matriz[i, j] = (
                    flujos_matriz[i, 1]
                    + flujos_matriz[i, 2]
                    + flujos_matriz[1:, 1].sum() * SMM_Vector[j] * factor
                )
            elif i != 0 and j == 0:
                matriz[i, j] = flujos_matriz[i, 1] * (1 - SMM_Vector[j] * factor)
            elif i == j:
                matriz[i, j] = (
                    matriz[i, j - 1]
                    + flujos_matriz[i, 2] * Comp_SMM[j - 1]
                    + matriz[i + 1:, j - 1].sum() * SMM_Vector[j] * factor
                )
            elif i > j:
                matriz[i, j] = matriz[i, j - 1] * (1 - SMM_Vector[j] * factor)
            else:
                matriz[i, j] = 0

    Vector_CW = SMM_Vector * factor
    Vector_CX = np.zeros(N)
    for i in range(Vector_CX.shape[0]):
        if i == 0:
            Vector_CX[i] = 1
        else:
            Vector_CX[i] = Vector_CX[i - 1] * (1 - Vector_CW[i - 1])

    Vector_Prepago = np.zeros(N)
    for j in range(M):
        for i in range(N):
            if j == i:
                Vector_Prepago[i] = matriz[i, j]

    Int_CapPre = np.zeros((N, 2))
    for i in range(N):
        Int_CapPre[i, 0] = max(Vector_CX[i] * flujos_matriz[i, 2], 0)
        Int_CapPre[i, 1] = max(Vector_Prepago[i] - Int_CapPre[i, 0], 0)

    fecha_venc = flujos_matriz[:, 0]
    amortizacion = Int_CapPre[:, 1]
    interes = Int_CapPre[:, 0]

    cod_sub_pro_extension = "_NO_SAV_" if smm_porcentaje == 0 else "_SAV_"
    if factor == 1.0:
        cod_pro = "MT_R13_TC_CMR_BASE"
        cod_sub_pro = "MT_R13_TC_CMR" + cod_sub_pro_extension + "BASE"
    elif factor == 0.8:
        cod_pro = "MT_R13_TC_CMR_UP"
        cod_sub_pro = "MT_R13_TC_CMR" + cod_sub_pro_extension + "UP"
    elif factor == 1.2:
        cod_pro = "MT_R13_TC_CMR_DOWN"
        cod_sub_pro = "MT_R13_TC_CMR" + cod_sub_pro_extension + "DOWN"
    else:
        raise ValueError(f"Factor no soportado: {factor}")

    df_des = pd.DataFrame({
        "FECHA_PROCESO": np.full(N, fecha_proceso),
        "CODIGO_EMPRESA": np.full(N, 3),
        "OPERACION": np.full(N, np.nan),
        "COD_ACT/PAS": np.full(N, "ACT"),
        "MONEDA_ORIGEN": np.full(N, "CLP"),
        "MONEDA_COMPENSACION": np.full(N, "CLP"),
        "COMPENSACION": np.full(N, np.nan),
        "CODIGO_PRODUCTO": np.full(N, cod_pro),
        "CODIGO_SUBPRODUCTO": np.full(N, cod_sub_pro),
        "FECHA_CREACION": np.full(N, np.nan),
        "NUMERO_CUOTA": np.full(N, np.nan),
        "FECHA_INICIO_CUOTA": np.full(N, np.nan),
        "FECHA_VENCIMIENTO_CUOTA": fecha_venc,
        "FECHA_PAGO": fecha_venc,
        "FECHA_REPRICING": fecha_venc,
        "AMORTIZACION": amortizacion,
        "INTERES": interes,
        "INTERES_DEVENGADO": np.full(N, np.nan),
        "VP_AMORTIZACION": np.full(N, np.nan),
        "VP_INTERES": np.full(N, np.nan),
        "FACTOR_DE_RIESGO": np.full(N, np.nan),
        "TIPO_CUOTA": np.full(N, 1),
        "AREA_NEGOCIO": np.full(N, "CMR_BKG"),
        "CODIGO_EJECUTIVO": np.full(N, np.nan),
        "CODIGO_ESTRATEGIA": np.full(N, "CMR_BKG"),
        "CLASIFICACION_CONTABLE": np.full(N, "HTM"),
        "TIPO_TASA": np.full(N, 1),
        "INDEXADOR": np.full(N, np.nan),
        "TASA": np.full(N, np.nan),
        "TASA_CF": np.full(N, np.nan),
        "SPREAD": np.full(N, np.nan),
    })
    return df_des


# ---------------------------------------------------------------------------
# 3. Procesamiento principal -- replica del bloque "5. Corremos funcion"
# ---------------------------------------------------------------------------
def procesamiento_y_guardado(
    fecha_t: datetime.datetime,
    interfaz: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce los pasos 3-7 del notebook (mapeo, separacion, generacion,
    guardado en xlsx principal y snapshot historico)."""

    # --- Paso 3 del notebook: agregar columnas y separar ---
    df = interfaz.copy()
    df['Dia_F'] = df['FECHA_VENCIMIENTO_CUOTA'].dt.day
    # Notebook: 28 y 29 -> 30 SIEMPRE
    df['Dia_F'] = df['Dia_F'].replace({28: 30, 29: 30})

    diff = (df['FECHA_VENCIMIENTO_CUOTA'] - df['FECHA_PROCESO']).dt.days
    df['Plazo_Antiguo'] = diff.apply(lambda x: 'NO' if x > -1 else 'SI')

    # Filtrar columnas para el modelo
    clean_df = df[[
        'FECHA_PROCESO', 'FECHA_VENCIMIENTO_CUOTA', 'Dia_F', 'Plazo_Antiguo',
        'CODIGO_SUBPRODUCTO', 'AMORTIZACION', 'INTERES'
    ]]

    # MORA: forzar Plazo_Antiguo = NO para incluirlas aunque esten vencidas
    df_vcdos_mora = clean_df[
        clean_df['CODIGO_SUBPRODUCTO'].str.contains("MORA", case=False, na=False)
    ].copy()
    df_vcdos_mora['Plazo_Antiguo'] = 'NO'

    clean_df = clean_df[
        ~clean_df['CODIGO_SUBPRODUCTO'].str.contains("MORA", case=False, na=False)
    ]

    df_sav = clean_df[
        clean_df['CODIGO_SUBPRODUCTO'].str.startswith('SUPER AVANCE')
    ]
    df_no_sav = clean_df[
        ~clean_df['CODIGO_SUBPRODUCTO'].str.startswith('SUPER AVANCE')
    ]
    df_no_sav = pd.concat([df_vcdos_mora, df_no_sav], ignore_index=True)

    # --- Paso 5 del notebook: correr para SAV y NO_SAV ---
    fechas_facturacion = df['Dia_F'].unique()
    fecha_proceso_ts = clean_df['FECHA_PROCESO'].iloc[0]

    df_desarrollo = pd.DataFrame()

    print("      Procesando SAV...")
    for valor_factor in FACTORES:
        for fecha_fac in fechas_facturacion:
            df_ciclo = generador_matriz_SAV(
                df_sav, fecha_fac, "NO",
                fecha_proceso=fecha_proceso_ts,
                smm_porcentaje=SMM_SAV_PCT,
                factor=valor_factor,
            )
            if not df_ciclo.empty:
                df_desarrollo = pd.concat(
                    [df_desarrollo, df_ciclo], ignore_index=True
                )

    print("      Procesando NO_SAV...")
    for valor_factor in FACTORES:
        for fecha_fac in fechas_facturacion:
            df_ciclo = generador_matriz_SAV(
                df_no_sav, fecha_fac, "NO",
                fecha_proceso=fecha_proceso_ts,
                smm_porcentaje=SMM_NO_SAV_PCT,
                factor=valor_factor,
            )
            if not df_ciclo.empty:
                df_desarrollo = pd.concat(
                    [df_desarrollo, df_ciclo], ignore_index=True
                )

    # --- Paso 6 del notebook: validador de capitales ---
    capital_bd = df['AMORTIZACION'].sum()
    capital_modelo = df_desarrollo['AMORTIZACION'].sum() / len(FACTORES)
    print(f"\n      Capital BD: {capital_bd:,.0f}")
    print(f"      Capital modelo (promedio escenarios): {capital_modelo:,.0f}")
    if abs(capital_bd - capital_modelo) < 1:
        print("      Capitales OK")
    else:
        print(f"      ADVERTENCIA: diferencia de capitales = "
              f"{capital_bd - capital_modelo:,.2f}")

    # --- Paso 7 del notebook: exportar resultado ---
    formatos_excel = {
        "FECHA_PROCESO": "dd-mm-yyyy",
        "FECHA_VENCIMIENTO_CUOTA": "dd-mm-yyyy",
        "FECHA_PAGO": "dd-mm-yyyy",
        "FECHA_REPRICING": "dd-mm-yyyy",
    }

    print("\n      Guardando archivo principal...")
    guardar_excel(
        ruta_archivo=ARCHIVO_OUTPUT_MODELO,
        hojas={"DESARROLLO": df_desarrollo},
        formatos_columnas=formatos_excel,
    )

    # Snapshot historico
    fecha_compacta = fecha_t.strftime('%Y%m%d')
    ruta_historia = RUTA_HISTORIA / f"{fecha_compacta}_Prepago_TC_CMR.xlsx"
    print(f"      Guardando snapshot historico: {ruta_historia.name}")
    try:
        guardar_excel(
            ruta_archivo=ruta_historia,
            hojas={"DESARROLLO": df_desarrollo},
            formatos_columnas=formatos_excel,
        )
    except OSError as e:
        # No queremos que un fallo de escritura en la red mate el flujo
        print(f"      ADVERTENCIA: no se pudo escribir snapshot historico: {e}")

    return df_desarrollo


# ---------------------------------------------------------------------------
# 4. Entry point para el orquestador
# ---------------------------------------------------------------------------
def ejecutar_modelo(fecha_proceso: datetime.datetime) -> bool:
    """Entry point unificado del repo. Llamado por el orquestador."""
    try:
        print("\n" + "=" * 50)
        print("INICIO -- MODELO PREPAGO CMR")
        print(f"Fecha de proceso: {fecha_proceso.strftime('%d-%m-%Y')}")
        print("=" * 50 + "\n")

        print("[1/3] Leyendo datos de interfaz (cache)...")
        interfaz = lectura_interfaz_de_datos(fecha_proceso)
        if interfaz.empty:
            raise ValueError(
                f"No hay datos para {fecha_proceso.strftime('%Y-%m-%d')}"
            )
        print(f"      {len(interfaz):,} registros leidos")

        print("\n[2/3] Procesando y calculando prepagos...")
        procesamiento_y_guardado(fecha_proceso, interfaz)

        print("\n[3/3] Proceso completado")
        print("=" * 50)
        print("PROCESO FINALIZADO EXITOSAMENTE")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\nERROR EN EL MODELO PREPAGO CMR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 50)
        print("PROCESO TERMINADO CON ERRORES")
        print("=" * 50)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m RF_Modelo_Prepago_CMR.mr_prepago_cmr YYYY-MM-DD")
        sys.exit(1)

    try:
        fecha = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print(f"Formato de fecha invalido: {sys.argv[1]}")
        sys.exit(1)

    sys.exit(0 if ejecutar_modelo(fecha) else 1)
