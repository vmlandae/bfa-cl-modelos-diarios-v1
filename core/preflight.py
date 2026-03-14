"""F13 — Pre-flight Checks: verificación rápida de dependencias antes de ejecutar modelos.

Verifica accesibilidad de rutas de red, archivos Access, parámetros Excel
y driver ODBC *antes* de lanzar la ejecución de modelos, de modo que los
errores se detecten en <10 segundos y no 5-10 minutos después.
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from core.logger import get_logger

logger = get_logger(__name__)

_CONFIG_EXT_YAML = Path(__file__).resolve().parent.parent / "config" / "config_rutas_ext_y_archivos.yaml"

# Timeout para verificar acceso a archivos de red (segundos)
_TIMEOUT_RED_SECS = 5


# ---------------------------------------------------------------------------
# Tipos de resultado
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """Resultado de un check individual."""
    nombre: str
    ok: bool
    detalle: str
    critico: bool = True


@dataclass
class PreflightReport:
    """Reporte consolidado de pre-flight por modelo."""
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks if c.critico)

    @property
    def errores_criticos(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.ok and c.critico]

    @property
    def warnings(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.ok and not c.critico]


# ---------------------------------------------------------------------------
# Checks individuales
# ---------------------------------------------------------------------------

def _check_ruta_red(ruta: str, nombre: str) -> CheckResult:
    """Verifica que una ruta UNC/absoluta sea accesible."""
    try:
        ok = os.path.exists(ruta)
        detalle = "Accesible" if ok else "No encontrada o inaccesible"
    except (OSError, PermissionError) as e:
        ok = False
        detalle = str(e)
    return CheckResult(
        nombre=nombre,
        ok=ok,
        detalle=f"{ruta} → {detalle}",
        critico=True,
    )


def _check_archivo(ruta: str, nombre: str, critico: bool = True) -> CheckResult:
    """Verifica que un archivo específico exista y sea legible."""
    path = Path(ruta)
    try:
        if not path.exists():
            return CheckResult(nombre=nombre, ok=False,
                               detalle=f"No existe: {ruta}", critico=critico)
        if not os.access(str(path), os.R_OK):
            return CheckResult(nombre=nombre, ok=False,
                               detalle=f"Sin permisos de lectura: {ruta}", critico=critico)
        size_kb = path.stat().st_size / 1024
        return CheckResult(nombre=nombre, ok=True,
                           detalle=f"OK ({size_kb:.0f} KB)", critico=critico)
    except (OSError, PermissionError) as e:
        return CheckResult(nombre=nombre, ok=False,
                           detalle=str(e), critico=critico)


def _check_odbc_driver() -> CheckResult:
    """Verifica que el driver ODBC de Access esté instalado."""
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        access_drivers = [d for d in drivers if "Access" in d]
        ok = len(access_drivers) > 0
        detalle = access_drivers[0] if ok else "No encontrado. Instalar AccessDatabaseEngine"
    except ImportError:
        ok = False
        detalle = "pyodbc no instalado"
    except Exception as e:
        ok = False
        detalle = f"Error: {e}"
    return CheckResult(
        nombre="Driver ODBC Access",
        ok=ok,
        detalle=detalle,
        critico=True,
    )


# ---------------------------------------------------------------------------
# Motor de pre-flight
# ---------------------------------------------------------------------------

def _cargar_config_ext() -> dict:
    """Carga y retorna el YAML de configuración externa."""
    with open(_CONFIG_EXT_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolver_ruta(ruta: str) -> Path:
    """Resuelve ruta absoluta o relativa a BASE_DIR."""
    from config.config_rutas import resolver_ruta
    return resolver_ruta(ruta)


def _checks_modelo(modelo_key: str, modelo_cfg_ext: dict,
                    modelo_cfg_orq: dict) -> List[CheckResult]:
    """Genera la lista de checks para un modelo específico.

    Examina la configuración del YAML para identificar qué recursos
    necesita el modelo (interfaz PML, Access DB, parámetros Excel,
    parámetros en red, etc.) y genera los checks correspondientes.
    """
    checks: List[CheckResult] = []
    vuelta = modelo_cfg_orq.get("vuelta", 0)
    nombre_modelo = modelo_cfg_orq.get("nombre", modelo_key)

    # --- 1. Interfaz PML (primera vuelta) ---
    interfaz = modelo_cfg_ext.get("interfaz_datos_input")
    if interfaz:
        checks.append(_check_ruta_red(
            interfaz,
            f"[{modelo_key}] Ruta interfaz PML",
        ))

    # --- 2. Access DB individual (ms_access_input) ---
    access_input = modelo_cfg_ext.get("ms_access_input")
    if access_input:
        checks.append(_check_archivo(
            access_input,
            f"[{modelo_key}] Access DB ({Path(access_input).name})",
        ))

    # --- 3. Access DB múltiples (ms_access_sources — inversiones) ---
    for source in modelo_cfg_ext.get("ms_access_sources", []):
        access_path = source.get("path", "")
        if access_path:
            checks.append(_check_archivo(
                access_path,
                f"[{modelo_key}] Access DB ({Path(access_path).name})",
            ))

    # --- 4. Parámetros Excel (locales y de red) ---
    for campo, valor in modelo_cfg_ext.items():
        if not campo.startswith("excel_parametros"):
            continue
        if isinstance(valor, str):
            ruta = _resolver_ruta(valor)
            es_red = valor.startswith("\\\\")
            checks.append(_check_archivo(
                str(ruta),
                f"[{modelo_key}] Parámetros ({Path(valor).name})",
                critico=True,
            ))

    # --- 5. Balance para cuadratura (inversiones) ---
    balance = modelo_cfg_ext.get("ruta_balance")
    if balance:
        checks.append(_check_archivo(
            balance,
            f"[{modelo_key}] Balance cuadratura ({Path(balance).name})",
            critico=False,
        ))

    return checks


def ejecutar_preflight(
    modelos_seleccionados: List[str],
    modelos_orquestador: Dict[str, dict],
) -> Dict[str, PreflightReport]:
    """Ejecuta pre-flight checks para los modelos seleccionados.

    Args:
        modelos_seleccionados: Lista de claves de modelos a verificar.
        modelos_orquestador: Diccionario ``self.modelos`` del orquestador.

    Returns:
        Diccionario {modelo_key: PreflightReport} con los resultados.
    """
    t0 = time.perf_counter()
    config_ext = _cargar_config_ext()
    modelos_ext = config_ext.get("modelos", {})

    reportes: Dict[str, PreflightReport] = {}

    # Check global: driver ODBC (si hay modelos que usan Access)
    necesita_access = any(
        modelos_ext.get(m, {}).get("ms_access_input") or
        modelos_ext.get(m, {}).get("ms_access_sources")
        for m in modelos_seleccionados
    )
    odbc_check: Optional[CheckResult] = None
    if necesita_access:
        odbc_check = _check_odbc_driver()

    # Deduplicar rutas de red para no verificar la misma ruta N veces
    rutas_verificadas: Dict[str, CheckResult] = {}

    for modelo_key in modelos_seleccionados:
        modelo_ext = modelos_ext.get(modelo_key, {})
        modelo_orq = modelos_orquestador.get(modelo_key, {})

        checks_modelo = _checks_modelo(modelo_key, modelo_ext, modelo_orq)

        # Deduplicar: si ya verificamos la misma ruta, reutilizar resultado
        checks_finales: List[CheckResult] = []
        for check in checks_modelo:
            # Extraer ruta del detalle para deduplicación
            ruta_key = check.detalle.split(" → ")[0] if " → " in check.detalle else check.detalle
            if ruta_key in rutas_verificadas:
                cached = rutas_verificadas[ruta_key]
                checks_finales.append(CheckResult(
                    nombre=check.nombre, ok=cached.ok,
                    detalle=cached.detalle, critico=check.critico,
                ))
            else:
                rutas_verificadas[ruta_key] = check
                checks_finales.append(check)

        # Agregar ODBC check si el modelo usa Access
        if odbc_check and (modelo_ext.get("ms_access_input") or
                           modelo_ext.get("ms_access_sources")):
            checks_finales.insert(0, odbc_check)

        reportes[modelo_key] = PreflightReport(checks=checks_finales)

    elapsed = time.perf_counter() - t0

    # --- Log resumen ---
    _log_resumen(reportes, elapsed)

    return reportes


def _log_resumen(reportes: Dict[str, PreflightReport], elapsed: float) -> None:
    """Imprime resumen de pre-flight al logger."""
    total_checks = sum(len(r.checks) for r in reportes.values())
    total_ok = sum(1 for r in reportes.values() for c in r.checks if c.ok)
    total_err = total_checks - total_ok
    todos_ok = all(r.ok for r in reportes.values())

    logger.info(f"\n{'─'*60}")
    logger.info(f"PRE-FLIGHT CHECKS ({elapsed:.1f}s)")
    logger.info(f"{'─'*60}")

    for modelo_key, reporte in reportes.items():
        if reporte.ok:
            logger.info(f"  ✅ {modelo_key}: todos los checks OK")
        else:
            errores = reporte.errores_criticos
            warns = reporte.warnings
            logger.warning(f"  ❌ {modelo_key}: {len(errores)} error(es) crítico(s)")
            for err in errores:
                logger.warning(f"     ⛔ {err.nombre}: {err.detalle}")
            for w in warns:
                logger.info(f"     ⚠️  {w.nombre}: {w.detalle}")

    logger.info(f"{'─'*60}")
    if todos_ok:
        logger.info(f"✅ Pre-flight OK — {total_checks} checks, {total_ok} OK ({elapsed:.1f}s)")
    else:
        logger.warning(f"⚠️  Pre-flight: {total_ok}/{total_checks} OK, {total_err} fallidos ({elapsed:.1f}s)")
    logger.info(f"{'─'*60}\n")


def filtrar_modelos_aptos(
    modelos_seleccionados: List[str],
    reportes: Dict[str, PreflightReport],
) -> List[str]:
    """Retorna solo los modelos que pasaron todos los checks críticos."""
    return [m for m in modelos_seleccionados if reportes.get(m, PreflightReport()).ok]
