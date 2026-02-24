"""
Tests para RF_Modelo_Inversiones/pipeline/orquestador.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_orquestador.py -v
"""

import pytest
import pandas as pd
import numpy as np

from RF_Modelo_Inversiones.pipeline.orquestador import (
    generar_flujo_liquidacion_instrumento,
    listar_tipos_instrumento,
    _obtener_config_instrumento,
    CONFIGURACION_INSTRUMENTOS_FALLBACK,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_cartera_inv():
    """DataFrame simulando cartera de inversiones disponible."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 8,
        'Cod_Emp': ['001'] * 8,
        'Moneda': ['CLP', 'CLP', 'CLF', 'CLF', 'CLP', 'CLP', 'CLP', 'CLP'],
        'Cod_Pro': ['PRO1'] * 8,
        'Cod_Sub_Pro': ['SUB1'] * 8,
        'Instrumento': ['BCP', 'BCP', 'BCU', 'BCU', 'PDBC', 'PDBC', 'LCH', 'LCH'],
        'Nemotecnico': ['BCP001', 'BCP002', 'BCU001', 'BCU002', 'PDBC001', 'PDBC002', 'LCH001', 'LCH002'],
        'Dias_Vcto': [30, 90, 180, 365, 7, 14, 21, 28],
        'VP_Flujo': [100000, 200000, 300000, 400000, 50000, 75000, 80000, 90000],
        'VP_Cap_Amort': [95000, 190000, 285000, 380000, 49000, 73500, 78400, 88200],
        'VP_Int_Total': [5000, 10000, 15000, 20000, 1000, 1500, 1600, 1800],
    })


@pytest.fixture
def df_cartera_inv_pacto():
    """DataFrame simulando cartera de inversiones en pacto."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 4,
        'Cod_Emp': ['001'] * 4,
        'Moneda': ['CLP', 'CLP', 'CLP', 'CLP'],
        'Cod_Pro': ['PRO1'] * 4,
        'Cod_Sub_Pro': ['SUB1'] * 4,
        'Instrumento': ['BCP', 'BCP', 'BCP', 'BCP'],
        'Nemotecnico': ['PACTO001', 'PACTO002', 'PACTO003', 'PACTO004'],
        'Dias_Pacto': [2, 5, 10, 15],
        'Dias_Vcto': [2, 5, 10, 15],
        'VP_Flujo': [500000, 1000000, 750000, 250000],
        'VP_Cap_Amort': [500000, 1000000, 750000, 250000],
        'VP_Int_Total': [0, 0, 0, 0],
    })


@pytest.fixture
def tablas_simuladas():
    """Dict simulando tablas de referencia."""
    # Factores para GobCLP
    df_factores_clp = pd.DataFrame({
        'Desde': [0, 31, 91, 181],
        'Hasta': [30, 90, 180, 365],
        'Dia': [1, 2, 3, 4],
        'Factor': [0.001, 0.002, 0.003, 0.004],
    })
    
    # Floor Piso Liquidez
    df_fpl = pd.DataFrame({
        'Instrumento': ['Gobierno CLP', 'Gobierno UF', 'LCH', 'BBC', 'Dep Plz Fijo CLP', 'Dep Plz Reaj UF'],
        'Haircut': [0.0015, 0.002, 0.0025, 0.003, 0.005, 0.006],
    })
    
    # Montos a Liquidar
    df_montos = pd.DataFrame({
        'Instrumento': ['Gobierno CLP', 'Gobierno UF', 'LCH', 'BBC', 'Dep Plz Fijo CLP', 'Dep Plz Reaj UF'],
        'Monto Mercado': [1000000000, 500000000, 200000000, 100000000, 150000000, 75000000],
        '% participacion': [0.10, 0.05, 0.02, 0.01, 0.03, 0.015],
        'Monto a Liquidar': [100000000, 25000000, 4000000, 1000000, 4500000, 1125000],
    })
    
    return {
        'RF_FactCLP_Gob': df_factores_clp,
        'RF_FactCLF_Gob': df_factores_clp.copy(),
        'RF_FactCLP_Priv': df_factores_clp.copy(),
        'RF_FactCLF_Priv': df_factores_clp.copy(),
        'FPL': df_fpl,
        'RF_MontosLiq': df_montos,
    }


# =============================================================================
# TESTS DE listar_tipos_instrumento
# =============================================================================

class TestListarTiposInstrumento:
    """Tests para listar_tipos_instrumento."""
    
    def test_retorna_lista(self):
        """Verificar que retorna lista."""
        resultado = listar_tipos_instrumento()
        assert isinstance(resultado, list)
    
    def test_contiene_6_instrumentos(self):
        """Verificar que contiene 6 instrumentos."""
        resultado = listar_tipos_instrumento()
        assert len(resultado) == 6
    
    def test_instrumentos_esperados(self):
        """Verificar instrumentos esperados."""
        resultado = listar_tipos_instrumento()
        esperados = {'GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH'}
        assert set(resultado) == esperados


# =============================================================================
# TESTS DE _obtener_config_instrumento
# =============================================================================

class TestObtenerConfigInstrumento:
    """Tests para _obtener_config_instrumento."""
    
    def test_retorna_config_valida(self):
        """Verificar que retorna configuración válida."""
        config = _obtener_config_instrumento('GobCLP')
        
        assert config is not None
        assert 'codigos_disp' in config
        assert 'instrumento_fpl' in config
        assert 'moneda' in config
    
    def test_gob_clp_config(self):
        """Verificar configuración de GobCLP."""
        config = _obtener_config_instrumento('GobCLP')
        
        assert 'BCP' in config['codigos_disp']
        assert config['instrumento_fpl'] == 'Gobierno CLP'
        assert config['moneda'] == 'CLP'
    
    def test_gob_clf_config(self):
        """Verificar configuración de GobCLF."""
        config = _obtener_config_instrumento('GobCLF')
        
        assert 'BCU' in config['codigos_disp']
        # instrumento_fpl puede ser 'Gobierno UF' o 'Gobierno CLF' según la fuente
        assert 'Gobierno' in config['instrumento_fpl']
        assert config['moneda'] == 'CLF'
    
    def test_instrumento_invalido_error(self):
        """Verificar error con instrumento inválido."""
        with pytest.raises(ValueError):
            _obtener_config_instrumento('InstrumentoInexistente')


# =============================================================================
# TESTS DE CONFIGURACION_INSTRUMENTOS_FALLBACK
# =============================================================================

class TestConfiguracionInstrumentosFallback:
    """Tests para CONFIGURACION_INSTRUMENTOS_FALLBACK."""
    
    def test_contiene_6_instrumentos(self):
        """Verificar que contiene 6 instrumentos."""
        assert len(CONFIGURACION_INSTRUMENTOS_FALLBACK) == 6
    
    def test_cada_instrumento_tiene_campos_requeridos(self):
        """Verificar campos requeridos en cada instrumento."""
        campos_requeridos = {'codigos_disp', 'instrumento_fpl', 'moneda'}
        
        for nombre, config in CONFIGURACION_INSTRUMENTOS_FALLBACK.items():
            for campo in campos_requeridos:
                assert campo in config, f"Falta {campo} en {nombre}"
    
    def test_codigos_disp_son_lista(self):
        """Verificar que códigos_disp son lista."""
        for nombre, config in CONFIGURACION_INSTRUMENTOS_FALLBACK.items():
            assert isinstance(config['codigos_disp'], list), f"codigos_disp no es lista en {nombre}"
    
    def test_moneda_es_string(self):
        """Verificar que moneda es string."""
        for nombre, config in CONFIGURACION_INSTRUMENTOS_FALLBACK.items():
            assert isinstance(config['moneda'], (str, type(None))), f"moneda inválida en {nombre}"


# =============================================================================
# TESTS DE generar_flujo_liquidacion_instrumento
# =============================================================================

class TestGenerarFlujoLiquidacionInstrumento:
    """Tests para generar_flujo_liquidacion_instrumento."""
    
    def test_genera_flujo_gob_clp(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Verificar que genera flujo para GobCLP."""
        resultado, queries = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        assert isinstance(resultado, pd.DataFrame)
        assert len(resultado) > 0
    
    def test_retorna_queries_generadas(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Verificar que retorna queries generadas."""
        _, queries = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        assert isinstance(queries, dict)
        assert len(queries) > 0
    
    def test_tipo_instrumento_invalido_error(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Verificar error con tipo de instrumento inválido."""
        with pytest.raises(ValueError):
            generar_flujo_liquidacion_instrumento(
                df_cartera_inv=df_cartera_inv,
                df_cartera_inv_pacto=df_cartera_inv_pacto,
                tablas=tablas_simuladas,
                tipo_instrumento='InstrumentoInexistente',
                fecha_proceso=20260131,
                verbose=False
            )
    
    def test_columnas_resultado(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Verificar columnas en resultado."""
        resultado, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        # Columnas esperadas mínimas
        columnas_esperadas = ['Dia', 'Monto_Liquidar']
        for col in columnas_esperadas:
            assert col in resultado.columns, f"Falta columna {col}"


# =============================================================================
# TESTS DE INTEGRACIÓN
# =============================================================================

class TestIntegracion:
    """Tests de integración del pipeline completo."""
    
    def test_pipeline_completo_gob_clp(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Test de integración: pipeline completo para GobCLP."""
        resultado, queries = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        # Verificar estructura del resultado
        assert 'Dia' in resultado.columns
        assert 'Monto_Liquidar' in resultado.columns
        
        # Verificar queries generadas
        assert len(queries) > 0
    
    def test_pipeline_determinista(self, df_cartera_inv, df_cartera_inv_pacto, tablas_simuladas):
        """Verificar que el pipeline es determinista."""
        r1, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        r2, _ = generar_flujo_liquidacion_instrumento(
            df_cartera_inv=df_cartera_inv,
            df_cartera_inv_pacto=df_cartera_inv_pacto,
            tablas=tablas_simuladas,
            tipo_instrumento='GobCLP',
            fecha_proceso=20260131,
            verbose=False
        )
        
        pd.testing.assert_frame_equal(r1, r2)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
