import sys
from pathlib import Path
from datetime import datetime
import argparse
import tkinter as tk

# Asegurar que el directorio raíz esté en el path
# BASE_DIR = Path(__file__).resolve().parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Importaciones del proyecto
from core.orquestador import OrquestadorModelos
from gui.interfaz import InterfazModelos
from gui.controladores import ControladorModelos

def ejecutar_modo_consola(args):
    try:
        fecha = datetime.strptime(args.fecha, '%Y-%m-%d')
    except ValueError:
        print("Error: Formato de fecha inválido. Use YYYY-MM-DD")
        return

    orquestador = OrquestadorModelos()
    
    if args.listar:
        print("\nModelos disponibles:")
        for key, config in orquestador.modelos.items():
            estado = "✓" if config["activado"] else "✗"
            carga_gcp = "✓" if config.get("tiene_carga_gcp", False) else "✗"
            print(f"[{estado}] {key}: {config['nombre']} | Carga GCP: {carga_gcp}")
        return

    # Modo: Solo carga a GCP
    if args.solo_carga_gcp:
        print(f"\n{'='*60}")
        print(f"MODO: SOLO CARGA A GCP")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Expandir "todos" si se especificó
        modelos_carga = args.solo_carga_gcp
        if 'todos' in modelos_carga:
            modelos_carga = [
                key for key, config in orquestador.modelos.items()
                if config.get("tiene_carga_gcp", False)
            ]
            print(f"Expandiendo 'todos' a: {', '.join(modelos_carga)}\n")
        
        resultados_carga = orquestador.cargar_modelos_gcp(modelos_carga, fecha)
        
        print("\n=== Resumen de carga a GCP ===")
        # Los resultados ahora vienen por tabla, no por modelo
        for tabla, exito in resultados_carga.items():
            estado = "ÉXITO" if exito else "ERROR"
            print(f"{tabla}: {estado}")
        return

    if not args.modelos:
        print("Error: Debe especificar --modelos, --solo-carga-gcp o usar --listar")
        return

    modelos_a_ejecutar = args.modelos
    if 'todos' in modelos_a_ejecutar:
        modelos_a_ejecutar = list(orquestador.modelos.keys())

    print(f"\nFecha de ejecución: {fecha.strftime('%Y-%m-%d')}")
    print(f"Modelos seleccionados: {', '.join(modelos_a_ejecutar)}")
    print(f"Cargar a GCP: {'Sí' if args.cargar_gcp else 'No'}\n")

    # Ejecutar modelos
    resultados = orquestador.ejecutar_modelos_paralelo(modelos_a_ejecutar, fecha)
    
    print("\n=== Resumen de ejecución ===")
    for modelo, exito in resultados.items():
        estado = "ÉXITO" if exito else "ERROR"
        print(f"{orquestador.modelos[modelo]['nombre']}: {estado}")

    # Cargar a GCP si se solicitó y hubo ejecuciones exitosas
    if args.cargar_gcp:
        modelos_exitosos = [modelo for modelo, exito in resultados.items() if exito]
        
        if modelos_exitosos:
            print(f"\n{'='*60}")
            print("Iniciando carga a GCP de modelos exitosos...")
            print(f"{'='*60}")
            
            resultados_carga = orquestador.cargar_modelos_gcp(modelos_exitosos, fecha)
            
            print("\n=== Resumen de carga a GCP ===")
            for modelo, exito in resultados_carga.items():
                estado = "ÉXITO" if exito else "ERROR"
                nombre = orquestador.modelos.get(modelo, {}).get('nombre', modelo)
                print(f"{nombre}: {estado}")
        else:
            print("\nNo hay modelos exitosos para cargar a GCP")

def ejecutar_modo_gui():
    root = tk.Tk()
    interfaz = InterfazModelos(root)
    controlador = ControladorModelos(interfaz)
    root.mainloop()

def main():
    print("=== Procesos Diarios Banco Falabella - Modelos & Metodologías ===")

    parser = argparse.ArgumentParser(
        description='Procesos Diarios Banco Falabella - Modelos & Metodologías',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Ejecutar modelo sin cargar a GCP
  python main.py --fecha 2025-11-28 --modelos mr_prepago_consumo
  
  # Ejecutar y cargar a GCP
  python main.py --fecha 2025-11-28 --modelos mr_prepago_consumo --cargar-gcp
  
  # Ejecutar todos los modelos y cargar
  python main.py --fecha 2025-11-28 --modelos todos --cargar-gcp
  
  # Solo cargar modelos específicos a GCP (sin ejecutar)
  python main.py --fecha 2025-11-28 --solo-carga-gcp mr_prepago_consumo mr_prepago_hipotecario
  
  # Solo cargar TODOS los modelos a GCP (sin ejecutar)
  python main.py --fecha 2025-11-28 --solo-carga-gcp todos
  
  # Modo GUI
  python main.py --gui
  
  # Listar modelos disponibles
  python main.py --listar
        """
    )
    parser.add_argument('--fecha', type=str, help='Fecha de ejecución (YYYY-MM-DD)', required=False)
    parser.add_argument('--modelos', type=str, nargs='+', help='Modelos a ejecutar (separados por espacio)')
    parser.add_argument('--listar', action='store_true', help='Listar modelos disponibles')
    parser.add_argument('--gui', action='store_true', help='Iniciar interfaz gráfica')
    parser.add_argument('--cargar-gcp', action='store_true', help='Cargar resultados a BigQuery después de ejecutar')
    parser.add_argument('--solo-carga-gcp', type=str, nargs='+', metavar='MODELO',
                       help='Solo cargar modelos a GCP sin ejecutarlos')
    args = parser.parse_args()

    if args.gui:
        ejecutar_modo_gui()
    else:
        if not args.fecha:
            print("Error: En modo consola, --fecha es requerido")
            return
        ejecutar_modo_consola(args)

if __name__ == "__main__":
    main()