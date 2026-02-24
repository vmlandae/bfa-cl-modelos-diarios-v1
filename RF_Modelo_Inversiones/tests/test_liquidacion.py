"""
Tests para RF_Modelo_Inversiones/pipeline/liquidacion.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_liquidacion.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from RF_Modelo_Inversiones.pipeline.liquidacion import (
    generar_cartera_instrumento,
    generar_cartera_pond,
    generar_monto_total_instrumento,
    calcular_flujo_liquidacion,
    monto_liq_gob_clp,
    COLUMNAS_CARTERA_DISP,
    COLUMNAS_CARTERA_PACTO,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_cartera_inv():
    """DataFrame simulando cartera de inversiones."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 6,
        'Instrumento': ['BCP', 'BCP', 'BTP', 'BTP', 'LET', 'LET'],
        'Nemotecnico': ['BCP001', 'BCP002', 'BTP001', 'BTP002', 'LET001', 'LET002'],
        'Moneda': ['CLP', 'CLP', 'CLF', 'CLF', 'CLP', 'CLP'],
        'Cod_Pro': ['PRO1', 'PRO1', 'PRO2', 'PRO2', 'PRO3', 'PRO3'],
        'Dias_Vcto': [30, 90, 180, 365, 7, 14],
        'VP_Flujo': [100000, 200000, 300000, 400000, 50000, 75000],
        'VP_Cap_Amort': [95000, 190000, 285000, 380000, 49000, 73500],
        'VP_Int_Total': [5000, 10000, 15000, 20000, 1000, 1500],
    })


@pytest.fixture
def df_cartera_filtrada():
    """DataFrame con cartera ya filtrada por instrumento."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 4,
        'Instrumento': ['BCP', 'BCP', 'BCP', 'BCP'],
        'Nemotecnico': ['BCP001', 'BCP002', 'BCP003', 'BCP004'],
        'Cod_Pro': ['PRO1', 'PRO1', 'PRO1', 'PRO1'],
        'Moneda': ['CLP', 'CLP', 'CLP', 'CLP'],
        'Dias_Vcto': [30, 60, 90, 120],
        'VP_Flujo': [100000, 200000, 150000, 250000],
        'VP_Cap_Amort': [95000, 190000, 142500, 237500],
        'VP_Int_Total': [5000, 10000, 7500, 12500],
    })


@pytest.fixture
def df_monto_total():
    """DataFrame con monto total calculado."""
    # El monto total debe ser VP_Cap_Amort + VP_Int_Total para que
    # la suma de ponderadores sea 1.0
    return pd.DataFrame({
        'Cod_Pro': ['PRO1'],
        'Moneda': ['CLP'],
        'VP_Flujo': [665000.0 + 35000.0],  # = 700000
    })


@pytest.fixture
def df_haircut_dia():
    """DataFrame con haircut por día."""
    return pd.DataFrame({
        'Dia': [1, 2, 3, 4, 5],
        'DiaSem': [5, 6, 7, 1, 2],  # Viernes, Sábado, Domingo, Lunes, Martes
        'Haircut': [0.01, 0.015, 0.02, 0.025, 0.03],
        'Monto_Pacto': [0, 0, 0, 1000000, 0],
    })


@pytest.fixture
def df_cartera_mon_total():
    """DataFrame con monto total para liquidación."""
    return pd.DataFrame({
        'VP_Flujo': [1000000.0],
    })


@pytest.fixture
def df_monto_liquidar():
    """DataFrame con monto a liquidar diario."""
    return pd.DataFrame({
        'Instrumento': ['Gobierno CLP'],
        'Monto a Liquidar': [50000.0],
    })


# =============================================================================
# TESTS DE CONSTANTES
# =============================================================================

class TestConstantes:
    """Tests para las constantes del módulo."""
    
    def test_columnas_cartera_disp_no_vacio(self):
        """Verificar que COLUMNAS_CARTERA_DISP no está vacío."""
        assert len(COLUMNAS_CARTERA_DISP) > 0
    
    def test_columnas_cartera_pacto_no_vacio(self):
        """Verificar que COLUMNAS_CARTERA_PACTO no está vacío."""
        assert len(COLUMNAS_CARTERA_PACTO) > 0
    
    def test_columnas_son_strings(self):
        """Verificar que todas las columnas son strings."""
        assert all(isinstance(c, str) for c in COLUMNAS_CARTERA_DISP)
        assert all(isinstance(c, str) for c in COLUMNAS_CARTERA_PACTO)


# =============================================================================
# TESTS DE generar_cartera_instrumento
# =============================================================================

class TestGenerarCarteraInstrumento:
    """Tests para generar_cartera_instrumento."""
    
    def test_filtra_por_codigo(self, df_cartera_inv):
        """Verificar que filtra por código de instrumento."""
        resultado = generar_cartera_instrumento(
            df_base=df_cartera_inv,
            cols_de_salida=['Fec_Pro', 'Instrumento', 'Moneda', 'VP_Flujo'],
            instrumento=['BCP', 'BTP'],
            nombre_instrumento='GobCLP',
            verbose=False
        )
        
        assert len(resultado) == 4
        assert set(resultado['Instrumento'].unique()) == {'BCP', 'BTP'}
    
    def test_filtra_por_moneda(self, df_cartera_inv):
        """Verificar que filtra por moneda."""
        resultado = generar_cartera_instrumento(
            df_base=df_cartera_inv,
            cols_de_salida=['Fec_Pro', 'Instrumento', 'Moneda', 'VP_Flujo'],
            instrumento=['BCP', 'BTP'],
            nombre_instrumento='GobCLP',
            filtro_moneda='CLP',
            verbose=False
        )
        
        assert len(resultado) == 2
        assert all(resultado['Moneda'] == 'CLP')
    
    def test_sin_filtro_moneda(self, df_cartera_inv):
        """Verificar que sin filtro_moneda incluye todas las monedas."""
        resultado = generar_cartera_instrumento(
            df_base=df_cartera_inv,
            cols_de_salida=['Fec_Pro', 'Instrumento', 'Moneda', 'VP_Flujo'],
            instrumento=['BCP', 'BTP'],
            nombre_instrumento='GobCLP',
            filtro_moneda=None,
            verbose=False
        )
        
        assert len(resultado) == 4
        assert set(resultado['Moneda'].unique()) == {'CLP', 'CLF'}
    
    def test_columnas_salida_correctas(self, df_cartera_inv):
        """Verificar que solo incluye columnas especificadas."""
        cols_salida = ['Fec_Pro', 'Instrumento', 'VP_Flujo']
        resultado = generar_cartera_instrumento(
            df_base=df_cartera_inv,
            cols_de_salida=cols_salida,
            instrumento=['BCP'],
            nombre_instrumento='GobCLP',
            verbose=False
        )
        
        assert list(resultado.columns) == cols_salida


# =============================================================================
# TESTS DE generar_monto_total_instrumento
# =============================================================================

class TestGenerarMontoTotalInstrumento:
    """Tests para generar_monto_total_instrumento."""
    
    def test_calcula_total_agrupado(self, df_cartera_filtrada):
        """Verificar que calcula total agrupado correctamente."""
        resultado = generar_monto_total_instrumento(
            df_cartera_instrumento=df_cartera_filtrada,
            cols_de_agrupacion=['Cod_Pro', 'Moneda'],
            cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
            verbose=False
        )
        
        assert 'VP_Flujo' in resultado.columns
        assert len(resultado) == 1  # Un solo grupo PRO1/CLP
    
    def test_suma_correcta(self, df_cartera_filtrada):
        """Verificar suma correcta de VP_Flujo."""
        resultado = generar_monto_total_instrumento(
            df_cartera_instrumento=df_cartera_filtrada,
            cols_de_agrupacion=['Cod_Pro', 'Moneda'],
            cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
            verbose=False
        )
        
        # VP_Flujo = Sum(VP_Cap_Amort) + Sum(VP_Int_Total)
        esperado = df_cartera_filtrada['VP_Cap_Amort'].sum() + df_cartera_filtrada['VP_Int_Total'].sum()
        assert resultado['VP_Flujo'].iloc[0] == esperado


# =============================================================================
# TESTS DE generar_cartera_pond
# =============================================================================

class TestGenerarCarteraPond:
    """Tests para generar_cartera_pond."""
    
    def test_genera_ponderador(self, df_cartera_filtrada, df_monto_total):
        """Verificar que genera columna Ponderador."""
        resultado = generar_cartera_pond(
            df_cartera_instrumento=df_cartera_filtrada,
            df_montototal=df_monto_total,
            verbose=False
        )
        
        assert 'Ponderador' in resultado.columns
    
    def test_ponderadores_todos_positivos(self, df_cartera_filtrada, df_monto_total):
        """Verificar que todos los ponderadores son positivos."""
        resultado = generar_cartera_pond(
            df_cartera_instrumento=df_cartera_filtrada,
            df_montototal=df_monto_total,
            verbose=False
        )
        
        assert all(resultado['Ponderador'] > 0)
    
    def test_mantiene_columnas_originales(self, df_cartera_filtrada, df_monto_total):
        """Verificar que mantiene columnas originales más Ponderador."""
        resultado = generar_cartera_pond(
            df_cartera_instrumento=df_cartera_filtrada,
            df_montototal=df_monto_total,
            verbose=False
        )
        
        # Columnas originales + Ponderador
        for col in df_cartera_filtrada.columns:
            assert col in resultado.columns
        assert 'Ponderador' in resultado.columns


# =============================================================================
# TESTS DE calcular_flujo_liquidacion
# =============================================================================

class TestCalcularFlujoLiquidacion:
    """Tests para calcular_flujo_liquidacion."""
    
    def test_genera_flujo(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar que genera flujo de liquidación."""
        resultado = calcular_flujo_liquidacion(
            df_cartera_mon_total=df_cartera_mon_total,
            df_haircut_dia_pcto=df_haircut_dia,
            df_monto_liquidar=df_monto_liquidar,
            verbose=False
        )
        
        assert 'Monto_Liquidar' in resultado.columns
        # 5 días + día 0 = 6 filas
        assert len(resultado) == 6
    
    def test_dia_cero_tiene_monto_inicial(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar que día 0 tiene monto inicial."""
        resultado = calcular_flujo_liquidacion(
            df_cartera_mon_total=df_cartera_mon_total,
            df_haircut_dia_pcto=df_haircut_dia,
            df_monto_liquidar=df_monto_liquidar,
            verbose=False
        )
        
        dia_0 = resultado[resultado['Dia'] == 0]
        assert dia_0['Monto_Liquidar'].iloc[0] == 1000000.0
    
    def test_fines_de_semana_sin_liquidacion(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar que no hay liquidación en fines de semana."""
        resultado = calcular_flujo_liquidacion(
            df_cartera_mon_total=df_cartera_mon_total,
            df_haircut_dia_pcto=df_haircut_dia,
            df_monto_liquidar=df_monto_liquidar,
            verbose=False
        )
        
        # Filtrar solo días con DiaSem (excluir día 0 que tiene None)
        dias_fds = resultado[(resultado['DiaSem'].isin([6, 7])) & (resultado['Dia'] > 0)]
        assert all(dias_fds['Monto_Liquidar'] == 0)
    
    def test_columnas_salida(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar columnas de salida."""
        resultado = calcular_flujo_liquidacion(
            df_cartera_mon_total=df_cartera_mon_total,
            df_haircut_dia_pcto=df_haircut_dia,
            df_monto_liquidar=df_monto_liquidar,
            verbose=False
        )
        
        columnas_esperadas = ['Dia', 'DiaSem', 'Haircut', 'Monto_Liquidar']
        for col in columnas_esperadas:
            assert col in resultado.columns


# =============================================================================
# TESTS DE monto_liq_gob_clp (DEPRECADO)
# =============================================================================

class TestMontoLiqGobClp:
    """Tests para monto_liq_gob_clp (función deprecada)."""
    
    def test_emite_deprecation_warning(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar que emite DeprecationWarning."""
        with pytest.warns(DeprecationWarning):
            monto_liq_gob_clp(df_cartera_mon_total, df_haircut_dia, df_monto_liquidar)
    
    def test_funciona_igual_que_calcular_flujo(self, df_cartera_mon_total, df_haircut_dia, df_monto_liquidar):
        """Verificar que funciona igual que calcular_flujo_liquidacion."""
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        
        r1 = calcular_flujo_liquidacion(
            df_cartera_mon_total, df_haircut_dia, df_monto_liquidar,
            nombre_instrumento="GobCLP", verbose=False
        )
        r2 = monto_liq_gob_clp(df_cartera_mon_total, df_haircut_dia, df_monto_liquidar)
        
        # Comparar columnas numéricas
        pd.testing.assert_frame_equal(
            r1[['Dia', 'Haircut', 'Monto_Liquidar']], 
            r2[['Dia', 'Haircut', 'Monto_Liquidar']]
        )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
