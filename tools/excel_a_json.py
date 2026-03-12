"""
Herramienta de migración Excel → JSON para archivos de parámetros.

Convierte cada hoja del Excel en una entrada del JSON resultante.
Los DataFrames se serializan con orient='split' para preservar
tipos numéricos y estructura columnar de forma compacta.

Uso:
    python -m tools.excel_a_json                          # migra todos
    python -m tools.excel_a_json mr_prepago_consumo       # migra uno
    python -m tools.excel_a_json --check                  # solo verifica

Estructura JSON generada:
    {
        "_meta": { "source_excel": "...", "migrated_at": "...", "sha256_excel": "..." },
        "hojas": {
            "SMM_PREPAGO": { "columns": [...], "data": [[...], ...] },
            "ESCENARIO":   { "columns": [...], "data": [[...], ...] }
        }
    }
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

# Raíz del proyecto
_BASE_DIR = Path(__file__).resolve().parent.parent

# Catálogo: modelo → ruta relativa del Excel de parámetros
CATALOGO_PARAMETROS: Dict[str, str] = {
    "mr_prepago_consumo": "RF_Modelo_Prepago_Consumo/parametros/parametros_mr_prepago_consumo.xlsx",
    "mr_prepago_hipotecario": "RF_Modelo_Prepago_Hipotecario/parametros/parametros_mr_prepago_hipotecario.xlsx",
    "mr_prepago_cmr": "RF_Modelo_Prepago_CMR/parametros/parametros_mr_prepago_cmr.xlsx",
    "ml_mora_consumo": "RF_Modelo_Mora_Consumo/parametros/parametros_ml_mora_consumo.xlsx",
    "ml_mora_cae": "RF_Modelo_Mora_CAE/parametros/parametros_ml_mora_cae.xlsx",
    "ml_mora_hipotecario": "RF_Modelo_Mora_Hipotecario/parametros/parametros_ml_mora_hipotecario.xlsx",
    "ml_mora_comercial": "RF_Modelo_Mora_Comercial/parametros/parametros_ml_mora_comercial.xlsx",
    "ml_nmd": "RF_Modelo_NMD/parametros/parametros_ml_nmd.xlsx",
    "ml_lc": "RF_Modelo_Linea_de_Credito/parametros/parametros_ml_lc.xlsx",
}


def _sha256_file(path: Path) -> str:
    """Calcula SHA-256 de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _ruta_json_para(ruta_excel: Path) -> Path:
    """Genera la ruta del JSON al lado del Excel (mismo directorio, extensión .json)."""
    return ruta_excel.with_suffix(".json")


class _NumpyEncoder(json.JSONEncoder):
    """Serializa tipos numpy a nativos Python."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            return None if np.isnan(v) else v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def excel_a_json(ruta_excel: Path, ruta_json: Optional[Path] = None) -> Path:
    """
    Convierte un archivo Excel de parámetros a JSON.

    Cada hoja se almacena en formato split (columns + data) para ser
    reconstruible a DataFrame con pd.DataFrame(**hoja).

    Args:
        ruta_excel: Ruta al .xlsx de parámetros.
        ruta_json: Ruta de salida (por defecto: mismo nombre .json).

    Returns:
        Path del JSON generado.
    """
    ruta_excel = Path(ruta_excel)
    if not ruta_excel.exists():
        raise FileNotFoundError(f"Excel no encontrado: {ruta_excel}")

    ruta_json = ruta_json or _ruta_json_para(ruta_excel)

    xls = pd.ExcelFile(ruta_excel)
    hojas = {}
    for nombre_hoja in xls.sheet_names:
        df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja)
        hojas[nombre_hoja] = {
            "columns": list(df.columns),
            "data": df.values.tolist(),
        }

    resultado = {
        "_meta": {
            "source_excel": ruta_excel.name,
            "migrated_at": datetime.now().isoformat(timespec="seconds"),
            "sha256_excel": _sha256_file(ruta_excel),
            "hojas_count": len(hojas),
        },
        "hojas": hojas,
    }

    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, cls=_NumpyEncoder, ensure_ascii=False)

    size_kb = ruta_json.stat().st_size / 1024
    print(f"  ✓ {ruta_excel.name} → {ruta_json.name} ({size_kb:.0f} KB, {len(hojas)} hojas)")
    return ruta_json


def migrar_todos(modelos: Optional[list] = None):
    """Migra todos los modelos (o un subconjunto) de Excel a JSON."""
    nombres = modelos or list(CATALOGO_PARAMETROS.keys())
    print(f"Migrando parámetros Excel→JSON para {len(nombres)} modelo(s)...\n")

    for nombre in nombres:
        ruta_rel = CATALOGO_PARAMETROS.get(nombre)
        if not ruta_rel:
            print(f"  ✗ Modelo '{nombre}' no está en el catálogo")
            continue
        ruta_excel = _BASE_DIR / ruta_rel
        try:
            excel_a_json(ruta_excel)
        except Exception as e:
            print(f"  ✗ Error migrando {nombre}: {e}")

    print("\nMigración completada.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    migrar_todos(args if args else None)
