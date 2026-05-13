"""Constantes de estilo y configuración compartida del dashboard."""

# Paleta de colores por estado de ejecución
STATUS_COLORS = {
    "OK": "#28a745",
    "PARCIAL": "#ffc107",
    "ERROR": "#dc3545",
    "SIN_MODELOS": "#6c757d",
}

STATUS_EMOJI = {
    "OK": "🟢",
    "PARCIAL": "🟡",
    "ERROR": "🔴",
    "SIN_MODELOS": "⚪",
}

# Lista canónica de modelos (orden de ejecución). Derivada de core.modelos_registry
# para evitar drift. Cuando se agregue un modelo solo se toca el registry.
from core.modelos_registry import listar_modelos, nombre_legible, vuelta as _vuelta

MODELOS_CANONICOS = {
    m: {"nombre": nombre_legible(m), "vuelta": _vuelta(m)}
    for m in listar_modelos()
}

# Niveles de log con colores
LOG_LEVEL_COLORS = {
    "DEBUG":    "#6c757d",
    "INFO":     "#0d6efd",
    "WARNING":  "#ffc107",
    "ERROR":    "#dc3545",
    "CRITICAL": "#842029",
}

LOG_LEVEL_EMOJI = {
    "DEBUG":    "⚪",
    "INFO":     "🔵",
    "WARNING":  "🟡",
    "ERROR":    "🔴",
    "CRITICAL": "🟣",
}
