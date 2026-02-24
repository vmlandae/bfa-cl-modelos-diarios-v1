"""
Tests para RF_Modelo_Inversiones/pipeline/cartera.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_cartera.py -v
"""

import pytest
import pandas as pd
import numpy as np
import warnings
from datetime import datetime


# =============================================================================
# IMPORTS DEL MÓDULO A TESTEAR
# =============================================================================

from RF_Modelo_Inversiones.pipeline.cartera import (
    genera_cartera_inv,
    genera_cartera_inv_001,
    genera_cartera_inv_pacto,
    FILTROS_CARTERA,
    COLUMNAS_BASE_SALIDA,
    PRODUCTOS_FONDOS_MUTUOS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def df_fecha():
    """DataFrame con fecha de proceso."""
    return pd.DataFrame({'Fecha': [pd.Timestamp('2026-01-31')]})


@pytest.fixture
def df_base_completa():
    """DataFrame simulando RF_base_Completa_Hist con diferentes casos."""
    return pd.DataFrame({
        'Fec_Pro': [pd.Timestamp('2026-01-31')] * 10 + [pd.Timestamp('2026-01-30')] * 2,
        'Cod_Emp': [1] * 12,
        'Moneda': ['CLP', 'CLP', 'CLF', 'CLP', 'CLP', 'CLF', 'CLP', 'CLP', 'CLP', 'CLP', 'CLP', 'CLP'],
        'Cod_Pro': [
            'Inversion Financiera Gob',  # 0: disponible
            'Inversion Financiera Gob',  # 1: disponible
            'INVERSIONES FINANCIERAS Banc',  # 2: disponible
            'INVERSIONES FINANCIERAS FONDOS MUTUOS',  # 3: fondos mutuos (transform)
            'Inversion Financiera Gob',  # 4: pacto
            'Inversion Financiera Gob',  # 5: pacto
            'Inversion Financiera Gob',  # 6: LCH (excluido en disponible)
            'Inversion Financiera Gob',  # 7: HTM (excluido en disponible)
            'Otro Producto',  # 8: no inversión (excluido)
            'Inversion Financiera Gob',  # 9: disponible
            'Inversion Financiera Gob',  # 10: fecha diferente (excluido)
            'Inversion Financiera Gob',  # 11: fecha diferente (excluido)
        ],
        'Cod_Sub_Pro': [
            'SubPro_Disp',  # 0
            'SubPro_Disp_Liq',  # 1
            'SubPro_MUTUOS',  # 2
            'SubPro_Disp',  # 3
            'SubPro_Pcto',  # 4
            'SubPro_Pcto_Liq',  # 5
            'SubPro_Disp',  # 6
            'SubPro_Disp',  # 7
            'SubPro_Disp',  # 8
            'SubPro_Disp',  # 9
            'SubPro_Disp',  # 10
            'SubPro_Pcto',  # 11
        ],
        'Nemotecnico': [
            'BCP001',  # 0
            'BTP002',  # 1
            'DPF003',  # 2
            'FFM004',  # 3
            'BCU005',  # 4
            'BTU006',  # 5
            'LCH007',  # 6: LCH excluido en disponible
            'BCP008',  # 7: HTM excluido
            'BCP009',  # 8: no inversión
            'BCP010',  # 9
            'BCP011',  # 10
            'BCP012',  # 11
        ],
        'Clasificacion_Contable': [
            'AFS', 'AFS', 'AFS', 'AFS', 'AFS', 'AFS',
            'AFS', 'HTM', 'AFS', 'AFS', 'AFS', 'AFS'
        ],
        'VP_Cap_Amort': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000],
        'VP_Int_Total': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200],
        'Dias_Vcto': [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360],
        'Dias_Pacto': [0, 0, 0, 0, 5, 10, 0, 0, 0, 0, 0, 15],
    })


# =============================================================================
# TESTS DE CONFIGURACIÓN
# =============================================================================

class TestConfiguracion:
    """Tests para la configuración del módulo."""
    
    def test_filtros_cartera_tiene_disponible_y_pacto(self):
        """Verificar que existen las configuraciones de ambos tipos."""
        assert 'disponible' in FILTROS_CARTERA
        assert 'pacto' in FILTROS_CARTERA
    
    def test_columnas_base_salida(self):
        """Verificar columnas base de salida."""
        assert 'Fec_Pro' in COLUMNAS_BASE_SALIDA
        assert 'Instrumento' in COLUMNAS_BASE_SALIDA
        assert len(COLUMNAS_BASE_SALIDA) == 10
    
    def test_productos_fondos_mutuos(self):
        """Verificar productos que se transforman."""
        assert 'INVERSIONES FINANCIERAS FONDOS MUTUOS' in PRODUCTOS_FONDOS_MUTUOS


# =============================================================================
# TESTS DE genera_cartera_inv (DISPONIBLE)
# =============================================================================

class TestGeneraCarteraInvDisponible:
    """Tests para genera_cartera_inv con tipo='disponible'."""
    
    def test_genera_cartera_disponible(self, df_base_completa, df_fecha):
        """Verificar que genera cartera disponible correctamente."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # Debe tener registros
        assert len(resultado) > 0
        
        # Verificar columnas
        for col in COLUMNAS_BASE_SALIDA:
            assert col in resultado.columns
    
    def test_excluye_lch(self, df_base_completa, df_fecha):
        """Verificar que excluye registros con Nemotecnico que empieza con LCH."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # No debe haber registros con LCH
        assert not resultado['Nemotecnico'].str.startswith('LCH').any()
    
    def test_excluye_htm(self, df_base_completa, df_fecha):
        """Verificar que excluye registros con Clasificacion_Contable = HTM."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # Verificar que los registros con HTM (índice 7) no están
        # El resultado no tiene la columna Clasificacion_Contable, pero podemos verificar
        # que el nemotécnico BCP008 (que tenía HTM) no está
        assert 'BCP008' not in resultado['Nemotecnico'].values
    
    def test_filtra_por_fecha(self, df_base_completa, df_fecha):
        """Verificar que solo incluye registros de la fecha de proceso."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # Todos los registros deben ser de la fecha 2026-01-31
        assert (resultado['Fec_Pro'] == pd.Timestamp('2026-01-31')).all()
    
    def test_filtra_cod_sub_pro_disponible(self, df_base_completa, df_fecha):
        """Verificar que filtra por sufijos de Cod_Sub_Pro para disponible."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # Los pactos (índice 4, 5) no deben estar
        assert 'BCU005' not in resultado['Nemotecnico'].values
        assert 'BTU006' not in resultado['Nemotecnico'].values
    
    def test_transforma_fondos_mutuos(self, df_base_completa, df_fecha):
        """Verificar que transforma Cod_Pro de fondos mutuos."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # No debe haber 'INVERSIONES FINANCIERAS FONDOS MUTUOS', sino 'Inversion Financiera Privado'
        assert 'INVERSIONES FINANCIERAS FONDOS MUTUOS' not in resultado['Cod_Pro'].values
    
    def test_crea_columna_instrumento(self, df_base_completa, df_fecha):
        """Verificar que crea columna Instrumento con primeros 3 caracteres."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        # Verificar que Instrumento tiene 3 caracteres
        assert (resultado['Instrumento'].str.len() == 3).all()


# =============================================================================
# TESTS DE genera_cartera_inv (PACTO)
# =============================================================================

class TestGeneraCarteraInvPacto:
    """Tests para genera_cartera_inv con tipo='pacto'."""
    
    def test_genera_cartera_pacto(self, df_base_completa, df_fecha):
        """Verificar que genera cartera de pactos correctamente."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'pacto', verbose=False)
        
        # Debe tener registros
        assert len(resultado) > 0
    
    def test_no_excluye_lch_en_pacto(self, df_base_completa, df_fecha):
        """Verificar que NO excluye LCH en pactos (solo en disponible)."""
        # Agregar un registro LCH con pacto
        df_con_lch_pacto = df_base_completa.copy()
        nuevo_registro = {
            'Fec_Pro': pd.Timestamp('2026-01-31'),
            'Cod_Emp': 1,
            'Moneda': 'CLF',
            'Cod_Pro': 'Inversion Financiera Corp',
            'Cod_Sub_Pro': 'SubPro_Pcto',
            'Nemotecnico': 'LCH999',
            'Clasificacion_Contable': 'AFS',
            'VP_Cap_Amort': 5000,
            'VP_Int_Total': 500,
            'Dias_Vcto': 100,
            'Dias_Pacto': 5,
        }
        df_con_lch_pacto = pd.concat([df_con_lch_pacto, pd.DataFrame([nuevo_registro])], ignore_index=True)
        
        resultado = genera_cartera_inv(df_con_lch_pacto, df_fecha, 'pacto', verbose=False)
        
        # LCH999 DEBE estar en pactos
        assert 'LCH999' in resultado['Nemotecnico'].values
    
    def test_incluye_dias_pacto(self, df_base_completa, df_fecha):
        """Verificar que incluye columna Dias_Pacto en pactos."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'pacto', verbose=False)
        
        assert 'Dias_Pacto' in resultado.columns
    
    def test_filtra_cod_sub_pro_pacto(self, df_base_completa, df_fecha):
        """Verificar que filtra por sufijos de Cod_Sub_Pro para pacto."""
        resultado = genera_cartera_inv(df_base_completa, df_fecha, 'pacto', verbose=False)
        
        # Solo deben estar los pactos (índice 4, 5)
        assert 'BCU005' in resultado['Nemotecnico'].values
        assert 'BTU006' in resultado['Nemotecnico'].values


# =============================================================================
# TESTS DE VALIDACIÓN
# =============================================================================

class TestValidacion:
    """Tests de validación de parámetros."""
    
    def test_tipo_invalido_genera_error(self, df_base_completa, df_fecha):
        """Verificar que tipo inválido genera ValueError."""
        with pytest.raises(ValueError, match="tipo='invalido' inválido"):
            genera_cartera_inv(df_base_completa, df_fecha, 'invalido', verbose=False)


# =============================================================================
# TESTS DE FUNCIONES DEPRECADAS
# =============================================================================

class TestFuncionesDeprecadas:
    """Tests para funciones deprecadas (compatibilidad)."""
    
    def test_genera_cartera_inv_001_genera_warning(self, df_base_completa, df_fecha):
        """Verificar que genera_cartera_inv_001 genera DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            resultado = genera_cartera_inv_001(df_base_completa, df_fecha, verbose=False)
            
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecado" in str(w[0].message).lower()
    
    def test_genera_cartera_inv_001_retorna_igual(self, df_base_completa, df_fecha):
        """Verificar que genera_cartera_inv_001 retorna mismo resultado que la nueva."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            resultado_viejo = genera_cartera_inv_001(df_base_completa, df_fecha, verbose=False)
        
        resultado_nuevo = genera_cartera_inv(df_base_completa, df_fecha, 'disponible', verbose=False)
        
        pd.testing.assert_frame_equal(resultado_viejo, resultado_nuevo)
    
    def test_genera_cartera_inv_pacto_genera_warning(self, df_base_completa, df_fecha):
        """Verificar que genera_cartera_inv_pacto genera DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            resultado = genera_cartera_inv_pacto(df_base_completa, df_fecha, verbose=False)
            
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
