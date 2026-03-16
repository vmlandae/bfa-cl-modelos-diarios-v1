"""
Dashboard de Modelos Diarios — Entry point multi-page.

Ejecución:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar config
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

_DEPS_FALTANTES = []
try:
    import streamlit as st
except ImportError:
    _DEPS_FALTANTES.append("streamlit")

try:
    import plotly.graph_objects as go  # noqa: F401
except ImportError:
    _DEPS_FALTANTES.append("plotly")

try:
    from google.cloud import bigquery  # noqa: F401
    from google.oauth2 import service_account  # noqa: F401
except ImportError:
    _DEPS_FALTANTES.append("google-cloud-bigquery")

if _DEPS_FALTANTES:
    print(
        f"ERROR: Faltan dependencias para el dashboard: {', '.join(_DEPS_FALTANTES)}\n"
        f"Instalar con: pip install {' '.join(_DEPS_FALTANTES)}"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuración de página (DEBE ser la primera llamada de Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Modelos Diarios",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Navegación multi-page
# ---------------------------------------------------------------------------
home = st.Page("pages/1_Home.py", title="Home", icon="🏠", default=True)
logs = st.Page("pages/2_Logs.py", title="Logs", icon="📋")
comparacion = st.Page("pages/3_Comparacion.py", title="Comparación Outputs", icon="📊")
benchmark = st.Page("pages/4_Benchmark.py", title="Benchmark", icon="📈")
parametros = st.Page("pages/5_Parametros.py", title="Parámetros", icon="⚙️")

pg = st.navigation([home, logs, comparacion, benchmark, parametros])
pg.run()
