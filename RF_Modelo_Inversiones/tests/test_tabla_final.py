"""
Tests para output/tabla_final.py

🚧 EN DESARROLLO - NO PRODUCTIVO 🚧
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fecha_proceso():
    """Fecha de proceso estándar para tests."""
    return 20260115


@pytest.fixture
def fecha_proceso_dt():
    """Fecha de proceso como datetime."""
    return pd.to_datetime('2026-01-15')


@pytest.fixture
def df_precios_dia():
    """DataFrame de precios del día simulado."""
    return pd.DataFrame({
        'Fecha': [pd.to_datetime('2026-01-15')],
        'NEMOTECNICO': ['TCRC'],
        'Instrumento': ['TCRC'],
        'Precio_Mid': [38500.50],
    })


@pytest.fixture
def df_precios_base():
    """DataFrame de precios históricos para filtrar."""
    return pd.DataFrame({
        'Fecha': [
            pd.to_datetime('2026-01-14'),
            pd.to_datetime('2026-01-15'),
            pd.to_datetime('2026-01-15'),
            pd.to_datetime('2026-01-16'),
        ],
        'NEMOTECNICO': ['TCRC', 'TCRC', 'DOLAR', 'TCRC'],
        'Instrumento': ['TCRC', 'TCRC', 'DOLAR', 'TCRC'],
        'Precio_Mid': [38450.00, 38500.50, 950.00, 38550.00],
    })


@pytest.fixture
def df_flujo_gob_clp():
    """Flujo de liquidación de GobCLP simulado."""
    return pd.DataFrame({
        'Dia': [0, 1, 2, 3, 5, 7],
        'Monto_Liquidar': [0, 100000, 150000, 200000, 180000, 120000],
        'Haircut': [1.0, 0.95, 0.90, 0.85, 0.75, 0.65],
    })


@pytest.fixture
def df_flujo_gob_clf():
    """Flujo de liquidación de GobCLF simulado."""
    return pd.DataFrame({
        'Dia': [1, 2, 3],
        'Monto_Liquidar': [50000, 75000, 60000],
        'Haircut': [0.95, 0.90, 0.85],
    })


@pytest.fixture
def flujos_instrumentos(df_flujo_gob_clp, df_flujo_gob_clf):
    """Diccionario completo de flujos por instrumento."""
    return {
        'GobCLP': df_flujo_gob_clp,
        'GobCLF': df_flujo_gob_clf,
        'DPF': pd.DataFrame({'Dia': [1, 2], 'Monto_Liquidar': [80000, 70000]}),
        'DPR': pd.DataFrame({'Dia': [1], 'Monto_Liquidar': [45000]}),
        'BBC': pd.DataFrame({'Dia': [1, 3], 'Monto_Liquidar': [30000, 25000]}),
        'LCH': pd.DataFrame({'Dia': [2], 'Monto_Liquidar': [20000]}),
    }


@pytest.fixture
def df_base_cartera():
    """Cartera base con garantías simulada."""
    return pd.DataFrame({
        'Fec_Pro': [pd.to_datetime('2026-01-15')] * 3,
        'Cod_Emp': [1, 1, 1],
        'Moneda': ['CLP', 'CLP', 'CLF'],
        'Cod_Pro': ['Inversion Financiera', 'Inversion Financiera', 'Inversion Financiera'],
        'Cod_Sub_Pro': ['Disp_Gtia', 'Disp_Gtia_Liq', 'Pcto_Gtia'],
        'Nemotecnico': ['BCP001', 'BTP002', 'BCU001'],
        'Cap_Amort': [100000, 150000, 80000],
        'Int_Total_Cont': [5000, 7000, 3000],
        'VP_Cap_Amort': [95000, 140000, 75000],
        'VP_Int_Total': [4500, 6500, 2800],
        'Dias_Liq': [2, 3, 5],
    })


@pytest.fixture
def df_pactos():
    """DataFrame de pactos simulado."""
    return pd.DataFrame({
        'Moneda': ['CLP', 'CLF'],
        'Dias_Pacto': [3, 5],
        'Monto': [200000, 150000],
    })


# =============================================================================
# TESTS PARA GENERAR_PRECIOS_DIA (PASO 20)
# =============================================================================

class TestGenerarPreciosDia:
    """Tests para generar_precios_dia()."""
    
    def test_filtra_por_fecha_e_instrumento(self, df_precios_base, fecha_proceso):
        """Debe filtrar correctamente por fecha e instrumento."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_precios_dia
        
        resultado = generar_precios_dia(
            df_precios_base,
            fecha_proceso,
            instrumento='TCRC',
            verbose=False
        )
        
        assert len(resultado) == 1
        assert resultado['Precio_Mid'].iloc[0] == 38500.50
    
    def test_columnas_correctas(self, df_precios_base, fecha_proceso):
        """Debe retornar las columnas esperadas."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_precios_dia
        
        resultado = generar_precios_dia(
            df_precios_base, fecha_proceso, verbose=False
        )
        
        assert list(resultado.columns) == ['Fecha', 'NEMOTECNICO', 'Instrumento', 'Precio_Mid']
    
    def test_fecha_como_int(self, df_precios_base):
        """Debe aceptar fecha como int YYYYMMDD."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_precios_dia
        
        resultado = generar_precios_dia(
            df_precios_base, 20260115, verbose=False
        )
        
        assert len(resultado) == 1
    
    def test_fecha_como_string(self, df_precios_base):
        """Debe aceptar fecha como string."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_precios_dia
        
        resultado = generar_precios_dia(
            df_precios_base, '2026-01-15', verbose=False
        )
        
        assert len(resultado) == 1
    
    def test_sin_coincidencias_retorna_vacio(self, df_precios_base):
        """Debe retornar DataFrame vacío si no hay coincidencias."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_precios_dia
        
        resultado = generar_precios_dia(
            df_precios_base, 20260120, verbose=False
        )
        
        assert len(resultado) == 0


# =============================================================================
# TESTS PARA FORMATEAR_FLUJO_INSTRUMENTO
# =============================================================================

class TestFormatearFlujoInstrumento:
    """Tests para formatear_flujo_instrumento()."""
    
    def test_formatea_correctamente(self, df_flujo_gob_clp, fecha_proceso):
        """Debe formatear flujo al esquema estándar."""
        from RF_Modelo_Inversiones.output.tabla_final import formatear_flujo_instrumento
        
        resultado = formatear_flujo_instrumento(
            df_flujo_gob_clp,
            fecha_proceso,
            moneda='CLP',
            cod_sub_pro='ML_C46_Inversiones_Financieras_GOBCLP',
            verbose=False
        )
        
        # Filtra Dia > 0 y Monto > 0
        assert len(resultado) == 5  # Excluye Dia=0
        assert all(resultado['Moneda'] == 'CLP')
        assert all(resultado['Cod_Sub_Pro'] == 'ML_C46_Inversiones_Financieras_GOBCLP')
    
    def test_calcula_fec_pago_correctamente(self, df_flujo_gob_clp, fecha_proceso_dt):
        """Debe calcular Fec_Pago = Fec_Pro + Dia."""
        from RF_Modelo_Inversiones.output.tabla_final import formatear_flujo_instrumento
        
        resultado = formatear_flujo_instrumento(
            df_flujo_gob_clp, fecha_proceso_dt, 'CLP', 'TEST', verbose=False
        )
        
        # Verificar primera fila (Dia=1)
        fila_dia_1 = resultado[resultado['Dias_Pago'] == 1].iloc[0]
        assert fila_dia_1['Fec_Pago'] == fecha_proceso_dt + pd.Timedelta(days=1)
    
    def test_excluye_dia_cero(self, fecha_proceso):
        """Debe excluir registros con Dia=0."""
        from RF_Modelo_Inversiones.output.tabla_final import formatear_flujo_instrumento
        
        df_con_dia_cero = pd.DataFrame({
            'Dia': [0, 1, 2],
            'Monto_Liquidar': [100, 200, 300]
        })
        
        resultado = formatear_flujo_instrumento(
            df_con_dia_cero, fecha_proceso, 'CLP', 'TEST', verbose=False
        )
        
        assert len(resultado) == 2
        assert 0 not in resultado['Dias_Pago'].values
    
    def test_excluye_monto_cero(self, fecha_proceso):
        """Debe excluir registros con Monto_Liquidar=0."""
        from RF_Modelo_Inversiones.output.tabla_final import formatear_flujo_instrumento
        
        df_con_monto_cero = pd.DataFrame({
            'Dia': [1, 2, 3],
            'Monto_Liquidar': [100, 0, 300]
        })
        
        resultado = formatear_flujo_instrumento(
            df_con_monto_cero, fecha_proceso, 'CLP', 'TEST', verbose=False
        )
        
        assert len(resultado) == 2


# =============================================================================
# TESTS PARA GENERAR_TABLA_FINAL_INVERSIONES (PASO 21)
# =============================================================================

class TestGenerarTablaFinalInversiones:
    """Tests para generar_tabla_final_inversiones()."""
    
    def test_concatena_todos_los_flujos(self, flujos_instrumentos, fecha_proceso):
        """Debe concatenar flujos de todos los instrumentos."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_tabla_final_inversiones
        
        resultado = generar_tabla_final_inversiones(
            flujos=flujos_instrumentos,
            fecha_proceso=fecha_proceso,
            verbose=False
        )
        
        # Verificar que hay registros de cada instrumento
        cod_sub_pros = resultado['Cod_Sub_Pro'].unique()
        assert any('GOBCLP' in c for c in cod_sub_pros)
        assert any('GOBCLF' in c for c in cod_sub_pros)
        assert any('DPFCLP' in c for c in cod_sub_pros)
    
    def test_incluye_garantias(self, flujos_instrumentos, df_base_cartera, fecha_proceso):
        """Debe incluir garantías si se proporciona df_base."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_tabla_final_inversiones
        
        resultado = generar_tabla_final_inversiones(
            flujos=flujos_instrumentos,
            fecha_proceso=fecha_proceso,
            df_base=df_base_cartera,
            verbose=False
        )
        
        assert any('Gtia' in str(c) for c in resultado['Cod_Sub_Pro'].unique())
    
    def test_incluye_pactos(self, flujos_instrumentos, df_pactos, fecha_proceso):
        """Debe incluir pactos si se proporcionan."""
        from RF_Modelo_Inversiones.output.tabla_final import generar_tabla_final_inversiones
        
        resultado = generar_tabla_final_inversiones(
            flujos=flujos_instrumentos,
            fecha_proceso=fecha_proceso,
            df_pactos=df_pactos,
            verbose=False
        )
        
        assert any('Pcto' in str(c) for c in resultado['Cod_Sub_Pro'].unique())
    
    def test_columnas_correctas(self, flujos_instrumentos, fecha_proceso):
        """Debe tener las columnas estándar."""
        from RF_Modelo_Inversiones.output.tabla_final import (
            generar_tabla_final_inversiones,
            COLUMNAS_TABLA_FINAL
        )
        
        resultado = generar_tabla_final_inversiones(
            flujos=flujos_instrumentos,
            fecha_proceso=fecha_proceso,
            verbose=False
        )
        
        for col in COLUMNAS_TABLA_FINAL:
            assert col in resultado.columns


# =============================================================================
# TESTS PARA AGREGAR_PRECIO_Y_FLUJO_CLP
# =============================================================================

class TestAgregarPrecioYFlujoCLP:
    """Tests para agregar_precio_y_flujo_clp()."""
    
    def test_agrega_precio_mid(self, df_precios_dia):
        """Debe agregar columna Precio_Mid."""
        from RF_Modelo_Inversiones.output.tabla_final import agregar_precio_y_flujo_clp
        
        df_inversiones = pd.DataFrame({
            'Moneda': ['CLP', 'CLF'],
            'Cap_Amort': [100000, 50000],
        })
        
        resultado = agregar_precio_y_flujo_clp(
            df_inversiones, df_precios_dia, verbose=False
        )
        
        assert 'Precio_Mid' in resultado.columns
        assert all(resultado['Precio_Mid'] == 38500.50)
    
    def test_calcula_flujo_clp_para_clp(self, df_precios_dia):
        """Para CLP, Flujo_CLP = Cap_Amort (sin conversión)."""
        from RF_Modelo_Inversiones.output.tabla_final import agregar_precio_y_flujo_clp
        
        df_inversiones = pd.DataFrame({
            'Moneda': ['CLP'],
            'Cap_Amort': [100000],
        })
        
        resultado = agregar_precio_y_flujo_clp(
            df_inversiones, df_precios_dia, verbose=False
        )
        
        assert resultado['Flujo_CLP'].iloc[0] == 100000
    
    def test_calcula_flujo_clp_para_clf(self, df_precios_dia):
        """Para CLF, Flujo_CLP = Cap_Amort * Precio_Mid."""
        from RF_Modelo_Inversiones.output.tabla_final import agregar_precio_y_flujo_clp
        
        df_inversiones = pd.DataFrame({
            'Moneda': ['CLF'],
            'Cap_Amort': [100],  # 100 UF
        })
        
        resultado = agregar_precio_y_flujo_clp(
            df_inversiones, df_precios_dia, verbose=False
        )
        
        expected = 100 * 38500.50
        assert resultado['Flujo_CLP'].iloc[0] == expected


# =============================================================================
# TESTS PARA FORMATEAR_PARA_EXCEL (PASO 27)
# =============================================================================

class TestFormatearParaExcel:
    """Tests para formatear_para_excel()."""
    
    def test_renombra_columnas(self, df_precios_dia):
        """Debe renombrar columnas según MAPEO_COLUMNAS_EXCEL."""
        from RF_Modelo_Inversiones.output.tabla_final import (
            formatear_para_excel,
            agregar_precio_y_flujo_clp
        )
        
        df_base = pd.DataFrame({
            'Fec_Pro': [pd.to_datetime('2026-01-15')],
            'Cod_Emp': [1],
            'Moneda': ['CLP'],
            'Cod_A_P': ['ACT'],
            'Cod_Pro': ['ML_C46'],
            'Cod_Sub_Pro': ['TEST'],
            'Fec_Pago': [pd.to_datetime('2026-01-16')],
            'Dias_Pago': [1],
            'Cap_Amort': [100000],
            'Int_Total_Cont': [5000],
            'VP_Cap_Amort': [95000],
            'VP_Int_Total_Cont': [4500],
        })
        
        df_con_precio = agregar_precio_y_flujo_clp(df_base, df_precios_dia, verbose=False)
        resultado = formatear_para_excel(df_con_precio, verbose=False)
        
        assert 'FECHA PROCESO' in resultado.columns
        assert 'FLUJO_CAPITAL' in resultado.columns
        assert 'FLUJO_CLP' in resultado.columns
    
    def test_agrega_columnas_constantes(self, df_precios_dia):
        """Debe agregar OPERACION, MONEDA_COMPENSACION, COMPENSACION."""
        from RF_Modelo_Inversiones.output.tabla_final import (
            formatear_para_excel,
            agregar_precio_y_flujo_clp
        )
        
        df_base = pd.DataFrame({
            'Fec_Pro': [pd.to_datetime('2026-01-15')],
            'Cod_Emp': [1],
            'Moneda': ['CLP'],
            'Cod_A_P': ['ACT'],
            'Cod_Pro': ['ML_C46'],
            'Cod_Sub_Pro': ['TEST'],
            'Fec_Pago': [pd.to_datetime('2026-01-16')],
            'Dias_Pago': [1],
            'Cap_Amort': [100000],
            'Int_Total_Cont': [5000],
            'VP_Cap_Amort': [95000],
            'VP_Int_Total_Cont': [4500],
        })
        
        df_con_precio = agregar_precio_y_flujo_clp(df_base, df_precios_dia, verbose=False)
        resultado = formatear_para_excel(df_con_precio, verbose=False)
        
        assert 'OPERACION' in resultado.columns
        assert resultado['OPERACION'].iloc[0] == 'INVERSIONES'
        assert resultado['COMPENSACION'].iloc[0] == 'NO'


# =============================================================================
# TESTS DE INTEGRACIÓN
# =============================================================================

class TestIntegracionCompleta:
    """Tests de integración end-to-end."""
    
    def test_ejecutar_pasos_20_a_27(self, flujos_instrumentos, df_precios_base, fecha_proceso):
        """Debe ejecutar todos los pasos sin errores."""
        from RF_Modelo_Inversiones.output.tabla_final import ejecutar_pasos_20_a_27
        
        tablas = {
            'RF_Base_Diaria_Precios': df_precios_base,
        }
        
        resultado = ejecutar_pasos_20_a_27(
            flujos=flujos_instrumentos,
            tablas=tablas,
            fecha_proceso=fecha_proceso,
            verbose=False
        )
        
        assert 'precios_dia' in resultado
        assert 'tabla_final_inversiones' in resultado
        assert 'tabla_desarrollo' in resultado
        assert 'tabla_excel' in resultado
        
        # Verificar que tabla_excel tiene datos
        assert len(resultado['tabla_excel']) > 0
    
    def test_flujo_clp_suma_correcta(self, flujos_instrumentos, df_precios_base, fecha_proceso):
        """El total de Flujo_CLP debe ser consistente."""
        from RF_Modelo_Inversiones.output.tabla_final import ejecutar_pasos_20_a_27
        
        tablas = {
            'RF_Base_Diaria_Precios': df_precios_base,
        }
        
        resultado = ejecutar_pasos_20_a_27(
            flujos=flujos_instrumentos,
            tablas=tablas,
            fecha_proceso=fecha_proceso,
            verbose=False
        )
        
        # Flujo_CLP debe ser > 0
        assert resultado['tabla_desarrollo']['Flujo_CLP'].sum() > 0


# =============================================================================
# TESTS DE VALIDACIÓN DE CONSTANTES
# =============================================================================

class TestConstantes:
    """Tests para validar constantes del módulo."""
    
    def test_columnas_tabla_final_no_vacia(self):
        """COLUMNAS_TABLA_FINAL debe tener elementos."""
        from RF_Modelo_Inversiones.output.tabla_final import COLUMNAS_TABLA_FINAL
        
        assert len(COLUMNAS_TABLA_FINAL) > 0
    
    def test_mapeo_columnas_excel_completo(self):
        """MAPEO_COLUMNAS_EXCEL debe mapear COLUMNAS_TABLA_DESARROLLO."""
        from RF_Modelo_Inversiones.output.tabla_final import (
            MAPEO_COLUMNAS_EXCEL,
            COLUMNAS_TABLA_DESARROLLO
        )
        
        for col in COLUMNAS_TABLA_DESARROLLO:
            assert col in MAPEO_COLUMNAS_EXCEL, f"Falta mapeo para {col}"
