"""
Módulo de gestión de almacenamiento histórico con DuckDB.

DuckDB es una base de datos columnar optimizada para analytics (OLAP),
ideal para almacenar series temporales y realizar consultas analíticas
sobre datos históricos de modelos.

Ventajas sobre SQLite para este caso de uso:
- Compresión columnar (~10x mejor)
- Queries analíticos 10-100x más rápidos
- Integración nativa con Pandas/Arrow
- Soporte nativo de Parquet
"""

import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Union
import sys

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import config_rutas as cr


class DuckDBManager:
    """
    Gestor de base de datos DuckDB para almacenamiento histórico de modelos.
    
    Características:
    - Almacena tablas de desarrollo por modelo con partición por fecha
    - Mantiene tabla consolidada de todos los modelos
    - Optimizado para queries analíticos y series temporales
    - Compresión automática para eficiencia de almacenamiento
    """
    
    DEFAULT_DB_PATH = cr.BASE_DIR / 'storage' / 'data' / 'modelos_historico.duckdb'
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa el gestor de DuckDB.
        
        Args:
            db_path: Ruta al archivo de base de datos. Si es None, usa la ruta por defecto.
        """
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Obtiene una conexión a la base de datos."""
        return duckdb.connect(str(self.db_path))
    
    def _init_database(self):
        """Inicializa las tablas base si no existen."""
        with self._get_connection() as conn:
            # Tabla de metadatos de cargas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS carga_metadata (
                    id INTEGER PRIMARY KEY,
                    modelo VARCHAR NOT NULL,
                    fecha_proceso DATE NOT NULL,
                    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    archivo_origen VARCHAR,
                    registros_cargados INTEGER,
                    estado VARCHAR DEFAULT 'OK',
                    observaciones VARCHAR,
                    UNIQUE(modelo, fecha_proceso)
                )
            """)
            
            # Crear secuencia para el ID si no existe
            conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS seq_carga_metadata START 1
            """)
            
            # Tabla consolidada de desarrollo de todos los modelos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS desarrollo_consolidado (
                    MODELO VARCHAR NOT NULL,
                    FECHA_PROCESO DATE NOT NULL,
                    CODIGO_EMPRESA INTEGER,
                    OPERACION INTEGER,
                    COD_ACT_PAS VARCHAR,
                    MONEDA_ORIGEN VARCHAR,
                    MONEDA_COMPENSACION VARCHAR,
                    COMPENSACION INTEGER,
                    CODIGO_PRODUCTO VARCHAR,
                    CODIGO_SUBPRODUCTO VARCHAR,
                    FECHA_CREACION DATE,
                    NUMERO_CUOTA INTEGER,
                    FECHA_INICIO_CUOTA DATE,
                    FECHA_VENCIMIENTO_CUOTA DATE,
                    FECHA_PAGO DATE,
                    FECHA_REPRICING DATE,
                    AMORTIZACION DOUBLE,
                    INTERES DOUBLE,
                    INTERES_DEVENGADO DOUBLE,
                    VP_AMORTIZACION DOUBLE,
                    VP_INTERES DOUBLE,
                    FACTOR_DE_RIESGO VARCHAR,
                    TIPO_CUOTA INTEGER,
                    AREA_NEGOCIO VARCHAR,
                    CODIGO_EJECUTIVO VARCHAR,
                    CODIGO_ESTRATEGIA VARCHAR,
                    CLASIFICACION_CONTABLE VARCHAR,
                    TIPO_TASA INTEGER,
                    INDEXADOR VARCHAR,
                    TASA DOUBLE,
                    TASA_CF DOUBLE,
                    SPREAD DOUBLE,
                    FECHA_CARGA TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear índices para optimizar consultas comunes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_consolidado_modelo_fecha 
                ON desarrollo_consolidado(MODELO, FECHA_PROCESO)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_consolidado_fecha 
                ON desarrollo_consolidado(FECHA_PROCESO)
            """)
            
            print(f"✓ Base de datos inicializada: {self.db_path}")
    
    def cargar_desarrollo_modelo(
        self,
        df: pd.DataFrame,
        modelo: str,
        fecha_proceso: Union[date, datetime],
        archivo_origen: Optional[str] = None,
        reemplazar_si_existe: bool = True
    ) -> bool:
        """
        Carga datos de desarrollo de un modelo a la base de datos.
        
        Args:
            df: DataFrame con los datos de desarrollo
            modelo: Nombre/código del modelo
            fecha_proceso: Fecha del proceso
            archivo_origen: Ruta del archivo de origen (para trazabilidad)
            reemplazar_si_existe: Si True, reemplaza datos existentes para esa fecha
            
        Returns:
            bool: True si la carga fue exitosa
        """
        if isinstance(fecha_proceso, datetime):
            fecha_proceso = fecha_proceso.date()
        
        # Preparar DataFrame
        df_carga = df.copy()
        df_carga['MODELO'] = modelo
        df_carga['FECHA_CARGA'] = datetime.now()
        
        # Normalizar nombre de columna si existe
        if 'COD_ACT/PAS' in df_carga.columns:
            df_carga = df_carga.rename(columns={'COD_ACT/PAS': 'COD_ACT_PAS'})
        
        try:
            with self._get_connection() as conn:
                # Si debe reemplazar, eliminar registros existentes
                if reemplazar_si_existe:
                    conn.execute("""
                        DELETE FROM desarrollo_consolidado 
                        WHERE MODELO = ? AND FECHA_PROCESO = ?
                    """, [modelo, fecha_proceso])
                    
                    conn.execute("""
                        DELETE FROM carga_metadata 
                        WHERE modelo = ? AND fecha_proceso = ?
                    """, [modelo, fecha_proceso])
                
                # Insertar datos en tabla consolidada
                # DuckDB puede insertar directamente desde un DataFrame
                conn.execute("""
                    INSERT INTO desarrollo_consolidado 
                    SELECT * FROM df_carga
                """)
                
                # Registrar metadata
                conn.execute("""
                    INSERT INTO carga_metadata (id, modelo, fecha_proceso, archivo_origen, registros_cargados)
                    VALUES (nextval('seq_carga_metadata'), ?, ?, ?, ?)
                """, [modelo, fecha_proceso, str(archivo_origen) if archivo_origen else None, len(df_carga)])
                
                print(f"  ✓ {modelo}: {len(df_carga)} registros cargados para {fecha_proceso}")
                return True
                
        except Exception as e:
            print(f"  ✗ Error al cargar {modelo}: {e}")
            return False
    
    def obtener_desarrollo_modelo(
        self,
        modelo: str,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Obtiene datos de desarrollo de un modelo.
        
        Args:
            modelo: Nombre del modelo
            fecha_inicio: Fecha inicial (inclusive)
            fecha_fin: Fecha final (inclusive)
            
        Returns:
            DataFrame con los datos
        """
        query = "SELECT * FROM desarrollo_consolidado WHERE MODELO = ?"
        params = [modelo]
        
        if fecha_inicio:
            query += " AND FECHA_PROCESO >= ?"
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += " AND FECHA_PROCESO <= ?"
            params.append(fecha_fin)
        
        query += " ORDER BY FECHA_PROCESO, OPERACION"
        
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchdf()
    
    def obtener_desarrollo_consolidado(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        modelos: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Obtiene datos consolidados de todos los modelos.
        
        Args:
            fecha_inicio: Fecha inicial (inclusive)
            fecha_fin: Fecha final (inclusive)
            modelos: Lista de modelos a incluir (None = todos)
            
        Returns:
            DataFrame consolidado
        """
        query = "SELECT * FROM desarrollo_consolidado WHERE 1=1"
        params = []
        
        if modelos:
            placeholders = ','.join(['?' for _ in modelos])
            query += f" AND MODELO IN ({placeholders})"
            params.extend(modelos)
        
        if fecha_inicio:
            query += " AND FECHA_PROCESO >= ?"
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += " AND FECHA_PROCESO <= ?"
            params.append(fecha_fin)
        
        query += " ORDER BY MODELO, FECHA_PROCESO"
        
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchdf()
    
    def obtener_historial_cargas(self, modelo: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene el historial de cargas realizadas.
        
        Args:
            modelo: Filtrar por modelo específico (None = todos)
            
        Returns:
            DataFrame con historial de cargas
        """
        query = "SELECT * FROM carga_metadata"
        params = []
        
        if modelo:
            query += " WHERE modelo = ?"
            params.append(modelo)
        
        query += " ORDER BY fecha_carga DESC"
        
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchdf()
    
    def obtener_fechas_disponibles(self, modelo: Optional[str] = None) -> List[date]:
        """
        Obtiene las fechas disponibles en la base de datos.
        
        Args:
            modelo: Filtrar por modelo específico
            
        Returns:
            Lista de fechas disponibles
        """
        query = "SELECT DISTINCT FECHA_PROCESO FROM desarrollo_consolidado"
        params = []
        
        if modelo:
            query += " WHERE MODELO = ?"
            params.append(modelo)
        
        query += " ORDER BY FECHA_PROCESO DESC"
        
        with self._get_connection() as conn:
            result = conn.execute(query, params).fetchall()
            return [row[0] for row in result]
    
    def obtener_modelos_disponibles(self) -> List[str]:
        """Obtiene la lista de modelos disponibles en la base de datos."""
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT DISTINCT MODELO FROM desarrollo_consolidado ORDER BY MODELO
            """).fetchall()
            return [row[0] for row in result]
    
    def obtener_estadisticas(self) -> pd.DataFrame:
        """
        Obtiene estadísticas de la base de datos.
        
        Returns:
            DataFrame con estadísticas por modelo
        """
        with self._get_connection() as conn:
            return conn.execute("""
                SELECT 
                    MODELO,
                    COUNT(*) as total_registros,
                    COUNT(DISTINCT FECHA_PROCESO) as dias_disponibles,
                    MIN(FECHA_PROCESO) as fecha_min,
                    MAX(FECHA_PROCESO) as fecha_max,
                    SUM(AMORTIZACION) as total_amortizacion,
                    SUM(INTERES) as total_interes
                FROM desarrollo_consolidado
                GROUP BY MODELO
                ORDER BY MODELO
            """).fetchdf()
    
    def exportar_a_parquet(
        self,
        ruta_salida: Path,
        modelo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None
    ):
        """
        Exporta datos a formato Parquet (útil para compartir o backup).
        
        Args:
            ruta_salida: Ruta del archivo Parquet de salida
            modelo: Filtrar por modelo
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
        """
        df = self.obtener_desarrollo_consolidado(fecha_inicio, fecha_fin, 
                                                  [modelo] if modelo else None)
        
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        
        # DuckDB puede escribir Parquet directamente con compresión
        with self._get_connection() as conn:
            conn.execute(f"""
                COPY (SELECT * FROM df) 
                TO '{ruta_salida}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
        
        print(f"✓ Exportado a {ruta_salida}")
    
    def vacuum(self):
        """Optimiza la base de datos (compacta y reorganiza)."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            print("✓ Base de datos optimizada")


# Ejemplo de uso
if __name__ == "__main__":
    # Crear instancia
    db = DuckDBManager()
    
    # Mostrar estadísticas si hay datos
    stats = db.obtener_estadisticas()
    if not stats.empty:
        print("\n=== Estadísticas de la base de datos ===")
        print(stats.to_string(index=False))
    else:
        print("\n⚠ Base de datos vacía. Use cargar_desarrollo_modelo() para agregar datos.")
