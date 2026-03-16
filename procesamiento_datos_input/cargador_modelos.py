import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import yaml

from .cargador_datos import CargadorDatosModelos
from .cargador_parametros import cargar_hojas_parametros
from .limpiador_datos import LimpiadorDatos
from config import config_rutas as cr

class CargadorModelos:
    """
    Clase principal que coordina la carga de datos y parámetros para todos los modelos
    """
    
    def __init__(self):
        # Cargar configuración directamente desde el YAML
        with open(cr.CONFIG / 'config_rutas_ext_y_archivos.yaml', 'r', encoding='utf-8') as file:
            config_ext = yaml.safe_load(file)
        
        # Construir configuraciones de modelos dinámicamente
        self.configuraciones = self._construir_configuraciones(config_ext['modelos'])
    
    def _construir_configuraciones(self, config_modelos: dict) -> dict:
        """
        Construir configuraciones de modelos desde el YAML
        
        Args:
            config_modelos: Diccionario con configuraciones desde el YAML
            
        Returns:
            Diccionario con configuraciones procesadas
        """
        configuraciones = {}
        
        for codigo_modelo, config in config_modelos.items():
            # Determinar tipo de fuente de datos
            if 'ms_access_input' in config:
                # Modelo que usa Access
                configuraciones[codigo_modelo] = {
                    'ruta_interfaz': Path(config['ms_access_input']),
                    'tabla_access': config['ms_access_tabla_input'],
                    'ruta_parametros': Path(config.get('excel_parametros_input', config.get('excel_parametros_modelo_input', ''))),
                    'ruta_output': Path(config['excel_output'])
                }
            else:
                # Modelo que usa interfaz estándar
                configuraciones[codigo_modelo] = {
                    'ruta_interfaz': Path(config['interfaz_datos_input']),
                    'ruta_parametros': Path(config.get('excel_parametros_input', config.get('excel_parametros_modelo_input', ''))),
                    'ruta_output': Path(config['excel_output'])
                }
                
                # Agregar outputs adicionales si existen
                if 'excel_output_2' in config:
                    configuraciones[codigo_modelo]['ruta_output_2'] = Path(config['excel_output_2'])
                
                # Para ml_nmd que tiene parámetros adicionales
                if 'excel_parametros_core_input' in config:
                    configuraciones[codigo_modelo]['ruta_parametros_core'] = Path(config['excel_parametros_core_input'])
        
        return configuraciones
    
    def _obtener_cargadores(self, codigo_modelo: str):
        """
        Obtener instancias de cargadores para un modelo específico
        
        Args:
            codigo_modelo: Código del modelo
            
        Returns:
            Tupla con (CargadorDatosModelos, dict_hojas_parametros)
        """
        if codigo_modelo not in self.configuraciones:
            raise ValueError(f"Modelo '{codigo_modelo}' no está configurado")
        
        config = self.configuraciones[codigo_modelo]
        
        cargador_datos = CargadorDatosModelos(config['ruta_interfaz'])
        hojas_parametros = cargar_hojas_parametros(codigo_modelo)
        
        return cargador_datos, hojas_parametros
    
    # === MODELOS DE PREPAGO ===
    
    def cargar_datos_mr_prepago_consumo(self, fecha_proceso: datetime) -> Dict[str, Any]:
        """
        Cargar datos completos para modelo Modelo Prepago Consumo
        
        Args:
            fecha_proceso: Fecha de proceso
            
        Returns:
            Dict con 'datos_interfaz' y 'parametros'
        """
        print("\n[CARGADOR] Procesando Modelo Prepago Consumo...")
        
        # Obtener cargadores
        cargador_datos, cargador_parametros = self._obtener_cargadores('mr_prepago_consumo')
        
        # 1. Cargar datos de interfaz
        print("\n  [1/3] Cargando datos de interfaz...")
        columnas = ["FECHA_PROCESO", "SISTEMA","CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO","DESTINOCREDITO", "MONEDA_ORIGEN",
                "AMORTIZACION", "INTERES","FECHA_VENCIMIENTO_CUOTA"]
        df_interfaz = cargador_datos.cargar_interfaz_pml(fecha_proceso, 
                                                         columnas_requeridas=columnas)
        
        # 2. Cargar parámetros
        print("\n  [2/3] Cargando parámetros...")
        parametros = cargador_parametros.cargar_parametros_mr_prepago_consumo()
        
        # 3. Aplicar limpieza y transformaciones específicas
        print("\n  [3/3] Aplicando transformaciones...")
        df_limpio = LimpiadorDatos.estandarizar_interfaz_pml(df_interfaz)
        df_filtrado = LimpiadorDatos.filtrar_por_subproductos_consumo(df_limpio)
        df_input = LimpiadorDatos.transformar_datos_mr_prepago_consumo(df_filtrado)
        # df_final = LimpiadorDatos.ajustar_fechas_vencimiento(df_categorizado, fecha_proceso)
        
        # print(f"\n  ✓ Procesamiento completado - {len(df_final):,} registros finales")
        
        return {
            'datos_interfaz': df_input,
            'parametros': parametros
        }
    
    # def cargar_datos_mr_prepago_cmr(self, fecha_proceso: datetime) -> Dict[str, Any]:
    #     """
    #     Cargar datos completos para modelo MR Prepago CMR
        
    #     Args:
    #         fecha_proceso: Fecha de proceso
            
    #     Returns:
    #         Dict con 'datos_interfaz' y 'parametros'
    #     """
    #     print("\n[CARGADOR] Procesando MR Prepago CMR...")
        
    #     # Obtener cargadores
    #     cargador_datos, cargador_parametros = self._obtener_cargadores('mr_prepago_cmr')
        
    #     # 1. Cargar desde Access
    #     print("\n  [1/3] Cargando datos desde Access...")
    #     config = self.configuraciones['mr_prepago_cmr']
    #     df_interfaz = cargador_datos.cargar_base_access(
    #         config['ruta_interfaz'], 
    #         config['tabla_access']
    #     )
        
    #     # 2. Cargar parámetros
    #     print("\n  [2/3] Cargando parámetros...")
    #     parametros = cargador_parametros.cargar_parametros_prepago()
        
    #     # 3. Aplicar limpieza básica (sin filtros específicos para CMR)
    #     print("\n  [3/3] Aplicando transformaciones...")
    #     df_final = LimpiadorDatos.limpiar_interfaz_basica(df_interfaz)
        
    #     print(f"\n  ✓ Procesamiento completado - {len(df_final):,} registros finales")
        
    #     return {
    #         'datos_interfaz': df_final,
    #         'parametros': parametros
    #     }
    
    # # === MODELOS DE MORA ===
    
    # def cargar_datos_ml_mora_consumo(self, fecha_proceso: datetime) -> Dict[str, Any]:
    #     """
    #     Cargar datos completos para modelo ML Mora Consumo
        
    #     Args:
    #         fecha_proceso: Fecha de proceso
            
    #     Returns:
    #         Dict con 'datos_interfaz' y 'parametros'
    #     """
    #     print("\n[CARGADOR] Procesando ML Mora Consumo...")
        
    #     # Obtener cargadores
    #     cargador_datos, cargador_parametros = self._obtener_cargadores('ml_mora_consumo')
        
    #     # 1. Cargar datos de interfaz
    #     print("\n  [1/3] Cargando datos de interfaz...")
    #     df_interfaz = cargador_datos.cargar_interfaz_estandar(fecha_proceso)
        
    #     # 2. Cargar parámetros de mora
    #     print("\n  [2/3] Cargando parámetros...")
    #     parametros = cargador_parametros.cargar_parametros_mora()
        
    #     # 3. Aplicar transformaciones específicas para consumo
    #     print("\n  [3/3] Aplicando transformaciones...")
    #     df_limpio = LimpiadorDatos.limpiar_interfaz_basica(df_interfaz)
    #     df_final = LimpiadorDatos.filtrar_por_subproductos_consumo(df_limpio)
        
    #     print(f"\n  ✓ Procesamiento completado - {len(df_final):,} registros finales")
        
    #     return {
    #         'datos_interfaz': df_final,
    #         'parametros': parametros
    #     }
    
    # def cargar_datos_ml_mora_hipotecario(self, fecha_proceso: datetime) -> Dict[str, Any]:
    #     """
    #     Cargar datos completos para modelo ML Mora Hipotecario
        
    #     Args:
    #         fecha_proceso: Fecha de proceso
            
    #     Returns:
    #         Dict con 'datos_interfaz' y 'parametros'
    #     """
    #     print("\n[CARGADOR] Procesando ML Mora Hipotecario...")
        
    #     # Obtener cargadores
    #     cargador_datos, cargador_parametros = self._obtener_cargadores('ml_mora_hipotecario')
        
    #     # 1. Cargar datos de interfaz
    #     print("\n  [1/3] Cargando datos de interfaz...")
    #     df_interfaz = cargador_datos.cargar_interfaz_estandar(fecha_proceso)
        
    #     # 2. Cargar parámetros de mora
    #     print("\n  [2/3] Cargando parámetros...")
    #     parametros = cargador_parametros.cargar_parametros_mora()
        
    #     # 3. Aplicar transformaciones específicas para hipotecario
    #     print("\n  [3/3] Aplicando transformaciones...")
    #     df_limpio = LimpiadorDatos.limpiar_interfaz_basica(df_interfaz)
    #     df_final = LimpiadorDatos.filtrar_por_subproductos_hipotecario(df_limpio)
        
    #     print(f"\n  ✓ Procesamiento completado - {len(df_final):,} registros finales")
        
    #     return {
    #         'datos_interfaz': df_final,
    #         'parametros': parametros
    #     }
    
    # # === MÉTODO GENÉRICO ===
    
    # def cargar_datos_modelo(self, codigo_modelo: str, fecha_proceso: datetime) -> Dict[str, Any]:
        """
        Método genérico para cargar cualquier modelo configurado
        
        Args:
            codigo_modelo: Código del modelo
            fecha_proceso: Fecha de proceso
            
        Returns:
            Dict con datos y parámetros del modelo
        """
        # Mapeo de códigos a métodos específicos
        metodos_carga = {
            'mr_prepago_consumo': self.cargar_datos_mr_prepago_consumo,
            'mr_prepago_cmr': self.cargar_datos_mr_prepago_cmr,
            'ml_mora_consumo': self.cargar_datos_ml_mora_consumo,
            'ml_mora_hipotecario': self.cargar_datos_ml_mora_hipotecario
        }
        
        if codigo_modelo not in metodos_carga:
            raise ValueError(f"Método de carga no implementado para modelo: {codigo_modelo}")
        
        return metodos_carga[codigo_modelo](fecha_proceso)