import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class CargadorParametrosModelos:
    """Clase especializada en cargar parámetros de modelos desde Excel"""
    
    def __init__(self, ruta_parametros: Path):
        self.ruta_parametros = Path(ruta_parametros)
        
    def cargar_parametros_mr_prepago_consumo(self) -> Dict[str, Any]:
        """
        Carga parámetros específicos para modelos de prepago
        
        Returns:
            Dict con SMM_MODELO y ESCENARIOS
        """
        print("      • Cargando parámetros de prepago...")
        
        if not self.ruta_parametros.exists():
            raise FileNotFoundError(f"Archivo de parámetros no encontrado: {self.ruta_parametros}")
        
        try:
            # Cargar SMM desde hoja SMM_PREPAGO
            df_smm = pd.read_excel(self.ruta_parametros, sheet_name='SMM_PREPAGO')
            nombres_subproductos = ["CONSUMO", "AUTOMOTRIZ", "REFINANCIADO", "RENEGOCIADO", "CONSOLIDADO"]
            
            smm_dict = {}
            for i, columna in enumerate(df_smm.columns):
                if i < len(nombres_subproductos):
                    smm_dict[nombres_subproductos[i]] = df_smm[columna].dropna().tolist()
            
            # Cargar escenarios desde hoja ESCENARIO
            df_escenarios = pd.read_excel(self.ruta_parametros, sheet_name='ESCENARIO')
            escenarios_dict = {}
            
            for _, row in df_escenarios.iterrows():
                id_esc = int(row['ID_ESCENARIO'])
                escenarios_dict[id_esc] = {
                    "DESCRIPCION": str(row['DESCRIPCION']).strip().upper(),
                    "PHI": float(row['PHI'])
                }
            
            print(f"        - SMM cargado para {len(smm_dict)} tipos de producto")
            print(f"        - {len(escenarios_dict)} escenarios cargados")
            
            return {
                'SMM_MODELO': smm_dict,
                'ESCENARIOS': escenarios_dict
            }
            
        except Exception as e:
            raise RuntimeError(f"Error al cargar parámetros de prepago: {str(e)}")
    
    # def cargar_parametros_mora(self) -> Dict[str, Any]:
    #     """
    #     Carga parámetros específicos para modelos de mora
        
    #     Returns:
    #         Dict con factores de mora y matrices
    #     """
    #     print("      • Cargando parámetros de mora...")
        
    #     if not self.ruta_parametros.exists():
    #         raise FileNotFoundError(f"Archivo de parámetros no encontrado: {self.ruta_parametros}")
        
    #     try:
    #         # Cargar diferentes hojas según tipo de mora
    #         factores_mora = pd.read_excel(
    #             self.ruta_parametros, 
    #             sheet_name="FACTORES_MORA"
    #         )
            
    #         factores_globales = pd.read_excel(
    #             self.ruta_parametros, 
    #             sheet_name="FACTORES_GLOBALES"
    #         )
            
    #         # Detectar qué matrices están disponibles
    #         parametros = {
    #             'FACTORES_MORA': factores_mora,
    #             'FACTORES_GLOBALES': factores_globales.iloc[0, 0] if not factores_globales.empty else 1.0
    #         }
            
    #         # Cargar matrices según disponibilidad
    #         try:
    #             matriz_consumo = pd.read_excel(self.ruta_parametros, sheet_name="MATRIZ_CONSUMO")
    #             parametros['MATRIZ_CONSUMO'] = matriz_consumo
    #         except:
    #             pass
                
    #         try:
    #             matriz_automotriz = pd.read_excel(self.ruta_parametros, sheet_name="MATRIZ_AUTOMOTRIZ")
    #             parametros['MATRIZ_AUTOMOTRIZ'] = matriz_automotriz
    #         except:
    #             pass
                
    #         try:
    #             matriz_hipotecario = pd.read_excel(self.ruta_parametros, sheet_name="MATRIZ_HIPOTECARIO")
    #             parametros['MATRIZ_HIPOTECARIO'] = matriz_hipotecario
    #         except:
    #             pass
            
    #         print(f"        - Parámetros de mora cargados: {len(parametros)} elementos")
    #         return parametros
            
    #     except Exception as e:
    #         raise RuntimeError(f"Error al cargar parámetros de mora: {str(e)}")
    
    # def cargar_parametros_personalizados(self, hojas_requeridas: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Carga parámetros de hojas específicas del Excel
        
        Args:
            hojas_requeridas: Lista de nombres de hojas a cargar
            
        Returns:
            Dict con los DataFrames de cada hoja
        """
        print(f"      • Cargando parámetros personalizados: {hojas_requeridas}")
        
        if not self.ruta_parametros.exists():
            raise FileNotFoundError(f"Archivo de parámetros no encontrado: {self.ruta_parametros}")
        
        parametros = {}
        
        try:
            for hoja in hojas_requeridas:
                df = pd.read_excel(self.ruta_parametros, sheet_name=hoja)
                parametros[hoja] = df
                print(f"        - Hoja '{hoja}' cargada: {len(df)} filas")
            
            return parametros
            
        except Exception as e:
            raise RuntimeError(f"Error al cargar parámetros personalizados: {str(e)}")