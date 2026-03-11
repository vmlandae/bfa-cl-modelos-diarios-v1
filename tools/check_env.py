"""
Diagnóstico de entorno para ejecución de modelos diarios.

Verifica que todas las dependencias, rutas de red, credenciales y
configuración estén disponibles antes de ejecutar los modelos.

Uso::

    python tools/check_env.py            # verificación completa
    python tools/check_env.py --rapido   # solo checks críticos (sin red)

Salida: resumen en consola + JSON en reports/health_check.json
"""

import importlib
import json
import os
import platform
import socket
import struct
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Directorio base del proyecto ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)

# ── Forzar UTF-8 en stdout (necesario para cmd.exe / cp1252) ─────────
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Colores ANSI para consola ────────────────────────────────────────
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _ok(msg: str) -> str:
    return f"  {_GREEN}[OK]{_RESET} {msg}"


def _fail(msg: str) -> str:
    return f"  {_RED}[FAIL]{_RESET} {msg}"


def _warn(msg: str) -> str:
    return f"  {_YELLOW}[WARN]{_RESET} {msg}"


# ── Checks individuales ──────────────────────────────────────────────

def check_python_version() -> dict:
    """Python >= 3.10 requerido."""
    v = sys.version_info
    ok = v >= (3, 10)
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    return {
        "nombre": "Python >= 3.10",
        "ok": ok,
        "detalle": f"{version_str} ({sys.executable})",
        "critico": True,
    }


def check_conda_env() -> dict:
    """Verifica que el env conda activo sea bfa-cl-modelos-v2."""
    env_name = os.environ.get("CONDA_DEFAULT_ENV", "")
    ok = env_name == "bfa-cl-modelos-v2"
    return {
        "nombre": "Conda env bfa-cl-modelos-v2",
        "ok": ok,
        "detalle": env_name if env_name else "(no hay conda env activo)",
        "critico": True,
    }


def check_dependencias_criticas() -> dict:
    """Importa las dependencias críticas del proyecto."""
    modulos = [
        "pandas", "numpy", "openpyxl", "yaml", "pyodbc",
        "google.cloud.bigquery", "scipy", "tqdm",
        "sqlalchemy", "sqlalchemy_access",
    ]
    faltantes = []
    for mod in modulos:
        try:
            importlib.import_module(mod)
        except ImportError:
            faltantes.append(mod)

    ok = len(faltantes) == 0
    detalle = "Todos presentes" if ok else f"Faltantes: {', '.join(faltantes)}"
    return {
        "nombre": "Dependencias Python críticas",
        "ok": ok,
        "detalle": detalle,
        "critico": True,
    }


def check_bfa_cl_utilidades() -> dict:
    """Verifica que bfa_cl_utilidades esté instalado."""
    try:
        importlib.import_module("bfa_cl_utilidades")
        ok = True
        detalle = "Instalado"
    except ImportError:
        ok = False
        detalle = "No instalado. Instalar desde Z:/RF_INSTALADORES/ o .whl incluido"
    return {
        "nombre": "bfa_cl_utilidades",
        "ok": ok,
        "detalle": detalle,
        "critico": True,
    }


def check_odbc_access() -> dict:
    """Verifica que el driver ODBC de Access esté disponible."""
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        access_drivers = [d for d in drivers if "Access" in d]
        ok = len(access_drivers) > 0
        detalle = access_drivers[0] if ok else "No hay driver Access. Instalar AccessDatabaseEngine"
    except Exception as e:
        ok = False
        detalle = f"Error al consultar drivers: {e}"
    return {
        "nombre": "Driver ODBC Microsoft Access",
        "ok": ok,
        "detalle": detalle,
        "critico": True,
    }


def check_credenciales_gcp() -> dict:
    """Verifica que el archivo de credenciales GCP exista y sea JSON válido."""
    cred_path = BASE_DIR / "credenciales" / "bfa-cl-trade-price-report-dev-9d137fc23b7f.json"
    if not cred_path.exists():
        return {
            "nombre": "Credenciales GCP",
            "ok": False,
            "detalle": f"No existe: {cred_path}",
            "critico": False,
        }
    try:
        with open(cred_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        email = data.get("client_email", "?")
        ok = "client_email" in data and "private_key" in data
        detalle = f"SA: {email}" if ok else "JSON incompleto"
    except json.JSONDecodeError:
        ok = False
        detalle = "Archivo no es JSON válido"
    return {
        "nombre": "Credenciales GCP",
        "ok": ok,
        "detalle": detalle,
        "critico": False,
    }


def check_config_yaml() -> dict:
    """Verifica que el YAML de configuración exista y se pueda parsear."""
    yaml_path = BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"
    if not yaml_path.exists():
        return {
            "nombre": "Config YAML",
            "ok": False,
            "detalle": f"No existe: {yaml_path.name}",
            "critico": True,
        }
    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        n_modelos = len(data.get("modelos", {}))
        return {
            "nombre": "Config YAML",
            "ok": True,
            "detalle": f"{n_modelos} modelos configurados",
            "critico": True,
        }
    except Exception as e:
        return {
            "nombre": "Config YAML",
            "ok": False,
            "detalle": str(e),
            "critico": True,
        }


def check_carpetas_proyecto() -> dict:
    """Verifica que las carpetas clave del proyecto existan."""
    carpetas = [
        "core", "config", "credenciales", "logs", "data",
        "procesamiento_datos_input", "carga_modelos_gcp",
        "RF_Modelo_Prepago_Consumo", "RF_Modelo_Prepago_Hipotecario",
        "RF_Modelo_Prepago_CMR", "RF_Modelo_Mora_Consumo",
        "RF_Modelo_Mora_CAE", "RF_Modelo_Mora_Hipotecario",
        "RF_Modelo_Mora_Comercial", "RF_Modelo_NMD",
        "RF_Modelo_Linea_de_Credito", "RF_Modelo_Inversiones",
    ]
    faltantes = [c for c in carpetas if not (BASE_DIR / c).is_dir()]
    ok = len(faltantes) == 0
    detalle = "Todas presentes" if ok else f"Faltantes: {', '.join(faltantes)}"
    return {
        "nombre": "Carpetas del proyecto",
        "ok": ok,
        "detalle": detalle,
        "critico": True,
    }


def check_parametros_json() -> dict:
    """Verifica que los archivos JSON de parámetros existan."""
    import yaml
    yaml_path = BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception:
        return {
            "nombre": "Parámetros JSON",
            "ok": False,
            "detalle": "No se pudo leer config YAML",
            "critico": False,
        }

    # Buscar archivos .json en subcarpetas parametros/
    modelos_dir = [d for d in BASE_DIR.iterdir() if d.is_dir() and d.name.startswith("RF_Modelo")]
    json_files = []
    for d in modelos_dir:
        param_dir = d / "parametros"
        if param_dir.exists():
            json_files.extend(param_dir.glob("*.json"))

    ok = len(json_files) > 0
    detalle = f"{len(json_files)} archivos JSON encontrados"
    return {
        "nombre": "Parámetros JSON de modelos",
        "ok": ok,
        "detalle": detalle,
        "critico": False,
    }


# ── Checks de red (pueden ser lentos) ────────────────────────────────

def check_ruta_red(ruta_unc: str, nombre: str) -> dict:
    """Verifica que una ruta UNC de red sea accesible."""
    ruta = Path(ruta_unc)
    try:
        ok = ruta.exists()
        detalle = "Accesible" if ok else "No accesible"
    except (OSError, PermissionError) as e:
        ok = False
        detalle = str(e)
    return {
        "nombre": f"Red: {nombre}",
        "ok": ok,
        "detalle": f"{ruta_unc[:60]}... → {detalle}",
        "critico": False,
    }


def check_rutas_red() -> list[dict]:
    """Verifica las rutas de red principales del YAML."""
    rutas_a_verificar = {
        "vmdvorak RF Folder": r"\\vmdvorak\Riesgo Financiero Folder\RRFF-GCP\Cartera\input",
        "vmdvorak RF2 Carteras": r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Carteras\INTERFAZ_DATOS",
        "vmdvorak RF2 Resultados": r"\\vmdvorak\Riesgo Financiero2\RF_PROCESOS\RF_Resultados",
        "Z: RF_INSTALADORES": r"Z:\RF_INSTALADORES",
    }
    resultados = []
    for nombre, ruta in rutas_a_verificar.items():
        resultados.append(check_ruta_red(ruta, nombre))
    return resultados


def check_bigquery_conexion() -> dict:
    """Intenta conectar a BigQuery y listar datasets."""
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account

        cred_path = BASE_DIR / "credenciales" / "bfa-cl-trade-price-report-dev-9d137fc23b7f.json"
        credentials = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        datasets = list(client.list_datasets(max_results=1))
        ok = True
        detalle = f"Conectado a proyecto {credentials.project_id}"
    except Exception as e:
        ok = False
        detalle = str(e)[:120]
    return {
        "nombre": "Conexión BigQuery",
        "ok": ok,
        "detalle": detalle,
        "critico": False,
    }


# ── Runner principal ─────────────────────────────────────────────────

def ejecutar_checks(rapido: bool = False) -> dict:
    """Ejecuta todos los checks y retorna resultados estructurados."""
    resultados = []

    # Checks locales (siempre)
    resultados.append(check_python_version())
    resultados.append(check_conda_env())
    resultados.append(check_dependencias_criticas())
    resultados.append(check_bfa_cl_utilidades())
    resultados.append(check_odbc_access())
    resultados.append(check_credenciales_gcp())
    resultados.append(check_config_yaml())
    resultados.append(check_carpetas_proyecto())
    resultados.append(check_parametros_json())

    # Checks de red (lentos, se omiten con --rapido)
    if not rapido:
        resultados.extend(check_rutas_red())
        resultados.append(check_bigquery_conexion())

    # Resumen
    total = len(resultados)
    ok_count = sum(1 for r in resultados if r["ok"])
    fail_count = total - ok_count
    criticos_fail = [r for r in resultados if not r["ok"] and r.get("critico")]

    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version,
        "modo": "rapido" if rapido else "completo",
        "resumen": {
            "total": total,
            "ok": ok_count,
            "errores": fail_count,
            "criticos_fallidos": len(criticos_fail),
        },
        "checks": resultados,
    }


def imprimir_resultados(resultados: dict) -> None:
    """Imprime los resultados en consola con colores."""
    print(f"\n{_BOLD}{_CYAN}=== Health Check -- Modelos Diarios ==={_RESET}")
    print(f"  Fecha: {resultados['timestamp']}")
    print(f"  Host:  {resultados['hostname']}")
    print(f"  Modo:  {resultados['modo']}\n")

    for check in resultados["checks"]:
        if check["ok"]:
            print(_ok(f"{check['nombre']}: {check['detalle']}"))
        else:
            etiqueta = "CRITICO" if check.get("critico") else "warning"
            print(_fail(f"{check['nombre']}: {check['detalle']} [{etiqueta}]"))

    resumen = resultados["resumen"]
    print(f"\n{_BOLD}Resumen: {resumen['ok']}/{resumen['total']} OK", end="")
    if resumen["errores"] > 0:
        print(f"  --  {_RED}{resumen['errores']} errores", end="")
        if resumen["criticos_fallidos"] > 0:
            print(f" ({resumen['criticos_fallidos']} criticos)", end="")
    print(f"{_RESET}\n")

    if resumen["criticos_fallidos"] > 0:
        print(f"{_RED}{_BOLD}!! HAY ERRORES CRITICOS. Resolver antes de ejecutar modelos.{_RESET}\n")


def guardar_json(resultados: dict) -> Path:
    """Guarda resultados en reports/health_check.json."""
    out_dir = BASE_DIR / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "health_check.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    return out_path


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Health check del entorno de modelos diarios")
    parser.add_argument("--rapido", action="store_true", help="Omitir checks de red y BigQuery")
    parser.add_argument("--json-only", action="store_true", help="Solo guardar JSON, sin output en consola")
    args = parser.parse_args()

    resultados = ejecutar_checks(rapido=args.rapido)

    if not args.json_only:
        imprimir_resultados(resultados)

    json_path = guardar_json(resultados)
    print(f"Reporte guardado en: {json_path.relative_to(BASE_DIR)}")

    # Exit code: 1 si hay errores críticos
    sys.exit(1 if resultados["resumen"]["criticos_fallidos"] > 0 else 0)


if __name__ == "__main__":
    main()
