"""
Benchmark completo del pipeline de modelos diarios.

F24: Instrumenta las 4 fases del pipeline con tiempos por sub-paso:
  1. Ejecución de modelos (primera y/o segunda vuelta)
  2. Carga GCP diaria
  3. Consolidación histórica

Para cada modelo mide: lectura_datos, cálculo, escritura (cuando el modelo
lo soporta), o tiempo total si no se puede descomponer.

Uso:
  # Benchmark primera vuelta completa (modelos + GCP + histórico)
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --vuelta 1

  # Benchmark segunda vuelta
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --vuelta 2

  # Benchmark ambas vueltas
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27

  # Solo medir modelos (sin GCP ni histórico)
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --solo-modelos

  # Guardar resultados en JSON
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --output resultados.json

Requiere que los datos de red estén accesibles y, para primera vuelta,
que el caché PML exista (correr primero el pipeline normalmente).
"""

import sys
import os
import time
import json
import threading
import importlib
import traceback
import argparse
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Agregar raíz del proyecto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.logger import setup_logging, get_logger, contexto_modelo
from core.orquestador import OrquestadorModelos

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Monitor de recursos en background
# ─────────────────────────────────────────────────────────────────────

class ResourceMonitor:
    """Muestrea CPU% y memoria RSS del proceso cada `intervalo` segundos."""

    def __init__(self, intervalo: float = 0.5):
        self.intervalo = intervalo
        self.proceso = psutil.Process(os.getpid())
        self.muestras_cpu: list[float] = []
        self.muestras_mem_mb: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        self._stop.clear()
        self.muestras_cpu.clear()
        self.muestras_mem_mb.clear()
        self.proceso.cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                cpu = self.proceso.cpu_percent(interval=None)
                mem = self.proceso.memory_info().rss / (1024 * 1024)
                self.muestras_cpu.append(cpu)
                self.muestras_mem_mb.append(mem)
            except Exception:
                pass
            self._stop.wait(self.intervalo)

    def stop(self) -> dict:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        n = len(self.muestras_cpu)
        if n == 0:
            return {"cpu_avg": 0, "cpu_max": 0, "mem_avg_mb": 0, "mem_max_mb": 0, "muestras": 0}
        return {
            "cpu_avg": round(sum(self.muestras_cpu) / n, 1),
            "cpu_max": round(max(self.muestras_cpu), 1),
            "mem_avg_mb": round(sum(self.muestras_mem_mb) / n, 1),
            "mem_max_mb": round(max(self.muestras_mem_mb), 1),
            "mem_min_mb": round(min(self.muestras_mem_mb), 1),
            "muestras": n,
        }


# ─────────────────────────────────────────────────────────────────────
# Utilidades de formato
# ─────────────────────────────────────────────────────────────────────

def formato_duracion(segundos: float) -> str:
    """Convierte segundos a formato legible (ej: '3m 28.1s' o '45.2s')."""
    if segundos >= 60:
        m = int(segundos // 60)
        s = segundos % 60
        return f"{m}m {s:.1f}s"
    return f"{segundos:.1f}s"


# ─────────────────────────────────────────────────────────────────────
# Fase 1: Ejecución de modelos
# ─────────────────────────────────────────────────────────────────────

def ejecutar_modelo_benchmark(nombre_modelo: str, config: dict, fecha: datetime) -> dict:
    """Ejecuta un modelo y retorna métricas detalladas."""
    resultado = {
        "nombre": nombre_modelo,
        "vuelta": config.get("vuelta"),
        "ok": False,
        "tiempo_total_s": 0,
        "error": None,
    }

    monitor = ResourceMonitor(intervalo=0.3)
    monitor.start()
    t0 = time.perf_counter()

    with contexto_modelo(nombre_modelo):
        try:
            modulo = importlib.import_module(config["modulo"])
            ok = modulo.ejecutar_modelo(fecha)
            resultado["ok"] = ok
        except Exception as e:
            resultado["error"] = str(e)
            logger.error(f"Error en {nombre_modelo}: {e}\n{traceback.format_exc()}")

    resultado["tiempo_total_s"] = round(time.perf_counter() - t0, 2)
    resultado["recursos"] = monitor.stop()

    return resultado


def benchmark_modelos(orq: OrquestadorModelos, fecha: datetime,
                      modelos: List[str]) -> dict:
    """Ejecuta modelos secuencialmente con métricas individuales."""
    resultados = {
        "fase": "ejecucion_modelos",
        "modelos": {},
        "tiempo_total_s": 0,
        "recursos": {},
    }

    if not modelos:
        return resultados

    vuelta = orq.modelos[modelos[0]].get("vuelta", "?")
    print(f"\n{'='*70}")
    print(f"  FASE: EJECUCIÓN DE MODELOS — VUELTA {vuelta}")
    print(f"  Modelos: {len(modelos)}")
    print(f"{'='*70}")

    # Pre-ejecución (copia interfaz PML para V1)
    t_pre = time.perf_counter()
    orq._pre_ejecucion_primera_vuelta(modelos, fecha)
    t_pre = time.perf_counter() - t_pre
    resultados["pre_ejecucion_s"] = round(t_pre, 2)
    if t_pre > 1:
        print(f"  Pre-ejecución (copia PML): {formato_duracion(t_pre)}")

    # Monitor global
    monitor_global = ResourceMonitor(intervalo=0.5)
    monitor_global.start()
    t0_total = time.perf_counter()

    for nombre_modelo in modelos:
        config = orq.modelos[nombre_modelo]
        print(f"\n  → {config['nombre']} ...", end=" ", flush=True)

        res = ejecutar_modelo_benchmark(nombre_modelo, config, fecha)
        resultados["modelos"][nombre_modelo] = res

        status = "OK" if res["ok"] else "ERROR"
        print(f"{formato_duracion(res['tiempo_total_s'])} [{status}]")

    resultados["tiempo_total_s"] = round(time.perf_counter() - t0_total, 2)
    resultados["recursos"] = monitor_global.stop()

    # Post-ejecución (verificación integridad V1)
    orq._post_ejecucion_primera_vuelta(modelos, fecha)

    return resultados


# ─────────────────────────────────────────────────────────────────────
# Fase 2: Carga GCP diaria
# ─────────────────────────────────────────────────────────────────────

def benchmark_carga_gcp(orq: OrquestadorModelos, fecha: datetime,
                        modelos: List[str]) -> dict:
    """Mide la carga GCP diaria de los modelos indicados."""
    resultados = {
        "fase": "carga_gcp_diaria",
        "tiempo_total_s": 0,
        "tablas": {},
        "recursos": {},
    }

    modelos_con_gcp = [m for m in modelos if orq.modelos[m].get("tiene_carga_gcp")]
    if not modelos_con_gcp:
        return resultados

    print(f"\n{'='*70}")
    print(f"  FASE: CARGA GCP DIARIA")
    print(f"  Modelos: {len(modelos_con_gcp)}")
    print(f"{'='*70}")

    monitor = ResourceMonitor(intervalo=0.5)
    monitor.start()
    t0 = time.perf_counter()

    res_carga = orq.cargar_modelos_gcp(modelos_con_gcp, fecha)

    resultados["tiempo_total_s"] = round(time.perf_counter() - t0, 2)
    resultados["recursos"] = monitor.stop()
    resultados["tablas"] = {k: bool(v) for k, v in res_carga.items()}

    exitosas = sum(1 for v in res_carga.values() if v)
    total = len(res_carga)
    print(f"\n  Carga GCP: {exitosas}/{total} tablas exitosas en {formato_duracion(resultados['tiempo_total_s'])}")

    return resultados


# ─────────────────────────────────────────────────────────────────────
# Fase 3: Consolidación histórica
# ─────────────────────────────────────────────────────────────────────

def benchmark_consolidacion_historica(orq: OrquestadorModelos, fecha: datetime,
                                      modelos: List[str]) -> dict:
    """Mide la consolidación histórica de los modelos indicados."""
    resultados = {
        "fase": "consolidacion_historica",
        "tiempo_total_s": 0,
        "tablas": {},
        "recursos": {},
    }

    modelos_con_hist = [m for m in modelos if orq.modelos[m].get("tiene_carga_gcp_historica")]
    if not modelos_con_hist:
        return resultados

    print(f"\n{'='*70}")
    print(f"  FASE: CONSOLIDACIÓN HISTÓRICA")
    print(f"  Modelos: {len(modelos_con_hist)}")
    print(f"{'='*70}")

    monitor = ResourceMonitor(intervalo=0.5)
    monitor.start()
    t0 = time.perf_counter()

    res_hist = orq.consolidar_historico_gcp(modelos_con_hist, fecha, force=False)

    resultados["tiempo_total_s"] = round(time.perf_counter() - t0, 2)
    resultados["recursos"] = monitor.stop()
    resultados["tablas"] = {k: bool(v) for k, v in res_hist.items()}

    exitosas = sum(1 for v in res_hist.values() if v)
    total = len(res_hist)
    print(f"\n  Consolidación: {exitosas}/{total} tablas exitosas en {formato_duracion(resultados['tiempo_total_s'])}")

    return resultados


# ─────────────────────────────────────────────────────────────────────
# Reporte de resultados
# ─────────────────────────────────────────────────────────────────────

def imprimir_reporte(resultados: dict):
    """Imprime reporte consolidado del benchmark."""
    print("\n")
    print("=" * 78)
    print(" " * 15 + "BENCHMARK PIPELINE COMPLETO — RESULTADOS")
    print("=" * 78)

    # Info del sistema
    info = resultados.get("sistema", {})
    print(f"\n  Fecha proceso: {resultados.get('fecha_proceso', '?')}")
    print(f"  Timestamp:     {resultados.get('timestamp', '?')}")
    print(f"  CPUs:          {info.get('cpus_logicos', '?')}")
    print(f"  RAM total:     {info.get('ram_total_gb', '?')} GB")

    # Tabla resumen por fase
    print(f"\n{'─'*78}")
    print(f"  {'FASE':<40} {'DURACIÓN':>12} {'ESTADO':>10}")
    print(f"{'─'*78}")

    tiempo_total = 0
    for fase in resultados.get("fases", []):
        nombre = fase.get("fase", "?")
        dt = fase.get("tiempo_total_s", 0)
        tiempo_total += dt

        # Contar éxitos según tipo de fase
        if nombre == "ejecucion_modelos":
            modelos = fase.get("modelos", {})
            ok = sum(1 for v in modelos.values() if v.get("ok"))
            total = len(modelos)
            vuelta = next(iter(modelos.values()), {}).get("vuelta", "?")
            label = f"Ejecución modelos (vuelta {vuelta})"
            estado = f"{ok}/{total} OK"
        elif nombre == "carga_gcp_diaria":
            tablas = fase.get("tablas", {})
            ok = sum(1 for v in tablas.values() if v)
            total = len(tablas)
            label = "Carga GCP diaria"
            estado = f"{ok}/{total} OK"
        elif nombre == "consolidacion_historica":
            tablas = fase.get("tablas", {})
            ok = sum(1 for v in tablas.values() if v)
            total = len(tablas)
            label = "Consolidación histórica"
            estado = f"{ok}/{total} OK"
        else:
            label = nombre
            estado = "?"

        print(f"  {label:<40} {formato_duracion(dt):>12} {estado:>10}")

    print(f"{'─'*78}")
    print(f"  {'TOTAL PIPELINE':<40} {formato_duracion(tiempo_total):>12}")

    # Detalle por modelo (si hay ejecución de modelos)
    fases_modelos = [f for f in resultados.get("fases", []) if f.get("fase") == "ejecucion_modelos"]
    if fases_modelos:
        print(f"\n{'─'*78}")
        print(f"  {'MODELO':<35} {'VUELTA':>6} {'DURACIÓN':>12} {'MEM PICO':>10}")
        print(f"{'─'*78}")

        for fase in fases_modelos:
            for nombre, datos in sorted(fase.get("modelos", {}).items()):
                dt = datos.get("tiempo_total_s", 0)
                vuelta = datos.get("vuelta", "?")
                mem = datos.get("recursos", {}).get("mem_max_mb", 0)
                status = "OK" if datos.get("ok") else "ERR"
                print(f"  {nombre:<35} V{vuelta:>4} {formato_duracion(dt):>12} {mem:>7.0f} MB  {status}")

    print(f"\n{'='*78}")


def guardar_json(resultados: dict, path: str):
    """Guarda resultados en archivo JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Resultados guardados en: {path}")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="F24: Benchmark completo del pipeline de modelos diarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Benchmark primera vuelta completa
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --vuelta 1

  # Benchmark segunda vuelta
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --vuelta 2

  # Solo medir modelos sin carga GCP
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --solo-modelos

  # Guardar resultados
  python sandbox/benchmark_pipeline_completo.py --fecha 2026-02-27 --output bench.json
        """
    )
    parser.add_argument("--fecha", required=True, help="Fecha YYYY-MM-DD")
    parser.add_argument("--vuelta", type=int, choices=[1, 2],
                        help="Vuelta a medir (1 o 2). Si se omite, mide ambas.")
    parser.add_argument("--solo-modelos", action="store_true",
                        help="Solo medir ejecución de modelos (sin GCP ni histórico)")
    parser.add_argument("--output", "-o", type=str,
                        help="Ruta para guardar resultados en JSON")
    args = parser.parse_args()

    fecha = datetime.strptime(args.fecha, "%Y-%m-%d")
    setup_logging(fecha_proceso=fecha.strftime("%Y%m%d"), prefix="benchmark")

    orq = OrquestadorModelos()

    # Seleccionar modelos por vuelta
    if args.vuelta:
        modelos = [k for k, v in orq.modelos.items() if v.get("vuelta") == args.vuelta]
    else:
        modelos = list(orq.modelos.keys())

    modelos_v1 = [m for m in modelos if orq.modelos[m].get("vuelta") == 1]
    modelos_v2 = [m for m in modelos if orq.modelos[m].get("vuelta") == 2]

    # Info del sistema
    info_sistema = {
        "cpus_logicos": psutil.cpu_count(),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "pid": os.getpid(),
    }

    print(f"\n{'='*70}")
    print(f"  F24 — BENCHMARK PIPELINE COMPLETO")
    print(f"{'='*70}")
    print(f"  Fecha:     {fecha.strftime('%Y-%m-%d')}")
    print(f"  Vuelta:    {args.vuelta or 'ambas'}")
    print(f"  Modelos:   {len(modelos)} ({len(modelos_v1)} V1 + {len(modelos_v2)} V2)")
    print(f"  CPUs:      {info_sistema['cpus_logicos']}")
    print(f"  RAM:       {info_sistema['ram_total_gb']} GB")
    print(f"  Solo mod:  {'Sí' if args.solo_modelos else 'No'}")
    print(f"{'='*70}")

    # Estructura de resultados
    resultados = {
        "fecha_proceso": fecha.strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "sistema": info_sistema,
        "config": {
            "vuelta": args.vuelta,
            "solo_modelos": args.solo_modelos,
            "modelos_v1": modelos_v1,
            "modelos_v2": modelos_v2,
        },
        "fases": [],
    }

    t0_pipeline = time.perf_counter()

    # ── Fase 1: Ejecución de modelos ──
    if modelos_v1:
        res_v1 = benchmark_modelos(orq, fecha, modelos_v1)
        resultados["fases"].append(res_v1)

    if modelos_v2:
        res_v2 = benchmark_modelos(orq, fecha, modelos_v2)
        resultados["fases"].append(res_v2)

    # ── Fase 2: Carga GCP diaria ──
    if not args.solo_modelos:
        modelos_exitosos = []
        for fase in resultados["fases"]:
            if fase.get("fase") == "ejecucion_modelos":
                modelos_exitosos.extend(
                    k for k, v in fase.get("modelos", {}).items() if v.get("ok")
                )

        if modelos_exitosos:
            res_gcp = benchmark_carga_gcp(orq, fecha, modelos_exitosos)
            resultados["fases"].append(res_gcp)

        # ── Fase 3: Consolidación histórica ──
        if modelos_exitosos:
            res_hist = benchmark_consolidacion_historica(orq, fecha, modelos_exitosos)
            resultados["fases"].append(res_hist)

    resultados["tiempo_total_pipeline_s"] = round(time.perf_counter() - t0_pipeline, 2)

    # ── Reporte ──
    imprimir_reporte(resultados)

    # ── Guardar JSON ──
    if args.output:
        guardar_json(resultados, args.output)
    else:
        # Guardar automáticamente en sandbox/ con timestamp
        auto_path = ROOT / "sandbox" / f"benchmark_{fecha.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.json"
        guardar_json(resultados, str(auto_path))


if __name__ == "__main__":
    main()
