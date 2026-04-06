r"""
Control exploratorio de interfaces PML (GCP y CMR).

Reemplaza completamente el proceso legacy de
``PROCESOS_DIARIOS_MODELOS/main.py`` + macros VBA.

Realiza analisis de sumas de control, conteo de registros y comparacion
t vs t-1 para las interfaces ProductosMercadoLiquidez (GCP y CMR),
evalua umbrales de tolerancia por producto, genera un reporte HTML y lo
envia por email via Outlook COM.

Flujo principal::

    ejecutar_control_interfaces(fecha, tipos=["gcp", "cmr"])
        -> copiar archivos UNC -> local (con verificacion MD5)
        -> agrupar por SISTEMA/MONEDA (GCP) o SUBPRODUCTO (CMR)
        -> comparar sumas t vs t-1 (capital, interes, registros)
        -> evaluar umbrales de tolerancia por producto
        -> generar reporte HTML con tablas coloreadas
        -> enviar email via Outlook

Feature: F26 Fase 5
Autor: Modelos & Metodologias
Fecha: 2026-03
"""

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml

from core.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _BASE_DIR / "config" / "config_rutas_ext_y_archivos.yaml"
_CACHE_DIR = _BASE_DIR / "data" / "cache" / "raw"

MONEDA_MAP: Dict[str, str] = {"999": "CLP", "998": "CLF", "13": "USD"}
"""Mapeo de codigos numericos de moneda a nombres legibles."""

_CSV_SEP = ";"
_CSV_DECIMAL = ","

# Colores de severidad para tablas HTML
_COLORES = {
    "OK":       {"fondo": "#C8E6C9", "texto": "#1B5E20"},
    "WARNING":  {"fondo": "#FFF9C4", "texto": "#F57F17"},
    "CRITICAL": {"fondo": "#FFCDD2", "texto": "#B71C1C"},
}


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class InterfazConfig:
    """Configuracion de una interfaz especifica (GCP o CMR)."""
    patron_archivo: str
    patron_archivo_t1: str
    columnas: List[str]
    tipos_datos: Dict[str, str]
    agrupacion: List[str]
    asunto_template: str
    sistemas_vistas: List[str] = field(default_factory=list)


@dataclass
class UmbralesConfig:
    """Umbrales de tolerancia global y por producto."""
    default: Dict[str, float]
    gcp: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cmr: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class ControlInterfacesConfig:
    """Configuracion completa del modulo de control de interfaces."""
    enabled: bool
    ruta_unc_base: str
    destinatarios: List[str]
    modo: str
    auto_con_primera_vuelta: bool
    horario_esperado_cmr: str
    horario_esperado_gcp: str
    interfaces: Dict[str, InterfazConfig]
    umbrales: UmbralesConfig
    watcher_enabled: bool = False
    polling_intervalo_segundos: int = 300
    timeout_alerta_minutos: int = 90
    timeout_abortar_minutos: int = 180
    backup_enabled: bool = True
    backup_config: dict = field(default_factory=dict)


@dataclass
class Alerta:
    """Una alerta individual generada por el analisis."""
    producto: str
    moneda: str
    metrica: str       # "capital", "interes", "registros"
    severidad: str     # "OK", "WARNING", "CRITICAL"
    valor_t: float
    valor_t1: float
    diferencia: float
    pct_cambio: float
    diagnostico: Optional[str] = None


@dataclass
class ResultadoAnalisis:
    """Resultado del analisis de una interfaz."""
    tipo: str          # "gcp" o "cmr"
    fecha_t: str
    fecha_t1: str
    comparacion: pd.DataFrame
    alertas: List[Alerta] = field(default_factory=list)
    registros_t: int = 0
    registros_t1: int = 0
    ruta_t: Optional[Path] = None
    ruta_t1: Optional[Path] = None


# =============================================================================
# CARGA DE CONFIGURACION
# =============================================================================

def cargar_config_interfaces(
    config_path: Optional[Path] = None,
) -> ControlInterfacesConfig:
    """Carga la configuracion de ``control_interfaces`` desde el YAML.

    Args:
        config_path: Ruta al YAML.  Por defecto usa el del proyecto.

    Returns:
        ControlInterfacesConfig con toda la configuracion.

    Raises:
        ValueError: Si la seccion ``control_interfaces`` no existe.
    """
    ruta = config_path or _CONFIG_PATH
    with open(ruta, "r", encoding="utf-8") as f:
        cfg_full = yaml.safe_load(f) or {}

    cfg = cfg_full.get("control_interfaces", {})
    if not cfg:
        raise ValueError(
            "Seccion 'control_interfaces' no encontrada en "
            f"{ruta}"
        )

    # Parsear interfaces
    interfaces: Dict[str, InterfazConfig] = {}
    for nombre, icfg in cfg.get("interfaces", {}).items():
        interfaces[nombre] = InterfazConfig(
            patron_archivo=icfg["patron_archivo"],
            patron_archivo_t1=icfg["patron_archivo_t1"],
            columnas=icfg.get("columnas", []),
            tipos_datos=icfg.get("tipos_datos", {}),
            agrupacion=icfg.get("agrupacion", []),
            asunto_template=icfg.get("asunto_template", ""),
            sistemas_vistas=icfg.get("sistemas_vistas", []),
        )

    # Parsear umbrales
    umbrales_raw = cfg.get("umbrales", {})
    umbrales = UmbralesConfig(
        default=umbrales_raw.get("default", {}),
        gcp=umbrales_raw.get("gcp", {}),
        cmr=umbrales_raw.get("cmr", {}),
    )

    watcher = cfg.get("watcher", {})
    backup = cfg.get("backup", {})

    return ControlInterfacesConfig(
        enabled=cfg.get("enabled", True),
        ruta_unc_base=cfg.get("ruta_unc_base", ""),
        destinatarios=cfg.get("destinatarios", []),
        modo=cfg.get("modo", "send"),
        auto_con_primera_vuelta=cfg.get("auto_con_primera_vuelta", True),
        horario_esperado_cmr=cfg.get("horario_esperado_cmr", "09:00"),
        horario_esperado_gcp=cfg.get("horario_esperado_gcp", "10:00"),
        interfaces=interfaces,
        umbrales=umbrales,
        watcher_enabled=watcher.get("enabled", False),
        polling_intervalo_segundos=watcher.get("polling_intervalo_segundos", 300),
        timeout_alerta_minutos=watcher.get("timeout_alerta_minutos", 90),
        timeout_abortar_minutos=watcher.get("timeout_abortar_minutos", 180),
        backup_enabled=backup.get("enabled", True),
        backup_config=backup,
    )


# =============================================================================
# UTILIDADES (MD5, METADATA, FECHAS)
# =============================================================================

def _md5_archivo(ruta: Path, chunk_size: int = 8192) -> str:
    """Calcula hash MD5 de un archivo."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def _guardar_metadata(ruta_local: Path, checksum: str) -> None:
    """Guarda metadata JSON junto al archivo copiado."""
    meta_path = ruta_local.with_suffix(ruta_local.suffix + ".meta.json")
    meta = {
        "checksum_md5": checksum,
        "timestamp_copia": datetime.now().isoformat(),
        "tamanio_bytes": ruta_local.stat().st_size,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def _leer_metadata(ruta_local: Path) -> Optional[dict]:
    """Lee metadata JSON junto al archivo."""
    meta_path = ruta_local.with_suffix(ruta_local.suffix + ".meta.json")
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fecha_habil_anterior(fecha: date) -> date:
    """Retorna el dia habil anterior (salta fines de semana y feriados CL).

    Intenta usar ``bfa_cl_utilidades`` para feriados chilenos.
    Fallback: solo salta weekends.
    """
    try:
        from bfa_cl_utilidades import es_dia_laboral
        d = fecha - timedelta(days=1)
        while not es_dia_laboral(d):
            d -= timedelta(days=1)
        return d
    except ImportError:
        d = fecha - timedelta(days=1)
        while d.weekday() >= 5:  # 5=sabado, 6=domingo
            d -= timedelta(days=1)
        return d


# =============================================================================
# FASE 5.2: DETECCION DE ARCHIVOS + COPIA LOCAL
# =============================================================================

def _resolver_nombre_archivo(patron: str, fecha: date) -> str:
    """Aplica la fecha al patron de nombre de archivo.

    Ejemplo: ``"...GCP{fecha}.txt"`` con fecha 2026-03-27
    -> ``"...GCP20260327.txt"``
    """
    return patron.format(fecha=fecha.strftime("%Y%m%d"))


def obtener_rutas_archivos(
    tipo: str,
    fecha_t: date,
    config: ControlInterfacesConfig,
) -> Tuple[Path, Path, Path, Path]:
    """Resuelve rutas UNC y locales para archivos t y t-1.

    Returns:
        ``(ruta_unc_t, ruta_unc_t1, ruta_local_t, ruta_local_t1)``
    """
    icfg = config.interfaces[tipo]
    fecha_t1 = _fecha_habil_anterior(fecha_t)

    nombre_t = _resolver_nombre_archivo(icfg.patron_archivo, fecha_t)
    nombre_t1 = _resolver_nombre_archivo(icfg.patron_archivo_t1, fecha_t1)

    ruta_unc = Path(config.ruta_unc_base)
    ruta_unc_t = ruta_unc / nombre_t
    ruta_unc_t1 = ruta_unc / nombre_t1

    cache_dir = _CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    ruta_local_t = cache_dir / nombre_t
    ruta_local_t1 = cache_dir / nombre_t1

    return ruta_unc_t, ruta_unc_t1, ruta_local_t, ruta_local_t1


def verificar_disponibilidad(
    tipo: str,
    fecha_t: date,
    config: ControlInterfacesConfig,
) -> dict:
    """Verifica si los archivos existen en red y/o localmente.

    Returns:
        Dict con estado por periodo ("t", "t1"): nombre, rutas,
        existe_red, existe_local, md5_match.
    """
    ruta_unc_t, ruta_unc_t1, ruta_local_t, ruta_local_t1 = (
        obtener_rutas_archivos(tipo, fecha_t, config)
    )

    resultado = {}
    for label, ruta_unc, ruta_local in [
        ("t", ruta_unc_t, ruta_local_t),
        ("t1", ruta_unc_t1, ruta_local_t1),
    ]:
        info = {
            "nombre": ruta_unc.name,
            "ruta_unc": str(ruta_unc),
            "ruta_local": str(ruta_local),
            "existe_red": False,
            "existe_local": ruta_local.exists(),
            "md5_match": None,
        }
        try:
            info["existe_red"] = ruta_unc.exists()
        except OSError:
            logger.warning("No se pudo acceder a ruta UNC: %s", ruta_unc)

        if info["existe_red"] and info["existe_local"]:
            try:
                md5_red = _md5_archivo(ruta_unc)
                md5_local = _md5_archivo(ruta_local)
                info["md5_match"] = (md5_red == md5_local)
            except OSError as e:
                logger.warning("Error comparando MD5: %s", e)

        resultado[label] = info

    return resultado


def copiar_archivos_a_local(
    tipo: str,
    fecha_t: date,
    config: ControlInterfacesConfig,
) -> Tuple[Path, Path]:
    """Copia archivos t y t-1 desde UNC a local con verificacion MD5.

    Si el archivo local ya existe y coincide con red (MD5), no se re-copia.
    Si difiere, se hace backup del local y se re-copia.

    Returns:
        ``(ruta_local_t, ruta_local_t1)``

    Raises:
        FileNotFoundError: Si algun archivo no existe en red ni local.
    """
    ruta_unc_t, ruta_unc_t1, ruta_local_t, ruta_local_t1 = (
        obtener_rutas_archivos(tipo, fecha_t, config)
    )

    logger.info(
        "Copiando archivos de interfaz %s (fecha_t=%s)...",
        tipo.upper(), fecha_t.strftime("%Y%m%d"),
    )

    ruta_local_t = _copiar_un_archivo(ruta_unc_t, ruta_local_t, "t", tipo)
    ruta_local_t1 = _copiar_un_archivo(ruta_unc_t1, ruta_local_t1, "t-1", tipo)

    return ruta_local_t, ruta_local_t1


def _copiar_un_archivo(
    ruta_unc: Path,
    ruta_local: Path,
    label: str,
    tipo: str,
) -> Path:
    """Copia un archivo individual de UNC a local con logica MD5.

    - Si existe local y coincide con red -> no copia.
    - Si existe local y difiere -> backup + re-copia.
    - Si red no disponible pero hay local -> usa local con warning.
    - Si ni red ni local -> FileNotFoundError.
    """
    ruta_local.parent.mkdir(parents=True, exist_ok=True)

    # --- Caso: existe copia local ---
    if ruta_local.exists():
        checksum_local = _md5_archivo(ruta_local)

        try:
            red_disponible = ruta_unc.exists()
        except OSError:
            red_disponible = False

        if not red_disponible:
            logger.warning(
                "  [%s %s] Archivo de red no disponible (%s), "
                "usando copia local (md5=%s...)",
                tipo.upper(), label, ruta_unc.name, checksum_local[:8],
            )
            _guardar_metadata(ruta_local, checksum_local)
            return ruta_local

        try:
            checksum_red = _md5_archivo(ruta_unc)
        except OSError as e:
            logger.warning(
                "  [%s %s] No se pudo leer archivo de red: %s. "
                "Usando copia local (md5=%s...)",
                tipo.upper(), label, e, checksum_local[:8],
            )
            _guardar_metadata(ruta_local, checksum_local)
            return ruta_local

        if checksum_red == checksum_local:
            logger.info(
                "  [%s %s] Copia local vigente (md5=%s...): %s",
                tipo.upper(), label, checksum_local[:8], ruta_local.name,
            )
            _guardar_metadata(ruta_local, checksum_local)
            return ruta_local

        # MD5 difiere -> backup del local viejo y caer al bloque de copia
        ts = datetime.now().strftime("%H%M%S")
        ruta_backup = ruta_local.with_suffix(f".pre_{ts}.txt")
        shutil.copy2(str(ruta_local), str(ruta_backup))
        logger.warning(
            "\n%s\n"
            "  [!] ARCHIVO %s %s CAMBIO EN RED\n"
            "%s\n"
            "  Archivo   : %s\n"
            "  MD5 local : %s...\n"
            "  MD5 red   : %s...\n"
            "  Backup    : %s\n"
            "  Se usara la version nueva de la red.\n"
            "%s",
            "!" * 60, tipo.upper(), label, "!" * 60,
            ruta_local.name, checksum_local[:12], checksum_red[:12],
            ruta_backup.name, "!" * 60,
        )

    # --- Copiar desde red ---
    if not ruta_unc.exists():
        raise FileNotFoundError(
            f"Archivo de interfaz no encontrado en red: {ruta_unc} "
            f"(tampoco existe copia local en {ruta_local})"
        )

    t0 = time.perf_counter()
    shutil.copy2(str(ruta_unc), str(ruta_local))
    dt = time.perf_counter() - t0
    size_mb = ruta_local.stat().st_size / (1024 * 1024)
    checksum = _md5_archivo(ruta_local)
    _guardar_metadata(ruta_local, checksum)

    logger.info(
        "  [%s %s] Interfaz copiada: %s (%.1f MB, %.1fs, md5=%s...)",
        tipo.upper(), label, ruta_local.name, size_mb, dt, checksum[:8],
    )
    return ruta_local


# =============================================================================
# FASE 5.3: MOTOR DE ANALISIS
# =============================================================================

def _leer_interfaz(ruta: Path, icfg: InterfazConfig) -> pd.DataFrame:
    """Lee un archivo de interfaz PML con las columnas configuradas.

    Args:
        ruta: Ruta local al archivo .txt.
        icfg: Configuracion de la interfaz (columnas, tipos, etc.).

    Returns:
        DataFrame con las columnas seleccionadas y tipos aplicados.
    """
    dtype_map = {}
    for col, tipo in icfg.tipos_datos.items():
        if tipo == "str":
            dtype_map[col] = str
        # float se lee por defecto con decimal=','

    df = pd.read_csv(
        ruta,
        sep=_CSV_SEP,
        decimal=_CSV_DECIMAL,
        usecols=icfg.columnas,
        dtype=dtype_map,
    )

    # Limpiar espacios en columnas de texto
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    return df


def _agrupar_y_comparar(
    df_t: pd.DataFrame,
    df_t1: pd.DataFrame,
    cols_grupo: List[str],
) -> pd.DataFrame:
    """Agrupa ambos DataFrames y compara sumas de capital, interes y conteo.

    Realiza groupby + sum(AMORTIZACION, INTERES) + count, luego merge
    outer entre t y t-1, y calcula diferencias absolutas y porcentuales.

    Args:
        df_t: DataFrame del periodo t.
        df_t1: DataFrame del periodo t-1.
        cols_grupo: Columnas de agrupacion (ej: ["SISTEMA", "MONEDA_ORIGEN"]).

    Returns:
        DataFrame con columnas: *cols_grupo, CAPITAL_T, CAPITAL_T1,
        DIFF_CAPITAL, PCT_CAPITAL, INTERES_T, INTERES_T1, DIFF_INTERES,
        PCT_INTERES, REGISTROS_T, REGISTROS_T1, DIFF_REGISTROS,
        PCT_REGISTROS.
    """
    agg_spec = {
        "CAPITAL": ("AMORTIZACION", "sum"),
        "INTERES": ("INTERES", "sum"),
        "REGISTROS": ("AMORTIZACION", "count"),
    }

    agrupado_t = (
        df_t.groupby(cols_grupo, dropna=False)
        .agg(**agg_spec)
        .reset_index()
    )
    agrupado_t1 = (
        df_t1.groupby(cols_grupo, dropna=False)
        .agg(**agg_spec)
        .reset_index()
    )

    # Merge outer para capturar productos nuevos/desaparecidos
    comp = pd.merge(
        agrupado_t, agrupado_t1,
        on=cols_grupo, suffixes=("_T", "_T1"),
        how="outer",
    ).fillna(0)

    # Diferencias absolutas
    comp["DIFF_CAPITAL"] = comp["CAPITAL_T"] - comp["CAPITAL_T1"]
    comp["DIFF_INTERES"] = comp["INTERES_T"] - comp["INTERES_T1"]
    comp["DIFF_REGISTROS"] = comp["REGISTROS_T"] - comp["REGISTROS_T1"]

    # Variacion porcentual (evitar division por cero)
    for metrica in ("CAPITAL", "INTERES", "REGISTROS"):
        col_t1 = f"{metrica}_T1"
        col_pct = f"PCT_{metrica}"
        comp[col_pct] = comp.apply(
            lambda row, c1=col_t1, m=metrica: (
                (row[f"DIFF_{m}"] / row[c1] * 100)
                if row[c1] != 0
                else (100.0 if row[f"DIFF_{m}"] != 0 else 0.0)
            ),
            axis=1,
        )

    # Ordenar por primera columna de grupo
    comp = comp.sort_values(cols_grupo).reset_index(drop=True)

    return comp


def analizar_interfaz(
    tipo: str,
    fecha_t: date,
    config: ControlInterfacesConfig,
    ruta_t: Optional[Path] = None,
    ruta_t1: Optional[Path] = None,
) -> ResultadoAnalisis:
    """Ejecuta el analisis completo de una interfaz (GCP o CMR).

    Pasos:
    1. Si no se proporcionan rutas, copia archivos de UNC a local.
    2. Lee ambos archivos con las columnas configuradas.
    3. Agrupa y compara t vs t-1 (capital, interes, registros).
    4. Evalua umbrales y genera alertas.

    Args:
        tipo: ``"gcp"`` o ``"cmr"``.
        fecha_t: Fecha de proceso (t).
        config: Configuracion completa.
        ruta_t: Ruta local al archivo t (opcional, si ya se copio).
        ruta_t1: Ruta local al archivo t-1 (opcional).

    Returns:
        ResultadoAnalisis con la tabla de comparacion y alertas.
    """
    icfg = config.interfaces[tipo]
    fecha_t1 = _fecha_habil_anterior(fecha_t)
    fecha_t_str = fecha_t.strftime("%Y%m%d")
    fecha_t1_str = fecha_t1.strftime("%Y%m%d")

    logger.info(
        "Analizando interfaz %s: %s vs %s",
        tipo.upper(), fecha_t_str, fecha_t1_str,
    )

    # Paso 1: obtener archivos locales
    if ruta_t is None or ruta_t1 is None:
        ruta_t, ruta_t1 = copiar_archivos_a_local(tipo, fecha_t, config)

    # Paso 2: leer CSVs
    t0 = time.perf_counter()
    df_t = _leer_interfaz(ruta_t, icfg)
    df_t1 = _leer_interfaz(ruta_t1, icfg)
    dt_read = time.perf_counter() - t0

    logger.info(
        "  Leidos: %s=%s filas, %s=%s filas (%.1fs)",
        fecha_t_str, f"{len(df_t):,}",
        fecha_t1_str, f"{len(df_t1):,}",
        dt_read,
    )

    # Paso 3: agrupar y comparar
    comparacion = _agrupar_y_comparar(df_t, df_t1, icfg.agrupacion)

    # Paso 4: evaluar umbrales y generar alertas
    comparacion = evaluar_umbrales(comparacion, tipo, config)
    alertas = _generar_alertas(comparacion, tipo, icfg)

    n_warn = sum(1 for a in alertas if a.severidad == "WARNING")
    n_crit = sum(1 for a in alertas if a.severidad == "CRITICAL")
    if n_crit > 0:
        logger.warning(
            "  Resultado %s: %d CRITICAL, %d WARNING de %d grupos",
            tipo.upper(), n_crit, n_warn, len(comparacion),
        )
    elif n_warn > 0:
        logger.info(
            "  Resultado %s: %d WARNING de %d grupos (sin CRITICAL)",
            tipo.upper(), n_warn, len(comparacion),
        )
    else:
        logger.info(
            "  Resultado %s: todos los grupos dentro de tolerancia (%d grupos)",
            tipo.upper(), len(comparacion),
        )

    return ResultadoAnalisis(
        tipo=tipo,
        fecha_t=fecha_t_str,
        fecha_t1=fecha_t1_str,
        comparacion=comparacion,
        alertas=alertas,
        registros_t=len(df_t),
        registros_t1=len(df_t1),
        ruta_t=ruta_t,
        ruta_t1=ruta_t1,
    )


# =============================================================================
# FASE 5.4: EVALUACION DE UMBRALES
# =============================================================================

def _obtener_umbral(
    producto: str,
    tipo: str,
    config: ControlInterfacesConfig,
) -> Dict[str, float]:
    """Obtiene umbrales para un producto, con fallback a default.

    Busca primero en umbrales especificos del tipo (gcp/cmr) para el
    producto; si no existe, retorna los umbrales default.
    """
    umbrales_tipo = getattr(config.umbrales, tipo, {})
    if producto in umbrales_tipo:
        # Merge con default para completar campos faltantes
        merged = dict(config.umbrales.default)
        merged.update(umbrales_tipo[producto])
        return merged
    return dict(config.umbrales.default)


def evaluar_umbrales(
    comparacion: pd.DataFrame,
    tipo: str,
    config: ControlInterfacesConfig,
) -> pd.DataFrame:
    """Agrega columnas de severidad a la tabla de comparacion.

    Para cada fila (producto), evalua el |delta%| contra los umbrales
    configurados y asigna ``SEV_CAPITAL``, ``SEV_INTERES``,
    ``SEV_REGISTROS``.
    """
    icfg = config.interfaces[tipo]
    # La primera columna de agrupacion es el "producto" para buscar umbrales
    col_producto = icfg.agrupacion[0]

    severidades = {"SEV_CAPITAL": [], "SEV_INTERES": [], "SEV_REGISTROS": []}

    for _, row in comparacion.iterrows():
        producto = str(row[col_producto])
        umbral = _obtener_umbral(producto, tipo, config)

        for metrica, sev_col in [
            ("capital", "SEV_CAPITAL"),
            ("interes", "SEV_INTERES"),
            ("registros", "SEV_REGISTROS"),
        ]:
            pct_abs = abs(row.get(f"PCT_{metrica.upper()}", 0))
            critical_key = f"{metrica}_critical_pct"
            warning_key = f"{metrica}_warning_pct"

            if pct_abs >= umbral.get(critical_key, 15.0):
                severidades[sev_col].append("CRITICAL")
            elif pct_abs >= umbral.get(warning_key, 5.0):
                severidades[sev_col].append("WARNING")
            else:
                severidades[sev_col].append("OK")

    for col, valores in severidades.items():
        comparacion[col] = valores

    return comparacion


def _generar_alertas(
    comparacion: pd.DataFrame,
    tipo: str,
    icfg: InterfazConfig,
) -> List[Alerta]:
    """Genera lista de alertas para filas con severidad WARNING o CRITICAL."""
    alertas = []
    col_producto = icfg.agrupacion[0]
    # Determinar columna de moneda (si existe)
    col_moneda = "MONEDA_ORIGEN" if "MONEDA_ORIGEN" in icfg.agrupacion else ""

    for _, row in comparacion.iterrows():
        producto = str(row[col_producto])
        moneda = str(row.get(col_moneda, "")) if col_moneda else ""

        for metrica, sev_col in [
            ("capital", "SEV_CAPITAL"),
            ("interes", "SEV_INTERES"),
            ("registros", "SEV_REGISTROS"),
        ]:
            sev = row.get(sev_col, "OK")
            if sev in ("WARNING", "CRITICAL"):
                alertas.append(Alerta(
                    producto=producto,
                    moneda=MONEDA_MAP.get(moneda, moneda),
                    metrica=metrica,
                    severidad=sev,
                    valor_t=float(row.get(f"{metrica.upper()}_T", 0)),
                    valor_t1=float(row.get(f"{metrica.upper()}_T1", 0)),
                    diferencia=float(row.get(f"DIFF_{metrica.upper()}", 0)),
                    pct_cambio=float(row.get(f"PCT_{metrica.upper()}", 0)),
                ))

    return alertas


# =============================================================================
# FASE 5.6: GENERACION DE REPORTE HTML + ENVIO EMAIL
# =============================================================================

def _fmt_numero(valor: float, decimales: int = 0) -> str:
    """Formatea numero con separador de miles (punto) y decimal (coma).

    Ejemplo: 1234567.89 -> "1.234.568" (0 dec) o "1.234.567,89" (2 dec).
    """
    if decimales == 0:
        txt = f"{valor:,.0f}"
    else:
        txt = f"{valor:,.{decimales}f}"
    # Convertir formato ingles (1,234.56) a chileno (1.234,56)
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return txt


def _fmt_pct(valor: float) -> str:
    """Formatea porcentaje con signo y 1 decimal."""
    signo = "+" if valor > 0 else ""
    return f"{signo}{valor:.1f}%"


def _color_celda(severidad: str) -> str:
    """Retorna atributo CSS de color de fondo segun severidad."""
    colores = _COLORES.get(severidad, _COLORES["OK"])
    return (
        f'style="background-color:{colores["fondo"]};'
        f'color:{colores["texto"]};padding:4px 8px;"'
    )


def _construir_html_tabla_metrica(
    comparacion: pd.DataFrame,
    metrica: str,
    cols_grupo: List[str],
    titulo: str,
    moneda_filtro: Optional[str] = None,
) -> str:
    """Construye una tabla HTML para una metrica (capital/interes/registros).

    Args:
        comparacion: DataFrame con la comparacion completa.
        metrica: "CAPITAL", "INTERES" o "REGISTROS".
        cols_grupo: Columnas de grupo para las etiquetas de fila.
        titulo: Titulo de la tabla.
        moneda_filtro: Si se especifica, filtra por MONEDA_ORIGEN.

    Returns:
        Fragmento HTML con la tabla.
    """
    df = comparacion.copy()
    if moneda_filtro and "MONEDA_ORIGEN" in df.columns:
        df = df[df["MONEDA_ORIGEN"] == moneda_filtro]
    if df.empty:
        return ""

    # Determinar columna de etiqueta (primera columna de grupo excl. moneda)
    col_label = [c for c in cols_grupo if c != "MONEDA_ORIGEN"]
    if not col_label:
        col_label = cols_grupo
    label_col = col_label[0]

    col_t = f"{metrica}_T"
    col_t1 = f"{metrica}_T1"
    col_diff = f"DIFF_{metrica}"
    col_pct = f"PCT_{metrica}"
    col_sev = f"SEV_{metrica}"

    es_registros = metrica == "REGISTROS"

    # Encabezado
    html = f"""
    <h3 style="margin-top:16px;margin-bottom:4px;color:#37474F;">{titulo}</h3>
    <table style="border-collapse:collapse;font-family:Calibri,Arial,sans-serif;
                  font-size:11pt;min-width:500px;">
      <tr style="background-color:#546E7A;color:white;">
        <th style="padding:6px 10px;text-align:left;">Producto</th>
        <th style="padding:6px 10px;text-align:right;">Monto T</th>
        <th style="padding:6px 10px;text-align:right;">Monto T-1</th>
        <th style="padding:6px 10px;text-align:right;">{"Diferencia" if es_registros else "Diferencia (MM$)"}</th>
        <th style="padding:6px 10px;text-align:right;">Delta %</th>
      </tr>"""

    for _, row in df.iterrows():
        sev = row.get(col_sev, "OK")
        estilo = _color_celda(sev)
        label = str(row[label_col])

        val_t = row[col_t]
        val_t1 = row[col_t1]
        diff = row[col_diff]
        pct = row[col_pct]

        if es_registros:
            fmt_t = _fmt_numero(val_t)
            fmt_t1 = _fmt_numero(val_t1)
            fmt_diff = _fmt_numero(diff)
        else:
            # Montos en MM$ (dividir por 1_000_000)
            fmt_t = _fmt_numero(val_t / 1_000_000, 0)
            fmt_t1 = _fmt_numero(val_t1 / 1_000_000, 0)
            fmt_diff = _fmt_numero(diff / 1_000_000, 0)

        html += f"""
      <tr>
        <td {estilo}>{label}</td>
        <td {estilo} style="text-align:right;">{fmt_t}</td>
        <td {estilo} style="text-align:right;">{fmt_t1}</td>
        <td {estilo} style="text-align:right;">{fmt_diff}</td>
        <td {estilo} style="text-align:right;">{_fmt_pct(pct)}</td>
      </tr>"""

    html += "\n    </table>\n"
    return html


def _construir_html_gcp(
    resultado: ResultadoAnalisis,
    config: ControlInterfacesConfig,
) -> str:
    """Construye el HTML completo para el reporte GCP.

    Estructura: tablas de CAPITAL y de INTERES separadas por moneda
    (CLP, CLF, USD), mas tabla de CONTEO DE REGISTROS agrupado.
    """
    comp = resultado.comparacion
    cols_grupo = config.interfaces["gcp"].agrupacion

    # Traducir codigos de moneda a nombres
    if "MONEDA_ORIGEN" in comp.columns:
        comp["MONEDA_NOMBRE"] = comp["MONEDA_ORIGEN"].map(MONEDA_MAP).fillna(
            comp["MONEDA_ORIGEN"]
        )

    html = ""

    # Tablas de CAPITAL por moneda
    for cod_moneda, nombre_moneda in MONEDA_MAP.items():
        html += _construir_html_tabla_metrica(
            comp, "CAPITAL", cols_grupo,
            titulo=f"CAPITAL - {nombre_moneda}",
            moneda_filtro=cod_moneda,
        )

    # Tablas de INTERES por moneda
    for cod_moneda, nombre_moneda in MONEDA_MAP.items():
        html += _construir_html_tabla_metrica(
            comp, "INTERES", cols_grupo,
            titulo=f"INTERES - {nombre_moneda}",
            moneda_filtro=cod_moneda,
        )

    # Tabla de CONTEO DE REGISTROS (todas las monedas juntas)
    html += _construir_html_tabla_metrica(
        comp, "REGISTROS", cols_grupo,
        titulo="CONTEO DE REGISTROS",
    )

    return html


def _construir_html_cmr(
    resultado: ResultadoAnalisis,
    config: ControlInterfacesConfig,
) -> str:
    """Construye el HTML completo para el reporte CMR.

    CMR tiene SISTEMA=TC y MONEDA=999 constantes, asi que no se
    desglosa por moneda.  Filas = CODIGO_SUBPRODUCTO.
    """
    cols_grupo = config.interfaces["cmr"].agrupacion

    html = ""
    html += _construir_html_tabla_metrica(
        resultado.comparacion, "CAPITAL", cols_grupo,
        titulo="CAPITAL - CMR (CLP)",
    )
    html += _construir_html_tabla_metrica(
        resultado.comparacion, "INTERES", cols_grupo,
        titulo="INTERES - CMR (CLP)",
    )
    html += _construir_html_tabla_metrica(
        resultado.comparacion, "REGISTROS", cols_grupo,
        titulo="CONTEO DE REGISTROS - CMR",
    )
    return html


def construir_reporte_html(
    resultados: Dict[str, ResultadoAnalisis],
    config: ControlInterfacesConfig,
) -> str:
    """Construye el HTML completo del reporte de control de interfaces.

    Combina las secciones GCP y CMR en un solo documento HTML.

    Args:
        resultados: Dict ``{"gcp": ResultadoAnalisis, "cmr": ...}``.
        config: Configuracion completa.

    Returns:
        HTML completo listo para enviar por email.
    """
    # Tomar fechas del primer resultado disponible
    primer_res = next(iter(resultados.values()))
    fecha_t = primer_res.fecha_t
    fecha_t1 = primer_res.fecha_t1

    html = f"""
<html>
<head>
  <style>
    body {{ font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #212121; }}
    h2 {{ color: #1B5E20; border-bottom: 2px solid #1B5E20; padding-bottom: 4px; }}
    h3 {{ color: #37474F; }}
    .info {{ color: #616161; font-size: 10pt; margin-bottom: 8px; }}
    .alerta-resumen {{ margin: 12px 0; padding: 8px 12px; border-radius: 4px; }}
    .alerta-critical {{ background-color: #FFCDD2; color: #B71C1C; }}
    .alerta-warning {{ background-color: #FFF9C4; color: #F57F17; }}
    .alerta-ok {{ background-color: #C8E6C9; color: #1B5E20; }}
  </style>
</head>
<body>
  <h2>Control Exploratorio de Interfaces PML</h2>
  <p class="info">
    Fecha Proceso (T): <b>{fecha_t}</b> &nbsp;|&nbsp;
    Fecha Proceso (T-1): <b>{fecha_t1}</b> &nbsp;|&nbsp;
    Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}
  </p>
"""

    # Resumen de alertas
    todas_alertas = []
    for res in resultados.values():
        todas_alertas.extend(res.alertas)

    n_crit = sum(1 for a in todas_alertas if a.severidad == "CRITICAL")
    n_warn = sum(1 for a in todas_alertas if a.severidad == "WARNING")

    if n_crit > 0:
        html += (
            f'  <div class="alerta-resumen alerta-critical">'
            f'[!] {n_crit} alerta(s) CRITICAL, {n_warn} WARNING</div>\n'
        )
    elif n_warn > 0:
        html += (
            f'  <div class="alerta-resumen alerta-warning">'
            f'[*] {n_warn} alerta(s) WARNING (sin alertas criticas)</div>\n'
        )
    else:
        html += (
            '  <div class="alerta-resumen alerta-ok">'
            'Todos los grupos dentro de tolerancia</div>\n'
        )

    # Seccion GCP
    if "gcp" in resultados:
        res_gcp = resultados["gcp"]
        html += f"""
  <h2>Interfaz GCP</h2>
  <p class="info">
    Archivo T: {res_gcp.ruta_t.name if res_gcp.ruta_t else "N/A"} ({res_gcp.registros_t:,} filas)
    &nbsp;|&nbsp;
    Archivo T-1: {res_gcp.ruta_t1.name if res_gcp.ruta_t1 else "N/A"} ({res_gcp.registros_t1:,} filas)
  </p>
"""
        html += _construir_html_gcp(res_gcp, config)

    # Seccion CMR
    if "cmr" in resultados:
        res_cmr = resultados["cmr"]
        html += f"""
  <h2>Interfaz CMR</h2>
  <p class="info">
    Archivo T: {res_cmr.ruta_t.name if res_cmr.ruta_t else "N/A"} ({res_cmr.registros_t:,} filas)
    &nbsp;|&nbsp;
    Archivo T-1: {res_cmr.ruta_t1.name if res_cmr.ruta_t1 else "N/A"} ({res_cmr.registros_t1:,} filas)
  </p>
"""
        html += _construir_html_cmr(res_cmr, config)

    # Alertas detalladas
    alertas_no_ok = [a for a in todas_alertas if a.severidad != "OK"]
    if alertas_no_ok:
        html += '\n  <h2>Detalle de Alertas</h2>\n'
        html += (
            '  <table style="border-collapse:collapse;font-family:Calibri,Arial,sans-serif;'
            'font-size:10pt;">\n'
            '    <tr style="background-color:#546E7A;color:white;">\n'
            '      <th style="padding:4px 8px;">Severidad</th>\n'
            '      <th style="padding:4px 8px;">Producto</th>\n'
            '      <th style="padding:4px 8px;">Moneda</th>\n'
            '      <th style="padding:4px 8px;">Metrica</th>\n'
            '      <th style="padding:4px 8px;">Delta %</th>\n'
            '    </tr>\n'
        )
        for a in sorted(
            alertas_no_ok,
            key=lambda x: (0 if x.severidad == "CRITICAL" else 1, x.producto),
        ):
            estilo = _color_celda(a.severidad)
            html += (
                f'    <tr>\n'
                f'      <td {estilo}>{a.severidad}</td>\n'
                f'      <td {estilo}>{a.producto}</td>\n'
                f'      <td {estilo}>{a.moneda}</td>\n'
                f'      <td {estilo}>{a.metrica}</td>\n'
                f'      <td {estilo}>{_fmt_pct(a.pct_cambio)}</td>\n'
                f'    </tr>\n'
            )
        html += '  </table>\n'

    html += """
  <br>
  <p style="color:#9E9E9E;font-size:9pt;">
    Generado automaticamente por bfa-cl-modelos-diarios (F26 Fase 5).
  </p>
</body>
</html>"""

    return html


def enviar_reporte_interfaces(
    resultados: Dict[str, ResultadoAnalisis],
    config: ControlInterfacesConfig,
    destinatarios_override: Optional[List[str]] = None,
) -> None:
    """Genera el reporte HTML y lo envia via Outlook COM.

    Reutiliza ``core.email_report._enviar_outlook`` para el envio.

    Args:
        resultados: Dict ``{"gcp": ResultadoAnalisis, "cmr": ...}``.
        config: Configuracion completa.
        destinatarios_override: Lista de destinatarios (override del YAML).
    """
    from core.email_report import _enviar_outlook

    destinatarios = destinatarios_override or config.destinatarios
    if not destinatarios:
        logger.warning("No hay destinatarios configurados. No se envia email.")
        return

    # Construir HTML
    html = construir_reporte_html(resultados, config)

    # Determinar asunto (usar el del primer tipo disponible)
    primer_res = next(iter(resultados.values()))
    primer_tipo = primer_res.tipo
    icfg = config.interfaces[primer_tipo]
    asunto = icfg.asunto_template.format(fecha=primer_res.fecha_t)
    if len(resultados) > 1:
        asunto = f"Comparacion Interfaces PML (GCP + CMR) al {primer_res.fecha_t}"

    logger.info("Enviando reporte de control de interfaces a: %s", destinatarios)

    _enviar_outlook(
        destinatarios=destinatarios,
        asunto=asunto,
        cuerpo_html=html,
        adjuntos=[],
        imagenes_cid={},
        modo=config.modo,
    )

    logger.info("Reporte de control de interfaces enviado exitosamente.")


# =============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# =============================================================================

def ejecutar_control_interfaces(
    fecha: date,
    tipos: Optional[List[str]] = None,
    config: Optional[ControlInterfacesConfig] = None,
    destinatarios_override: Optional[List[str]] = None,
    enviar_email: bool = True,
) -> Dict[str, ResultadoAnalisis]:
    """Ejecuta el pipeline completo de control de interfaces.

    Pasos:
    1. Cargar configuracion (si no se proporciona).
    2. Para cada tipo solicitado (gcp, cmr):
       a. Copiar archivos de UNC a local (con MD5).
       b. Leer, agrupar, comparar t vs t-1.
       c. Evaluar umbrales y generar alertas.
    3. Generar y enviar reporte HTML via email.

    Args:
        fecha: Fecha de proceso (t).
        tipos: Lista de tipos a analizar (``["gcp", "cmr"]``).
            Default: todos los configurados.
        config: Configuracion (si None, se carga del YAML).
        destinatarios_override: Override de destinatarios.
        enviar_email: Si True, envia el reporte por email.

    Returns:
        Dict ``{tipo: ResultadoAnalisis}`` con los resultados.
    """
    if config is None:
        config = cargar_config_interfaces()

    if not config.enabled:
        logger.info("Control de interfaces deshabilitado en configuracion.")
        return {}

    if tipos is None:
        tipos = list(config.interfaces.keys())

    logger.info(
        "=" * 60 + "\n"
        "  CONTROL EXPLORATORIO DE INTERFACES PML\n"
        "  Fecha: %s | Tipos: %s\n" +
        "=" * 60,
        fecha.strftime("%Y-%m-%d"), ", ".join(t.upper() for t in tipos),
    )

    resultados: Dict[str, ResultadoAnalisis] = {}
    for tipo in tipos:
        if tipo not in config.interfaces:
            logger.warning("Tipo de interfaz '%s' no configurado. Saltando.", tipo)
            continue
        try:
            resultado = analizar_interfaz(tipo, fecha, config)
            resultados[tipo] = resultado
        except FileNotFoundError as e:
            logger.error("Error en interfaz %s: %s", tipo.upper(), e)
        except Exception:
            logger.exception("Error inesperado analizando interfaz %s", tipo.upper())

    if not resultados:
        logger.warning("No se obtuvieron resultados de ninguna interfaz.")
        return resultados

    # Enviar reporte
    if enviar_email:
        try:
            enviar_reporte_interfaces(
                resultados, config,
                destinatarios_override=destinatarios_override,
            )
        except Exception:
            logger.exception("Error enviando reporte de control de interfaces")

    return resultados
