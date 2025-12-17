from datetime import datetime, date
import threading
from typing import Dict
from core.orquestador import OrquestadorModelos

class ControladorModelos:
    def __init__(self, interfaz):
        self.interfaz = interfaz
        self.orquestador = OrquestadorModelos()
        self.ejecuciones_activas: Dict[str, threading.Thread] = {}
        
        # Configurar callbacks de botones
        self.interfaz.configurar_callbacks(
            self.ejecutar_modelo,
            self.ejecutar_todos_modelos
        )

    def ejecutar_modelo(self, codigo_modelo: str):
        """Maneja la ejecución de un modelo específico"""
        # Evitar múltiples ejecuciones del mismo modelo
        if codigo_modelo in self.ejecuciones_activas:
            self.interfaz.agregar_log(f"El modelo {codigo_modelo} ya está en ejecución")
            return
            
        fecha = self.interfaz.obtener_fecha()
        
        # Actualizar estado visual
        self.interfaz.actualizar_estado_modelo(codigo_modelo, 'ejecutando')
        self.interfaz.agregar_log(f"Iniciando ejecución de {codigo_modelo}")
        
        # Crear y ejecutar thread
        thread = threading.Thread(
            target=self._ejecutar_modelo_thread,
            args=(codigo_modelo, fecha)
        )
        self.ejecuciones_activas[codigo_modelo] = thread
        thread.start()
        
    def _ejecutar_modelo_thread(self, codigo_modelo: str, fecha: datetime):
        """Ejecuta el modelo en un thread separado"""
        try:
            config = self.orquestador.modelos[codigo_modelo]
            # Convertir la fecha a datetime
            if isinstance(fecha, date):
                fecha = datetime.combine(fecha, datetime.min.time())
            
            exito = self.orquestador.ejecutar_modelo(
                codigo_modelo, 
                config,
                fecha
            )
            
            # Actualizar interfaz según resultado
            if exito:
                self.interfaz.actualizar_estado_modelo(codigo_modelo, 'exitoso')
                self.interfaz.agregar_log(f"Ejecución exitosa de {codigo_modelo}")
            else:
                self.interfaz.actualizar_estado_modelo(codigo_modelo, 'error')
                self.interfaz.agregar_log(f"Error en la ejecución de {codigo_modelo}")
                
        except Exception as e:
            self.interfaz.actualizar_estado_modelo(codigo_modelo, 'error')
            self.interfaz.agregar_log(f"Error en {codigo_modelo}: {str(e)}")
            
        finally:
            # Limpiar referencia al thread
            if codigo_modelo in self.ejecuciones_activas:
                del self.ejecuciones_activas[codigo_modelo]

    def ejecutar_todos_modelos(self):
        """Ejecuta todos los modelos primarios en secuencia"""
        for codigo_modelo in self.interfaz.botones_modelos.keys():
            if codigo_modelo not in self.ejecuciones_activas:
                self.ejecutar_modelo(codigo_modelo)