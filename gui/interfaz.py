import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from tkcalendar import DateEntry
from typing import Callable
# import tkinter.messagebox as messagebox
# from io import StringIO

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.stdout = sys.stdout
        
    def write(self, str):
        self.text_widget.config(state='normal')
        self.text_widget.insert(tk.END, str)
        self.text_widget.see(tk.END)
        self.text_widget.config(state='disabled')
        self.stdout.write(str)  # También escribir a la consola original
        
    def flush(self):
        pass

class InterfazModelos:
    def __init__(self, root):
        self.root = root
        self.root.title("Banco Falabella Modelos & Metodologías - Procesos Diarios")
        self.root.geometry("1200x800")  # Ventana más grande para el nuevo layout
        
        # Colores para estados
        self.COLORES = {
            'sin_ejecutar': '#333333',    # Gris oscuro
            'ejecutando': '#FFA500',      # Naranja
            'error': '#FF0000',           # Rojo
            'exitoso': '#00FF00'          # Verde
        }
        
        self._crear_interfaz()
        
    def _crear_interfaz(self):
        # Frame principal
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.main_frame.columnconfigure(0, weight=1)  # Columna izquierda (modelos)
        self.main_frame.columnconfigure(1, weight=1)  # Columna derecha (terminal)
        
        # Sección superior - Fecha
        self._crear_seccion_superior()
        
        # Layout de dos columnas
        left_frame = ttk.Frame(self.main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        right_frame = ttk.Frame(self.main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # Crear secciones en sus respectivos frames
        self._crear_seccion_modelos(left_frame)
        self._crear_terminal(right_frame)

    def _crear_seccion_superior(self):
        # Frame superior
        top_frame = ttk.Frame(self.main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Selector de fecha
        ttk.Label(top_frame, text="Fecha de Proceso:").grid(row=0, column=0, padx=5)
        self.fecha_proceso = DateEntry(
            top_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='dd-mm-yyyy',
            locale='es_ES'
        )
        self.fecha_proceso.grid(row=0, column=1, padx=5)
        
        # Botón Ejecutar Todos
        self.btn_ejecutar_todos = tk.Button(
            top_frame,
            text="▶ Ejecutar Todos",
            width=15,
            height=1,
            bg='#004d99',  # Azul oscuro
            fg='white',
            font=('Arial', 10, 'bold')
        )
        self.btn_ejecutar_todos.grid(row=0, column=2, padx=20)

    def _crear_terminal(self, parent):
        # Terminal con redirección de stdout
        terminal_frame = ttk.LabelFrame(parent, text="Terminal", padding="5")
        terminal_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Crear scrollbar
        scrollbar = ttk.Scrollbar(terminal_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configurar terminal con scrollbar
        self.terminal = tk.Text(terminal_frame, height=25, width=80,
                              yscrollcommand=scrollbar.set)
        self.terminal.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.terminal.yview)
        
        # Configurar redirección de stdout
        self.stdout_redirector = StdoutRedirector(self.terminal)
        sys.stdout = self.stdout_redirector
        
        # Configurar expansión
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)

    def _crear_seccion_modelos(self, parent):
        # Frame para modelos
        modelos_frame = ttk.LabelFrame(parent, text="Modelos Primarios", padding="5")
        modelos_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Crear botones para cada modelo
        self.botones_modelos = {}
        modelos = [
            ("MR - Prepago Hipotecario", "mr_prepago_hipotecario", True),
            ("MR - Prepago Consumo", "mr_prepago_consumo", True),
            ("ML - Mora Hipotecario", "ml_mora_hipotecario", False),
            ("ML - Mora Consumo", "ml_mora_consumo", False),
            ("ML - Mora Comercial", "ml_mora_comercial", False),
            ("ML - Mora CAE", "ml_mora_cae", False)
        ]
        
        for i, (nombre, codigo, habilitado) in enumerate(modelos):
            estado = 'normal' if habilitado else 'disabled'
            color_bg = self.COLORES['sin_ejecutar'] if habilitado else '#666666'
            
            btn = tk.Button(modelos_frame, text=nombre, width=25, height=2,
                          bg=color_bg, fg='white', state=estado)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5)
            self.botones_modelos[codigo] = btn
            
    def configurar_callbacks(self, callback_modelo: Callable, callback_todos: Callable):
        """Configura los callbacks para los botones de modelos"""
        for codigo, btn in self.botones_modelos.items():
            btn.configure(command=lambda c=codigo: callback_modelo(c))
        
        # Configurar callback para el botón Ejecutar Todos
        self.btn_ejecutar_todos.configure(command=callback_todos)

    def actualizar_estado_modelo(self, codigo: str, estado: str):
        """Actualiza el estado visual de un botón de modelo"""
        if codigo in self.botones_modelos and estado in self.COLORES:
            self.botones_modelos[codigo].configure(bg=self.COLORES[estado])
            
    def agregar_log(self, mensaje: str):
        """Agrega un mensaje al terminal"""
        self.terminal.config(state='normal')
        self.terminal.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {mensaje}\n")
        self.terminal.see(tk.END)
        self.terminal.config(state='disabled')
        
    def obtener_fecha(self) -> datetime:
        """Retorna la fecha seleccionada como datetime"""
        fecha = self.fecha_proceso.get_date()
        if isinstance(fecha, date):
            return datetime.combine(fecha, datetime.min.time())
        return fecha

    def __del__(self):
        # Restaurar stdout original al cerrar
        if hasattr(self, 'stdout_redirector'):
            sys.stdout = self.stdout_redirector.stdout