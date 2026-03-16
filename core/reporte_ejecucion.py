"""
Generador de reportes de ejecución estructurados (JSON + Markdown).

Recopila resultados de cada modelo, tiempos, errores y benchmark
para generar un reporte completo de la sesión de ejecución.

Uso típico (integrado en orquestador)::

    from core.reporte_ejecucion import ReporteEjecucion

    reporte = ReporteEjecucion(fecha)
    reporte.registrar_inicio()

    for modelo in modelos:
        reporte.registrar_modelo_inicio(modelo)
        ok = ejecutar(modelo)
        reporte.registrar_modelo_fin(modelo, ok, error=...)

    reporte.registrar_fin(resultados_carga_gcp={...})
    reporte.guardar()  # → reports/{YYYYMMDD}/reporte_ejecucion.json + .md
"""

import json
import platform
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
_BENCHMARK_FILE = BASE_DIR / "data" / "benchmark" / "historial.jsonl"


class ReporteEjecucion:
    """Acumula datos de una sesión de ejecución y genera reportes."""

    def __init__(self, fecha: datetime):
        self.fecha = fecha
        self.fecha_str = fecha.strftime("%Y%m%d")
        self.hostname = socket.gethostname()
        self.usuario = platform.node()
        self._inicio: Optional[float] = None
        self._fin: Optional[float] = None
        self._modelos: Dict[str, Dict[str, Any]] = {}
        self._carga_gcp: Dict[str, bool] = {}
        self._alertas: List[str] = []

    # ------------------------------------------------------------------
    # Registro de eventos
    # ------------------------------------------------------------------

    def registrar_inicio(self) -> None:
        """Marca el inicio de la sesión de ejecución."""
        self._inicio = time.time()

    def registrar_modelo_inicio(self, nombre_modelo: str) -> None:
        """Marca el inicio de ejecución de un modelo."""
        self._modelos[nombre_modelo] = {
            "inicio": time.time(),
            "inicio_ts": datetime.now().isoformat(timespec="seconds"),
        }

    def registrar_modelo_fin(
        self,
        nombre_modelo: str,
        exitoso: bool,
        error_msg: Optional[str] = None,
    ) -> None:
        """Marca el fin de ejecución de un modelo."""
        m = self._modelos.get(nombre_modelo, {})
        ahora = time.time()
        m["fin"] = ahora
        m["fin_ts"] = datetime.now().isoformat(timespec="seconds")
        m["duracion_seg"] = round(ahora - m.get("inicio", ahora), 2)
        m["status"] = "OK" if exitoso else "ERROR"
        if error_msg:
            m["error_msg"] = error_msg
            self._alertas.append(f"{nombre_modelo}: {error_msg[:200]}")
        self._modelos[nombre_modelo] = m

    def registrar_fin(self, resultados_carga_gcp: Optional[Dict[str, bool]] = None) -> None:
        """Marca el fin de la sesión y agrega resultados de carga GCP."""
        self._fin = time.time()
        if resultados_carga_gcp:
            self._carga_gcp = resultados_carga_gcp

    # ------------------------------------------------------------------
    # Benchmark
    # ------------------------------------------------------------------

    # Modelos por vuelta (debe coincidir con theme.MODELOS_CANONICOS)
    _VUELTA_1 = frozenset([
        "mr_prepago_consumo", "mr_prepago_hipotecario",
        "ml_mora_consumo", "ml_mora_cae",
        "ml_mora_hipotecario", "ml_mora_comercial",
    ])
    _VUELTA_2 = frozenset([
        "mr_prepago_cmr", "ml_nmd", "ml_lc", "ml_inversiones",
    ])

    @staticmethod
    def _clasificar_fase(modelos_keys: set[str]) -> str:
        """Clasifica un conjunto de modelos en primera_vuelta, segunda_vuelta o mixta."""
        if modelos_keys and modelos_keys <= ReporteEjecucion._VUELTA_1:
            return "primera_vuelta"
        if modelos_keys and modelos_keys <= ReporteEjecucion._VUELTA_2:
            return "segunda_vuelta"
        return "mixta"

    def _calcular_benchmark(self) -> Dict[str, Any]:
        """Calcula benchmark comparando con historial previo de la misma fase."""
        total_seg = round((self._fin or time.time()) - (self._inicio or 0), 2)
        por_modelo = {
            k: v.get("duracion_seg", 0) for k, v in self._modelos.items()
        }
        modelo_mas_lento = (
            max(por_modelo, key=por_modelo.get, default="N/A")
            if por_modelo else "N/A"
        )
        fase_actual = self._clasificar_fase(set(por_modelo.keys()))
        suma_modelos = sum(por_modelo.values())
        overhead_seg = round(total_seg - suma_modelos, 2)

        benchmark: Dict[str, Any] = {
            "total_seg": total_seg,
            "por_modelo": por_modelo,
            "modelo_mas_lento": modelo_mas_lento,
            "fase": fase_actual,
            "overhead_seg": overhead_seg,
        }

        if not _BENCHMARK_FILE.exists():
            return benchmark

        # Leer historial y filtrar por misma fase
        try:
            entradas_misma_fase: list[dict] = []
            with open(_BENCHMARK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    entry_modelos = set(entry.get("por_modelo", {}).keys())
                    entry_fase = entry.get("fase") or self._clasificar_fase(entry_modelos)
                    if entry_fase == fase_actual:
                        entradas_misma_fase.append(entry)
        except Exception:
            return benchmark

        if not entradas_misma_fase:
            return benchmark

        n_previas = len(entradas_misma_fase)
        benchmark["n_ejecuciones_previas"] = n_previas
        benchmark["fase_label"] = fase_actual

        # --- Comparación total (misma fase) ---
        totales_previos = [e.get("total_seg", 0) for e in entradas_misma_fase]
        promedio_total = sum(totales_previos) / len(totales_previos)
        benchmark["promedio_historico_seg"] = round(promedio_total, 2)
        if promedio_total > 0:
            diff_total_pct = round(((total_seg - promedio_total) / promedio_total) * 100, 1)
            benchmark["comparacion_vs_promedio"] = f"{diff_total_pct:+.1f}%"
            if diff_total_pct > 50:
                self._alertas.append(
                    f"Duración {fase_actual} {diff_total_pct:+.1f}% sobre promedio "
                    f"({total_seg:.0f}s vs {promedio_total:.0f}s, {n_previas} ejecuciones previas)"
                )

        # --- Comparación overhead (misma fase) ---
        overheads_previos = []
        for e in entradas_misma_fase:
            e_total = e.get("total_seg", 0)
            e_suma = sum(e.get("por_modelo", {}).values())
            overheads_previos.append(e_total - e_suma)
        if overheads_previos:
            prom_overhead = sum(overheads_previos) / len(overheads_previos)
            if prom_overhead > 0 and overhead_seg > 0:
                diff_oh_pct = round(((overhead_seg - prom_overhead) / prom_overhead) * 100, 1)
                if diff_oh_pct > 100:
                    self._alertas.append(
                        f"Overhead (pre/post ejecución) {diff_oh_pct:+.1f}% sobre promedio "
                        f"({overhead_seg:.0f}s vs {prom_overhead:.0f}s)"
                    )

        # --- Comparación por modelo ---
        alertas_modelos: list[str] = []
        for modelo_id, dur_actual in por_modelo.items():
            durs_previas = [
                e["por_modelo"][modelo_id]
                for e in entradas_misma_fase
                if modelo_id in e.get("por_modelo", {})
            ]
            if not durs_previas:
                continue
            prom_modelo = sum(durs_previas) / len(durs_previas)
            if prom_modelo > 0:
                diff_m_pct = round(((dur_actual - prom_modelo) / prom_modelo) * 100, 1)
                if diff_m_pct > 100:
                    alertas_modelos.append(
                        f"{modelo_id} {diff_m_pct:+.1f}% sobre promedio "
                        f"({dur_actual:.1f}s vs {prom_modelo:.1f}s)"
                    )
        if alertas_modelos:
            self._alertas.extend(alertas_modelos)

        return benchmark

    # ------------------------------------------------------------------
    # Generación del reporte
    # ------------------------------------------------------------------

    def generar(self) -> Dict[str, Any]:
        """Genera el dict completo del reporte."""
        modelos_ok = sum(1 for m in self._modelos.values() if m.get("status") == "OK")
        modelos_error = sum(1 for m in self._modelos.values() if m.get("status") == "ERROR")

        if modelos_error == 0 and modelos_ok > 0:
            status_global = "OK"
        elif modelos_ok > 0 and modelos_error > 0:
            status_global = "PARCIAL"
        elif modelos_ok == 0 and modelos_error > 0:
            status_global = "ERROR"
        else:
            status_global = "SIN_MODELOS"

        benchmark = self._calcular_benchmark()

        return {
            "version": "1.0",
            "fecha_proceso": self.fecha.strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "hostname": self.hostname,
            "status_global": status_global,
            "duracion_total_seg": benchmark["total_seg"],
            "modelos_ok": modelos_ok,
            "modelos_error": modelos_error,
            "modelos": self._modelos,
            "carga_gcp": self._carga_gcp,
            "benchmark": benchmark,
            "alertas": self._alertas,
        }

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def guardar(self) -> Path:
        """Guarda reporte JSON + MD + actualiza historial benchmark.

        Returns:
            Path al archivo JSON generado.
        """
        reporte = self.generar()

        # --- JSON ---
        report_dir = BASE_DIR / "reports" / self.fecha_str
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "reporte_ejecucion.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)

        # --- Markdown ---
        md_path = report_dir / "reporte_ejecucion.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._generar_markdown(reporte))

        # --- Benchmark historial (append JSONL) ---
        _BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "fecha": reporte["fecha_proceso"],
            "total_seg": reporte["duracion_total_seg"],
            "por_modelo": reporte["benchmark"]["por_modelo"],
            "fase": reporte["benchmark"].get("fase", "mixta"),
            "hostname": self.hostname,
            "status": reporte["status_global"],
        }
        with open(_BENCHMARK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"📊 Reporte guardado: {json_path}")
        logger.info(f"📊 Benchmark actualizado: {_BENCHMARK_FILE}")

        return json_path

    def _generar_markdown(self, reporte: Dict[str, Any]) -> str:
        """Genera versión Markdown legible del reporte."""
        lines = [
            f"# Reporte de Ejecución — {reporte['fecha_proceso']}",
            "",
            f"- **Timestamp:** {reporte['timestamp']}",
            f"- **Hostname:** {reporte['hostname']}",
            f"- **Status:** {reporte['status_global']}",
            f"- **Duración total:** {reporte['duracion_total_seg']:.1f}s",
            f"- **Modelos OK:** {reporte['modelos_ok']} | **Error:** {reporte['modelos_error']}",
            "",
            "## Detalle por Modelo",
            "",
            "| Modelo | Status | Duración (s) | Error |",
            "|---|---|---|---|",
        ]
        for nombre, datos in reporte["modelos"].items():
            err = datos.get("error_msg", "—")[:80]
            lines.append(
                f"| {nombre} | {datos.get('status', '?')} "
                f"| {datos.get('duracion_seg', 0):.1f} | {err} |"
            )

        if reporte["carga_gcp"]:
            lines += [
                "",
                "## Carga GCP",
                "",
                "| Tabla | Status |",
                "|---|---|",
            ]
            for tabla, ok in reporte["carga_gcp"].items():
                lines.append(f"| {tabla} | {'OK' if ok else 'ERROR'} |")

        bm = reporte["benchmark"]
        lines += [
            "",
            "## Benchmark",
            "",
            f"- **Total:** {bm['total_seg']:.1f}s",
            f"- **Modelo más lento:** {bm.get('modelo_mas_lento', 'N/A')}",
        ]
        if "promedio_historico_seg" in bm:
            lines.append(f"- **Promedio histórico:** {bm['promedio_historico_seg']:.1f}s ({bm.get('n_ejecuciones_previas', '?')} ejecuciones)")
            lines.append(f"- **vs promedio:** {bm.get('comparacion_vs_promedio', 'N/A')}")

        if reporte["alertas"]:
            lines += ["", "## Alertas", ""]
            for a in reporte["alertas"]:
                lines.append(f"- ⚠️ {a}")

        lines.append("")
        return "\n".join(lines)
