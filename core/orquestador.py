import importlib
import shutil
from datetime import datetime
from pathlib import Path
import concurrent.futures
import argparse
from typing import List, Dict, Any
import traceback
import yaml

from core.logger import get_logger, contexto_modelo

logger = get_logger(__name__)

# Ruta al YAML de configuración externa (rutas de red, parametros, outputs)
_CONFIG_EXT_YAML = Path(__file__).resolve().parent.parent / "config" / "config_rutas_ext_y_archivos.yaml"

class OrquestadorModelos:
    def __init__(self):
        self.modelos = {
            "mr_prepago_consumo": {
                "nombre": "Modelo Prepago Consumo",
                "modulo": "RF_Modelo_Prepago_Consumo.mr_prepago_consumo",
                "activado": True,
                "orden": 1,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "mr_prepago_hipotecario": {
                "nombre": "Modelo Prepago Hipotecario",
                "modulo": "RF_Modelo_Prepago_Hipotecario.mr_prepago_hipotecario",
                "activado": True,
                "orden": 2,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "mr_prepago_cmr": {
                "nombre": "Modelo Prepago CMR",
                "modulo": "RF_Modelo_Prepago_CMR.mr_prepago_cmr",
                "activado": True,
                "orden": 3,
                "vuelta": 2,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_consumo": {
                "nombre": "Modelo Mora Consumo",
                "modulo": "RF_Modelo_Mora_Consumo.ml_mora_consumo",
                "activado": True,
                "orden": 4,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_cae": {
                "nombre": "Modelo Mora CAE",
                "modulo": "RF_Modelo_Mora_CAE.ml_mora_cae",
                "activado": True,
                "orden": 5,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_hipotecario": {
                "nombre": "Modelo Mora Hipotecario",
                "modulo": "RF_Modelo_Mora_Hipotecario.ml_mora_hipotecario",
                "activado": True,
                "orden": 6,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_comercial": {
                "nombre": "Modelo Mora Comercial",
                "modulo": "RF_Modelo_Mora_Comercial.ml_mora_comercial",
                "activado": True,
                "orden": 7,
                "vuelta": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_nmd": {
                "nombre": "Modelo NMD",
                "modulo": "RF_Modelo_NMD.ml_nmd",
                "activado": True,
                "orden": 8,
                "vuelta": 2,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_lc": {
                "nombre": "Modelo Linea de Credito",
                "modulo": "RF_Modelo_Linea_de_Credito.ml_lc",
                "activado": True,
                "orden": 8,
                "vuelta": 2,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_inversiones": {
                "nombre": "Modelo Inversiones",
                "modulo": "RF_Modelo_Inversiones.ml_inversiones",
                "activado": True,
                "orden": 9,
                "vuelta": 2,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            }
        }

    # -----------------------------------------------------------------
    # F02 — Máquina del Tiempo: Snapshots de parámetros
    # -----------------------------------------------------------------

    def _snapshot_parametros(self, modelo_key: str, fecha: datetime) -> None:
        """Copia los Excel de parámetros del modelo a snapshots/{YYYYMMDD}/{modelo_key}/.

        Lee los campos ``excel_parametros_*`` del YAML de configuración
        externa y copia cada archivo con ``shutil.copy2`` (preserva
        metadata).  Si alguna copia falla (red caída, archivo no
        encontrado), lanza excepción para abortar la ejecución del
        modelo.

        Args:
            modelo_key: Clave del modelo en ``self.modelos`` (ej: ``mr_prepago_consumo``).
            fecha: Fecha de proceso.

        Raises:
            RuntimeError: Si no se puede copiar algún archivo de parámetros.
        """
        from config.config_rutas import resolver_ruta, BASE_DIR

        with open(_CONFIG_EXT_YAML, "r", encoding="utf-8") as f:
            config_ext = yaml.safe_load(f)

        modelo_cfg = config_ext.get("modelos", {}).get(modelo_key, {})
        if not modelo_cfg:
            logger.debug(f"Sin configuración externa para '{modelo_key}', omitiendo snapshot")
            return

        # Recolectar todos los campos que apuntan a Excel de parámetros
        rutas_parametros: List[Path] = []
        for campo, valor in modelo_cfg.items():
            if campo.startswith("excel_parametros") and isinstance(valor, str):
                rutas_parametros.append(resolver_ruta(valor))

        if not rutas_parametros:
            logger.debug(f"Modelo '{modelo_key}' sin rutas de parámetros en YAML, omitiendo snapshot")
            return

        fecha_str = fecha.strftime("%Y%m%d")
        destino_dir = BASE_DIR / "snapshots" / fecha_str / modelo_key
        destino_dir.mkdir(parents=True, exist_ok=True)

        for ruta_origen in rutas_parametros:
            destino = destino_dir / ruta_origen.name
            try:
                shutil.copy2(str(ruta_origen), str(destino))
                logger.info(f"📸 Snapshot: {ruta_origen.name} → snapshots/{fecha_str}/{modelo_key}/")
            except Exception as e:
                msg = (
                    f"No se pudo copiar parámetros para snapshot: {ruta_origen} → {destino}. "
                    f"Error: {e}"
                )
                logger.error(f"❌ {msg}")
                raise RuntimeError(msg) from e

    # -----------------------------------------------------------------
    # F14 — Pre/Post hooks para copia de interfaz PML
    # -----------------------------------------------------------------

    def _obtener_ruta_interfaz_red(self) -> Path:
        """Lee la ruta de red de la interfaz PML desde el YAML de config.

        Todos los modelos de primera vuelta comparten la misma ruta de
        red (``interfaz_datos_input``), así que tomamos la del primero.
        """
        from config.config_rutas import resolver_ruta

        with open(_CONFIG_EXT_YAML, "r", encoding="utf-8") as f:
            config_ext = yaml.safe_load(f)

        # Buscar el primer modelo de vuelta 1 que tenga interfaz_datos_input
        for key, cfg in self.modelos.items():
            if cfg.get("vuelta") == 1:
                interfaz = config_ext["modelos"].get(key, {}).get("interfaz_datos_input")
                if interfaz:
                    return resolver_ruta(interfaz)

        raise RuntimeError(
            "No se encontró 'interfaz_datos_input' para ningún modelo de primera vuelta"
        )

    def _pre_ejecucion_primera_vuelta(self, modelos_seleccionados: List[str], fecha: datetime) -> None:
        """Hook pre-ejecución: copia interfaz PML una sola vez si hay modelos de vuelta 1."""
        modelos_v1 = [
            m for m in modelos_seleccionados
            if m in self.modelos and self.modelos[m].get("vuelta") == 1
        ]
        if not modelos_v1:
            return

        from procesamiento_datos_input.cache_tablas import copiar_interfaz_a_local

        fecha_str = fecha.strftime("%Y%m%d")
        ruta_red = self._obtener_ruta_interfaz_red()

        logger.info(f"\n{'─'*60}")
        logger.info("PRE-EJECUCIÓN: Copiando interfaz PML a caché local...")
        logger.info(f"{'─'*60}")

        copiar_interfaz_a_local(ruta_red, fecha_str)

    def _post_ejecucion_primera_vuelta(self, modelos_seleccionados: List[str], fecha: datetime) -> None:
        """Hook post-ejecución: verifica que el archivo de red no cambió."""
        modelos_v1 = [
            m for m in modelos_seleccionados
            if m in self.modelos and self.modelos[m].get("vuelta") == 1
        ]
        if not modelos_v1:
            return

        from procesamiento_datos_input.cache_tablas import verificar_interfaz_post_ejecucion

        fecha_str = fecha.strftime("%Y%m%d")
        ruta_red = self._obtener_ruta_interfaz_red()

        logger.info(f"\n{'─'*60}")
        logger.info("POST-EJECUCIÓN: Verificando integridad de interfaz PML...")
        logger.info(f"{'─'*60}")

        verificar_interfaz_post_ejecucion(ruta_red, fecha_str)

    def ejecutar_modelo(self, nombre_modelo: str, config: Dict[str, Any], fecha: datetime) -> bool:
        with contexto_modelo(nombre_modelo):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Iniciando ejecución de {config['nombre']}")
                logger.info(f"{'='*60}")

                # F02: Snapshot de parámetros antes de ejecutar
                self._snapshot_parametros(nombre_modelo, fecha)
                
                # Importar dinámicamente el módulo
                modelo = importlib.import_module(config["modulo"])
                
                # Todos los modelos ahora tienen la función ejecutar_modelo unificada
                return modelo.ejecutar_modelo(fecha)
                
            except Exception as e:
                logger.error(f"Error en la ejecución de {config['nombre']}: {str(e)}")
                logger.error(f"Detalles del error: {traceback.format_exc()}")
                return False

    def cargar_modelos_gcp(self, modelos_a_cargar: List[str], fecha: datetime) -> Dict[str, bool]:
        """
        Carga los resultados de los modelos a BigQuery en GCP
        
        Args:
            modelos_a_cargar: Lista de códigos de modelos a cargar
            fecha: Fecha de proceso
            
        Returns:
            dict: Diccionario con los resultados de cada carga {tabla: bool}
        """
        try:
            # Importar el módulo de carga
            from carga_modelos_gcp.cargar_output_modelos_bigquery_dly import cargar_modelos_a_bigquery
            
            # Filtrar solo modelos que tienen configuración de carga GCP
            modelos_con_carga = [
                modelo for modelo in modelos_a_cargar 
                if modelo in self.modelos and self.modelos[modelo].get("tiene_carga_gcp", False)
            ]
            
            if not modelos_con_carga:
                logger.warning("Ninguno de los modelos seleccionados tiene configuración de carga a GCP")
                return {}
            
            logger.info(f"\n{'='*60}")
            logger.info("CARGA A BIGQUERY (GCP)")
            logger.info(f"Modelos seleccionados: {', '.join([self.modelos[m]['nombre'] for m in modelos_con_carga])}")
            logger.info(f"{'='*60}\n")
            
            # Ejecutar carga - la función ahora maneja múltiples tablas por modelo automáticamente
            resultados_tablas = cargar_modelos_a_bigquery(fecha, modelos_con_carga)
            
            # Los resultados vienen por tabla, retornarlos directamente
            return resultados_tablas
            
        except ImportError as e:
            logger.error(f"Error al importar módulo de carga GCP: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error en carga a GCP: {str(e)}")
            logger.error(f"Detalles del error: {traceback.format_exc()}")
            return {}

    def consolidar_historico_gcp(self, modelos_a_consolidar: List[str], fecha: datetime) -> Dict[str, bool]:
        """
        Consolida los datos diarios en las tablas históricas de BigQuery
        
        Args:
            modelos_a_consolidar: Lista de códigos de modelos a consolidar
            fecha: Fecha de proceso
            
        Returns:
            dict: Diccionario con los resultados de cada consolidación {tabla: bool}
        """
        try:
            # Importar el módulo de consolidación histórica
            from carga_modelos_gcp.cargar_output_modelos_bigquery_hist import consolidar_historico_bigquery
            
            # Filtrar solo modelos que tienen configuración de carga GCP histórica
            modelos_con_carga_historica = [
                modelo for modelo in modelos_a_consolidar 
                if modelo in self.modelos and self.modelos[modelo].get("tiene_carga_gcp_historica", False)
            ]
            
            if not modelos_con_carga_historica:
                logger.warning("Ninguno de los modelos seleccionados tiene configuración de consolidación histórica")
                return {}
            
            logger.info(f"\n{'='*60}")
            logger.info("CONSOLIDACION HISTORICA EN BIGQUERY")
            logger.info(f"Modelos seleccionados: {', '.join([self.modelos[m]['nombre'] for m in modelos_con_carga_historica])}")
            logger.info(f"{'='*60}\n")
            
            # Ejecutar consolidación
            resultados_tablas = consolidar_historico_bigquery(fecha, modelos_con_carga_historica)
            
            return resultados_tablas
            
        except ImportError as e:
            logger.error(f"Error al importar módulo de consolidación histórica: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error en consolidación histórica: {str(e)}")
            logger.error(f"Detalles del error: {traceback.format_exc()}")
            return {}

    def ejecutar_modelo_secuencial(self, nombre_modelo: str, fecha: datetime) -> Dict[str, bool]:
        """Ejecuta un único modelo de forma secuencial"""
        logger.info(f"Iniciando ejecución secuencial del modelo para fecha: {fecha.strftime('%Y-%m-%d')}")

        # F14: pre-ejecución (copia interfaz si es vuelta 1)
        self._pre_ejecucion_primera_vuelta([nombre_modelo], fecha)
        
        resultados = {}
        if nombre_modelo in self.modelos:
            config = self.modelos[nombre_modelo]
            if config["activado"]:
                resultados[nombre_modelo] = self.ejecutar_modelo(nombre_modelo, config, fecha)
            else:
                logger.warning(f"El modelo {nombre_modelo} está deshabilitado")
                resultados[nombre_modelo] = False
        else:
            logger.error(f"El modelo {nombre_modelo} no existe")
            resultados[nombre_modelo] = False

        # F14: post-ejecución (verifica integridad si es vuelta 1)
        self._post_ejecucion_primera_vuelta([nombre_modelo], fecha)
            
        return resultados

    def ejecutar_modelos_paralelo(self, modelos_seleccionados: List[str], fecha: datetime) -> Dict[str, bool]:
        """Ejecuta múltiples modelos en paralelo o uno solo en secuencial"""
        # Si solo hay un modelo, usar ejecución secuencial
        if len(modelos_seleccionados) == 1:
            return self.ejecutar_modelo_secuencial(modelos_seleccionados[0], fecha)
            
        logger.info(f"Iniciando ejecución paralela de {len(modelos_seleccionados)} modelos para fecha: {fecha.strftime('%Y-%m-%d')}")

        # F14: pre-ejecución (copia interfaz una sola vez si hay modelos de vuelta 1)
        self._pre_ejecucion_primera_vuelta(modelos_seleccionados, fecha)
        
        resultados = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            for nombre_modelo in modelos_seleccionados:
                if nombre_modelo in self.modelos:
                    config = self.modelos[nombre_modelo]
                    if config["activado"]:
                        futures[executor.submit(self.ejecutar_modelo, nombre_modelo, config, fecha)] = nombre_modelo
            
            for future in concurrent.futures.as_completed(futures):
                nombre_modelo = futures[future]
                try:
                    resultados[nombre_modelo] = future.result()
                except Exception as e:
                    logger.error(f"Error en modelo {nombre_modelo}: {str(e)}")
                    resultados[nombre_modelo] = False

        # F14: post-ejecución (verifica integridad si hubo modelos de vuelta 1)
        self._post_ejecucion_primera_vuelta(modelos_seleccionados, fecha)
        
        return resultados

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Orquestador de Modelos de Riesgo Financiero',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Ejecutar modelo
  python orquestador.py --fecha 2025-11-28 --modelos mr_prepago_consumo
  
  # Ejecutar y cargar a GCP
  python orquestador.py --fecha 2025-11-28 --modelos mr_prepago_consumo --cargar-gcp
  
  # Ejecutar todos y cargar
  python orquestador.py --fecha 2025-11-28 --modelos todos --cargar-gcp
  
  # Solo cargar modelos específicos a GCP (sin ejecutar)
  python orquestador.py --fecha 2025-11-28 --solo-carga-gcp mr_prepago_consumo mr_prepago_hipotecario
  
  # Solo cargar TODOS los modelos a GCP (sin ejecutar)
  python orquestador.py --fecha 2025-11-28 --solo-carga-gcp todos
  
  # Consolidar datos diarios en tablas históricas
  python orquestador.py --fecha 2025-11-28 --consolidar-historico mr_prepago_consumo
  
  # Consolidar TODOS los modelos en histórico
  python orquestador.py --fecha 2025-11-28 --consolidar-historico todos
  
  # Listar modelos disponibles
  python orquestador.py --listar
        """
    )
    parser.add_argument('--fecha', type=str, help='Fecha de ejecución (YYYY-MM-DD)')
    parser.add_argument('--modelos', type=str, nargs='+', help='Modelos a ejecutar (separados por espacio)')
    parser.add_argument('--listar', action='store_true', help='Listar modelos disponibles')
    parser.add_argument('--cargar-gcp', action='store_true', help='Cargar resultados a BigQuery después de ejecutar')
    parser.add_argument('--solo-carga-gcp', type=str, nargs='+', metavar='MODELO', 
                       help='Solo cargar modelos a GCP sin ejecutarlos')
    parser.add_argument('--consolidar-historico', type=str, nargs='+', metavar='MODELO',
                       help='Consolidar datos diarios en tablas históricas de BigQuery')
    return parser.parse_args()

def listar_modelos_disponibles(orquestador: OrquestadorModelos):
    logger.info("\n" + "="*60)
    logger.info("MODELOS DISPONIBLES")
    logger.info("="*60)
    for key, config in orquestador.modelos.items():
        estado = "Habilitado" if config["activado"] else "Deshabilitado"
        carga_gcp = "Si" if config.get("tiene_carga_gcp", False) else "No"
        logger.info(f"\n{key}:")
        logger.info(f"  Nombre: {config['nombre']}")
        logger.info(f"  Estado: {estado}")
        logger.info(f"  Carga GCP: {carga_gcp}")
    logger.info("\n" + "="*60)

def main():
    args = parse_arguments()
    
    orquestador = OrquestadorModelos()
    
    # Listar modelos
    if args.listar:
        listar_modelos_disponibles(orquestador)
        return
    
    # Validar fecha
    if not args.fecha:
        print("Error: --fecha es requerido")
        return
        
    try:
        fecha = datetime.strptime(args.fecha, '%Y-%m-%d')
    except ValueError:
        print("Formato de fecha inválido. Use YYYY-MM-DD")
        return

    # Modo: Solo carga a GCP
    if args.solo_carga_gcp:
        print(f"\n{'='*60}")
        print("MODO: SOLO CARGA A GCP")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Expandir "todos" si se especificó
        modelos_carga = args.solo_carga_gcp
        if 'todos' in modelos_carga:
            # Obtener todos los modelos que tienen carga GCP habilitada
            modelos_carga = [
                key for key, config in orquestador.modelos.items()
                if config.get("tiene_carga_gcp", False)
            ]
            print(f"Expandiendo 'todos' a: {', '.join(modelos_carga)}\n")
        
        resultados_carga = orquestador.cargar_modelos_gcp(modelos_carga, fecha)
        
        print("\n" + "="*60)
        print("RESUMEN DE CARGA A GCP")
        print("="*60)
        for modelo, exito in resultados_carga.items():
            estado = "ÉXITO" if exito else "ERROR"
            print(f"{orquestador.modelos[modelo]['nombre']}: {estado}")
        return

    # Modo: Consolidar histórico
    if args.consolidar_historico:
        print(f"\n{'='*60}")
        print("MODO: CONSOLIDACION HISTORICA")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Expandir "todos" si se especificó
        modelos_consolidar = args.consolidar_historico
        if 'todos' in modelos_consolidar:
            modelos_consolidar = [
                key for key, config in orquestador.modelos.items()
                if config.get("tiene_carga_gcp_historica", False)
            ]
            print(f"Expandiendo 'todos' a: {', '.join(modelos_consolidar)}\n")
        
        resultados_consolidacion = orquestador.consolidar_historico_gcp(modelos_consolidar, fecha)
        
        print("\n" + "="*60)
        print("RESUMEN DE CONSOLIDACION HISTORICA")
        print("="*60)
        for tabla, exito in resultados_consolidacion.items():
            estado = "ÉXITO" if exito else "ERROR"
            print(f"{tabla}: {estado}")
        return

    # Modo: Ejecutar modelos
    if not args.modelos:
        print("Error: Debe especificar --modelos o usar --listar")
        return

    modelos_a_ejecutar = args.modelos
    if 'todos' in modelos_a_ejecutar:
        modelos_a_ejecutar = list(orquestador.modelos.keys())

    # Ejecutar modelos
    resultados = orquestador.ejecutar_modelos_paralelo(modelos_a_ejecutar, fecha)
    
    print("\n" + "="*60)
    print("RESUMEN DE EJECUCIÓN DE MODELOS")
    print("="*60)
    for modelo, exito in resultados.items():
        estado = "ÉXITO" if exito else "ERROR"
        print(f"{orquestador.modelos[modelo]['nombre']}: {estado}")
    
    # Cargar a GCP si se solicitó y hubo ejecuciones exitosas
    if args.cargar_gcp:
        modelos_exitosos = [modelo for modelo, exito in resultados.items() if exito]
        
        if modelos_exitosos:
            resultados_carga = orquestador.cargar_modelos_gcp(modelos_exitosos, fecha)
            
            print("\n" + "="*60)
            print("RESUMEN DE CARGA A GCP")
            print("="*60)
            for modelo, exito in resultados_carga.items():
                estado = "ÉXITO" if exito else "ERROR"
                print(f"{orquestador.modelos[modelo]['nombre']}: {estado}")
        else:
            print("\nNo hay modelos exitosos para cargar a GCP")

if __name__ == "__main__":
    main()