import pandas as pd
import pathlib
import os
import datetime
import numpy as np
import warnings

# =============================================================================
# IMPORTAR CONFIGURACIÓN CENTRALIZADA
# =============================================================================
# La configuración de instrumentos ahora está en config/instrumentos.py
# Este import provee: INSTRUMENTOS, ConfigInstrumento, obtener_instrumento, etc.
try:
    from RF_Modelo_Inversiones.config.instrumentos import (
        INSTRUMENTOS,
        ConfigInstrumento,
        obtener_instrumento,
        listar_instrumentos,
        COLUMNAS_TABLA_FINAL,
        CODIGO_EMPRESA,
        CODIGO_ACTIVO_PASIVO,
        CODIGO_PRODUCTO,
    )
    _CONFIG_CENTRALIZADA_DISPONIBLE = True
except ImportError:
    # Fallback para ejecución directa desde dev/
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from RF_Modelo_Inversiones.config.instrumentos import (
            INSTRUMENTOS,
            ConfigInstrumento,
            obtener_instrumento,
            listar_instrumentos,
            COLUMNAS_TABLA_FINAL,
            CODIGO_EMPRESA,
            CODIGO_ACTIVO_PASIVO,
            CODIGO_PRODUCTO,
        )
        _CONFIG_CENTRALIZADA_DISPONIBLE = True
    except ImportError:
        _CONFIG_CENTRALIZADA_DISPONIBLE = False
        warnings.warn(
            "No se pudo importar config/instrumentos.py. "
            "Usando CONFIGURACION_INSTRUMENTOS local (deprecado).",
            DeprecationWarning
        )

# =============================================================================
# CONFIGURACIÓN DE INSTRUMENTOS (DEPRECADO - usar config/instrumentos.py)
# =============================================================================
# DEPRECADO: Este diccionario se mantiene por compatibilidad.
# Usar `from RF_Modelo_Inversiones.config.instrumentos import INSTRUMENTOS` en código nuevo.
# 
# NOTA sobre nomenclatura:
# - BBC en CLP → Flujo_BBC (usa Corporativo CLP en FPL/MontosLiq)
# - BBC en CLF + LCH → Flujo_LCH (usa Corporativo CLF en FPL/MontosLiq)
#   Access combina BBC_CLF con LCH (Letras de Crédito Hipotecario) en Flujo_LCH

CONFIGURACION_INSTRUMENTOS = {
    'GobCLP': {
        'nombre_completo': 'Gobierno CLP',
        'codigos_disp': ['BCP', 'BTP', 'PDB'],      # Filtro cartera disponible
        'codigos_pacto': ['BCP', 'BTP', 'PDB'],     # Filtro cartera pacto
        'filtro_moneda': None,                       # No filtrar por moneda (ya están en CLP)
        'tabla_factores': 'RF_FactCLP_Gob',
        'instrumento_fpl': 'Gobierno CLP',
        'instrumento_montos_liq': 'Gobierno CLP',
        'moneda': 'CLP',
        'nombre_salida': 'Flujo_GobCLP',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_GOBCLP'
    },
    'GobCLF': {
        'nombre_completo': 'Gobierno CLF',
        'codigos_disp': ['BCU', 'BTU'],
        'codigos_pacto': ['BCU', 'BTU', 'CER'],     # Nota: incluye CER en pactos
        'filtro_moneda': None,                       # No filtrar por moneda (ya están en CLF)
        'tabla_factores': 'RF_FactCLF_Gob',
        'instrumento_fpl': 'Gobierno CLF',
        'instrumento_montos_liq': 'Gobierno CLF',
        'moneda': 'CLF',
        'nombre_salida': 'Flujo_GobCLF',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_GOBCLF'
    },
    'DPF': {
        'nombre_completo': 'Depósito a Plazo Fijo',
        'codigos_disp': ['DPF'],
        'codigos_pacto': ['DPF', 'FFM'],            # Nota: incluye FFM en pactos
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLP_Banc',
        'instrumento_fpl': 'DPF',
        'instrumento_montos_liq': 'DPF',
        'moneda': 'CLP',
        'nombre_salida': 'Flujo_DPF',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_DPFCLP'
    },
    'DPR': {
        'nombre_completo': 'Depósito a Plazo Reajustable',
        'codigos_disp': ['DPR'],
        'codigos_pacto': ['DPR'],
        'filtro_moneda': None,
        'tabla_factores': 'RF_FactCLF_Banc',
        'instrumento_fpl': 'DPR',
        'instrumento_montos_liq': 'DPR',
        'moneda': 'CLF',
        'nombre_salida': 'Flujo_DPR',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_DPRCLF'
    },
    # BBC en CLP - Bonos Bancarios Corporativos en pesos
    'BBC': {
        'nombre_completo': 'Bonos Bancarios Corporativos CLP',
        'codigos_disp': ['BBC'],
        'codigos_pacto': ['BBC'],
        'filtro_moneda': 'CLP',                      # Filtrar solo BBC en CLP
        'tabla_factores': 'RF_FactCLP_Banc',
        'instrumento_fpl': 'Corporativo CLP',
        'instrumento_montos_liq': 'Corporativo CLP',
        'moneda': 'CLP',
        'nombre_salida': 'Flujo_BBC',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_CORPCLP'
    },
    # LCH - Combina Letras de Crédito Hipotecario + BBC en CLF
    # Access combina ambos en Flujo_LCH usando Corporativo CLF
    'LCH': {
        'nombre_completo': 'Letras Crédito Hipotecario + BBC CLF',
        'codigos_disp': ['LCH', 'BBC'],              # Ambos códigos (LCH cuando exista, BBC siempre)
        'codigos_pacto': ['LCH', 'BBC'],
        'filtro_moneda': 'CLF',                      # Filtrar solo los que están en CLF
        'tabla_factores': 'RF_FactCLF_Banc',
        'instrumento_fpl': 'Corporativo CLF',
        'instrumento_montos_liq': 'Corporativo CLF',
        'moneda': 'CLF',
        'nombre_salida': 'Flujo_LCH',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_LCHR'
    }
}

# =============================================================================
# FUNCIÓN DE COMPATIBILIDAD PARA TRANSICIÓN
# =============================================================================

def obtener_config_instrumento(nombre: str) -> dict:
    """
    Obtiene la configuración de un instrumento.
    
    Usa la configuración centralizada si está disponible,
    de lo contrario usa el dict local CONFIGURACION_INSTRUMENTOS.
    
    Args:
        nombre: Clave del instrumento ('GobCLP', 'DPF', etc.)
        
    Returns:
        Dict con la configuración del instrumento.
        
    Raises:
        KeyError: Si el instrumento no existe.
        
    Note:
        En código nuevo, preferir:
        >>> from RF_Modelo_Inversiones.config.instrumentos import obtener_instrumento
        >>> config = obtener_instrumento('GobCLP')
    """
    if _CONFIG_CENTRALIZADA_DISPONIBLE:
        # Usar configuración centralizada (retorna dataclass)
        cfg = obtener_instrumento(nombre)
        # Convertir dataclass a dict para compatibilidad
        return {
            'nombre_completo': cfg.nombre_completo,
            'codigos_disp': cfg.codigos_disp,
            'codigos_pacto': cfg.codigos_pacto,
            'filtro_moneda': cfg.filtro_moneda,
            'tabla_factores': cfg.tabla_factores,
            'instrumento_fpl': cfg.instrumento_fpl,
            'instrumento_montos_liq': cfg.instrumento_montos_liq,
            'moneda': cfg.moneda,
            'nombre_salida': cfg.nombre_salida,
            'cod_sub_pro_final': cfg.cod_sub_pro_final,
        }
    else:
        # Fallback a dict local
        if nombre not in CONFIGURACION_INSTRUMENTOS:
            raise KeyError(f"Instrumento '{nombre}' no existe.")
        return CONFIGURACION_INSTRUMENTOS[nombre]


def ejecutar_query_access(ruta_accdb: str, query: str, retornar_datos: bool = True) -> pd.DataFrame | None:
    """
    Ejecuta una query en MS Access que puede ser de tipo SELECT o de acción (INSERT, UPDATE, DELETE, SELECT INTO).
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        query: Query SQL a ejecutar
        retornar_datos: Si True, intenta retornar un DataFrame. Si False, solo ejecuta la query.
                       Usar False para queries de acción como SELECT INTO, UPDATE, DELETE.
    
    Returns:
        DataFrame con los resultados si retornar_datos=True, None en caso contrario.
    
    Ejemplos:
        # Query SELECT normal
        df = ejecutar_query_access(ruta, "SELECT * FROM tabla", retornar_datos=True)
        
        # Query de acción (crear tabla)
        ejecutar_query_access(ruta, "SELECT * INTO nueva_tabla FROM tabla_origen", retornar_datos=False)
        
        # Query UPDATE
        ejecutar_query_access(ruta, "UPDATE tabla SET campo = valor WHERE condicion", retornar_datos=False)
    """
    import pyodbc
    from sqlalchemy import create_engine, URL, text
    import pandas as pd
    
    # Configurar conexión
    connection_str = r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};'
    connection_str += f'DBQ={ruta_accdb};'
    
    if retornar_datos:
        # Para queries SELECT que retornan datos, usar pandas + SQLAlchemy
        connection_url = URL.create("access+pyodbc", query={"odbc_connect": connection_str})
        engine = create_engine(connection_url)
        try:
            resultado = pd.read_sql(text(query), con=engine)
            return resultado
        finally:
            engine.dispose()
    else:
        # Para queries de acción (INSERT, UPDATE, DELETE, SELECT INTO), usar pyodbc directo
        conn = None
        cursor = None
        try:
            conn = pyodbc.connect(connection_str)
            cursor = conn.cursor()
            
            # Ejecutar la query
            cursor.execute(query)
            
            # Commit para queries de acción
            conn.commit()
            
            print(f"Query ejecutada exitosamente. Filas afectadas: {cursor.rowcount}")
            return None
            
        except pyodbc.Error as e:
            if conn:
                conn.rollback()
            print(f"Error al ejecutar query: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

def compactar_access_db(ruta_accdb: str, ruta_backup: str = None) -> None:
    """
    Compacta y repara una base de datos MS Access para liberar espacio no utilizado.
    
    Este proceso:
    1. Reduce el tamaño del archivo eliminando espacio fragmentado
    2. Repara inconsistencias menores
    3. Reorganiza los datos para mejorar el rendimiento
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb a compactar
        ruta_backup: (Opcional) Ruta donde guardar una copia antes de compactar
    
    Nota: Requiere que Access esté instalado en el sistema (usa win32com)
    """
    import win32com.client
    import shutil
    import tempfile
    
    # Crear backup si se solicita
    if ruta_backup:
        print(f"Creando backup en: {ruta_backup}")
        shutil.copy2(ruta_accdb, ruta_backup)
    
    # Obtener tamaño inicial
    tamaño_inicial = os.path.getsize(ruta_accdb) / (1024 * 1024)  # MB
    print(f"Tamaño inicial: {tamaño_inicial:.2f} MB")
    
    # Crear archivo temporal para compactación
    fd, temp_path = tempfile.mkstemp(suffix='.accdb', prefix='compact_')
    print(f"Archivo temporal para compactación: {temp_path}")
    print(f"fd: {fd}")

    temp_path = os.path.normpath(temp_path)
    try:
        # Crear instancia de Access
        access = win32com.client.Dispatch("Access.Application")
        
        # Compactar: crea una copia compactada en temp_path
        print("Compactando base de datos...")
        access.CompactRepair(ruta_accdb,fd)        
        # Cerrar Access
        access.Quit()
        os.close(fd)
        # Reemplazar archivo original con el compactado
        shutil.move(temp_path, ruta_accdb)
        
        # Obtener tamaño final
        tamaño_final = os.path.getsize(ruta_accdb) / (1024 * 1024)  # MB
        ahorro = tamaño_inicial - tamaño_final
        porcentaje = (ahorro / tamaño_inicial) * 100
        
        print(f"Tamaño final: {tamaño_final:.2f} MB")
        print(f"Espacio liberado: {ahorro:.2f} MB ({porcentaje:.1f}%)")
        
    except Exception as e:
        print(f"Error al compactar: {e}")
        # Limpiar archivo temporal si existe
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise
    finally:
        # Asegurar que Access se cierre
        try:
            access.Quit()
        except:
            pass
        os.close(temp_path)

def guardar_tablas_linkeadas_pickle(tablas: dict, fecha_proceso: int, data_path: pathlib.Path) -> None:
    import pickle
    import datetime
    import pathlib
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = data_path / f"tablas_linkeadas_ml_inversiones_{fecha_proceso}_{timestamp}.pkl"
    
    with open(nombre_archivo, "wb") as f:
        pickle.dump(tablas, f)
    
    print(f"Tablas linkeadas guardadas en pickle: {nombre_archivo}")

# leyendo las tablas linkeadas
def leer_tablas_linkeadas( df_links: pd.DataFrame) -> dict:
    """
    Lee las tablas linkeadas desde un DataFrame de links y retorna un diccionario de DataFrames.
    
    Args:
        df_links: DataFrame con columnas 'nombre', 'ruta_normalizada', 'nombre_tabla_fuente'

    Returns:
        Diccionario donde las claves son los nombres de las tablas y los valores son los DataFrames correspondientes.
    """
    import pandas as pd
    
    tablas_linkeadas = {}
    for idx, row in df_links.iterrows():
        nombre_tabla = row['nombre']
        ruta_fuente = row['ruta_normalizada']
        nombre_tabla_fuente = row['nombre_tabla_fuente']
        if ruta_fuente.endswith('.accdb'):
            tipo_fuente = "Access"
        elif ruta_fuente.endswith('.xlsx') or ruta_fuente.endswith('.xlsm'):
            tipo_fuente = "Excel"
        else:
            tipo_fuente = "Otro"
        if tipo_fuente=="Access":    
            print(f"Tabla Access: {nombre_tabla} -> Fuente: {ruta_fuente} / Tabla fuente: {nombre_tabla_fuente}")
            df_temp = ejecutar_query_access(ruta_fuente,f"SELECT * FROM {nombre_tabla_fuente}",retornar_datos=True)
            print(f"  - Filas: {df_temp.shape[0]}, Columnas: {df_temp.shape[1]}")
            tablas_linkeadas[nombre_tabla] = df_temp
        elif tipo_fuente=="Excel":
            print(f"Tabla Excel: {nombre_tabla} -> Fuente: {ruta_fuente} / Tabla fuente: {nombre_tabla_fuente}")
            df_temp = pd.read_excel(ruta_fuente,sheet_name=nombre_tabla_fuente)
            print(f"  - Filas: {df_temp.shape[0]}, Columnas: {df_temp.shape[1]}")
            tablas_linkeadas[nombre_tabla] = df_temp
        else:
            print(f"Tipo de fuente no soportado para tabla {nombre_tabla}: {ruta_fuente}")
    
    return tablas_linkeadas
# chequeamos si hay un pickle con las tablas linkeadas ya leídas para la fecha de proceso correspondiente
def check_pickle_tablas_linkeadas(fecha_proceso: int, data_path: pathlib.Path, df_links: pd.DataFrame) -> dict | None:
    import pickle
    import datetime
    import pathlib
    import os
    
    archivos_pickle = list(data_path.glob(f"tablas_linkeadas_ml_inversiones_{fecha_proceso}_*.pkl"))
    if archivos_pickle:
        # Tomamos el archivo más reciente
        archivo_reciente = max(archivos_pickle, key=os.path.getctime)
        print(f"Cargando tablas linkeadas desde pickle: {archivo_reciente}")
        with open(archivo_reciente, "rb") as f:
            tablas_linkeadas = pickle.load(f)
    else:
        print("No se encontró pickle con tablas linkeadas para la fecha de proceso.")
        print("Leyendo tablas linkeadas desde las fuentes originales...")
        tablas_linkeadas = leer_tablas_linkeadas(df_links)
        guardar_tablas_linkeadas_pickle(tablas_linkeadas, fecha_proceso, data_path)

    return tablas_linkeadas

def extraer_tablas_access (ruta_accdb: str, lista_tablas: list) -> dict:
    """
    Extrae tablas específicas desde una base de datos MS Access y las retorna en un diccionario de DataFrames.
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        lista_tablas: Lista de nombres de tablas a extraer
    
    Returns:
        Diccionario donde las claves son los nombres de las tablas y los valores son los DataFrames correspondientes.
    """
    tablas_extraidas = {}
    for nombre_tabla in lista_tablas:
        print(f"Extrayendo tabla: {nombre_tabla}")
        query = f"SELECT * FROM {nombre_tabla}"
        df_tabla = ejecutar_query_access(ruta_accdb, query, retornar_datos=True)
        print(f"  - Filas: {df_tabla.shape[0]}, Columnas: {df_tabla.shape[1]}")
        tablas_extraidas[nombre_tabla] = df_tabla
    return tablas_extraidas

def check_pickle_tablas_inversiones(fecha_proceso: int, data_path: pathlib.Path, ruta_accdb: str, lista_tablas: list) -> dict | None:

    import pickle
    import datetime
    import pathlib
    import os
    
    archivos_pickle = list(data_path.glob(f"tablas_inversiones_ml_{fecha_proceso}_*.pkl"))
    if archivos_pickle:
        # Tomamos el archivo más reciente
        archivo_reciente = max(archivos_pickle, key=os.path.getctime)
        print(f"Cargando tablas de inversiones desde pickle: {archivo_reciente}")
        with open(archivo_reciente, "rb") as f:
            tablas_inversiones = pickle.load(f)
    else:
        print("No se encontró pickle con tablas de inversiones para la fecha de proceso.")
        print("Extrayendo tablas de inversiones desde Access...")
        tablas_inversiones = extraer_tablas_access(ruta_accdb, lista_tablas)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = data_path / f"tablas_inversiones_ml_{fecha_proceso}_{timestamp}.pkl"
        with open(nombre_archivo, "wb") as f:
            pickle.dump(tablas_inversiones, f)
        print(f"Tablas de inversiones guardadas en pickle: {nombre_archivo}")

    return tablas_inversiones


# =============================================================================
# FUNCIONES PARA EXTRACCIÓN COMPLETA DE ACCESS PRODUCTIVO
# =============================================================================

def listar_objetos_access(ruta_accdb: str) -> dict:
    """
    Lista TODOS los objetos (tablas y queries) de una base de datos Access.
    
    IMPORTANTE: Esta función es SOLO LECTURA. No modifica la base de datos.
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        
    Returns:
        Diccionario con dos listas:
        {
            'tablas': [{'nombre': str, 'tipo': str, 'es_sistema': bool}, ...],
            'queries': [{'nombre': str, 'tipo': str}, ...]
        }
        
    Notas:
        - Tablas del sistema (MSys*, ~*) se incluyen pero marcadas con es_sistema=True
        - Queries guardadas se obtienen con tableType='VIEW' en pyodbc
    """
    import pyodbc
    
    conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta_accdb};'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    resultado = {
        'tablas': [],
        'queries': []
    }
    
    # Listar TABLAS (tableType='TABLE')
    for table_info in cursor.tables(tableType='TABLE'):
        nombre = table_info.table_name
        es_sistema = nombre.startswith('MSys') or nombre.startswith('~')
        resultado['tablas'].append({
            'nombre': nombre,
            'tipo': 'TABLE',
            'es_sistema': es_sistema
        })
    
    # Listar QUERIES guardadas (tableType='VIEW')
    for query_info in cursor.tables(tableType='VIEW'):
        nombre = query_info.table_name
        resultado['queries'].append({
            'nombre': nombre,
            'tipo': 'VIEW'
        })
    
    conn.close()
    
    print(f"Objetos en Access: {len(resultado['tablas'])} tablas, {len(resultado['queries'])} queries")
    tablas_usuario = sum(1 for t in resultado['tablas'] if not t['es_sistema'])
    tablas_sistema = len(resultado['tablas']) - tablas_usuario
    print(f"  Tablas usuario: {tablas_usuario}, Tablas sistema: {tablas_sistema}")
    
    return resultado


def extraer_todas_tablas_access(ruta_accdb: str, incluir_sistema: bool = False, verbose: bool = True) -> dict:
    """
    Extrae TODAS las tablas de una base de datos Access a un diccionario de DataFrames.
    
    IMPORTANTE: Esta función es SOLO LECTURA. No modifica la base de datos.
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        incluir_sistema: Si True, incluye tablas del sistema (MSys*, ~*). Default False.
        verbose: Si True, muestra progreso de extracción
        
    Returns:
        Diccionario {nombre_tabla: DataFrame, ...}
        
    Notas:
        - Las tablas que fallan se registran en el dict con valor None y se documentan
        - No modifica la base de datos bajo ninguna circunstancia
    """
    import pyodbc
    
    # Primero listar todas las tablas
    objetos = listar_objetos_access(ruta_accdb)
    lista_tablas = objetos['tablas']
    
    # Filtrar tablas de sistema si no se incluyen
    if not incluir_sistema:
        lista_tablas = [t for t in lista_tablas if not t['es_sistema']]
    
    if verbose:
        print(f"\nExtrayendo {len(lista_tablas)} tablas de Access...")
        print("-" * 60)
    
    tablas_extraidas = {}
    errores = []
    
    for i, tabla_info in enumerate(lista_tablas, 1):
        nombre_tabla = tabla_info['nombre']
        try:
            query = f"SELECT * FROM [{nombre_tabla}]"
            df = ejecutar_query_access(ruta_accdb, query, retornar_datos=True)
            tablas_extraidas[nombre_tabla] = df
            if verbose:
                print(f"  [{i:3d}/{len(lista_tablas)}] ✓ {nombre_tabla}: {len(df):,} filas, {len(df.columns)} cols")
        except Exception as e:
            error_msg = str(e)[:80]
            tablas_extraidas[nombre_tabla] = None  # Marcamos como fallida pero incluimos
            errores.append({'tabla': nombre_tabla, 'error': error_msg})
            if verbose:
                print(f"  [{i:3d}/{len(lista_tablas)}] ✗ {nombre_tabla}: {error_msg}")
    
    if verbose:
        print("-" * 60)
        exitosas = sum(1 for v in tablas_extraidas.values() if v is not None)
        print(f"Extracción completada: {exitosas}/{len(lista_tablas)} tablas exitosas")
        if errores:
            print(f"\n⚠️ Tablas con errores ({len(errores)}):")
            for err in errores:
                print(f"  - {err['tabla']}: {err['error']}")
    
    return tablas_extraidas


def obtener_sql_queries_access(ruta_accdb: str) -> dict:
    """
    Obtiene el SQL de todas las queries guardadas en Access consultando MSysQueries.
    
    IMPORTANTE: Esta función es SOLO LECTURA. No modifica la base de datos.
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        
    Returns:
        Diccionario {nombre_query: sql_text, ...}
        Si no se puede obtener el SQL, retorna diccionario vacío.
        
    Notas:
        - Requiere permisos de lectura en tablas del sistema
        - En algunos Access puede fallar por restricciones de seguridad
    """
    import pyodbc
    
    sql_queries = {}
    
    try:
        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta_accdb};'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Intentar leer MSysQueries para obtener el SQL
        # Esta tabla contiene el SQL de las queries guardadas
        try:
            cursor.execute("""
                SELECT Name1 as QueryName, Expression as SQLText
                FROM MSysQueries 
                WHERE Attribute = 6
            """)
            for row in cursor.fetchall():
                nombre = row.QueryName
                sql = row.SQLText if row.SQLText else ''
                if nombre in sql_queries:
                    sql_queries[nombre] += ' ' + sql
                else:
                    sql_queries[nombre] = sql
        except Exception as e:
            # MSysQueries puede no ser accesible
            print(f"⚠️ No se pudo leer MSysQueries: {str(e)[:60]}")
            print("   Se usará detección por nombre de query")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Error al conectar para obtener SQL: {str(e)[:60]}")
    
    return sql_queries


def clasificar_query_por_tipo(nombre_query: str, sql_text: str = None) -> dict:
    """
    Clasifica una query como de LECTURA o ESCRITURA basado en su SQL o nombre.
    
    Args:
        nombre_query: Nombre de la query
        sql_text: Texto SQL de la query (opcional)
        
    Returns:
        Diccionario con:
        {
            'tipo': 'LECTURA' | 'ESCRITURA' | 'DESCONOCIDO',
            'razon': str explicando la clasificación,
            'es_segura': bool
        }
        
    PALABRAS CLAVE DE ESCRITURA (PELIGROSAS):
    - INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE
    - SELECT INTO (crea tablas)
    - MAKE TABLE, APPEND
    """
    # Palabras clave que indican queries de escritura (PELIGROSAS)
    PALABRAS_ESCRITURA = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
        'INTO',  # SELECT INTO crea tablas
        'MAKE', 'APPEND'
    ]
    
    # Patrones en nombres que indican queries de acción
    PATRONES_NOMBRE_ESCRITURA = [
        '_Gener_',      # Queries que "generan" tablas
        '_Borrar',      # Queries de borrado
        '_Delete',      # Queries de borrado
        '_Actualizar',  # Queries de actualización
        '_Update',      # Queries de actualización
        '_Insert',      # Queries de inserción
        '_Crear',       # Queries de creación
        '_Create',      # Queries de creación
        'Append_',      # Queries de append
        'MakeTable_',   # Queries de crear tabla
    ]
    
    resultado = {
        'tipo': 'DESCONOCIDO',
        'razon': '',
        'es_segura': False
    }
    
    # 1. Si tenemos el SQL, analizarlo
    if sql_text:
        sql_upper = sql_text.upper().strip()
        
        # Verificar palabras de escritura
        for palabra in PALABRAS_ESCRITURA:
            if palabra in sql_upper:
                # Caso especial: "INTO" solo es peligroso en "SELECT ... INTO"
                if palabra == 'INTO':
                    if 'SELECT' in sql_upper and 'INTO' in sql_upper:
                        # Verificar que INTO viene después de SELECT (SELECT INTO)
                        pos_select = sql_upper.find('SELECT')
                        pos_into = sql_upper.find('INTO')
                        if pos_into > pos_select:
                            resultado['tipo'] = 'ESCRITURA'
                            resultado['razon'] = f'SQL contiene SELECT INTO (crea tabla)'
                            return resultado
                else:
                    resultado['tipo'] = 'ESCRITURA'
                    resultado['razon'] = f'SQL contiene palabra clave: {palabra}'
                    return resultado
        
        # Si llegamos aquí y empieza con SELECT (sin INTO después), es lectura
        if sql_upper.startswith('SELECT') and 'INTO' not in sql_upper:
            resultado['tipo'] = 'LECTURA'
            resultado['razon'] = 'Query SELECT pura'
            resultado['es_segura'] = True
            return resultado
    
    # 2. Si no tenemos SQL, analizar por nombre
    nombre_upper = nombre_query.upper()
    
    for patron in PATRONES_NOMBRE_ESCRITURA:
        if patron.upper() in nombre_upper:
            resultado['tipo'] = 'ESCRITURA'
            resultado['razon'] = f'Nombre contiene patrón sospechoso: {patron}'
            return resultado
    
    # 3. Si no hay indicios de escritura, marcar como lectura pero con precaución
    if sql_text:
        resultado['tipo'] = 'LECTURA'
        resultado['razon'] = 'No se detectaron palabras de escritura en SQL'
        resultado['es_segura'] = True
    else:
        resultado['tipo'] = 'DESCONOCIDO'
        resultado['razon'] = 'Sin SQL disponible, no se puede determinar con certeza'
        resultado['es_segura'] = False
    
    return resultado


def extraer_todas_queries_access(ruta_accdb: str, verbose: bool = True, solo_lectura: bool = True) -> dict:
    """
    Ejecuta las queries guardadas de una base de datos Access y retorna los resultados.
    
    IMPORTANTE: Por defecto solo ejecuta queries de LECTURA (SELECT puro).
    Las queries de ESCRITURA se reportan pero NO se ejecutan.
    
    Args:
        ruta_accdb: Ruta completa al archivo .accdb o .mdb
        verbose: Si True, muestra progreso de extracción
        solo_lectura: Si True (default), SOLO ejecuta queries de lectura.
                     Las queries de escritura se reportan pero NO se ejecutan.
        
    Returns:
        Diccionario con estructura:
        {
            'resultados': {nombre_query: DataFrame, ...},
            'errores': [{'query': str, 'error': str}, ...],
            'queries_escritura': [{'query': str, 'razon': str, 'sql': str}, ...],
            'queries_desconocidas': [{'query': str, 'razon': str}, ...]
        }
        
    Notas:
        - Queries de escritura (INSERT, UPDATE, DELETE, SELECT INTO, etc.) 
          se reportan en 'queries_escritura' pero NO se ejecutan
        - Solo lee datos, NUNCA modifica la base de datos
    """
    # Primero listar todas las queries
    objetos = listar_objetos_access(ruta_accdb)
    lista_queries = objetos['queries']
    
    if verbose:
        print(f"\nAnalizando {len(lista_queries)} queries de Access...")
        print("-" * 70)
    
    # Intentar obtener el SQL de las queries para clasificarlas
    sql_queries = obtener_sql_queries_access(ruta_accdb)
    if sql_queries:
        print(f"  ✓ SQL obtenido para {len(sql_queries)} queries")
    
    # Clasificar queries
    queries_lectura = []
    queries_escritura = []
    queries_desconocidas = []
    
    for query_info in lista_queries:
        nombre = query_info['nombre']
        sql_text = sql_queries.get(nombre, None)
        
        clasificacion = clasificar_query_por_tipo(nombre, sql_text)
        
        if clasificacion['tipo'] == 'ESCRITURA':
            queries_escritura.append({
                'query': nombre,
                'razon': clasificacion['razon'],
                'sql': sql_text[:200] if sql_text else 'N/A'
            })
        elif clasificacion['tipo'] == 'LECTURA' and clasificacion['es_segura']:
            queries_lectura.append(nombre)
        else:
            queries_desconocidas.append({
                'query': nombre,
                'razon': clasificacion['razon']
            })
    
    if verbose:
        print(f"\nClasificación de queries:")
        print(f"  ✓ LECTURA (seguras): {len(queries_lectura)}")
        print(f"  ⚠️ ESCRITURA (NO ejecutar): {len(queries_escritura)}")
        print(f"  ❓ DESCONOCIDAS: {len(queries_desconocidas)}")
    
    # Mostrar queries de escritura detectadas
    if verbose and queries_escritura:
        print(f"\n{'='*70}")
        print("⚠️  QUERIES DE ESCRITURA DETECTADAS - NO SE EJECUTARÁN")
        print("    (Estas queries modifican datos: INSERT, UPDATE, DELETE, SELECT INTO)")
        print(f"{'='*70}")
        for q in queries_escritura:
            print(f"  - {q['query']}")
            print(f"    Razón: {q['razon']}")
            if q['sql'] != 'N/A':
                print(f"    SQL: {q['sql'][:100]}...")
        print(f"{'='*70}\n")
    
    # Ejecutar SOLO queries de lectura
    if verbose:
        print(f"\nEjecutando {len(queries_lectura)} queries de LECTURA...")
        print("-" * 70)
    
    resultados = {}
    errores = []
    
    for i, nombre_query in enumerate(queries_lectura, 1):
        try:
            # Las queries guardadas se pueden consultar igual que tablas
            sql = f"SELECT * FROM [{nombre_query}]"
            df = ejecutar_query_access(ruta_accdb, sql, retornar_datos=True)
            resultados[nombre_query] = df
            if verbose:
                print(f"  [{i:3d}/{len(queries_lectura)}] ✓ {nombre_query}: {len(df):,} filas, {len(df.columns)} cols")
        except Exception as e:
            error_msg = str(e)[:100]
            errores.append({'query': nombre_query, 'error': error_msg})
            if verbose:
                print(f"  [{i:3d}/{len(queries_lectura)}] ✗ {nombre_query}: {error_msg}")
    
    if verbose:
        print("-" * 70)
        print(f"Ejecución completada: {len(resultados)}/{len(queries_lectura)} queries de lectura exitosas")
        if errores:
            print(f"\n⚠️ Queries de lectura con errores ({len(errores)}):")
            for err in errores[:10]:
                print(f"  - {err['query']}: {err['error']}")
            if len(errores) > 10:
                print(f"  ... y {len(errores) - 10} más")
    
    return {
        'resultados': resultados,
        'errores': errores,
        'queries_escritura': queries_escritura,
        'queries_desconocidas': queries_desconocidas
    }


def check_pickle_access_prod(
    fecha_proceso: int, 
    data_path: pathlib.Path, 
    ruta_accdb: str,
    tipo: str = 'tablas',
    forzar_recarga: bool = False
) -> dict:
    """
    Verifica si existe un pickle con las tablas o queries del Access productivo.
    Si no existe (o se fuerza recarga), extrae desde Access y guarda pickle.
    
    IMPORTANTE: Esta función es SOLO LECTURA sobre el Access. No modifica nada.
    
    Args:
        fecha_proceso: Fecha de proceso en formato YYYYMMDD
        data_path: Ruta al directorio donde guardar/buscar pickles
        ruta_accdb: Ruta al archivo Access productivo
        tipo: 'tablas' o 'queries' - qué extraer
        forzar_recarga: Si True, recarga desde Access aunque exista pickle
        
    Returns:
        Diccionario con los datos extraídos:
        - Si tipo='tablas': {nombre_tabla: DataFrame, ...}
        - Si tipo='queries': {'resultados': {...}, 'errores': [...]}
        
    Nomenclatura de pickles:
        - Tablas: tablas_access_prod_{fecha_proceso}_{timestamp}.pkl
        - Queries: queries_access_prod_{fecha_proceso}_{timestamp}.pkl
    """
    import pickle
    
    # Determinar nombre base según tipo
    if tipo == 'tablas':
        patron_pickle = f"tablas_access_prod_{fecha_proceso}_*.pkl"
    elif tipo == 'queries':
        patron_pickle = f"queries_access_prod_{fecha_proceso}_*.pkl"
    else:
        raise ValueError(f"Tipo inválido: {tipo}. Usar 'tablas' o 'queries'.")
    
    # Buscar pickle existente
    archivos_pickle = list(data_path.glob(patron_pickle))
    
    if archivos_pickle and not forzar_recarga:
        # Cargar pickle más reciente
        archivo_reciente = max(archivos_pickle, key=os.path.getctime)
        print(f"Cargando {tipo} desde pickle: {archivo_reciente.name}")
        with open(archivo_reciente, "rb") as f:
            datos = pickle.load(f)
        
        # Mostrar resumen
        if tipo == 'tablas':
            exitosas = sum(1 for v in datos.values() if v is not None)
            print(f"  → {exitosas} tablas cargadas")
        else:
            n_resultados = len(datos.get('resultados', {}))
            n_errores = len(datos.get('errores', []))
            n_escritura = len(datos.get('queries_escritura', []))
            n_desconocidas = len(datos.get('queries_desconocidas', []))
            print(f"  → {n_resultados} queries de lectura cargadas")
            print(f"  → {n_errores} queries con errores")
            if n_escritura > 0:
                print(f"  → ⚠️ {n_escritura} queries de ESCRITURA (NO ejecutadas)")
            if n_desconocidas > 0:
                print(f"  → ❓ {n_desconocidas} queries sin clasificar")
        
        return datos
    
    # No existe pickle o se fuerza recarga: extraer desde Access
    if forzar_recarga:
        print(f"Forzando recarga de {tipo} desde Access productivo...")
    else:
        print(f"No se encontró pickle de {tipo} para fecha {fecha_proceso}")
    
    print(f"Extrayendo {tipo} desde: {ruta_accdb}")
    print("NOTA: Operación de SOLO LECTURA - No se modifica el Access")
    
    if tipo == 'tablas':
        datos = extraer_todas_tablas_access(ruta_accdb, incluir_sistema=False, verbose=True)
    else:
        datos = extraer_todas_queries_access(ruta_accdb, verbose=True)
    
    # Guardar pickle
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if tipo == 'tablas':
        nombre_archivo = data_path / f"tablas_access_prod_{fecha_proceso}_{timestamp}.pkl"
    else:
        nombre_archivo = data_path / f"queries_access_prod_{fecha_proceso}_{timestamp}.pkl"
    
    with open(nombre_archivo, "wb") as f:
        pickle.dump(datos, f)
    print(f"\n✓ Datos guardados en: {nombre_archivo.name}")
    
    return datos


def ejecutar_query_access_con_cache(
    nombre_query: str,
    ruta_accdb: str,
    fecha_proceso: int,
    data_path: pathlib.Path,
    forzar_recarga: bool = False
) -> pd.DataFrame:
    """
    Ejecuta una query específica de Access y guarda el resultado en pickle.
    Si ya existe el pickle, carga desde ahí (mucho más rápido).
    
    IMPORTANTE: 
    - Esta función ejecuta queries de LECTURA (SELECT) solamente
    - Si la query modifica datos, se recomienda NO usarla sin revisar primero
    - Queries lentas (~2 min) se benefician enormemente del cache
    
    Args:
        nombre_query: Nombre de la query guardada en Access (ej: 'RF_PLI_006c_Haircut_Dia_Pcto')
        ruta_accdb: Ruta completa al archivo .accdb
        fecha_proceso: Fecha de proceso en formato YYYYMMDD (para nombrar el pickle)
        data_path: Directorio donde guardar/buscar el pickle
        forzar_recarga: Si True, ejecuta desde Access aunque exista pickle
        
    Returns:
        DataFrame con el resultado de la query
        
    Ejemplo:
        df_haircut = ejecutar_query_access_con_cache(
            nombre_query='RF_PLI_006c_Haircut_Dia_Pcto',
            ruta_accdb=accdb_prod_path,
            fecha_proceso=20251117,
            data_path=data_path
        )
    """
    import pickle
    import pyodbc
    import time
    
    # Nombre del pickle: query_{nombre_query}_{fecha_proceso}.pkl
    nombre_archivo_pkl = data_path / f"query_{nombre_query}_{fecha_proceso}.pkl"
    
    # Verificar si existe cache
    if nombre_archivo_pkl.exists() and not forzar_recarga:
        print(f"✓ Cargando query '{nombre_query}' desde cache...")
        with open(nombre_archivo_pkl, "rb") as f:
            datos = pickle.load(f)
        df = datos['dataframe']
        tiempo_original = datos.get('tiempo_ejecucion', 'N/A')
        print(f"  → {len(df):,} registros cargados (tiempo original: {tiempo_original})")
        return df
    
    # Ejecutar query desde Access
    print(f"Ejecutando query '{nombre_query}' desde Access...")
    print(f"  Ruta: {ruta_accdb}")
    
    tiempo_inicio = time.time()
    
    try:
        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={ruta_accdb};'
        conn = pyodbc.connect(conn_str)
        
        # Ejecutar query guardada (SELECT * FROM [nombre_query])
        query_sql = f"SELECT * FROM [{nombre_query}]"
        df = pd.read_sql(query_sql, conn)
        conn.close()
        
        tiempo_fin = time.time()
        tiempo_ejecucion = tiempo_fin - tiempo_inicio
        
        print(f"✓ Query ejecutada en {tiempo_ejecucion:.1f} segundos")
        print(f"  → {len(df):,} registros, {len(df.columns)} columnas")
        
        # Guardar en pickle
        datos_cache = {
            'dataframe': df,
            'nombre_query': nombre_query,
            'fecha_proceso': fecha_proceso,
            'tiempo_ejecucion': f"{tiempo_ejecucion:.1f}s",
            'timestamp_extraccion': datetime.datetime.now().isoformat(),
            'columnas': list(df.columns)
        }
        
        with open(nombre_archivo_pkl, "wb") as f:
            pickle.dump(datos_cache, f)
        print(f"  → Cache guardado: {nombre_archivo_pkl.name}")
        
        return df
        
    except Exception as e:
        print(f"✗ Error ejecutando query '{nombre_query}': {e}")
        raise


def listar_queries_cacheadas(fecha_proceso: int, data_path: pathlib.Path) -> list:
    """
    Lista todas las queries que ya están cacheadas en pickle para una fecha de proceso.
    
    Args:
        fecha_proceso: Fecha de proceso en formato YYYYMMDD
        data_path: Directorio donde buscar los pickles
        
    Returns:
        Lista de nombres de queries cacheadas
    """
    import pickle
    
    archivos = list(data_path.glob(f"query_*_{fecha_proceso}.pkl"))
    queries_cacheadas = []
    
    print(f"Queries cacheadas para fecha {fecha_proceso}:")
    print("-" * 60)
    
    for archivo in sorted(archivos):
        # Extraer nombre de query del nombre de archivo
        # Formato: query_{nombre_query}_{fecha_proceso}.pkl
        nombre = archivo.stem  # query_RF_PLI_006c_Haircut_Dia_Pcto_20251117
        partes = nombre.split('_')
        # Quitar 'query' del inicio y fecha del final
        nombre_query = '_'.join(partes[1:-1])
        
        # Leer metadata del pickle
        try:
            with open(archivo, "rb") as f:
                datos = pickle.load(f)
            n_registros = len(datos['dataframe'])
            tiempo = datos.get('tiempo_ejecucion', 'N/A')
            print(f"  • {nombre_query}: {n_registros:,} registros (tiempo: {tiempo})")
            queries_cacheadas.append(nombre_query)
        except Exception as e:
            print(f"  • {nombre_query}: Error leyendo - {e}")
    
    if not queries_cacheadas:
        print("  (ninguna query cacheada)")
    
    print("-" * 60)
    print(f"Total: {len(queries_cacheadas)} queries cacheadas")
    
    return queries_cacheadas


def genera_tabla_RF_base_Completa_Hist(df = input, 
                    fecha_proceso = int(datetime.datetime.now(

                    ).strftime("%Y%m%d")), delta=10):
    """
    Paso 01: query 'RF_PLI_000_Gener_CarteraInv'
    args

    """    

    # WHERE RF_base_Completa_Hist_Input.Fec_Pro > DateAdd('d', -10, #2025 -11 -20 #)
    mask_1 = (df['Fec_Pro'] > pd.to_datetime(str(fecha_proceso), format="%Y%m%d") - pd.Timedelta(days=delta))
    # AND (RF_base_Completa_Hist_Input.Cod_Pro NOT LIKE '*publico*' 
    #      OR RF_base_Completa_Hist_Input.Clasificacion_Contable NOT LIKE 'htm')
    #ojo con los asteriscos en Access: se usan como comodines, en pandas usamos contains con case insensitive
    # en cambio para 'htm' no hay asteriscos, así que usamos contains normal

    mask_2 = (~df['Cod_Pro'].str.contains('publico', case=False, na=False)) | (~df['Clasificacion_Contable'].str.contains('htm', na=False))
    df_result = df[mask_1 & mask_2].copy()
    return df_result


def genera_cartera_inv_001(df_base: pd.DataFrame, df_fecha: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Objetivo de la función: 
    Recrear RF_PLI_001_CarteraInv en pandas
    
    
    Como inputs tiene RF_base_Completa_Hist y RF_Fecha_Proceso_Carteras, que ambas son tablas en el access. Por tanto no tiene dependencia directa de otras queries.   
    La tabla RF_base_Completa_Hist viene del paso 01 donde la query RF_PLI_000_Gener_CarteraInv genera esa tabla.
    La tabla RF_Fecha_Proceso_Carteras es una tabla linkeada en el access a una tabla de igual nombre en RF_Base_Carteras_Completas.accdb


    Args:
        df_base: DataFrame RF_base_Completa_Hist. 
        df_fecha: DataFrame RF_Fecha_Proceso_Carteras que
        verbose: Mostrar estadísticas de filtrado
    
    Returns:
        DataFrame RF_PLI_001_CarteraInv

    Query original Access:
    SELECT RF_base_Completa_Hist.Fec_Pro,
        RF_base_Completa_Hist.Cod_Emp, RF_base_Completa_Hist.Moneda,
        IIf(RF_base_Completa_Hist.Cod_Pro='INVERSIONES FINANCIERAS FONDOS MUTUOS' 
        Or RF_base_Completa_Hist.Cod_Pro='INVERSIONES FINANCIERAS FONDOS MUTUOS DERIVADOS',
        'Inversion Financiera Privado',RF_base_Completa_Hist.Cod_Pro) AS Cod_Pro,
        RF_base_Completa_Hist.Cod_Sub_Pro, RF_base_Completa_Hist.Nemotecnico,
        Left(RF_base_Completa_Hist.Nemotecnico,3) AS Instrumento, RF_base_Completa_Hist.VP_Cap_Amort, 
        RF_base_Completa_Hist.VP_Int_Total, RF_base_Completa_Hist.Dias_Vcto
    FROM RF_Fecha_Proceso_Carteras 
    INNER JOIN RF_base_Completa_Hist ON RF_Fecha_Proceso_Carteras.Fecha = RF_base_Completa_Hist.Fec_Pro
    WHERE Left(RF_base_Completa_Hist.Nemotecnico,3)<>'LCH' 
        And (Left(RF_base_Completa_Hist.Cod_Pro,20)='Inversion Financiera' 
        Or Left(RF_base_Completa_Hist.Cod_Pro,23)='INVERSIONES FINANCIERAS') 
        And (Right(RF_base_Completa_Hist.Cod_Sub_Pro,4)='Disp' 
        Or Right(RF_base_Completa_Hist.Cod_Sub_Pro,8)='Disp_Liq' 
        Or Right(RF_base_Completa_Hist.Cod_Sub_Pro,6)='MUTUOS') 
        And RF_base_Completa_Hist.Clasificacion_Contable<>"HTM";
    """
    # =========================================================================
    # CONFIGURACIÓN: Columnas y Constantes
    # =========================================================================
    COLUMNAS_SALIDA = [
        'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
        'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 'Dias_Vcto'
    ]
    
    PRODUCTOS_FONDOS_MUTUOS = [
        'INVERSIONES FINANCIERAS FONDOS MUTUOS',
        'INVERSIONES FINANCIERAS FONDOS MUTUOS DERIVADOS'
    ]
    
    if verbose:
        print("\n" + "="*70)
        print("PASO 01b: RF_PLI_001_CarteraInv")
        print("="*70)
        print(f"Registros entrada: {len(df_base):,}")
    
    # =========================================================================
    # PASO 1: FROM + JOIN (filtro por fecha de proceso)
    # El INNER JOIN con RF_Fecha_Proceso_Carteras filtra por fecha
    # =========================================================================
    fecha_proceso = df_fecha.loc[0, 'Fecha']
    
    # Asegurar tipos datetime compatibles
    if not pd.api.types.is_datetime64_any_dtype(df_base['Fec_Pro']):
        df_base = df_base.copy()
        df_base['Fec_Pro'] = pd.to_datetime(df_base['Fec_Pro'])
    if not pd.api.types.is_datetime64_any_dtype(fecha_proceso):
        fecha_proceso = pd.to_datetime(fecha_proceso)
    
    mask_fecha = df_base['Fec_Pro'] == fecha_proceso
    
    if verbose:
        print(f"\n[JOIN] Filtro fecha proceso = {fecha_proceso.strftime('%Y-%m-%d')}")
        print(f"  Registros que cumplen: {mask_fecha.sum():,}")
    
    # =========================================================================
    # PASO 2: WHERE (aplicar filtros secuencialmente)
    # =========================================================================
    
    # FILTRO 2.1: Nemotecnico NO empieza con 'LCH'
    # Access: Left(Nemotecnico,3)<>'LCH'
    mask_no_lch = ~df_base['Nemotecnico'].str[:3].eq('LCH')
    
    if verbose:
        print(f"\n[WHERE 1] Nemotecnico NO empieza con 'LCH'")
        print(f"  Registros que cumplen: {mask_no_lch.sum():,}")
    
    # FILTRO 2.2: Cod_Pro empieza con 'Inversion Financiera' O 'INVERSIONES FINANCIERAS'
    # Access: Left(Cod_Pro,20)='Inversion Financiera' Or Left(Cod_Pro,23)='INVERSIONES FINANCIERAS'
    mask_inversion = (
        df_base['Cod_Pro'].str[:20].eq('Inversion Financiera') |
        df_base['Cod_Pro'].str[:23].eq('INVERSIONES FINANCIERAS')
    )
    
    if verbose:
        print(f"\n[WHERE 2] Cod_Pro es inversión financiera")
        print(f"  Registros que cumplen: {mask_inversion.sum():,}")
    
    # FILTRO 2.3: Cod_Sub_Pro termina en 'Disp', 'Disp_Liq' o 'MUTUOS'
    # Access: Right(Cod_Sub_Pro,4)='Disp' Or Right(...)='Disp_Liq' Or Right(...)='MUTUOS'
    mask_subpro = (
        df_base['Cod_Sub_Pro'].str[-4:].eq('Disp') |
        df_base['Cod_Sub_Pro'].str[-8:].eq('Disp_Liq') |
        df_base['Cod_Sub_Pro'].str[-6:].eq('MUTUOS')
    )
    
    if verbose:
        print(f"\n[WHERE 3] Cod_Sub_Pro termina en 'Disp', 'Disp_Liq' o 'MUTUOS'")
        print(f"  Registros que cumplen: {mask_subpro.sum():,}")
    
    # FILTRO 2.4: Clasificacion_Contable NO es 'HTM'
    # Access: Clasificacion_Contable<>"HTM"
    mask_no_htm = ~df_base['Clasificacion_Contable'].str.upper().eq('HTM')
    
    if verbose:
        print(f"\n[WHERE 4] Clasificacion_Contable <> 'HTM'")
        print(f"  Registros que cumplen: {mask_no_htm.sum():,}")
    
    # COMBINAR TODOS LOS FILTROS (AND)
    mask_final = mask_fecha & mask_no_lch & mask_inversion & mask_subpro & mask_no_htm
    
    if verbose:
        print(f"\n[WHERE FINAL] Todos los filtros combinados (AND)")
        print(f"  Registros que cumplen: {mask_final.sum():,}")
    
    # Aplicar filtros
    df_filtrado = df_base[mask_final].copy()
    
    # =========================================================================
    # PASO 3: SELECT (transformaciones de columnas)
    # =========================================================================
    
    # TRANSFORMACIÓN 3.1: Cod_Pro con IIf
    # Access: IIf(Cod_Pro='INVERSIONES FINANCIERAS FONDOS MUTUOS' Or 
    #             Cod_Pro='...DERIVADOS', 'Inversion Financiera Privado', Cod_Pro)
    df_filtrado['Cod_Pro'] = df_filtrado['Cod_Pro'].replace(
        PRODUCTOS_FONDOS_MUTUOS,
        'Inversion Financiera Privado'
    )
    
    # TRANSFORMACIÓN 3.2: Crear columna 'Instrumento'
    # Access: Left(Nemotecnico,3) AS Instrumento
    df_filtrado['Instrumento'] = df_filtrado['Nemotecnico'].str[:3]
    
    # =========================================================================
    # PASO 4: Seleccionar solo columnas de salida
    # =========================================================================
    df_salida = df_filtrado[COLUMNAS_SALIDA].copy()
    
    if verbose:
        print(f"\n{'='*70}")
        print("RESULTADO FINAL")
        print(f"{'='*70}")
        print(f"  Registros entrada: {len(df_base):,}")
        print(f"  Registros salida:  {len(df_salida):,}")
        print(f"\n  Distribución Cod_Pro:")
        print(df_salida['Cod_Pro'].value_counts().to_string())
        print(f"\n  Distribución Instrumento:")
        print(df_salida['Instrumento'].value_counts().to_string())
    
    return df_salida


def generar_cartera_pond(df_cartera_instrumento, df_montototal, output_table_name):

    """
    Genera la tabla de cartera ponderada a partir de la cartera y el monto total.
    
    Args:
        df_cartera_instrumento: DataFrame con la cartera filtrada por el instrumento (input) 
        df_montototal: DataFrame con el monto total (input)
        output_table_name: Nombre de la tabla de output (string)
        
    Returns:
        DataFrame con la cartera ponderada
    """
    # Hacemos el merge entre las dos tablas
    df_merged = pd.merge(df_cartera_instrumento, df_montototal, on=['Cod_Pro', 'Moneda'], how='inner', suffixes=('', '_total'))
    
    # Calculamos el ponderador
    df_merged['Ponderador'] = (df_merged['VP_Cap_Amort'] + df_merged['VP_Int_Total']) / df_merged['VP_Flujo']
    
    # Seleccionamos las columnas necesarias para el output
    columnas_output = ['Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro', 'Nemotecnico', 
                       'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 'Dias_Vcto', 'Ponderador']
    
    df_output = df_merged[columnas_output].copy()
    print(f"Cartera ponderada {output_table_name}: {df_output.shape[0]} registros generados.")
    
    return df_output

def generar_cartera_instrumento(df_base, cols_de_salida, instrumento, nombre_instrumento, filtro_moneda=None):
    """
    Genera la tabla de cartera filtrada por instrumento y opcionalmente por moneda.
    
    Args:
        df_base: DataFrame con la base completa de cartera (input)
        cols_de_salida: Lista de columnas a mantener en el output
        instrumento: Lista de instrumentos a filtrar (list of strings)
        nombre_instrumento: Nombre del instrumento para logging (string)
        filtro_moneda: Moneda para filtrar (opcional). Si None, no filtra por moneda.
        
    Returns:
        DataFrame con la cartera filtrada por instrumento (y moneda si aplica)
    """
    # Filtrar por instrumento
    mask = df_base['Instrumento'].isin(instrumento)
    
    # Filtrar adicionalmente por moneda si se especifica
    if filtro_moneda is not None:
        mask = mask & (df_base['Moneda'] == filtro_moneda)
    
    df_filtrado = df_base[mask][cols_de_salida].copy()
    
    if filtro_moneda:
        print(f"Cartera {nombre_instrumento}: {df_filtrado.shape[0]} registros después de filtrar por instrumento {instrumento} y moneda {filtro_moneda}")
    else:
        print(f"Cartera {nombre_instrumento}: {df_filtrado.shape[0]} registros después de filtrar por instrumento {instrumento}")
    
    return df_filtrado

def generar_monto_total_instrumento(df_cartera_instrumento, cols_de_agrupacion,cols_suma, nombre_tabla):
    """
    Genera la tabla de monto total agrupada por Cod_Pro y Moneda.
    
    Args:
        df_cartera_instrumento: DataFrame con la cartera filtrada por instrumento (input)
        cols_de_agrupacion: Lista de columnas para agrupar (list of strings)
        cols_suma: Lista de columnas para sumar (list of strings)
        
    Returns:
        DataFrame con el monto total agrupado
    """
    df_monto_total = df_cartera_instrumento.groupby(cols_de_agrupacion)[cols_suma].sum().reset_index()
    df_monto_total['VP_Flujo'] = df_monto_total[cols_suma].sum(axis=1)
    df_monto_total = df_monto_total.drop(columns=cols_suma)

    print(f"Monto total {nombre_tabla} generado: {df_monto_total.shape[0]} registros después de agrupar por {cols_de_agrupacion}")
    
    return df_monto_total


def calcular_flujo_liquidacion(
    df_cartera_mon_total: pd.DataFrame,
    df_haircut_dia_pcto: pd.DataFrame,
    df_monto_liquidar: pd.DataFrame,
    nombre_instrumento: str = "Generico"
) -> pd.DataFrame:
    """
    Calcula el flujo de liquidación diario para cualquier tipo de instrumento.
    
    Traducción parametrizada de las funciones VBA MontoLiq{Instrumento}() a Python.
    Esta función es genérica y puede usarse para: GobCLP, GobCLF, DPF, DPR, LCH, BBC.
    
    Args:
        df_cartera_mon_total: DataFrame con columna 'VP_Flujo' (monto total inicial)
        df_haircut_dia_pcto: DataFrame con columnas:
            - Dia: número de día
            - DiaSem: día de la semana (1=Lun, ..., 6=Sáb, 7=Dom)
            - Haircut: factor de haircut
            - Monto_Pacto: monto de nuevos pactos que entran ese día
        df_monto_liquidar: DataFrame con columna 'Monto a Liquidar' por día
        nombre_instrumento: Nombre del instrumento para logging (ej: "GobCLP", "GobCLF")
    
    Returns:
        DataFrame con flujo diario: Dia, DiaSem, Haircut, Monto_Liquidar
    
    Notas:
        - No liquida en fines de semana (DiaSem = 6 o 7)
        - Haircut se aplica exponencialmente acumulado
        - Nuevos pactos entran con descuento por haircut
    """
    
    # 1. INICIALIZACIÓN
    # Obtener monto total inicial
    monto_tot = df_cartera_mon_total['VP_Flujo'].iloc[0]
    monto_acum = monto_tot
    
    # Crear lista para almacenar resultados
    flujo_salida = []
    
    # Registro inicial (día 0)
    flujo_salida.append({
        'Dia': 0,
        'DiaSem': None,
        'Haircut': 0.0,
        'Monto_Liquidar': monto_tot
    })
    
    # Factores iniciales
    factor_ti = 0.0
    monto_hc_ti = 0.0
    
    # Obtener monto diario planificado a liquidar (es un valor único para todos los días)
    # df_monto_liquidar tiene 1 solo registro con el monto diario constante
    monto_liq_diario = df_monto_liquidar['Monto a Liquidar'].iloc[0]
    
    # 2. LOOP POR CADA DÍA
    for idx, row_haircut in df_haircut_dia_pcto.iterrows():
        
        # Obtener valores del día actual
        dia = row_haircut['Dia']
        dia_sem = row_haircut['DiaSem']
        factor_t = row_haircut['Haircut']
        monto_pacto = row_haircut.get('Monto_Pacto', 0)  # Puede no existir la columna
        
        # Monto a liquidar planificado es constante todos los días hábiles
        monto_liq_planificado = monto_liq_diario
        
        # Calcular haircut incremental del día
        # MontoHC_t = max(0, Monto_Acum * (exp(factor_t) - exp(factor_ti)))
        monto_hc_t = max(
            0,
            monto_acum * (np.exp(factor_t) - np.exp(factor_ti))
        )
        
        # Determinar monto a liquidar (0 si es fin de semana)
        if dia_sem in [6, 7]:  # Sábado o Domingo
            monto_liq = 0.0
        else:
            monto_liq = monto_liq_planificado
        
        # 3. APLICAR REGLAS DE LIQUIDACIÓN
        saldo_disponible = monto_acum - monto_liq - monto_hc_t
        
        # Regla 1: Hay suficiente saldo para liquidar todo
        if saldo_disponible >= 0:
            flujo_salida.append({
                'Dia': dia,
                'DiaSem': dia_sem,
                'Haircut': factor_t,
                'Monto_Liquidar': monto_liq
            })
        
        # Regla 2: Déficit menor al 100% del monto planificado -> liquidación parcial
        elif (saldo_disponible < 0 and 
              abs(saldo_disponible) / monto_liq_planificado < 1):
            # Liquidar solo lo disponible después del haircut
            monto_liq_parcial = monto_acum - monto_hc_t if dia_sem not in [6, 7] else 0
            flujo_salida.append({
                'Dia': dia,
                'DiaSem': dia_sem,
                'Haircut': factor_t,
                'Monto_Liquidar': monto_liq_parcial
            })
        
        # Regla 3: Déficit mayor al 100% -> no liquidar nada
        elif (saldo_disponible < 0 and 
              abs(saldo_disponible) / monto_liq_planificado >= 1):
            flujo_salida.append({
                'Dia': dia,
                'DiaSem': dia_sem,
                'Haircut': factor_t,
                'Monto_Liquidar': 0.0
            })
        
        # 4. ACTUALIZAR MONTO ACUMULADO
        # Lógica compleja con IIf anidados en VBA:
        # - Si monto_acum < 0 y hay nuevo pacto: resetear con pacto descontado
        # - Si monto_acum > 0 y hay nuevo pacto: sumar pacto descontado
        # - Si no hay pacto: solo restar liquidación y haircut
        
        if monto_acum < 0 and monto_pacto > 0:
            # Caso 1: Monto negativo, entra nuevo pacto -> resetear
            monto_acum = monto_pacto * np.exp(-1 * factor_t)
        elif monto_acum > 0 and monto_pacto > 0:
            # Caso 2: Monto positivo, entra nuevo pacto -> acumular
            monto_acum = (monto_acum + 
                         monto_pacto * np.exp(-1 * factor_t) - 
                         monto_liq - 
                         monto_hc_t)
        else:
            # Caso 3: No hay pacto nuevo -> solo descontar liquidación y haircut
            monto_acum = monto_acum - monto_liq - monto_hc_t
        
        # Actualizar factor anterior
        factor_ti = factor_t
    
    # 5. RETORNAR DATAFRAME DE SALIDA
    df_flujo = pd.DataFrame(flujo_salida)
    
    return df_flujo


# Alias para compatibilidad hacia atrás
def monto_liq_gob_clp(
    df_cartera_mon_total: pd.DataFrame,
    df_haircut_dia_pcto: pd.DataFrame,
    df_monto_liquidar: pd.DataFrame
) -> pd.DataFrame:
    """Alias para compatibilidad. Usar calcular_flujo_liquidacion() en código nuevo."""
    return calcular_flujo_liquidacion(
        df_cartera_mon_total, df_haircut_dia_pcto, df_monto_liquidar, 
        nombre_instrumento="GobCLP"
    )


# =============================================================================
# FASE 1: RAMA PACTOS
# =============================================================================

def genera_cartera_inv_pacto(df_base: pd.DataFrame, df_fecha: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Genera RF_PLI_001d_CarteraInv_Pcto: Cartera de inversiones con pactos.
    
    Similar a genera_cartera_inv_001() pero con filtros para pactos:
    - Cod_Sub_Pro termina en 'Pcto' o 'Pcto_Liq' (en vez de 'Disp'/'Disp_Liq'/'MUTUOS')
    - NO tiene filtro de Nemotecnico != 'LCH'
    - NO tiene filtro de Clasificacion_Contable != 'HTM'
    - Incluye columna Dias_Pacto
    
    Args:
        df_base: DataFrame RF_base_Completa_Hist
        df_fecha: DataFrame con columna 'Fecha' (fecha de proceso)
        verbose: Mostrar estadísticas de filtrado
    
    Returns:
        DataFrame RF_PLI_001d_CarteraInv_Pcto
    
    SQL de referencia:
        SELECT Fec_Pro, Cod_Emp, Moneda, 
               IIf(Cod_Pro='INVERSIONES FINANCIERAS FONDOS MUTUOS','Inversion Financiera Privado',Cod_Pro) AS Cod_Pro,
               Cod_Sub_Pro, Nemotecnico, Left(Nemotecnico,3) AS Instrumento, 
               VP_Cap_Amort, VP_Int_Total, Dias_Vcto, Dias_Pacto
        FROM RF_Fecha_Proceso_Carteras 
        INNER JOIN RF_base_Completa_Hist ON Fecha = Fec_Pro
        WHERE (Left(Cod_Pro,20)='Inversion Financiera' Or Left(Cod_Pro,23)='INVERSIONES FINANCIERAS') 
          And (Right(Cod_Sub_Pro,4)='Pcto' Or Right(Cod_Sub_Pro,8)='Pcto_Liq');
    """
    # =========================================================================
    # CONFIGURACIÓN: Columnas de salida (incluye Dias_Pacto)
    # =========================================================================
    COLUMNAS_SALIDA = [
        'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
        'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 
        'Dias_Vcto', 'Dias_Pacto'
    ]
    
    if verbose:
        print("\n" + "="*70)
        print("FASE 1.1: RF_PLI_001d_CarteraInv_Pcto (Cartera Pactos)")
        print("="*70)
        print(f"Registros entrada: {len(df_base):,}")
    
    # =========================================================================
    # PASO 1: JOIN por fecha de proceso
    # =========================================================================
    fecha_proceso = df_fecha.loc[0, 'Fecha']
    
    # Asegurar tipos datetime compatibles
    if not pd.api.types.is_datetime64_any_dtype(df_base['Fec_Pro']):
        df_base = df_base.copy()
        df_base['Fec_Pro'] = pd.to_datetime(df_base['Fec_Pro'])
    if not pd.api.types.is_datetime64_any_dtype(fecha_proceso):
        fecha_proceso = pd.to_datetime(fecha_proceso)
    
    mask_fecha = df_base['Fec_Pro'] == fecha_proceso
    
    if verbose:
        print(f"\n[JOIN] Filtro fecha proceso = {fecha_proceso.strftime('%Y-%m-%d')}")
        print(f"  Registros que cumplen: {mask_fecha.sum():,}")
    
    # =========================================================================
    # PASO 2: WHERE - Filtros para pactos
    # =========================================================================
    
    # FILTRO 2.1: Cod_Pro empieza con 'Inversion Financiera' O 'INVERSIONES FINANCIERAS'
    mask_inversion = (
        df_base['Cod_Pro'].str[:20].eq('Inversion Financiera') |
        df_base['Cod_Pro'].str[:23].eq('INVERSIONES FINANCIERAS')
    )
    
    if verbose:
        print(f"\n[WHERE 1] Cod_Pro es inversión financiera")
        print(f"  Registros que cumplen: {mask_inversion.sum():,}")
    
    # FILTRO 2.2: Cod_Sub_Pro termina en 'Pcto' o 'Pcto_Liq'
    mask_pacto = (
        df_base['Cod_Sub_Pro'].str[-4:].eq('Pcto') |
        df_base['Cod_Sub_Pro'].str[-8:].eq('Pcto_Liq')
    )
    
    if verbose:
        print(f"\n[WHERE 2] Cod_Sub_Pro termina en 'Pcto' o 'Pcto_Liq'")
        print(f"  Registros que cumplen: {mask_pacto.sum():,}")
    
    # COMBINAR FILTROS (AND)
    mask_final = mask_fecha & mask_inversion & mask_pacto
    
    if verbose:
        print(f"\n[WHERE FINAL] Todos los filtros combinados (AND)")
        print(f"  Registros que cumplen: {mask_final.sum():,}")
    
    # Aplicar filtros
    df_filtrado = df_base[mask_final].copy()
    
    # =========================================================================
    # PASO 3: SELECT - Transformaciones
    # =========================================================================
    
    # Transformación Cod_Pro: IIf para fondos mutuos
    df_filtrado['Cod_Pro'] = df_filtrado['Cod_Pro'].replace(
        'INVERSIONES FINANCIERAS FONDOS MUTUOS',
        'Inversion Financiera Privado'
    )
    
    # Crear columna Instrumento
    df_filtrado['Instrumento'] = df_filtrado['Nemotecnico'].str[:3]
    
    # =========================================================================
    # PASO 4: Seleccionar columnas de salida
    # =========================================================================
    # Verificar que Dias_Pacto existe
    if 'Dias_Pacto' not in df_filtrado.columns:
        print("  ADVERTENCIA: Columna 'Dias_Pacto' no existe, creando con valor 0")
        df_filtrado['Dias_Pacto'] = 0
    
    df_salida = df_filtrado[COLUMNAS_SALIDA].copy()
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"RESULTADO: {len(df_salida):,} registros generados")
        print(f"Columnas: {list(df_salida.columns)}")
        print(f"{'='*70}")
    
    return df_salida


def generar_monto_plazo_pacto(df_cartera_pacto: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Genera RF_PLI_0XX_{instrumento}_MontoPlazo_Pacto: Monto total por plazo de pacto.
    
    Args:
        df_cartera_pacto: DataFrame con cartera de pactos (RF_PLI_002_CarteraGobCLP_Pacto)
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dias_Pacto, Monto
    
    SQL de referencia:
        SELECT Dias_Pacto, sum(VP_Cap_Amort + VP_Int_Total) AS Monto
        FROM RF_PLI_002_CarteraGobCLP_Pacto
        GROUP BY Dias_Pacto
        ORDER BY Dias_Pacto;
    """

    
    # Agrupar por Dias_Pacto y sumar VP_Cap_Amort + VP_Int_Total
    df_resultado = df_cartera_pacto.groupby('Dias_Pacto').agg(
        Monto=('VP_Cap_Amort', lambda x: x.sum() + df_cartera_pacto.loc[x.index, 'VP_Int_Total'].sum())
    ).reset_index()
    
    # Alternativa más limpia: calcular suma primero
    df_cartera_pacto_temp = df_cartera_pacto.copy()
    df_cartera_pacto_temp['VP_Total'] = df_cartera_pacto_temp['VP_Cap_Amort'] + df_cartera_pacto_temp['VP_Int_Total']
    df_resultado = df_cartera_pacto_temp.groupby('Dias_Pacto')['VP_Total'].sum().reset_index()
    df_resultado.columns = ['Dias_Pacto', 'Monto']
    
    # Ordenar por Dias_Pacto
    df_resultado = df_resultado.sort_values('Dias_Pacto').reset_index(drop=True)
    
    
    return df_resultado


# =============================================================================
# FASE 2: RAMA HAIRCUT
# =============================================================================

def generar_cartera_haircut(
    df_cartera_pond: pd.DataFrame,
    df_factores: pd.DataFrame,
    df_fpl: pd.DataFrame,
    filtro_instrumento: str | list,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera RF_PLI_0XX_CarteraHC: Cartera con factores de haircut.
    
    Realiza un JOIN entre la cartera ponderada y la tabla de factores,
    aplicando el máximo entre Factor y Haircut (piso FPL).
    
    Args:
        df_cartera_pond: DataFrame cartera ponderada (RF_PLI_0XX_Cartera{tipo_instrumento}_Pond)
        df_factores: DataFrame con factores por plazo (RF_FactCLP_Gob)
        df_fpl: DataFrame Floor Piso Liquidez (FPL)
        filtro_instrumento: Nombre del instrumento para filtrar FPL (ej: "Gobierno CLP")
                           Puede ser string o lista de strings
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas originales + Dia, Factor, FactorPond
    
    SQL de referencia:
        SELECT RF_CarteraGobCLP_Pond.*, RF_FactCLP_Gob.Dia, RF_FactCLP_Gob.Factor,
               Ponderador * (0.5*((Factor+Haircut)+ABS(Factor-Haircut))) AS FactorPond
        FROM FPL, RF_CarteraGobCLP_Pond 
        INNER JOIN RF_FactCLP_Gob ON (Dias_Vcto <= Hasta) AND (Dias_Vcto >= Desde)
        WHERE FPL.Instrumento = "Gobierno CLP";
    
    Nota: 0.5*((A+B)+|A-B|) = MAX(A,B)
    """
    if verbose:
        print("\n" + "="*70)
        print("FASE 2.1: RF_PLI_0XX_CarteraHC (Cartera con Haircut)")
        print("="*70)
        print(f"Registros cartera entrada: {len(df_cartera_pond):,}")
        print(f"Registros factores: {len(df_factores):,}")
    
    # =========================================================================
    # PASO 1: Obtener Haircut desde FPL
    # =========================================================================
    if isinstance(filtro_instrumento, str):
        filtro_instrumento = [filtro_instrumento]
    
    mask_fpl = df_fpl['Instrumento'].isin(filtro_instrumento)
    haircut_valor = df_fpl.loc[mask_fpl, 'Haircut'].values
    
    if len(haircut_valor) == 0:
        raise ValueError(f"No se encontró Haircut para instrumento: {filtro_instrumento}")
    
    # Si hay múltiples valores (caso mencionado), tomamos el máximo o sumamos según negocio
    haircut = haircut_valor[0] if len(haircut_valor) == 1 else haircut_valor.max()
    
    if verbose:
        print(f"\n[FPL] Haircut para '{filtro_instrumento}': {haircut:.6f}")
    
    # =========================================================================
    # PASO 2: JOIN cartera con factores (Dias_Vcto BETWEEN Desde AND Hasta)
    # =========================================================================
    # Cross join y luego filtrar por rango
    df_cartera_pond = df_cartera_pond.copy()
    df_cartera_pond['_key'] = 1
    df_factores_temp = df_factores.copy()
    df_factores_temp['_key'] = 1
    
    # Cross join
    df_cross = pd.merge(df_cartera_pond, df_factores_temp, on='_key', how='outer')
    df_cross = df_cross.drop(columns=['_key'])
    
    # Filtrar por rango: Dias_Vcto >= Desde AND Dias_Vcto <= Hasta
    mask_rango = (df_cross['Dias_Vcto'] >= df_cross['Desde']) & (df_cross['Dias_Vcto'] <= df_cross['Hasta'])
    df_joined = df_cross[mask_rango].copy()
    
    if verbose:
        print(f"\n[JOIN] Registros después de JOIN con factores: {len(df_joined):,}")
    
    # =========================================================================
    # PASO 3: Calcular FactorPond = Ponderador * MAX(Factor, Haircut)
    # =========================================================================
    # Fórmula original: Ponderador*(0.5*((Factor+Haircut)+ABS(Factor-Haircut)))
    # Equivalente a: Ponderador * MAX(Factor, Haircut)
    df_joined['FactorPond'] = df_joined['Ponderador'] * np.maximum(df_joined['Factor'], haircut)
    
    if verbose:
        print(f"\n[CALC] FactorPond calculado usando MAX(Factor, {haircut:.6f})")
        print(f"  Factor min: {df_joined['Factor'].min():.6f}")
        print(f"  Factor max: {df_joined['Factor'].max():.6f}")
    
    # =========================================================================
    # PASO 4: Seleccionar columnas de salida
    # =========================================================================
    # Columnas originales de cartera + Dia, Factor, FactorPond
    cols_cartera = [c for c in df_cartera_pond.columns if c != '_key']
    cols_salida = cols_cartera + ['Dia', 'Factor', 'FactorPond']
    
    df_salida = df_joined[cols_salida].copy()
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"RESULTADO: {len(df_salida):,} registros generados")
        print(f"{'='*70}")
    
    return df_salida


def generar_haircut_dia(df_cartera_hc: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Genera RF_PLI_0XX_Haircut_Dia: Haircut agregado por día.
    
    Args:
        df_cartera_hc: DataFrame con cartera y haircuts (RF_PLI_0XX_CarteraHC)
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, Haircut
    
    SQL de referencia:
        SELECT Dia, sum(FactorPond) AS Haircut
        FROM RF_PLI_005_CarteraHC
        GROUP BY Dia
        ORDER BY Dia;
    """
    if verbose:
        print("\n" + "-"*50)
        print("FASE 2.2: RF_PLI_0XX_Haircut_Dia")
        print("-"*50)
        print(f"Registros entrada: {len(df_cartera_hc):,}")
    
    # Agrupar por Dia y sumar FactorPond
    df_resultado = df_cartera_hc.groupby('Dia')['FactorPond'].sum().reset_index()
    df_resultado.columns = ['Dia', 'Haircut']
    
    # Ordenar por Dia
    df_resultado = df_resultado.sort_values('Dia').reset_index(drop=True)
    
    if verbose:
        print(f"Registros salida: {len(df_resultado):,}")
        print(f"Días: {df_resultado['Dia'].min()} a {df_resultado['Dia'].max()}")
    
    return df_resultado


def agregar_dia_semana(
    df_haircut_dia: pd.DataFrame,
    fecha_proceso: pd.Timestamp | datetime.datetime | int,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera RF_PLI_0XXb_Haircut_Dia: Agrega día de la semana al haircut.
    
    Args:
        df_haircut_dia: DataFrame con haircuts por día (RF_PLI_006_Haircut_Dia)
        fecha_proceso: Fecha de proceso (datetime o int YYYYMMDD)
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, DiaSem, Haircut
    
    SQL de referencia:
        SELECT Dia, weekday(Fecha + Dia, 2) AS DiaSem, Haircut
        FROM RF_Fecha_Proceso_Carteras, RF_PLI_006_Haircut_Dia;
    
    Nota: weekday(..., 2) en Access → Lunes=1, ..., Domingo=7
    """
    if verbose:
        print("\n" + "-"*50)
        print("FASE 2.3: RF_PLI_0XXb_Haircut_Dia (con día semana)")
        print("-"*50)
        print(f"Registros entrada: {len(df_haircut_dia):,}")
    
    # Convertir fecha_proceso a datetime si es necesario
    if isinstance(fecha_proceso, int):
        fecha_proceso = pd.to_datetime(str(fecha_proceso), format='%Y%m%d')
    elif not isinstance(fecha_proceso, (pd.Timestamp, datetime.datetime)):
        fecha_proceso = pd.to_datetime(fecha_proceso)
    
    df_resultado = df_haircut_dia.copy()
    
    # Calcular fecha para cada día y obtener día de semana
    # En pandas: Monday=0, ..., Sunday=6
    # En Access con param 2: Monday=1, ..., Sunday=7
    # Entonces sumamos 1 al resultado de pandas
    df_resultado['_fecha'] = fecha_proceso + pd.to_timedelta(df_resultado['Dia'], unit='D')
    df_resultado['DiaSem'] = df_resultado['_fecha'].dt.dayofweek + 1  # Lunes=1, ..., Domingo=7
    
    # Seleccionar columnas en orden correcto
    df_resultado = df_resultado[['Dia', 'DiaSem', 'Haircut']].copy()
    
    if verbose:
        print(f"Fecha proceso: {fecha_proceso.strftime('%Y-%m-%d')} ({['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'][fecha_proceso.dayofweek]})")
        print(f"Registros salida: {len(df_resultado):,}")
    
    return df_resultado


# =============================================================================
# FASE 3: COMBINACIÓN HAIRCUT + PACTOS
# =============================================================================

def combinar_haircut_con_pactos(
    df_haircut_dia_sem: pd.DataFrame,
    df_monto_plazo_pacto: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera RF_PLI_0XXc_Haircut_Dia_Pcto: Combina haircut con montos de pactos.
    
    Args:
        df_haircut_dia_sem: DataFrame con haircuts por día y semana (RF_PLI_006b)
        df_monto_plazo_pacto: DataFrame con montos por plazo de pacto (RF_PLI_003b)
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Dia, DiaSem, Haircut, Monto_Pacto
    
    SQL de referencia:
        SELECT Dia, DiaSem, Haircut, 
               IIf(IsNull(Monto), 0, Monto) AS Monto_Pacto
        FROM RF_PLI_006b_Haircut_Dia 
        LEFT JOIN RF_PLI_003b_GobCLP_MontoPlazo_Pacto ON Dia = Dias_Pacto
        ORDER BY Dia;
    """
    if verbose:
        print("\n" + "="*70)
        print("FASE 3: RF_PLI_0XXc_Haircut_Dia_Pcto (Haircut + Pactos)")
        print("="*70)
        print(f"Registros haircut: {len(df_haircut_dia_sem):,}")
        print(f"Registros pactos: {len(df_monto_plazo_pacto):,}")
    
    # LEFT JOIN en Dia = Dias_Pacto
    df_resultado = pd.merge(
        df_haircut_dia_sem,
        df_monto_plazo_pacto,
        left_on='Dia',
        right_on='Dias_Pacto',
        how='left'
    )
    
    # Llenar nulos con 0 y renombrar columna
    df_resultado['Monto_Pacto'] = df_resultado['Monto'].fillna(0)
    
    # Seleccionar columnas finales
    df_resultado = df_resultado[['Dia', 'DiaSem', 'Haircut', 'Monto_Pacto']].copy()
    
    # Ordenar por Dia
    df_resultado = df_resultado.sort_values('Dia').reset_index(drop=True)
    
    if verbose:
        dias_con_pacto = (df_resultado['Monto_Pacto'] > 0).sum()
        print(f"\nRegistros salida: {len(df_resultado):,}")
        print(f"Días con pactos: {dias_con_pacto}")
        print(f"{'='*70}")
    
    return df_resultado


# =============================================================================
# FASE 4: MONTO A LIQUIDAR
# =============================================================================

def filtrar_monto_liquidar(
    df_montos_liq: pd.DataFrame,
    instrumento: str,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera RF_PLI_0XX_MontoLiquidar: Filtra montos a liquidar por instrumento.
    
    Args:
        df_montos_liq: DataFrame con montos a liquidar (RF_MontosLiq)
        instrumento: Nombre del instrumento (ej: "Gobierno CLP")
        verbose: Mostrar estadísticas
    
    Returns:
        DataFrame con columnas: Instrumento, Monto Mercado, % participacion, Monto a Liquidar
    
    SQL de referencia:
        SELECT Instrumento, [Monto Mercado], [% participacion], [Monto a Liquidar]
        FROM RF_MontosLiq
        WHERE Instrumento = 'Gobierno CLP';
    """
    if verbose:
        print("\n" + "-"*50)
        print(f"FASE 4: RF_PLI_0XX_MontoLiquidar ({instrumento})")
        print("-"*50)
    
    # Filtrar por instrumento
    mask = df_montos_liq['Instrumento'] == instrumento
    df_resultado = df_montos_liq[mask].copy()
    
    if verbose:
        if len(df_resultado) > 0:
            monto = df_resultado['Monto a Liquidar'].iloc[0]
            print(f"Monto a liquidar: {monto:,.2f}")
        else:
            print(f"ADVERTENCIA: No se encontró instrumento '{instrumento}'")
    
    return df_resultado


# =============================================================================
# PIPELINE COMPLETO PARAMETRIZADO POR INSTRUMENTO
# =============================================================================

def generar_flujo_liquidacion_instrumento(
    df_cartera_inv: pd.DataFrame,
    df_cartera_inv_pacto: pd.DataFrame,
    tablas: dict,
    tipo_instrumento: str,
    fecha_proceso: int | datetime.datetime,
    verbose: bool = True
) -> tuple[pd.DataFrame, dict]:
    """
    Pipeline completo de liquidación parametrizado por instrumento.
    
    Ejecuta todo el flujo de liquidación para un instrumento específico:
    1. Filtrar cartera por instrumento (disponible y pacto)
    2. Calcular monto total y ponderadores
    3. Aplicar factores de haircut
    4. Agregar montos de pacto por día
    5. Calcular flujo de liquidación diario
    
    Args:
        df_cartera_inv: Cartera de inversiones disponible (RF_PLI_001_CarteraInv)
        df_cartera_inv_pacto: Cartera de inversiones en pacto (RF_PLI_001d_CarteraInv_Pcto)
        tablas: Dict con tablas base necesarias:
            - 'RF_FactXXX_YYY': Tabla de factores según el instrumento
            - 'FPL': Floor Piso Liquidez
            - 'RF_MontosLiq': Montos a liquidar
        tipo_instrumento: Clave del instrumento en CONFIGURACION_INSTRUMENTOS
            Opciones: 'GobCLP', 'GobCLF', 'DPF', 'DPR', 'LCH', 'BBC'
        fecha_proceso: Fecha de proceso (int YYYYMMDD o datetime)
        verbose: Mostrar progreso detallado
    
    Returns:
        Tupla con:
        - DataFrame con flujo diario: Dia, DiaSem, Haircut, Monto_Liquidar
        - Dict con todas las queries intermedias generadas
    
    Example:
        flujo, queries = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=queries['RF_PLI_001_CarteraInv'],
            df_cartera_inv_pacto=queries['RF_PLI_001d_CarteraInv_Pcto'],
            tablas=tablas,
            tipo_instrumento='GobCLF',
            fecha_proceso=20260109,
            verbose=True
        )
    """
    # Validar tipo de instrumento
    if tipo_instrumento not in CONFIGURACION_INSTRUMENTOS:
        raise ValueError(f"Tipo de instrumento no válido: {tipo_instrumento}. "
                        f"Opciones: {list(CONFIGURACION_INSTRUMENTOS.keys())}")
    
    config = CONFIGURACION_INSTRUMENTOS[tipo_instrumento]
    queries_generadas = {}
    
    # Obtener filtro de moneda si existe
    filtro_moneda = config.get('filtro_moneda', None)
    
    if verbose:
        print("\n" + "="*70)
        print(f"PIPELINE DE LIQUIDACIÓN: {config['nombre_completo']}")
        print("="*70)
        print(f"Tipo: {tipo_instrumento}")
        print(f"Códigos disponible: {config['codigos_disp']}")
        print(f"Códigos pacto: {config['codigos_pacto']}")
        if filtro_moneda:
            print(f"Filtro moneda: {filtro_moneda}")
        print(f"Tabla factores: {config['tabla_factores']}")
        print(f"Instrumento FPL: {config['instrumento_fpl']}")
    
    # =========================================================================
    # PASO 1: Filtrar cartera por instrumento (disponible)
    # =========================================================================
    COLUMNAS_SALIDA = [
        'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
        'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total', 'Dias_Vcto'
    ]
    
    df_cartera_instr = generar_cartera_instrumento(
        df_cartera_inv,
        COLUMNAS_SALIDA,
        config['codigos_disp'],
        tipo_instrumento,
        filtro_moneda=filtro_moneda
    )
    queries_generadas[f'RF_PLI_00X_Cartera{tipo_instrumento}'] = df_cartera_instr
    if verbose:
        print(f"\nCartera filtrada para {tipo_instrumento}: {len(df_cartera_instr):,} registros")
        
    # =========================================================================
    # PASO 2: Calcular monto total
    # =========================================================================
    df_monto_total = generar_monto_total_instrumento(
        df_cartera_instrumento=df_cartera_instr,
        cols_de_agrupacion=['Fec_Pro', 'Cod_Pro', 'Moneda'],
        cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        nombre_tabla=tipo_instrumento
    )
    queries_generadas[f'RF_PLI_00X_Cartera{tipo_instrumento}_MonTotal'] = df_monto_total
    if verbose:
        print(f"\nMonto total calculado para {tipo_instrumento}: {len(df_monto_total):,} registros")
    
    # =========================================================================
    # PASO 3: Calcular ponderadores
    # =========================================================================
    df_cartera_pond = generar_cartera_pond(
        df_cartera_instrumento=df_cartera_instr,
        df_montototal=df_monto_total,
        output_table_name=f'RF_Cartera{tipo_instrumento}_Pond'
    )
    queries_generadas[f'RF_PLI_00X_Cartera{tipo_instrumento}_Pond'] = df_cartera_pond
    
    if verbose:
        print(f"\nCartera ponderada para {tipo_instrumento}: {len(df_cartera_pond):,} registros")
    # =========================================================================
    # PASO 4: Filtrar cartera pactos y calcular monto por plazo
    # =========================================================================
    COLUMNAS_SALIDA_PACTO = COLUMNAS_SALIDA + ['Dias_Pacto']
    
    df_cartera_pacto = generar_cartera_instrumento(
        df_cartera_inv_pacto,
        COLUMNAS_SALIDA_PACTO,
        config['codigos_pacto'],  # Puede incluir códigos adicionales (ej: CER para GobCLF)
        f'{tipo_instrumento}_Pacto',
        filtro_moneda=filtro_moneda  # Aplicar mismo filtro de moneda
    )
    queries_generadas[f'RF_PLI_00X_Cartera{tipo_instrumento}_Pacto'] = df_cartera_pacto
    if verbose:
        print(f"\nCartera pactos filtrada para {tipo_instrumento}: {len(df_cartera_pacto):,} registros")

    df_monto_plazo_pacto = generar_monto_plazo_pacto(
        df_cartera_pacto,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_00X_{tipo_instrumento}_MontoPlazo_Pacto'] = df_monto_plazo_pacto
    if verbose:
        print(f"\nMonto por plazo de pacto para {tipo_instrumento}: {len(df_monto_plazo_pacto):,} registros")
    # =========================================================================
    # PASO 5: Aplicar haircut
    # =========================================================================
    # Obtener tabla de factores según configuración
    tabla_factores_nombre = config['tabla_factores']
    if tabla_factores_nombre not in tablas:
        raise ValueError(f"Tabla de factores '{tabla_factores_nombre}' no encontrada en tablas")
    df_factores = tablas[tabla_factores_nombre]
    
    if verbose:
        print(f"\nUsando tabla de factores: {tabla_factores_nombre} ({len(df_factores):,} registros)")
    df_cartera_hc = generar_cartera_haircut(
        df_cartera_pond=df_cartera_pond,
        df_factores=df_factores,
        df_fpl=tablas['FPL'],
        filtro_instrumento=config['instrumento_fpl'],
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_00X_CarteraHC_{tipo_instrumento}'] = df_cartera_hc
    
    if verbose:
        print(f"\nCartera con haircut para {tipo_instrumento}: {len(df_cartera_hc):,} registros")
    # =========================================================================
    # PASO 6: Agregar haircut por día
    # =========================================================================
    df_haircut_dia = generar_haircut_dia(df_cartera_hc, verbose=verbose)
    queries_generadas[f'RF_PLI_00X_Haircut_Dia_{tipo_instrumento}'] = df_haircut_dia
    
    if verbose:
        print(f"\nHaircut agregado por día para {tipo_instrumento}: {len(df_haircut_dia):,} registros")

    # =========================================================================
    # PASO 7: Agregar día de semana
    # =========================================================================
    df_haircut_dia_sem = agregar_dia_semana(
        df_haircut_dia,
        fecha_proceso=fecha_proceso,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_00X_Haircut_Dia_b_{tipo_instrumento}'] = df_haircut_dia_sem
    
    if verbose:
        print(f"\nHaircut con día de semana para {tipo_instrumento}: {len(df_haircut_dia_sem):,} registros")

    # =========================================================================
    # PASO 8: Combinar haircut con pactos
    # =========================================================================
    df_haircut_dia_pcto = combinar_haircut_con_pactos(
        df_haircut_dia_sem,
        df_monto_plazo_pacto,
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_00X_Haircut_Dia_Pcto_{tipo_instrumento}'] = df_haircut_dia_pcto
    if verbose:
        print(f"\nHaircut combinado con pactos para {tipo_instrumento}: {len(df_haircut_dia_pcto):,} registros")
    # =========================================================================
    # PASO 9: Obtener monto a liquidar
    # =========================================================================
    df_monto_liquidar = filtrar_monto_liquidar(
        tablas['RF_MontosLiq'],
        instrumento=config['instrumento_montos_liq'],
        verbose=verbose
    )
    queries_generadas[f'RF_PLI_00X_MontoLiquidar_{tipo_instrumento}'] = df_monto_liquidar
    
    if verbose:
        print(f"\nMonto a liquidar para {tipo_instrumento} obtenido: {len(df_monto_liquidar):,} registros")
    # =========================================================================
    # PASO 10: Calcular flujo de liquidación
    # =========================================================================
    df_flujo = calcular_flujo_liquidacion(
        df_cartera_mon_total=df_monto_total,
        df_haircut_dia_pcto=df_haircut_dia_pcto,
        df_monto_liquidar=df_monto_liquidar,
        nombre_instrumento=tipo_instrumento
    )
    queries_generadas[config['nombre_salida']] = df_flujo
    
    if verbose:
        print("\n" + "="*70)
        print(f"RESULTADO: {config['nombre_salida']}")
        print("="*70)
        print(f"Registros generados: {len(df_flujo)}")
        print(f"Monto total día 0: {df_flujo.loc[0, 'Monto_Liquidar']:,.2f}")
        monto_total_liq = df_flujo['Monto_Liquidar'].sum()
        print(f"Suma total liquidaciones: {monto_total_liq:,.2f}")
    
    return df_flujo, queries_generadas