"""
Carga de archivo TXT de cartera CMR.

Lee el archivo ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT
desde el directorio local (data/) previamente copiado desde red.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


def ajustar_dia_habil(fecha: datetime) -> datetime:
    """
    Ajusta fecha a dia habil (retrocede si es fin de semana).

    Equivalente VBA:
        If Weekday(THISDAY) = 7 Then THISDAY = THISDAY - 1  ' Sabado
        If Weekday(THISDAY) = 1 Then THISDAY = THISDAY - 2  ' Domingo
    """
    dia_semana = fecha.weekday()  # 0=lunes, 6=domingo
    if dia_semana == 5:  # Sabado
        return fecha - timedelta(days=1)
    elif dia_semana == 6:  # Domingo
        return fecha - timedelta(days=2)
    return fecha


def buscar_archivo_cartera(ruta_base: Path, fecha_str: str) -> Path:
    """
    Busca archivo de cartera con extension .TXT o .txt (case insensitive).
    Retorna None si no se encuentra.
    """
    for ext in ['.TXT', '.txt']:
        ruta = ruta_base / f"ProductosMercadoLiquidezCMR{fecha_str}{ext}"
        if ruta.exists():
            return ruta
    return None


def cargar_cartera_txt(fecha_proceso: datetime, ruta_cartera: Path) -> pd.DataFrame:
    """
    Carga archivo TXT de cartera CMR.

    Args:
        fecha_proceso: Fecha de proceso (se ajusta a dia habil para buscar archivo)
        ruta_cartera: Directorio donde buscar el archivo TXT

    Returns:
        DataFrame con la cartera cargada (todas las columnas como str)
    """
    fecha_archivo = ajustar_dia_habil(fecha_proceso)
    fecha_str = fecha_archivo.strftime('%Y%m%d')

    ruta_archivo = buscar_archivo_cartera(ruta_cartera, fecha_str)

    if ruta_archivo is None:
        raise FileNotFoundError(
            f"No se encuentra archivo ProductosMercadoLiquidezCMR{fecha_str}.TXT/txt "
            f"en {ruta_cartera}"
        )

    print(f"        - Cargando: {ruta_archivo.name}")

    df = pd.read_csv(
        ruta_archivo,
        sep=';',
        encoding='latin-1',
        dtype=str,
        low_memory=False,
        na_values=[],
        keep_default_na=False
    )

    df.columns = df.columns.str.strip()
    print(f"        - Filas cargadas: {len(df):,}")

    return df
