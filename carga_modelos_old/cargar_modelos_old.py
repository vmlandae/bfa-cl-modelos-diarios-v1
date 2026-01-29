"""
Módulo para cargar tablas de desarrollo de modelos legacy (no implementados en Python).

Este módulo lee archivos Excel (.xlsm/.xlsx) desde carpetas compartidas de red,
extrae la hoja "DESARROLLO" y carga los datos tanto a BigQuery (GCP) como 
a la base de datos local DuckDB para histórico.

Los modelos "old" son aquellos que aún se ejecutan en Excel/VBA y no han sido
migrados a Python, pero necesitamos capturar sus outputs para análisis.
"""

import os
import sys
import yaml
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from concurrent.futures import ProcessPoolExecutor, as_completed

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import config_rutas as cr
from storage.duckdb_manager import DuckDBManager

# Importar utilidades de GCP
try:
    from google.cloud import bigquery
    import bfa_cl_utilidades as ut
    GCP_DISPONIBLE = True
except ImportError:
    GCP_DISPONIBLE = False
    print("⚠ Módulos de GCP no disponibles. Solo se cargará a DuckDB local.")


# Cargar configuración
CONFIG_PATH = cr.CONFIG / 'config_modelos_old.yaml'


class CargadorModelosOld:
    """
    Cargador de modelos legacy desde carpetas compartidas.
    
    Lee archivos Excel desde rutas de red, extrae la hoja DESARROLLO
    y carga a BigQuery y/o DuckDB.
    """
    
    HOJA_DESARROLLO = "DESARROLLO"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el cargador.
        
        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config_path = config_path or CONFIG_PATH
        self.config = self._cargar_config()
        self.db_manager = DuckDBManager()
        
        if GCP_DISPONIBLE:
            self.ruta_credenciales_gcp = cr.obtener_ruta_credenciales_gcp()
    
    def _cargar_config(self) -> Dict[str, Any]:
        """Carga la configuración de modelos old desde YAML."""
        if not self.config_path.exists():
            print(f"⚠ Archivo de configuración no encontrado: {self.config_path}")
            print("  Creando configuración de ejemplo...")
            self._crear_config_ejemplo()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _crear_config_ejemplo(self):
        """Crea un archivo de configuración de ejemplo."""
        config_ejemplo = {
            'modelos_old': {
                'ejemplo_modelo_1': {
                    'descripcion': 'Descripción del modelo',
                    'ruta_excel': '\\\\servidor\\carpeta\\archivo.xlsm',
                    'hoja': 'DESARROLLO',
                    'tabla_bigquery': 'report_ejemplo_modelo_1_dly',
                    'activo': False
                }
            },
            'gcp': {
                'proyecto_id': 'bfa-cl-trade-price-report-dev',
                'dataset_id': 'bfa_cl_prd_financial_risk_dly_proc_models'
            }
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_ejemplo, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✓ Configuración de ejemplo creada en: {self.config_path}")
    
    def _crear_esquema_bigquery(self) -> List:
        """Crea el esquema estándar para BigQuery."""
        if not GCP_DISPONIBLE:
            return []
        
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
    
    def _leer_excel_desarrollo(self, ruta_excel: str, hoja: str = None) -> pd.DataFrame:
        """
        Lee la hoja de desarrollo de un archivo Excel.
        
        Args:
            ruta_excel: Ruta al archivo Excel (puede ser ruta de red)
            hoja: Nombre de la hoja (por defecto DESARROLLO)
            
        Returns:
            DataFrame con los datos
        """
        hoja = hoja or self.HOJA_DESARROLLO
        
        print(f"  Leyendo: {ruta_excel}")
        
        # Verificar que el archivo existe
        if not Path(ruta_excel).exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_excel}")
        
        # Definir tipos de datos para la lectura
        dtype_excel = {
            "CODIGO_EMPRESA": "Int64",
            "OPERACION": "Int64",
            "COD_ACT/PAS": "str",
            "MONEDA_ORIGEN": "str",
            "MONEDA_COMPENSACION": "str",
            "COMPENSACION": "Int64",
            "CODIGO_PRODUCTO": "str",
            "CODIGO_SUBPRODUCTO": "str",
            "NUMERO_CUOTA": "Int64",
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
        
        df = pd.read_excel(ruta_excel, sheet_name=hoja, engine='openpyxl', dtype=dtype_excel)
        
        # Procesar fechas
        columnas_fecha = ['FECHA_PROCESO', 'FECHA_CREACION', 'FECHA_INICIO_CUOTA',
                         'FECHA_VENCIMIENTO_CUOTA', 'FECHA_PAGO', 'FECHA_REPRICING']
        
        for col in columnas_fecha:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
        # Normalizar nombres de columnas
        df = df.rename(columns={
            'COD_ACT/PAS': 'COD_ACT_PAS',
            'COD ACT/PAS': 'COD_ACT_PAS'
        })
        
        print(f"    ✓ {len(df)} registros leídos")
        return df
    
    def cargar_modelo(
        self,
        modelo: str,
        fecha_proceso: Union[date, datetime],
        cargar_gcp: bool = True,
        cargar_duckdb: bool = True
    ) -> Dict[str, bool]:
        """
        Carga un modelo específico a GCP y/o DuckDB.
        
        Args:
            modelo: Código del modelo a cargar
            fecha_proceso: Fecha del proceso
            cargar_gcp: Si debe cargar a BigQuery
            cargar_duckdb: Si debe cargar a DuckDB local
            
        Returns:
            Dict con resultados de cada destino
        """
        if modelo not in self.config.get('modelos_old', {}):
            raise ValueError(f"Modelo '{modelo}' no encontrado en configuración")
        
        config_modelo = self.config['modelos_old'][modelo]
        
        if not config_modelo.get('activo', True):
            print(f"⚠ Modelo '{modelo}' está desactivado en configuración")
            return {'gcp': False, 'duckdb': False}
        
        if isinstance(fecha_proceso, datetime):
            fecha_proceso = fecha_proceso.date()
        
        print(f"\n{'='*60}")
        print(f"Cargando modelo: {modelo}")
        print(f"Fecha proceso: {fecha_proceso}")
        print(f"{'='*60}")
        
        resultados = {'gcp': False, 'duckdb': False}
        
        try:
            # Leer datos
            df = self._leer_excel_desarrollo(
                config_modelo['ruta_excel'],
                config_modelo.get('hoja', self.HOJA_DESARROLLO)
            )
            
            # Filtrar por fecha de proceso
            if 'FECHA_PROCESO' in df.columns:
                df = df[df['FECHA_PROCESO'] == fecha_proceso].copy()
                print(f"  Registros para fecha {fecha_proceso}: {len(df)}")
            
            if df.empty:
                print(f"  ⚠ No hay datos para la fecha {fecha_proceso}")
                return resultados
            
            # Cargar a DuckDB
            if cargar_duckdb:
                try:
                    resultados['duckdb'] = self.db_manager.cargar_desarrollo_modelo(
                        df=df,
                        modelo=modelo,
                        fecha_proceso=fecha_proceso,
                        archivo_origen=config_modelo['ruta_excel']
                    )
                except Exception as e:
                    print(f"  ✗ Error al cargar a DuckDB: {e}")
            
            # Cargar a GCP
            if cargar_gcp and GCP_DISPONIBLE:
                try:
                    df_gcp = df.copy()
                    df_gcp['FECHA_ACTUALIZACION'] = datetime.now().replace(second=0, microsecond=0)
                    
                    ut.cargar_dataframe_bigquery(
                        data=df_gcp,
                        ruta_cuenta_servicio=str(self.ruta_credenciales_gcp),
                        proyecto_id=self.config['gcp']['proyecto_id'],
                        dataset_id=self.config['gcp']['dataset_id'],
                        tabla_id=config_modelo['tabla_bigquery'],
                        esquema_tabla=self._crear_esquema_bigquery(),
                        tipo_escritura="TRUNCATE"
                    )
                    resultados['gcp'] = True
                    print(f"  ✓ Cargado a BigQuery: {config_modelo['tabla_bigquery']}")
                except Exception as e:
                    print(f"  ✗ Error al cargar a GCP: {e}")
            
        except Exception as e:
            print(f"  ✗ Error general: {e}")
        
        return resultados
    
    def cargar_todos(
        self,
        fecha_proceso: Union[date, datetime],
        cargar_gcp: bool = True,
        cargar_duckdb: bool = True,
        modelos_filtro: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, bool]]:
        """
        Carga todos los modelos old activos.
        
        Args:
            fecha_proceso: Fecha del proceso
            cargar_gcp: Si debe cargar a BigQuery
            cargar_duckdb: Si debe cargar a DuckDB
            modelos_filtro: Lista de modelos a cargar (None = todos los activos)
            
        Returns:
            Dict con resultados por modelo
        """
        print("\n" + "="*70)
        print("CARGA DE MODELOS OLD")
        print(f"Fecha de proceso: {fecha_proceso}")
        print("="*70)
        
        modelos_config = self.config.get('modelos_old', {})
        
        if not modelos_config:
            print("⚠ No hay modelos configurados")
            return {}
        
        # Filtrar modelos activos
        modelos_a_cargar = {
            k: v for k, v in modelos_config.items()
            if v.get('activo', True) and (modelos_filtro is None or k in modelos_filtro)
        }
        
        print(f"Modelos a cargar: {list(modelos_a_cargar.keys())}")
        
        resultados = {}
        for modelo in modelos_a_cargar:
            try:
                resultados[modelo] = self.cargar_modelo(
                    modelo, fecha_proceso, cargar_gcp, cargar_duckdb
                )
            except Exception as e:
                print(f"✗ Error en {modelo}: {e}")
                resultados[modelo] = {'gcp': False, 'duckdb': False}
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DE CARGA")
        print("="*70)
        for modelo, res in resultados.items():
            gcp_status = "✓" if res.get('gcp') else "✗"
            duck_status = "✓" if res.get('duckdb') else "✗"
            print(f"  {modelo}: GCP={gcp_status} DuckDB={duck_status}")
        
        return resultados
    
    def listar_modelos(self) -> pd.DataFrame:
        """Lista todos los modelos configurados con su estado."""
        modelos = self.config.get('modelos_old', {})
        
        data = []
        for nombre, config in modelos.items():
            data.append({
                'modelo': nombre,
                'descripcion': config.get('descripcion', ''),
                'activo': config.get('activo', True),
                'ruta': config.get('ruta_excel', ''),
                'tabla_bigquery': config.get('tabla_bigquery', '')
            })
        
        return pd.DataFrame(data)


def cargar_modelos_old_a_gcp(
    fecha_proceso: Union[str, date, datetime],
    modelos: Optional[List[str]] = None,
    solo_duckdb: bool = False
) -> Dict[str, Dict[str, bool]]:
    """
    Función de conveniencia para cargar modelos old.
    
    Args:
        fecha_proceso: Fecha en formato YYYY-MM-DD o date/datetime
        modelos: Lista de modelos a cargar (None = todos)
        solo_duckdb: Si True, solo carga a DuckDB local (no GCP)
        
    Returns:
        Dict con resultados
    """
    if isinstance(fecha_proceso, str):
        fecha_proceso = datetime.strptime(fecha_proceso, "%Y-%m-%d").date()
    
    cargador = CargadorModelosOld()
    return cargador.cargar_todos(
        fecha_proceso=fecha_proceso,
        cargar_gcp=not solo_duckdb,
        cargar_duckdb=True,
        modelos_filtro=modelos
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python cargar_modelos_old.py YYYY-MM-DD [modelo1 modelo2 ...]")
        print("\nOpciones:")
        print("  --solo-duckdb    Solo cargar a DuckDB local (no GCP)")
        print("  --listar         Listar modelos configurados")
        sys.exit(1)
    
    if sys.argv[1] == '--listar':
        cargador = CargadorModelosOld()
        print("\nModelos configurados:")
        print(cargador.listar_modelos().to_string(index=False))
        sys.exit(0)
    
    fecha_str = sys.argv[1]
    solo_duckdb = '--solo-duckdb' in sys.argv
    modelos = [arg for arg in sys.argv[2:] if not arg.startswith('--')] or None
    
    try:
        resultados = cargar_modelos_old_a_gcp(fecha_str, modelos, solo_duckdb)
        
        # Exit code basado en si hubo errores
        exitos = sum(1 for r in resultados.values() if r.get('gcp') or r.get('duckdb'))
        sys.exit(0 if exitos == len(resultados) else 1)
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
