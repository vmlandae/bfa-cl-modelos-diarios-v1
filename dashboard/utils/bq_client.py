"""Utilidades compartidas para conexión a BigQuery."""

import sys
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

from config import config_rutas as cr

PROJECT_ID = "bfa-cl-trade-price-report-dev"
DATASET_DLY = "bfa_cl_prd_financial_risk_dly_proc_models"
DATASET_HIST = "bfa_cl_prd_financial_risk_dly_proc_models_hist"


@st.cache_resource
def get_bq_client() -> bigquery.Client:
    """Crea y cachea el cliente de BigQuery usando la cuenta de servicio."""
    ruta_credenciales = cr.obtener_ruta_credenciales_gcp()
    credentials = service_account.Credentials.from_service_account_file(
        str(ruta_credenciales),
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=credentials)
