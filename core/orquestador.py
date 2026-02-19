import importlib
from datetime import datetime
import concurrent.futures
import argparse
from typing import List, Dict, Any
import traceback

class OrquestadorModelos:
    def __init__(self):
        self.modelos = {
            "mr_prepago_consumo": {
                "nombre": "Modelo Prepago Consumo",
                "modulo": "RF_Modelo_Prepago_Consumo.mr_prepago_consumo",
                "activado": True,
                "orden": 1,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "mr_prepago_hipotecario": {
                "nombre": "Modelo Prepago Hipotecario",
                "modulo": "RF_Modelo_Prepago_Hipotecario.mr_prepago_hipotecario",
                "activado": True,
                "orden": 2,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "mr_prepago_cmr": {
                "nombre": "Modelo Prepago CMR",
                "modulo": "RF_Modelo_Prepago_CMR.mr_prepago_cmr",
                "activado": True,
                "orden": 3,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_consumo": {
                "nombre": "Modelo Mora Consumo",
                "modulo": "RF_Modelo_Mora_Consumo.ml_mora_consumo",
                "activado": True,
                "orden": 4,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_cae": {
                "nombre": "Modelo Mora CAE",
                "modulo": "RF_Modelo_Mora_CAE.ml_mora_cae",
                "activado": True,
                "orden": 5,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_hipotecario": {
                "nombre": "Modelo Mora Hipotecario",
                "modulo": "RF_Modelo_Mora_Hipotecario.ml_mora_hipotecario",
                "activado": True,
                "orden": 6,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_mora_comercial": {
                "nombre": "Modelo Mora Comercial",
                "modulo": "RF_Modelo_Mora_Comercial.ml_mora_comercial",
                "activado": True,
                "orden": 7,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_nmd": {
                "nombre": "Modelo NMD",
                "modulo": "RF_Modelo_NMD.ml_nmd",
                "activado": True,
                "orden": 8,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_lc": {
                "nombre": "Modelo Linea de Credito",
                "modulo": "RF_Modelo_Linea_de_Credito.ml_lc",
                "activado": True,
                "orden": 8,
                "tiene_carga_gcp": True,
                "tiene_carga_gcp_historica": True
            },
            "ml_inversiones": {
                "nombre": "Modelo Inversiones",
                "modulo": "RF_Modelo_Inversiones.ml_inversiones",
                "activado": True,
                "orden": 9,
                "tiene_carga_gcp": False,
                "tiene_carga_gcp_historica": False
            }
        }
        

    def ejecutar_modelo(self, nombre_modelo: str, config: Dict[str, Any], fecha: datetime) -> bool:
        try:
            print(f"\n{'='*60}")
            print(f"Iniciando ejecución de {config['nombre']}")
            print(f"{'='*60}")
            
            # Importar dinámicamente el módulo
            modelo = importlib.import_module(config["modulo"])
            
            # Todos los modelos ahora tienen la función ejecutar_modelo unificada
            return modelo.ejecutar_modelo(fecha)
            
        except Exception as e:
            print(f"Error en la ejecución de {config['nombre']}: {str(e)}")
            print(f"Detalles del error: {traceback.format_exc()}")
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
                print("Ninguno de los modelos seleccionados tiene configuración de carga a GCP")
                return {}
            
            print(f"\n{'='*60}")
            print("CARGA A BIGQUERY (GCP)")
            print(f"Modelos seleccionados: {', '.join([self.modelos[m]['nombre'] for m in modelos_con_carga])}")
            print(f"{'='*60}\n")
            
            # Ejecutar carga - la función ahora maneja múltiples tablas por modelo automáticamente
            resultados_tablas = cargar_modelos_a_bigquery(fecha, modelos_con_carga)
            
            # Los resultados vienen por tabla, retornarlos directamente
            return resultados_tablas
            
        except ImportError as e:
            print(f"Error al importar módulo de carga GCP: {str(e)}")
            return {}
        except Exception as e:
            print(f"Error en carga a GCP: {str(e)}")
            print(f"Detalles del error: {traceback.format_exc()}")
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
                print("Ninguno de los modelos seleccionados tiene configuración de consolidación histórica")
                return {}
            
            print(f"\n{'='*60}")
            print("CONSOLIDACION HISTORICA EN BIGQUERY")
            print(f"Modelos seleccionados: {', '.join([self.modelos[m]['nombre'] for m in modelos_con_carga_historica])}")
            print(f"{'='*60}\n")
            
            # Ejecutar consolidación
            resultados_tablas = consolidar_historico_bigquery(fecha, modelos_con_carga_historica)
            
            return resultados_tablas
            
        except ImportError as e:
            print(f"Error al importar módulo de consolidación histórica: {str(e)}")
            return {}
        except Exception as e:
            print(f"Error en consolidación histórica: {str(e)}")
            print(f"Detalles del error: {traceback.format_exc()}")
            return {}

    def ejecutar_modelo_secuencial(self, nombre_modelo: str, fecha: datetime) -> Dict[str, bool]:
        """Ejecuta un único modelo de forma secuencial"""
        print(f"Iniciando ejecución secuencial del modelo para fecha: {fecha.strftime('%Y-%m-%d')}")
        
        resultados = {}
        if nombre_modelo in self.modelos:
            config = self.modelos[nombre_modelo]
            if config["activado"]:
                resultados[nombre_modelo] = self.ejecutar_modelo(nombre_modelo, config, fecha)
            else:
                print(f"El modelo {nombre_modelo} está deshabilitado")
                resultados[nombre_modelo] = False
        else:
            print(f"El modelo {nombre_modelo} no existe")
            resultados[nombre_modelo] = False
            
        return resultados

    def ejecutar_modelos_paralelo(self, modelos_seleccionados: List[str], fecha: datetime) -> Dict[str, bool]:
        """Ejecuta múltiples modelos en paralelo o uno solo en secuencial"""
        # Si solo hay un modelo, usar ejecución secuencial
        if len(modelos_seleccionados) == 1:
            return self.ejecutar_modelo_secuencial(modelos_seleccionados[0], fecha)
            
        print(f"Iniciando ejecución paralela de {len(modelos_seleccionados)} modelos para fecha: {fecha.strftime('%Y-%m-%d')}")
        
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
                    print(f"Error en modelo {nombre_modelo}: {str(e)}")
                    resultados[nombre_modelo] = False
        
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
    print("\n" + "="*60)
    print("MODELOS DISPONIBLES")
    print("="*60)
    for key, config in orquestador.modelos.items():
        estado = "Habilitado" if config["activado"] else "Deshabilitado"
        carga_gcp = "Si" if config.get("tiene_carga_gcp", False) else "No"
        print(f"\n{key}:")
        print(f"  Nombre: {config['nombre']}")
        print(f"  Estado: {estado}")
        print(f"  Carga GCP: {carga_gcp}")
    print("\n" + "="*60)

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