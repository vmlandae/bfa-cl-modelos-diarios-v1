import sys
import os
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
from core.logger import setup_logging
from gui.interfaz import InterfazModelos

def expandir_modelos(nombres: list, orquestador: OrquestadorModelos, *, filtro_gcp: bool = False) -> list:
    """Expande aliases (todos, primera_vuelta, segunda_vuelta) a listas de modelos.

    Los grupos se derivan dinámicamente del campo 'vuelta' en la metadata de
    cada modelo registrado en el orquestador.

    Args:
        nombres: Lista de nombres/aliases de modelos.
        orquestador: Instancia del orquestador (para obtener la lista completa).
        filtro_gcp: Si True, al expandir 'todos' solo incluye modelos con tiene_carga_gcp.
    """
    if 'todos' in nombres:
        if filtro_gcp:
            return [
                key for key, config in orquestador.modelos.items()
                if config.get("tiene_carga_gcp", False)
            ]
        return list(orquestador.modelos.keys())
    if 'primera_vuelta' in nombres:
        return [
            key for key, config in orquestador.modelos.items()
            if config.get("vuelta") == 1
        ]
    if 'segunda_vuelta' in nombres:
        return [
            key for key, config in orquestador.modelos.items()
            if config.get("vuelta") == 2
        ]
    return nombres
from gui.controladores import ControladorModelos


def mostrar_tabla_resumen(orquestador, resultados_ejecucion: dict, resultados_carga: dict, incluir_carga: bool):
    """
    Muestra una tabla resumen con el estado de ejecución y carga de los modelos
    
    Args:
        orquestador: Instancia del OrquestadorModelos
        resultados_ejecucion: Dict con resultados de ejecución {modelo: bool}
        resultados_carga: Dict con resultados de carga {tabla: bool}
        incluir_carga: Si se debe mostrar la columna de carga GCP
    """
    # Mapeo de modelos a sus tablas (para relacionar resultados de carga)
    MODELO_A_TABLAS = {
        'mr_prepago_hipotecario': ['report_mr_prepago_hipotecario_dly'],
        'mr_prepago_consumo': ['report_mr_prepago_consumo_dly'],
        'mr_prepago_cmr': ['report_mr_prepago_cmr_dly'],
        'ml_mora_consumo': ['report_ml_mora_consumo_dly', 'report_ml_mora_consumo_renegociado_dly'],
        'ml_mora_cae': ['report_ml_mora_cae_dly'],
        'ml_mora_hipotecario': ['report_ml_mora_hipotecario_dly'],
        'ml_mora_comercial': ['report_ml_mora_comercial_dly'],
        'ml_nmd': ['report_ml_nmd_dly'],
        'ml_lc': ['report_ml_lc_dly'],
        'ml_inversiones': ['report_ml_inversiones_dly'],
        'ml_tc_cmr': ['report_ml_tc_cmr_dly'],
    }
    
    print("\n")
    print("=" * 80)
    print(" " * 25 + "RESUMEN DE EJECUCION")
    print("=" * 80)
    
    # Definir anchos de columna
    col_modelo = 30
    col_ejecucion = 15
    col_carga = 15
    
    # Encabezado
    if incluir_carga:
        encabezado = f"{'MODELO':<{col_modelo}} | {'EJECUCION':^{col_ejecucion}} | {'CARGA GCP':^{col_carga}}"
        separador = "-" * col_modelo + "-+-" + "-" * col_ejecucion + "-+-" + "-" * col_carga
    else:
        encabezado = f"{'MODELO':<{col_modelo}} | {'EJECUCION':^{col_ejecucion}}"
        separador = "-" * col_modelo + "-+-" + "-" * col_ejecucion
    
    print(encabezado)
    print(separador)
    
    # Contadores para resumen
    total_modelos = len(resultados_ejecucion)
    ejecuciones_exitosas = 0
    cargas_exitosas = 0
    total_tablas_cargadas = 0
    
    # Filas de datos
    for modelo, exito_ejecucion in resultados_ejecucion.items():
        nombre_modelo = orquestador.modelos.get(modelo, {}).get('nombre', modelo)
        
        # Estado de ejecución
        estado_ejecucion = "OK" if exito_ejecucion else "ERROR"
        if exito_ejecucion:
            ejecuciones_exitosas += 1
        
        if incluir_carga:
            # Determinar estado de carga para este modelo
            tablas_modelo = MODELO_A_TABLAS.get(modelo, [])
            
            if not exito_ejecucion:
                estado_carga = "NO EJECUTADO"
            elif not tablas_modelo:
                estado_carga = "SIN CONFIG"
            else:
                # Verificar si todas las tablas del modelo se cargaron correctamente
                cargas_tablas = [resultados_carga.get(tabla, False) for tabla in tablas_modelo]
                total_tablas_cargadas += len(tablas_modelo)
                
                if all(cargas_tablas):
                    estado_carga = "OK"
                    cargas_exitosas += sum(cargas_tablas)
                elif any(cargas_tablas):
                    estado_carga = "PARCIAL"
                    cargas_exitosas += sum(cargas_tablas)
                else:
                    estado_carga = "ERROR"
            
            fila = f"{nombre_modelo:<{col_modelo}} | {estado_ejecucion:^{col_ejecucion}} | {estado_carga:^{col_carga}}"
        else:
            fila = f"{nombre_modelo:<{col_modelo}} | {estado_ejecucion:^{col_ejecucion}}"
        
        print(fila)
    
    print(separador)
    
    # Resumen de totales
    print("\nTotales:")
    print(f"  Modelos ejecutados: {ejecuciones_exitosas}/{total_modelos}")
    if incluir_carga:
        print(f"  Tablas cargadas a GCP: {cargas_exitosas}/{total_tablas_cargadas}")
    
    # Estado final
    if incluir_carga:
        exito_total = (ejecuciones_exitosas == total_modelos) and (cargas_exitosas == total_tablas_cargadas)
    else:
        exito_total = ejecuciones_exitosas == total_modelos
    
    estado_final = "COMPLETADO EXITOSAMENTE" if exito_total else "COMPLETADO CON ERRORES"
    print(f"\nEstado final: {estado_final}")
    print("=" * 80)


def mostrar_tabla_consolidacion(resultados_consolidacion: dict):
    """
    Muestra una tabla resumen con el estado de consolidación histórica
    
    Args:
        resultados_consolidacion: Dict con resultados de consolidación {tabla: bool}
    """
    print("\n")
    print("=" * 80)
    print(" " * 20 + "RESUMEN DE CONSOLIDACION HISTORICA")
    print("=" * 80)
    
    # Definir anchos de columna
    col_tabla = 45
    col_estado = 18
    
    # Encabezado
    encabezado = f"{'TABLA DESTINO':<{col_tabla}} | {'CONSOLIDACION':^{col_estado}}"
    separador = "-" * col_tabla + "-+-" + "-" * col_estado
    
    print(encabezado)
    print(separador)
    
    # Contadores para resumen
    total_tablas = len(resultados_consolidacion)
    consolidaciones_exitosas = 0
    
    # Filas de datos
    for tabla, exito in resultados_consolidacion.items():
        estado = "OK" if exito else "ERROR"
        if exito:
            consolidaciones_exitosas += 1
        
        fila = f"{tabla:<{col_tabla}} | {estado:^{col_estado}}"
        print(fila)
    
    print(separador)
    
    # Resumen de totales
    print("\nTotales:")
    print(f"  Tablas consolidadas: {consolidaciones_exitosas}/{total_tablas}")
    
    # Estado final
    exito_total = consolidaciones_exitosas == total_tablas
    estado_final = "COMPLETADO EXITOSAMENTE" if exito_total else "COMPLETADO CON ERRORES"
    print(f"\nEstado final: {estado_final}")
    print("=" * 80)


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

    # Modo: Control de interfaces PML
    if args.control_interfaces is not None:
        from core.control_interfaces import ejecutar_control_interfaces
        tipos = None if "todos" in args.control_interfaces else args.control_interfaces
        print(f"\n{'='*60}")
        print("MODO: CONTROL DE INTERFACES PML")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"Tipos: {', '.join(t.upper() for t in tipos) if tipos else 'TODOS'}")
        print(f"{'='*60}")

        resultados = ejecutar_control_interfaces(fecha.date(), tipos=tipos)

        for tipo, res in resultados.items():
            n_crit = sum(1 for a in res.alertas if a.severidad == "CRITICAL")
            n_warn = sum(1 for a in res.alertas if a.severidad == "WARNING")
            print(f"\n  {tipo.upper()}: {len(res.comparacion)} grupos, "
                  f"{n_crit} CRITICAL, {n_warn} WARNING")
        return

    # Modo: Solo carga a GCP
    if args.solo_carga_gcp:
        print(f"\n{'='*60}")
        print("MODO: SOLO CARGA A GCP")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Expandir aliases (todos, primera_vuelta, segunda_vuelta)
        modelos_carga = expandir_modelos(args.solo_carga_gcp, orquestador, filtro_gcp=True)
        if modelos_carga != args.solo_carga_gcp:
            print(f"Expandiendo a: {', '.join(modelos_carga)}\n")
        
        resultados_carga = orquestador.cargar_modelos_gcp(modelos_carga, fecha)
        
        print("\n=== Resumen de carga a GCP ===")
        # Los resultados ahora vienen por tabla, no por modelo
        for tabla, exito in resultados_carga.items():
            estado = "ÉXITO" if exito else "ERROR"
            print(f"{tabla}: {estado}")
        return

    # Modo: Consolidar histórico
    if args.consolidar_historico:
        print(f"\n{'='*60}")
        print("MODO: CONSOLIDACION HISTORICA")
        print(f"Fecha: {fecha.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Expandir aliases (todos, primera_vuelta, segunda_vuelta)
        modelos_consolidar = expandir_modelos(args.consolidar_historico, orquestador, filtro_gcp=True)
        if modelos_consolidar != args.consolidar_historico:
            print(f"Expandiendo a: {', '.join(modelos_consolidar)}\n")
        
        resultados_consolidacion = orquestador.consolidar_historico_gcp(
            modelos_consolidar, fecha, force=args.force_historico
        )
        
        # Mostrar tabla resumen de consolidación
        mostrar_tabla_consolidacion(resultados_consolidacion)
        return

    if not args.modelos:
        print("Error: Debe especificar --modelos, --solo-carga-gcp o usar --listar")
        return

    modelos_a_ejecutar = expandir_modelos(args.modelos, orquestador)

    print(f"\nFecha de ejecución: {fecha.strftime('%Y-%m-%d')}")
    print(f"Modelos seleccionados: {', '.join(modelos_a_ejecutar)}")
    print(f"Cargar a GCP: {'Sí' if args.cargar_gcp else 'No'}")
    if args.forzar_recarga:
        print(f"Caché: DESACTIVADO (--forzar-recarga)")
        os.environ['CACHE_FORZAR_RECARGA'] = '1'
    else:
        os.environ.pop('CACHE_FORZAR_RECARGA', None)
    print()

    # Ejecutar modelos
    resultados = orquestador.ejecutar_modelos_paralelo(modelos_a_ejecutar, fecha)
    
    # Inicializar resultados de carga (vacío si no se carga a GCP)
    resultados_carga = {}
    
    # Cargar a GCP si se solicitó y hubo ejecuciones exitosas
    if args.cargar_gcp:
        modelos_exitosos = [modelo for modelo, exito in resultados.items() if exito]
        
        if modelos_exitosos:
            print(f"\n{'='*60}")
            print("Iniciando carga a GCP de modelos exitosos...")
            print(f"{'='*60}")
            
            resultados_carga = orquestador.cargar_modelos_gcp(modelos_exitosos, fecha)
        else:
            print("\nNo hay modelos exitosos para cargar a GCP")
    
    # Mostrar tabla resumen final
    mostrar_tabla_resumen(orquestador, resultados, resultados_carga, args.cargar_gcp)

    # F25: Generar reporte de ejecución y sincronizar a BigQuery
    if orquestador.reporte:
        orquestador.reporte.registrar_fin(resultados_carga_gcp=resultados_carga)
        json_path = orquestador.reporte.guardar()

        # Sincronizar a BigQuery (con fallback local si falla)
        from core.sync_reportes import sync_reporte_a_bigquery, sync_pendientes
        reporte_dict = orquestador.reporte.generar()
        sync_reporte_a_bigquery(reporte_dict, fecha.strftime("%Y%m%d"))

        # Reintentar pendientes anteriores (si hay)
        sync_pendientes()

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
  
  # Ejecutar primera vuelta (prepago consumo/hipotecario + 4 moras)
  python main.py --fecha 2025-11-28 --modelos primera_vuelta --cargar-gcp
  
  # Ejecutar segunda vuelta (prepago CMR, NMD, LC, inversiones)
  python main.py --fecha 2025-11-28 --modelos segunda_vuelta --cargar-gcp
  
  # Solo cargar modelos específicos a GCP (sin ejecutar)
  python main.py --fecha 2025-11-28 --solo-carga-gcp mr_prepago_consumo mr_prepago_hipotecario
  
  # Solo cargar segunda vuelta a GCP
  python main.py --fecha 2025-11-28 --solo-carga-gcp segunda_vuelta
  
  # Consolidar datos diarios en tablas históricas
  python main.py --fecha 2025-11-28 --consolidar-historico mr_prepago_consumo
  
  # Consolidar segunda vuelta en histórico
  python main.py --fecha 2025-11-28 --consolidar-historico segunda_vuelta
  
  # Consolidar TODOS los modelos en histórico
  python main.py --fecha 2025-11-28 --consolidar-historico todos
  
  # Aliases disponibles: todos, primera_vuelta, segunda_vuelta
  # Funcionan en --modelos, --solo-carga-gcp y --consolidar-historico
  
  # Control de interfaces PML (comparacion sumas t vs t-1)
  python main.py --fecha 2026-03-27 --control-interfaces
  python main.py --fecha 2026-03-27 --control-interfaces gcp
  python main.py --fecha 2026-03-27 --control-interfaces gcp cmr
  
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
    parser.add_argument('--consolidar-historico', type=str, nargs='+', metavar='MODELO',
                       help='Consolidar datos diarios en tablas históricas de BigQuery')
    parser.add_argument('--force-historico', action='store_true',
                       help='Permitir re-inserción en históricos: backup CSV + DELETE + INSERT')
    parser.add_argument('--forzar-recarga', action='store_true',
                       help='Ignorar cache parquet y leer directamente de Access')
    parser.add_argument('--control-interfaces', type=str, nargs='+', metavar='TIPO',
                       help='Ejecutar control de interfaces PML (gcp, cmr, o "todos").')
    parser.add_argument('--check-env', action='store_true',
                       help='Ejecutar diagnóstico del entorno y salir')
    args = parser.parse_args()

    # Inicializar logging estructurado (F11)
    fecha_log = args.fecha.replace('-', '') if args.fecha else None
    setup_logging(fecha_proceso=fecha_log)

    # Health check rápido (no requiere --fecha)
    if args.check_env:
        from tools.check_env import ejecutar_checks, imprimir_resultados, guardar_json
        resultados = ejecutar_checks(rapido=False)
        imprimir_resultados(resultados)
        guardar_json(resultados)
        return

    if args.gui:
        ejecutar_modo_gui()
    else:
        if not args.fecha:
            print("Error: En modo consola, --fecha es requerido")
            return
        ejecutar_modo_consola(args)

if __name__ == "__main__":
    main()