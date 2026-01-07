import pandas as pd
from datetime import datetime
from pathlib import Path
import bfa_cl_utilidades as ut

class CargadorDatosModelos:
    """Clase especializada en cargar datos para modelos"""
    
    def __init__(self, ruta_interfaz: Path):
        self.ruta_interfaz = Path(ruta_interfaz)
        
    def cargar_interfaz_pml(self, fecha_proceso: datetime, 
                            columnas_requeridas: list = None
                            ) -> pd.DataFrame:
        """
        Carga archivo de interfaz estándar ProductosMercadoLiquidezGCP
        
        Args:
            fecha_proceso: Fecha para construir nombre del archivo
            columnas_requeridas: Lista de columnas a cargar (opcional)
            
        Returns:
            DataFrame con los datos cargados
        """
        print("      • Cargando datos de interfaz ProductosMercadoLiquidezGCP...")
        
        # Columnas por defecto si no se especifican
        if columnas_requeridas is None:
            columnas_requeridas = [
                "FECHA_PROCESO", "SISTEMA", "CODIGO_EMPRESA", "OPERACION", "COD_ACT_PAS",
                "MONEDA_ORIGEN", "MONEDA_COMPENSACION", "COMPENSACION", "CODIGO_PRODUCTO", 
                "CODIGO_SUBPRODUCTO", "DESTINOCREDITO", "FECHA_CREACION", "NUMERO_CUOTA",
                "FECHA_INICIO_CUOTA", "FECHA_VENCIMIENTO_CUOTA", "FECHA_PAGO", "FECHA_REPRICING",
                "AMORTIZACION", "INTERES", "INTERES_DEVENGADO", "VP_AMORTIZACION", "VP_INTERES",
                "FACTOR_DE_RIESGO", "TIPO_CUOTA", "AREA_NEGOCIO", "CODIGO_EJECUTIVO",
                "CODIGO_ESTRATEGIA", "CLASIFICACION_CONTABLE", "TIPO_TASA", "INDEXADOR",
                "TASA", "TASA_CF", "SPREAD", "MAYORISTAMINORISTA", "MARCA_CUMPLIMIENTO",
                "EMPRESA_RELACIONADA", "MODELO_PERFIL"
            ]
        
        # Tipos de datos estándar - todas las columnas como string por defecto
        tipos_datos = {columna: "str" for columna in columnas_requeridas}
        
        # Construir ruta del archivo
        nombre_archivo = f"ProductosMercadoLiquidezGCP{fecha_proceso.strftime('%Y%m%d')}.txt"
        ruta_completa = self.ruta_interfaz / nombre_archivo
        
        if not ruta_completa.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_completa}")
        
        # Cargar archivo
        try:
            df = pd.read_csv(
                ruta_completa, 
                sep=';', 
                decimal=',', 
                usecols=columnas_requeridas,
                encoding='utf-8', 
                dtype=tipos_datos
            )
            
            print(f"        - {len(df):,} registros cargados desde: {nombre_archivo}")
            print(f"        - {len(columnas_requeridas)} columnas cargadas")
            return df
            
        except Exception as e:
            raise RuntimeError(f"Error al cargar archivo {nombre_archivo}: {str(e)}")
        
    def cargar_bd_gestion_rl(self, fecha_proceso: datetime, 
                            columnas_requeridas: list = None
                            ) -> pd.DataFrame:
        """
        Carga archivo de Base de Datos de Gestión de Riesgo de Liquidez
        
        Args:
            fecha_proceso: Fecha para construir nombre del archivo
            columnas_requeridas: Lista de columnas a cargar (opcional)
            
        Returns:
            DataFrame con los datos cargados
        """
        print("      • Cargando datos de Base de Datos de Gestión de Riesgo de Liquidez...")

        if columnas_requeridas is None:
            query = """
                SELECT
                    *
                FROM
                    RF_BD_Gestion_RL
                WHERE
                    RF_BD_Gestion_RL.Fec_Pro = #{}#
            """.format(fecha_proceso.strftime('%Y-%m-%d'))
        else:
            columnas_str = ",\n".join([f"RF_BD_Gestion_RL.{col}" for col in columnas_requeridas])
            query = """
                SELECT
                    {}
                FROM
                    RF_BD_Gestion_RL
                WHERE
                    RF_BD_Gestion_RL.Fec_Pro = #{}#
            """.format(columnas_str, fecha_proceso.strftime('%Y-%m-%d'))

        
        if not self.ruta_interfaz.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.ruta_interfaz}")
        
        # Cargar datos desde MS Access
        try:
            df = ut.lectura_datos_ms_access(ruta=self.ruta_interfaz, 
                                            query=query)
            
            print(f"        - {len(df):,} registros cargados desde: RF_BD_Gestion_RL")
            print(f"        - {len(columnas_requeridas)} columnas cargadas")
            return df
            
        except Exception as e:
            raise RuntimeError(f"Error al cargar datos RF_BD_Gestion_RL: {str(e)}")
    
    def cargar_bd_gestion_rm(self, fecha_proceso: datetime, 
                            columnas_requeridas: list = None
                            ) -> pd.DataFrame:
        """
        Carga archivo de Base de Datos de Gestión de Riesgo de Mercado
        
        Args:
            fecha_proceso: Fecha para construir nombre del archivo
            columnas_requeridas: Lista de columnas a cargar (opcional)
            
        Returns:
            DataFrame con los datos cargados
        """
        print("      • Cargando datos de Base de Datos de Gestión de Riesgo de Liquidez...")

        if columnas_requeridas is None:
            query = """
                SELECT
                    *
                FROM
                    RF_BD_Gestion_RM
                WHERE
                    RF_BD_Gestion_RM.Fec_Pro = #{}#
            """.format(fecha_proceso.strftime('%Y-%m-%d'))
        else:
            columnas_str = ",\n".join([f"RF_BD_Gestion_RM.{col}" for col in columnas_requeridas])
            query = """
                SELECT
                    {}
                FROM
                    RF_BD_Gestion_RM
                WHERE
                    RF_BD_Gestion_RM.Fec_Pro = #{}#
            """.format(columnas_str, fecha_proceso.strftime('%Y-%m-%d'))

        
        if not self.ruta_interfaz.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.ruta_interfaz}")
        
        # Cargar datos desde MS Access
        try:
            df = ut.lectura_datos_ms_access(ruta=self.ruta_interfaz, 
                                            query=query)
            
            print(f"        - {len(df):,} registros cargados desde: RF_BD_Gestion_RM")
            print(f"        - {len(columnas_requeridas)} columnas cargadas")
            return df
            
        except Exception as e:
            raise RuntimeError(f"Error al cargar datos RF_BD_Gestion_RM: {str(e)}")
     