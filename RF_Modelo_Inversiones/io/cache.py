"""
Sistema de Cache con Pickle para RF_Modelo_Inversiones.

Este módulo proporciona un sistema genérico de caché usando pickle que
reemplaza las múltiples funciones de cache en helpers.py:
- check_pickle_tablas_linkeadas()
- check_pickle_tablas_inversiones() 
- check_pickle_access_prod()
- ejecutar_query_access_con_cache()

Uso básico:
    from RF_Modelo_Inversiones.io.cache import cache_pickle
    
    # Con función extractora
    datos = cache_pickle(
        nombre_base='tablas_inversiones',
        fecha_proceso=20260131,
        data_path=Path('./data'),
        extractor=lambda: extraer_datos_de_access(),
    )

Autor: Modelos & Metodologías
Fecha: 2026-02
"""

import pickle
import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import TypeVar, Callable, Optional, Dict, Any, List, Union
from glob import glob

# Tipo genérico para el retorno del cache
T = TypeVar('T')


# =============================================================================
# FUNCIÓN PRINCIPAL DE CACHE
# =============================================================================

def cache_pickle(
    nombre_base: str,
    fecha_proceso: Union[int, str],
    data_path: Union[str, Path],
    extractor: Callable[[], T],
    forzar_recarga: bool = False,
    verbose: bool = True,
    max_archivos_cache: int = 5,
) -> T:
    """
    Sistema genérico de cache con pickle.
    
    Busca un archivo pickle existente con el patrón {nombre_base}_{fecha_proceso}_*.pkl.
    Si existe y forzar_recarga=False, lo carga y retorna.
    Si no existe (o forzar_recarga=True), ejecuta el extractor, guarda el resultado y lo retorna.
    
    Args:
        nombre_base: Nombre base para el archivo de cache (ej: 'tablas_inversiones')
        fecha_proceso: Fecha de proceso como int (YYYYMMDD) o string
        data_path: Directorio donde se guardan los archivos de cache
        extractor: Función sin argumentos que extrae/genera los datos
        forzar_recarga: Si True, ignora cache existente y regenera
        verbose: Si True, imprime mensajes informativos
        max_archivos_cache: Máximo de archivos de cache a mantener (elimina los más antiguos)
    
    Returns:
        Los datos cacheados o recién extraídos (tipo T, generalmente dict o DataFrame)
    
    Raises:
        Exception: Propaga cualquier excepción del extractor
    
    Example:
        >>> from RF_Modelo_Inversiones.io.cache import cache_pickle
        >>> datos = cache_pickle(
        ...     nombre_base='mi_cache',
        ...     fecha_proceso=20260131,
        ...     data_path=Path('./cache'),
        ...     extractor=lambda: {'key': 'value'},
        ... )
        Cargando cache: mi_cache_20260131_20260203_143022.pkl
        >>> datos
        {'key': 'value'}
    """
    data_path = Path(data_path)
    fecha_str = str(fecha_proceso)
    
    # Asegurar que el directorio existe
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Buscar archivos de cache existentes
    patron = f"{nombre_base}_{fecha_str}_*.pkl"
    archivos_existentes = sorted(
        data_path.glob(patron),
        key=lambda p: os.path.getctime(p),
        reverse=True  # Más reciente primero
    )
    
    # Si existe cache y no se fuerza recarga, cargar
    if archivos_existentes and not forzar_recarga:
        archivo_cache = archivos_existentes[0]
        if verbose:
            print(f"📂 Cargando cache: {archivo_cache.name}")
        
        try:
            with open(archivo_cache, 'rb') as f:
                datos = pickle.load(f)
            
            if verbose:
                _imprimir_info_datos(datos)
            
            return datos
        
        except Exception as e:
            warnings.warn(
                f"Error cargando cache {archivo_cache.name}: {e}. Regenerando...",
                UserWarning
            )
            # Continuar para regenerar
    
    # Extraer datos frescos
    if verbose:
        print(f"🔄 Extrayendo datos para: {nombre_base} (fecha={fecha_str})")
    
    datos = extractor()
    
    # Guardar nuevo cache
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{nombre_base}_{fecha_str}_{timestamp}.pkl"
    ruta_cache = data_path / nombre_archivo
    
    with open(ruta_cache, 'wb') as f:
        pickle.dump(datos, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    if verbose:
        print(f"💾 Cache guardado: {nombre_archivo}")
        _imprimir_info_datos(datos)
    
    # Limpiar archivos antiguos si hay demasiados
    _limpiar_cache_antiguos(data_path, nombre_base, fecha_str, max_archivos_cache, verbose)
    
    return datos


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def _imprimir_info_datos(datos: Any) -> None:
    """Imprime información sobre los datos cacheados."""
    if isinstance(datos, dict):
        print(f"   → {len(datos)} elementos en dict")
        for key in list(datos.keys())[:5]:  # Mostrar primeras 5 keys
            valor = datos[key]
            if hasattr(valor, '__len__'):
                print(f"      - {key}: {len(valor)} registros")
            else:
                print(f"      - {key}: {type(valor).__name__}")
        if len(datos) > 5:
            print(f"      ... y {len(datos) - 5} más")
    elif hasattr(datos, 'shape'):  # DataFrame/ndarray
        print(f"   → Shape: {datos.shape}")
    elif hasattr(datos, '__len__'):
        print(f"   → {len(datos)} elementos")


def _limpiar_cache_antiguos(
    data_path: Path, 
    nombre_base: str, 
    fecha_str: str,
    max_archivos: int,
    verbose: bool
) -> None:
    """Elimina archivos de cache antiguos si hay más del máximo permitido."""
    patron = f"{nombre_base}_{fecha_str}_*.pkl"
    archivos = sorted(
        data_path.glob(patron),
        key=lambda p: os.path.getctime(p),
        reverse=True
    )
    
    if len(archivos) > max_archivos:
        archivos_a_eliminar = archivos[max_archivos:]
        for archivo in archivos_a_eliminar:
            try:
                archivo.unlink()
                if verbose:
                    print(f"🗑️  Cache antiguo eliminado: {archivo.name}")
            except Exception as e:
                warnings.warn(f"No se pudo eliminar {archivo.name}: {e}")


def listar_caches(
    data_path: Union[str, Path],
    nombre_base: Optional[str] = None,
    fecha_proceso: Optional[Union[int, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Lista los archivos de cache disponibles.
    
    Args:
        data_path: Directorio donde buscar archivos de cache
        nombre_base: Filtrar por nombre base (opcional)
        fecha_proceso: Filtrar por fecha de proceso (opcional)
    
    Returns:
        Lista de dicts con info de cada archivo de cache:
        [{'archivo': Path, 'nombre_base': str, 'fecha': str, 'timestamp': str, 'size_mb': float}]
    
    Example:
        >>> caches = listar_caches('./cache')
        >>> for c in caches:
        ...     print(f"{c['nombre_base']}: {c['size_mb']:.2f} MB")
    """
    data_path = Path(data_path)
    
    if not data_path.exists():
        return []
    
    # Construir patrón de búsqueda
    if nombre_base and fecha_proceso:
        patron = f"{nombre_base}_{fecha_proceso}_*.pkl"
    elif nombre_base:
        patron = f"{nombre_base}_*.pkl"
    elif fecha_proceso:
        patron = f"*_{fecha_proceso}_*.pkl"
    else:
        patron = "*.pkl"
    
    archivos = list(data_path.glob(patron))
    resultado = []
    
    for archivo in archivos:
        try:
            # Parsear nombre: {nombre_base}_{fecha}_{timestamp}.pkl
            partes = archivo.stem.split('_')
            if len(partes) >= 3:
                # Asumir que las últimas 2 partes son timestamp (YYYYMMDD_HHMMSS)
                timestamp_str = '_'.join(partes[-2:])
                fecha_str = partes[-3] if len(partes) >= 3 else 'unknown'
                nombre = '_'.join(partes[:-3]) if len(partes) > 3 else partes[0]
            else:
                nombre = archivo.stem
                fecha_str = 'unknown'
                timestamp_str = 'unknown'
            
            resultado.append({
                'archivo': archivo,
                'nombre_base': nombre,
                'fecha': fecha_str,
                'timestamp': timestamp_str,
                'size_mb': archivo.stat().st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(os.path.getctime(archivo)),
            })
        except Exception:
            # Si no se puede parsear, incluir con info básica
            resultado.append({
                'archivo': archivo,
                'nombre_base': archivo.stem,
                'fecha': 'unknown',
                'timestamp': 'unknown',
                'size_mb': archivo.stat().st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(os.path.getctime(archivo)),
            })
    
    # Ordenar por fecha de creación (más reciente primero)
    resultado.sort(key=lambda x: x['created'], reverse=True)
    
    return resultado


def limpiar_caches(
    data_path: Union[str, Path],
    nombre_base: Optional[str] = None,
    fecha_proceso: Optional[Union[int, str]] = None,
    dias_antiguos: int = 30,
    verbose: bool = True,
) -> int:
    """
    Elimina archivos de cache antiguos.
    
    Args:
        data_path: Directorio donde buscar archivos de cache
        nombre_base: Filtrar por nombre base (opcional)
        fecha_proceso: Filtrar por fecha de proceso (opcional)
        dias_antiguos: Eliminar archivos más antiguos que N días
        verbose: Si True, imprime mensajes informativos
    
    Returns:
        Número de archivos eliminados
    
    Example:
        >>> eliminados = limpiar_caches('./cache', dias_antiguos=7)
        🗑️  Eliminados 3 archivos de cache antiguos
    """
    from datetime import timedelta
    
    data_path = Path(data_path)
    caches = listar_caches(data_path, nombre_base, fecha_proceso)
    
    fecha_limite = datetime.now() - timedelta(days=dias_antiguos)
    eliminados = 0
    
    for cache in caches:
        if cache['created'] < fecha_limite:
            try:
                cache['archivo'].unlink()
                eliminados += 1
                if verbose:
                    print(f"🗑️  Eliminado: {cache['archivo'].name}")
            except Exception as e:
                if verbose:
                    print(f"⚠️  No se pudo eliminar {cache['archivo'].name}: {e}")
    
    if verbose and eliminados > 0:
        print(f"🗑️  Total eliminados: {eliminados} archivos de cache")
    
    return eliminados


def invalidar_cache(
    data_path: Union[str, Path],
    nombre_base: str,
    fecha_proceso: Union[int, str],
    verbose: bool = True,
) -> int:
    """
    Invalida (elimina) todos los archivos de cache para un nombre y fecha específicos.
    
    Útil cuando los datos fuente han cambiado y se necesita regenerar el cache.
    
    Args:
        data_path: Directorio donde buscar archivos de cache
        nombre_base: Nombre base del cache a invalidar
        fecha_proceso: Fecha de proceso del cache a invalidar
        verbose: Si True, imprime mensajes informativos
    
    Returns:
        Número de archivos eliminados
    
    Example:
        >>> invalidar_cache('./cache', 'tablas_inversiones', 20260131)
        🗑️  Invalidado: tablas_inversiones_20260131_20260203_143022.pkl
        1
    """
    data_path = Path(data_path)
    patron = f"{nombre_base}_{fecha_proceso}_*.pkl"
    archivos = list(data_path.glob(patron))
    
    eliminados = 0
    for archivo in archivos:
        try:
            archivo.unlink()
            eliminados += 1
            if verbose:
                print(f"🗑️  Invalidado: {archivo.name}")
        except Exception as e:
            if verbose:
                print(f"⚠️  No se pudo invalidar {archivo.name}: {e}")
    
    return eliminados


# =============================================================================
# DECORADOR DE CACHE (OPCIONAL)
# =============================================================================

def cached(
    nombre_base: str,
    data_path: Union[str, Path],
    param_fecha: str = 'fecha_proceso',
    forzar_recarga_param: str = 'forzar_recarga',
):
    """
    Decorador para agregar cache automático a una función.
    
    La función decorada debe recibir un parámetro con la fecha de proceso.
    
    Args:
        nombre_base: Nombre base para los archivos de cache
        data_path: Directorio donde guardar los archivos
        param_fecha: Nombre del parámetro que contiene la fecha de proceso
        forzar_recarga_param: Nombre del parámetro para forzar recarga
    
    Example:
        >>> @cached('mi_funcion', './cache')
        ... def mi_funcion(fecha_proceso: int) -> dict:
        ...     # Lógica costosa
        ...     return {'dato': 'valor'}
        >>> 
        >>> resultado = mi_funcion(20260131)  # Primera vez: ejecuta y guarda
        >>> resultado = mi_funcion(20260131)  # Segunda vez: carga de cache
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            # Obtener fecha de proceso de los argumentos
            fecha = kwargs.get(param_fecha)
            if fecha is None and args:
                # Intentar obtener del primer argumento posicional
                fecha = args[0]
            
            if fecha is None:
                raise ValueError(
                    f"No se pudo obtener {param_fecha} de los argumentos. "
                    f"Asegúrate de pasar fecha_proceso como argumento."
                )
            
            forzar = kwargs.pop(forzar_recarga_param, False)
            
            return cache_pickle(
                nombre_base=nombre_base,
                fecha_proceso=fecha,
                data_path=data_path,
                extractor=lambda: func(*args, **kwargs),
                forzar_recarga=forzar,
            )
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator
