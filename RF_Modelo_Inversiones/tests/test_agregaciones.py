"""
Tests para RF_Modelo_Inversiones/pipeline/agregaciones.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_agregaciones.py -v
"""

import pytest
import pandas as pd
import numpy as np

from RF_Modelo_Inversiones.pipeline.agregaciones import (
    agregar_por_columnas,
    generar_monto_total_instrumento,
    generar_haircut_dia,
    generar_monto_plazo_pacto,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_cartera():
    """DataFrame simulando cartera de inversiones."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 6,
        'Instrumento': ['BCP', 'BCP', 'BTP', 'BTP', 'BCU', 'BCU'],
        'Moneda': ['CLP', 'CLP', 'CLP', 'CLP', 'CLF', 'CLF'],
        'VP_Cap_Amort': [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0],
        'VP_Int_Total': [100.0, 200.0, 300.0, 400.0, 500.0, 600.0],
        'Dias_Vcto': [30, 60, 90, 120, 150, 180],
        'Dia': [1, 2, 1, 2, 1, 2],
        'FactorPond': [0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
    })


@pytest.fixture
def df_pacto():
    """DataFrame simulando cartera de pactos."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 4,
        'Instrumento': ['BCP', 'BCP', 'BCU', 'BCU'],
        'Moneda': ['CLP', 'CLP', 'CLF', 'CLF'],
        'Dias_Pacto': [5, 5, 10, 10],
        'VP_Cap_Amort': [1000.0, 2000.0, 3000.0, 4000.0],
        'VP_Int_Total': [100.0, 200.0, 300.0, 400.0],
    })


# =============================================================================
# TESTS DE agregar_por_columnas
# =============================================================================

class TestAgregarPorColumnas:
    """Tests para la función genérica de agregación."""
    
    def test_agregacion_simple(self, df_cartera):
        """Verificar agregación por una columna."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort'],
        )
        
        assert len(resultado) == 3  # BCP, BTP, BCU
        assert resultado[resultado['Instrumento'] == 'BCP']['VP_Cap_Amort'].iloc[0] == 3000.0
        assert resultado[resultado['Instrumento'] == 'BTP']['VP_Cap_Amort'].iloc[0] == 7000.0
    
    def test_agregacion_multiples_columnas(self, df_cartera):
        """Verificar agregación por múltiples columnas."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Instrumento', 'Moneda'],
            cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
        )
        
        # 3 instrumentos x 1 moneda cada uno (en este fixture)
        assert len(resultado) == 3
        
        # Verificar que suma correctamente
        bcp = resultado[resultado['Instrumento'] == 'BCP']
        assert bcp['VP_Cap_Amort'].iloc[0] == 3000.0
        assert bcp['VP_Int_Total'].iloc[0] == 300.0
    
    def test_columna_faltante_error(self, df_cartera):
        """Verificar error si falta columna de agrupación."""
        with pytest.raises(ValueError, match="Columnas no encontradas"):
            agregar_por_columnas(
                df=df_cartera,
                cols_grupo=['Columna_Inexistente'],
                cols_suma=['VP_Cap_Amort'],
            )
    
    def test_columna_suma_faltante_error(self, df_cartera):
        """Verificar error si falta columna a sumar."""
        with pytest.raises(ValueError, match="Columnas no encontradas"):
            agregar_por_columnas(
                df=df_cartera,
                cols_grupo=['Instrumento'],
                cols_suma=['Columna_Inexistente'],
            )
    
    def test_reset_index(self, df_cartera):
        """Verificar que retorna DataFrame con índice limpio."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort'],
        )
        
        # Debe ser un DataFrame con columnas, no índice multi-nivel
        assert 'Instrumento' in resultado.columns
    
    def test_df_vacio(self):
        """Verificar comportamiento con DataFrame vacío."""
        df_vacio = pd.DataFrame({
            'Instrumento': pd.Series([], dtype=str),
            'VP_Cap_Amort': pd.Series([], dtype=float),
        })
        
        resultado = agregar_por_columnas(
            df=df_vacio,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort'],
        )
        
        assert len(resultado) == 0
    
    def test_col_total(self, df_cartera):
        """Verificar que col_total suma columnas y las elimina."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort', 'VP_Int_Total'],
            col_total='VP_Flujo',
        )
        
        assert 'VP_Flujo' in resultado.columns
        assert 'VP_Cap_Amort' not in resultado.columns
        assert 'VP_Int_Total' not in resultado.columns
        
        # BCP: 3000 + 300 = 3300
        bcp = resultado[resultado['Instrumento'] == 'BCP']['VP_Flujo'].iloc[0]
        assert bcp == 3300.0
    
    def test_ordenar_por(self, df_cartera):
        """Verificar ordenamiento del resultado."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Dia'],
            cols_suma=['FactorPond'],
            ordenar_por='Dia',
        )
        
        # Debe estar ordenado por Dia
        assert resultado['Dia'].is_monotonic_increasing


# =============================================================================
# TESTS DE generar_monto_total_instrumento
# =============================================================================

class TestGenerarMontoTotalInstrumento:
    """Tests para generar_monto_total_instrumento."""
    
    def test_genera_monto_por_instrumento(self, df_cartera):
        """Verificar que genera monto total por instrumento."""
        resultado = generar_monto_total_instrumento(df_cartera, verbose=False)
        
        assert len(resultado) == 3  # BCP, BTP, BCU
        assert 'Instrumento' in resultado.columns
        assert 'VP_Flujo' in resultado.columns  # Suma de VP_Cap_Amort + VP_Int_Total
    
    def test_suma_correcta(self, df_cartera):
        """Verificar que suma VP_Cap_Amort + VP_Int_Total correctamente."""
        resultado = generar_monto_total_instrumento(df_cartera, verbose=False)
        
        # BCP: (1000 + 100) + (2000 + 200) = 3300
        bcp = resultado[resultado['Instrumento'] == 'BCP']['VP_Flujo'].iloc[0]
        assert bcp == 3300.0


# =============================================================================
# TESTS DE generar_haircut_dia
# =============================================================================

class TestGenerarHaircutDia:
    """Tests para generar_haircut_dia."""
    
    def test_genera_haircut_por_dia(self, df_cartera):
        """Verificar que genera suma de FactorPond por día."""
        resultado = generar_haircut_dia(df_cartera, verbose=False)
        
        assert len(resultado) == 2  # Dia 1 y 2
        assert 'Dia' in resultado.columns
        assert 'FactorPond' in resultado.columns
    
    def test_suma_factor_pond_correcta(self, df_cartera):
        """Verificar que suma FactorPond correctamente."""
        resultado = generar_haircut_dia(df_cartera, verbose=False)
        
        # Dia 1: 0.01 + 0.03 + 0.05 = 0.09
        dia_1 = resultado[resultado['Dia'] == 1]['FactorPond'].iloc[0]
        assert np.isclose(dia_1, 0.09)
    
    def test_ordenado_por_dia(self, df_cartera):
        """Verificar que el resultado está ordenado por Dia."""
        resultado = generar_haircut_dia(df_cartera, verbose=False)
        assert resultado['Dia'].is_monotonic_increasing


# =============================================================================
# TESTS DE generar_monto_plazo_pacto
# =============================================================================

class TestGenerarMontoPlazoPacto:
    """Tests para generar_monto_plazo_pacto."""
    
    def test_genera_monto_por_plazo_pacto(self, df_pacto):
        """Verificar que genera monto por Dias_Pacto."""
        resultado = generar_monto_plazo_pacto(df_pacto, verbose=False)
        
        # 2 valores únicos de Dias_Pacto: 5, 10
        assert len(resultado) == 2
        assert 'Dias_Pacto' in resultado.columns
        assert 'Monto' in resultado.columns  # Suma de VP_Cap_Amort + VP_Int_Total
    
    def test_suma_correcta_por_plazo(self, df_pacto):
        """Verificar suma correcta por plazo de pacto."""
        resultado = generar_monto_plazo_pacto(df_pacto, verbose=False)
        
        # Dias_Pacto 5: (1000 + 100) + (2000 + 200) = 3300
        dias_5 = resultado[resultado['Dias_Pacto'] == 5]['Monto'].iloc[0]
        # Dias_Pacto 10: (3000 + 300) + (4000 + 400) = 7700
        dias_10 = resultado[resultado['Dias_Pacto'] == 10]['Monto'].iloc[0]
        
        assert dias_5 == 3300.0
        assert dias_10 == 7700.0


# =============================================================================
# TESTS DE EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_valores_nan(self):
        """Verificar manejo de valores NaN."""
        df = pd.DataFrame({
            'Instrumento': ['BCP', 'BCP', 'BTP'],
            'VP_Cap_Amort': [1000.0, np.nan, 3000.0],
        })
        
        resultado = agregar_por_columnas(
            df=df,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort'],
        )
        
        # NaN se ignora en la suma
        bcp = resultado[resultado['Instrumento'] == 'BCP']['VP_Cap_Amort'].iloc[0]
        assert bcp == 1000.0
    
    def test_un_solo_grupo(self):
        """Verificar con un solo grupo."""
        df = pd.DataFrame({
            'Instrumento': ['BCP', 'BCP', 'BCP'],
            'VP_Cap_Amort': [1000.0, 2000.0, 3000.0],
        })
        
        resultado = agregar_por_columnas(
            df=df,
            cols_grupo=['Instrumento'],
            cols_suma=['VP_Cap_Amort'],
        )
        
        assert len(resultado) == 1
        assert resultado['VP_Cap_Amort'].iloc[0] == 6000.0
    
    def test_multiples_sumas(self, df_cartera):
        """Verificar suma de múltiples columnas."""
        resultado = agregar_por_columnas(
            df=df_cartera,
            cols_grupo=['Moneda'],
            cols_suma=['VP_Cap_Amort', 'VP_Int_Total', 'FactorPond'],
        )
        
        assert 'VP_Cap_Amort' in resultado.columns
        assert 'VP_Int_Total' in resultado.columns
        assert 'FactorPond' in resultado.columns


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
