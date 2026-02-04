"""
Tests para RF_Modelo_Inversiones/pipeline/haircut.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_haircut.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from RF_Modelo_Inversiones.pipeline.haircut import (
    generar_cartera_haircut,
    generar_haircut_dia,
    agregar_dia_semana,
    combinar_haircut_con_pactos,
    filtrar_monto_liquidar,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_cartera_pond():
    """DataFrame simulando cartera ponderada."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 4,
        'Instrumento': ['BCP', 'BCP', 'BTP', 'BTP'],
        'Nemotecnico': ['BCP001', 'BCP002', 'BTP001', 'BTP002'],
        'Dias_Vcto': [30, 90, 180, 365],
        'Ponderador': [0.25, 0.25, 0.25, 0.25],
    })


@pytest.fixture
def df_factores():
    """DataFrame simulando tabla de factores."""
    return pd.DataFrame({
        'Desde': [0, 31, 91, 181],
        'Hasta': [30, 90, 180, 365],
        'Dia': [1, 2, 3, 4],
        'Factor': [0.001, 0.002, 0.003, 0.004],
    })


@pytest.fixture
def df_fpl():
    """DataFrame simulando Floor Piso Liquidez."""
    return pd.DataFrame({
        'Instrumento': ['Gobierno CLP', 'Gobierno UF', 'LCH', 'BBC'],
        'Haircut': [0.0015, 0.002, 0.0025, 0.003],
    })


@pytest.fixture
def df_cartera_hc():
    """DataFrame simulando cartera con haircut."""
    return pd.DataFrame({
        'Dia': [1, 1, 2, 2, 3, 3],
        'FactorPond': [0.001, 0.002, 0.003, 0.004, 0.005, 0.006],
    })


@pytest.fixture
def df_haircut_dia():
    """DataFrame con haircut por día."""
    return pd.DataFrame({
        'Dia': [1, 2, 3, 4, 5],
        'Haircut': [0.01, 0.02, 0.03, 0.04, 0.05],
    })


@pytest.fixture
def df_haircut_dia_sem():
    """DataFrame con haircut y día de semana."""
    return pd.DataFrame({
        'Dia': [1, 2, 3, 4, 5],
        'DiaSem': [1, 2, 3, 4, 5],  # Lunes a Viernes
        'Haircut': [0.01, 0.02, 0.03, 0.04, 0.05],
    })


@pytest.fixture
def df_monto_plazo_pacto():
    """DataFrame con montos por plazo de pacto."""
    return pd.DataFrame({
        'Dias_Pacto': [2, 5],
        'Monto': [1000.0, 2000.0],
    })


@pytest.fixture
def df_montos_liq():
    """DataFrame con montos a liquidar."""
    return pd.DataFrame({
        'Instrumento': ['Gobierno CLP', 'Gobierno UF', 'LCH'],
        'Monto Mercado': [1000000, 500000, 200000],
        '% participacion': [0.10, 0.05, 0.02],
        'Monto a Liquidar': [100000, 25000, 4000],
    })


# =============================================================================
# TESTS DE generar_cartera_haircut
# =============================================================================

class TestGenerarCarteraHaircut:
    """Tests para generar_cartera_haircut."""
    
    def test_genera_cartera_con_haircut(self, df_cartera_pond, df_factores, df_fpl):
        """Verificar que genera cartera con haircut."""
        resultado = generar_cartera_haircut(
            df_cartera_pond, df_factores, df_fpl,
            filtro_instrumento='Gobierno CLP',
            verbose=False
        )
        
        assert len(resultado) > 0
        assert 'FactorPond' in resultado.columns
        assert 'Dia' in resultado.columns
        assert 'Factor' in resultado.columns
    
    def test_instrumento_no_encontrado_error(self, df_cartera_pond, df_factores, df_fpl):
        """Verificar error cuando instrumento no existe."""
        with pytest.raises(ValueError, match="No se encontró Haircut"):
            generar_cartera_haircut(
                df_cartera_pond, df_factores, df_fpl,
                filtro_instrumento='Instrumento Inexistente',
                verbose=False
            )
    
    def test_factor_pond_usa_maximo(self, df_cartera_pond, df_factores, df_fpl):
        """Verificar que FactorPond usa MAX(Factor, Haircut)."""
        resultado = generar_cartera_haircut(
            df_cartera_pond, df_factores, df_fpl,
            filtro_instrumento='Gobierno CLP',  # Haircut = 0.0015
            verbose=False
        )
        
        # Verificar que FactorPond = Ponderador * max(Factor, 0.0015)
        for _, row in resultado.iterrows():
            esperado = row['Ponderador'] * max(row['Factor'], 0.0015)
            assert np.isclose(row['FactorPond'], esperado)
    
    def test_lista_instrumentos(self, df_cartera_pond, df_factores, df_fpl):
        """Verificar que acepta lista de instrumentos."""
        resultado = generar_cartera_haircut(
            df_cartera_pond, df_factores, df_fpl,
            filtro_instrumento=['LCH', 'BBC'],
            verbose=False
        )
        
        assert len(resultado) > 0


# =============================================================================
# TESTS DE generar_haircut_dia
# =============================================================================

class TestGenerarHaircutDia:
    """Tests para generar_haircut_dia."""
    
    def test_agrega_por_dia(self, df_cartera_hc):
        """Verificar que agrega FactorPond por día."""
        resultado = generar_haircut_dia(df_cartera_hc, verbose=False)
        
        assert len(resultado) == 3  # 3 días únicos
        assert 'Dia' in resultado.columns
        assert 'Haircut' in resultado.columns
    
    def test_suma_correcta(self, df_cartera_hc):
        """Verificar suma correcta de FactorPond."""
        resultado = generar_haircut_dia(df_cartera_hc, verbose=False)
        
        # Dia 1: 0.001 + 0.002 = 0.003
        dia_1 = resultado[resultado['Dia'] == 1]['Haircut'].iloc[0]
        assert np.isclose(dia_1, 0.003)
    
    def test_ordenado_por_dia(self, df_cartera_hc):
        """Verificar que está ordenado por día."""
        resultado = generar_haircut_dia(df_cartera_hc, verbose=False)
        assert resultado['Dia'].is_monotonic_increasing


# =============================================================================
# TESTS DE agregar_dia_semana
# =============================================================================

class TestAgregarDiaSemana:
    """Tests para agregar_dia_semana."""
    
    def test_agrega_dia_semana(self, df_haircut_dia):
        """Verificar que agrega columna DiaSem."""
        # 2026-01-31 es Sábado
        resultado = agregar_dia_semana(
            df_haircut_dia,
            fecha_proceso=20260131,
            verbose=False
        )
        
        assert 'DiaSem' in resultado.columns
        assert len(resultado) == len(df_haircut_dia)
    
    def test_dia_semana_correcto(self, df_haircut_dia):
        """Verificar cálculo correcto de día de semana."""
        # 2026-01-26 es Lunes
        resultado = agregar_dia_semana(
            df_haircut_dia,
            fecha_proceso=pd.Timestamp('2026-01-26'),
            verbose=False
        )
        
        # Día 1 desde Lunes = Martes (DiaSem = 2)
        dia_1 = resultado[resultado['Dia'] == 1]['DiaSem'].iloc[0]
        assert dia_1 == 2  # Martes
    
    def test_acepta_int_fecha(self, df_haircut_dia):
        """Verificar que acepta fecha como int YYYYMMDD."""
        resultado = agregar_dia_semana(
            df_haircut_dia,
            fecha_proceso=20260131,
            verbose=False
        )
        
        assert 'DiaSem' in resultado.columns
    
    def test_acepta_datetime(self, df_haircut_dia):
        """Verificar que acepta datetime."""
        resultado = agregar_dia_semana(
            df_haircut_dia,
            fecha_proceso=datetime(2026, 1, 31),
            verbose=False
        )
        
        assert 'DiaSem' in resultado.columns


# =============================================================================
# TESTS DE combinar_haircut_con_pactos
# =============================================================================

class TestCombinarHaircutConPactos:
    """Tests para combinar_haircut_con_pactos."""
    
    def test_combina_correctamente(self, df_haircut_dia_sem, df_monto_plazo_pacto):
        """Verificar que combina haircut con pactos."""
        resultado = combinar_haircut_con_pactos(
            df_haircut_dia_sem, df_monto_plazo_pacto,
            verbose=False
        )
        
        assert 'Monto_Pacto' in resultado.columns
        assert len(resultado) == len(df_haircut_dia_sem)
    
    def test_monto_pacto_correcto(self, df_haircut_dia_sem, df_monto_plazo_pacto):
        """Verificar montos de pacto correctos."""
        resultado = combinar_haircut_con_pactos(
            df_haircut_dia_sem, df_monto_plazo_pacto,
            verbose=False
        )
        
        # Día 2 tiene pacto de 1000
        dia_2 = resultado[resultado['Dia'] == 2]['Monto_Pacto'].iloc[0]
        assert dia_2 == 1000.0
        
        # Día 5 tiene pacto de 2000
        dia_5 = resultado[resultado['Dia'] == 5]['Monto_Pacto'].iloc[0]
        assert dia_5 == 2000.0
    
    def test_dias_sin_pacto_tienen_cero(self, df_haircut_dia_sem, df_monto_plazo_pacto):
        """Verificar que días sin pacto tienen Monto_Pacto = 0."""
        resultado = combinar_haircut_con_pactos(
            df_haircut_dia_sem, df_monto_plazo_pacto,
            verbose=False
        )
        
        # Día 1 no tiene pacto
        dia_1 = resultado[resultado['Dia'] == 1]['Monto_Pacto'].iloc[0]
        assert dia_1 == 0.0


# =============================================================================
# TESTS DE filtrar_monto_liquidar
# =============================================================================

class TestFiltrarMontoLiquidar:
    """Tests para filtrar_monto_liquidar."""
    
    def test_filtra_por_instrumento(self, df_montos_liq):
        """Verificar que filtra por instrumento."""
        resultado = filtrar_monto_liquidar(
            df_montos_liq,
            instrumento='Gobierno CLP',
            verbose=False
        )
        
        assert len(resultado) == 1
        assert resultado['Instrumento'].iloc[0] == 'Gobierno CLP'
    
    def test_monto_correcto(self, df_montos_liq):
        """Verificar que retorna monto correcto."""
        resultado = filtrar_monto_liquidar(
            df_montos_liq,
            instrumento='Gobierno CLP',
            verbose=False
        )
        
        assert resultado['Monto a Liquidar'].iloc[0] == 100000
    
    def test_instrumento_no_encontrado(self, df_montos_liq):
        """Verificar comportamiento cuando instrumento no existe."""
        resultado = filtrar_monto_liquidar(
            df_montos_liq,
            instrumento='Instrumento Inexistente',
            verbose=False
        )
        
        assert len(resultado) == 0


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
