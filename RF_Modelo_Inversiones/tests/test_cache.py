"""
Tests para RF_Modelo_Inversiones/io/cache.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_cache.py -v
"""

import pytest
import pickle
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict


# =============================================================================
# IMPORTS DEL MÓDULO A TESTEAR
# =============================================================================

from RF_Modelo_Inversiones.io.cache import (
    cache_pickle,
    listar_caches,
    limpiar_caches,
    invalidar_cache,
    cached,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Directorio temporal para tests de cache."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def sample_data():
    """Datos de ejemplo para cachear."""
    return {
        'tabla1': [1, 2, 3, 4, 5],
        'tabla2': {'a': 1, 'b': 2},
        'tabla3': 'texto de prueba',
    }


# =============================================================================
# TESTS DE cache_pickle
# =============================================================================

class TestCachePickle:
    """Tests para la función cache_pickle()."""
    
    def test_crear_cache_nuevo(self, temp_cache_dir, sample_data):
        """Verificar que se crea un archivo de cache nuevo."""
        resultado = cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        assert resultado == sample_data
        
        # Verificar que el archivo se creó
        archivos = list(temp_cache_dir.glob('test_cache_20260131_*.pkl'))
        assert len(archivos) == 1
    
    def test_cargar_cache_existente(self, temp_cache_dir, sample_data):
        """Verificar que se carga un cache existente."""
        contador_llamadas = [0]
        
        def extractor_con_contador():
            contador_llamadas[0] += 1
            return sample_data
        
        # Primera llamada: debe ejecutar extractor
        resultado1 = cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=extractor_con_contador,
            verbose=False,
        )
        
        # Segunda llamada: debe cargar de cache, no ejecutar extractor
        resultado2 = cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=extractor_con_contador,
            verbose=False,
        )
        
        assert resultado1 == resultado2
        assert contador_llamadas[0] == 1  # Solo se llamó una vez
    
    def test_forzar_recarga(self, temp_cache_dir, sample_data):
        """Verificar que forzar_recarga=True regenera el cache."""
        contador_llamadas = [0]
        
        def extractor_con_contador():
            contador_llamadas[0] += 1
            return sample_data
        
        # Primera llamada
        cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=extractor_con_contador,
            verbose=False,
        )
        
        # Segunda llamada con forzar_recarga=True
        cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=extractor_con_contador,
            forzar_recarga=True,
            verbose=False,
        )
        
        assert contador_llamadas[0] == 2  # Se llamó dos veces
    
    def test_fechas_diferentes_generan_caches_diferentes(self, temp_cache_dir, sample_data):
        """Verificar que fechas diferentes generan archivos de cache diferentes."""
        cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260201,
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        archivos = list(temp_cache_dir.glob('test_cache_*.pkl'))
        assert len(archivos) == 2
    
    def test_nombres_diferentes_generan_caches_diferentes(self, temp_cache_dir, sample_data):
        """Verificar que nombres diferentes generan archivos de cache diferentes."""
        cache_pickle(
            nombre_base='cache_tipo_a',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        cache_pickle(
            nombre_base='cache_tipo_b',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        archivos = list(temp_cache_dir.glob('*.pkl'))
        assert len(archivos) == 2
    
    def test_limpieza_cache_antiguos(self, temp_cache_dir, sample_data):
        """Verificar que se limpian caches antiguos cuando hay más del máximo."""
        # Crear 3 caches con max_archivos_cache=2
        for i in range(3):
            cache_pickle(
                nombre_base='test_cache',
                fecha_proceso=20260131,
                data_path=temp_cache_dir,
                extractor=lambda: sample_data,
                forzar_recarga=True,
                max_archivos_cache=2,
                verbose=False,
            )
            time.sleep(0.1)  # Pequeña pausa para timestamps diferentes
        
        archivos = list(temp_cache_dir.glob('test_cache_20260131_*.pkl'))
        assert len(archivos) <= 2
    
    def test_crea_directorio_si_no_existe(self, tmp_path, sample_data):
        """Verificar que se crea el directorio si no existe."""
        nuevo_dir = tmp_path / "nuevo" / "directorio" / "cache"
        assert not nuevo_dir.exists()
        
        cache_pickle(
            nombre_base='test_cache',
            fecha_proceso=20260131,
            data_path=nuevo_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        assert nuevo_dir.exists()
    
    def test_fecha_como_string(self, temp_cache_dir, sample_data):
        """Verificar que la fecha puede pasarse como string."""
        resultado = cache_pickle(
            nombre_base='test_cache',
            fecha_proceso='20260131',  # String en lugar de int
            data_path=temp_cache_dir,
            extractor=lambda: sample_data,
            verbose=False,
        )
        
        assert resultado == sample_data
        archivos = list(temp_cache_dir.glob('test_cache_20260131_*.pkl'))
        assert len(archivos) == 1
    
    def test_datos_dataframe(self, temp_cache_dir):
        """Verificar que funciona con DataFrames de pandas."""
        import pandas as pd
        
        df_original = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        
        resultado = cache_pickle(
            nombre_base='test_df',
            fecha_proceso=20260131,
            data_path=temp_cache_dir,
            extractor=lambda: df_original,
            verbose=False,
        )
        
        pd.testing.assert_frame_equal(resultado, df_original)
    
    def test_propaga_excepcion_de_extractor(self, temp_cache_dir):
        """Verificar que las excepciones del extractor se propagan."""
        def extractor_con_error():
            raise ValueError("Error intencional")
        
        with pytest.raises(ValueError, match="Error intencional"):
            cache_pickle(
                nombre_base='test_cache',
                fecha_proceso=20260131,
                data_path=temp_cache_dir,
                extractor=extractor_con_error,
                verbose=False,
            )


# =============================================================================
# TESTS DE listar_caches
# =============================================================================

class TestListarCaches:
    """Tests para la función listar_caches()."""
    
    def test_lista_vacia_si_no_hay_caches(self, temp_cache_dir):
        """Verificar que retorna lista vacía si no hay caches."""
        resultado = listar_caches(temp_cache_dir)
        assert resultado == []
    
    def test_lista_caches_existentes(self, temp_cache_dir, sample_data):
        """Verificar que lista los caches existentes."""
        # Crear algunos caches
        cache_pickle('cache_a', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        cache_pickle('cache_b', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        resultado = listar_caches(temp_cache_dir)
        assert len(resultado) == 2
    
    def test_filtrar_por_nombre_base(self, temp_cache_dir, sample_data):
        """Verificar que puede filtrar por nombre base."""
        cache_pickle('cache_a', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        cache_pickle('cache_b', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        resultado = listar_caches(temp_cache_dir, nombre_base='cache_a')
        assert len(resultado) == 1
        assert 'cache_a' in resultado[0]['nombre_base']
    
    def test_filtrar_por_fecha(self, temp_cache_dir, sample_data):
        """Verificar que puede filtrar por fecha."""
        cache_pickle('cache', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        cache_pickle('cache', 20260201, temp_cache_dir, lambda: sample_data, verbose=False)
        
        resultado = listar_caches(temp_cache_dir, fecha_proceso=20260131)
        assert len(resultado) == 1
    
    def test_incluye_tamaño_archivo(self, temp_cache_dir, sample_data):
        """Verificar que incluye el tamaño del archivo."""
        cache_pickle('cache', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        resultado = listar_caches(temp_cache_dir)
        assert 'size_mb' in resultado[0]
        assert resultado[0]['size_mb'] > 0
    
    def test_ordenado_por_fecha_creacion(self, temp_cache_dir, sample_data):
        """Verificar que los resultados están ordenados por fecha (más reciente primero)."""
        cache_pickle('cache_old', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        time.sleep(0.1)
        cache_pickle('cache_new', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        resultado = listar_caches(temp_cache_dir)
        assert resultado[0]['nombre_base'] == 'cache_new'


# =============================================================================
# TESTS DE invalidar_cache
# =============================================================================

class TestInvalidarCache:
    """Tests para la función invalidar_cache()."""
    
    def test_elimina_cache_especifico(self, temp_cache_dir, sample_data):
        """Verificar que elimina el cache especificado."""
        cache_pickle('cache', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        archivos_antes = list(temp_cache_dir.glob('cache_20260131_*.pkl'))
        assert len(archivos_antes) == 1
        
        eliminados = invalidar_cache(temp_cache_dir, 'cache', 20260131, verbose=False)
        
        archivos_despues = list(temp_cache_dir.glob('cache_20260131_*.pkl'))
        assert len(archivos_despues) == 0
        assert eliminados == 1
    
    def test_no_elimina_otros_caches(self, temp_cache_dir, sample_data):
        """Verificar que no elimina caches de otras fechas."""
        cache_pickle('cache', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        cache_pickle('cache', 20260201, temp_cache_dir, lambda: sample_data, verbose=False)
        
        invalidar_cache(temp_cache_dir, 'cache', 20260131, verbose=False)
        
        archivos = list(temp_cache_dir.glob('cache_*.pkl'))
        assert len(archivos) == 1  # Solo queda el de 20260201
    
    def test_retorna_cero_si_no_hay_cache(self, temp_cache_dir):
        """Verificar que retorna 0 si no hay cache para invalidar."""
        eliminados = invalidar_cache(temp_cache_dir, 'inexistente', 20260131, verbose=False)
        assert eliminados == 0


# =============================================================================
# TESTS DE limpiar_caches
# =============================================================================

class TestLimpiarCaches:
    """Tests para la función limpiar_caches()."""
    
    def test_no_elimina_caches_recientes(self, temp_cache_dir, sample_data):
        """Verificar que no elimina caches recientes."""
        cache_pickle('cache', 20260131, temp_cache_dir, lambda: sample_data, verbose=False)
        
        eliminados = limpiar_caches(temp_cache_dir, dias_antiguos=30, verbose=False)
        
        assert eliminados == 0
        archivos = list(temp_cache_dir.glob('*.pkl'))
        assert len(archivos) == 1


# =============================================================================
# TESTS DE DECORADOR @cached
# =============================================================================

class TestCachedDecorator:
    """Tests para el decorador @cached."""
    
    def test_decorador_funciona(self, temp_cache_dir, sample_data):
        """Verificar que el decorador funciona básicamente."""
        contador = [0]
        
        @cached('test_func', temp_cache_dir)
        def mi_funcion(fecha_proceso: int) -> dict:
            contador[0] += 1
            return sample_data
        
        # Primera llamada
        resultado1 = mi_funcion(20260131)
        # Segunda llamada (debe usar cache)
        resultado2 = mi_funcion(20260131)
        
        assert resultado1 == resultado2
        assert contador[0] == 1  # Solo se ejecutó una vez
    
    def test_decorador_forzar_recarga(self, temp_cache_dir, sample_data):
        """Verificar que el decorador soporta forzar_recarga."""
        contador = [0]
        
        @cached('test_func', temp_cache_dir)
        def mi_funcion(fecha_proceso: int) -> dict:
            contador[0] += 1
            return sample_data
        
        mi_funcion(20260131)
        mi_funcion(20260131, forzar_recarga=True)
        
        assert contador[0] == 2  # Se ejecutó dos veces


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
