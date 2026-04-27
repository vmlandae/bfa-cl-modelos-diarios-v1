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

# Lista canónica de modelos (orden de ejecución)
MODELOS_CANONICOS = {
    "mr_prepago_consumo":     {"nombre": "Prepago Consumo",      "vuelta": 1},
    "mr_prepago_hipotecario": {"nombre": "Prepago Hipotecario",  "vuelta": 1},
    "mr_prepago_cmr":         {"nombre": "Prepago CMR",          "vuelta": 2},
    "ml_mora_consumo":        {"nombre": "Mora Consumo",         "vuelta": 1},
    "ml_mora_cae":            {"nombre": "Mora CAE",             "vuelta": 1},
    "ml_mora_hipotecario":    {"nombre": "Mora Hipotecario",     "vuelta": 1},
    "ml_mora_comercial":      {"nombre": "Mora Comercial",       "vuelta": 1},
    "ml_nmd":                 {"nombre": "NMD",                  "vuelta": 2},
    "ml_lc":                  {"nombre": "Línea de Crédito",     "vuelta": 2},
    "ml_inversiones":         {"nombre": "Inversiones",          "vuelta": 2},
    "mr_ssv":                 {"nombre": "SSV (EOM)",            "vuelta": 2},
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
