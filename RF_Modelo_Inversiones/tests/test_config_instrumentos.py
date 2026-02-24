"""
Tests para RF_Modelo_Inversiones/config/instrumentos.py

Ejecutar con:
    pytest RF_Modelo_Inversiones/tests/test_config_instrumentos.py -v
    
O desde la raíz del proyecto:
    python -m pytest RF_Modelo_Inversiones/tests/ -v
"""

import pytest
import warnings
from typing import List


# =============================================================================
# IMPORTS DEL MÓDULO A TESTEAR
# =============================================================================

from RF_Modelo_Inversiones.config.instrumentos import (
    # Dataclass y constantes
    ConfigInstrumento,
    INSTRUMENTOS,
    MONEDAS_VALIDAS,
    COLUMNAS_TABLA_FINAL,
    CODIGO_EMPRESA,
    CODIGO_ACTIVO_PASIVO,
    CODIGO_PRODUCTO,
    CODIGOS_NEMOTECNICO_CONOCIDOS,
    PREFIJOS_TABLAS_FACTORES,
    # Funciones
    obtener_instrumento,
    listar_instrumentos,
    obtener_instrumentos_por_moneda,
    validar_configuracion_completa,
)


# =============================================================================
# TESTS DE CONSTANTES
# =============================================================================

class TestConstantes:
    """Tests para las constantes del módulo."""
    
    def test_monedas_validas_contiene_clp_clf_usd(self):
        """Verificar que las monedas válidas incluyen CLP, CLF y USD."""
        assert 'CLP' in MONEDAS_VALIDAS
        assert 'CLF' in MONEDAS_VALIDAS
        assert 'USD' in MONEDAS_VALIDAS
    
    def test_codigo_empresa_es_bfa(self):
        """Verificar que el código de empresa es BFA."""
        assert CODIGO_EMPRESA == 'BFA'
    
    def test_codigo_activo_pasivo_es_a(self):
        """Verificar que el código A/P es 'A' (Activo)."""
        assert CODIGO_ACTIVO_PASIVO == 'A'
    
    def test_columnas_tabla_final_tiene_12_columnas(self):
        """Verificar que la tabla final tiene las 12 columnas esperadas."""
        assert len(COLUMNAS_TABLA_FINAL) == 12
        assert 'Fec_Pro' in COLUMNAS_TABLA_FINAL
        assert 'VP_Cap_Amort' in COLUMNAS_TABLA_FINAL
    
    def test_prefijos_tablas_factores_validos(self):
        """Verificar que los prefijos de tablas de factores son correctos."""
        assert 'RF_FactCLP_' in PREFIJOS_TABLAS_FACTORES
        assert 'RF_FactCLF_' in PREFIJOS_TABLAS_FACTORES
        assert 'RF_FactUSD_' in PREFIJOS_TABLAS_FACTORES


# =============================================================================
# TESTS DE ConfigInstrumento DATACLASS
# =============================================================================

class TestConfigInstrumento:
    """Tests para la dataclass ConfigInstrumento."""
    
    def test_crear_instrumento_valido(self):
        """Verificar que se puede crear un instrumento válido."""
        cfg = ConfigInstrumento(
            nombre_completo='Test Instrumento',
            codigos_disp=['TST'],
            codigos_pacto=['TST'],
            moneda='CLP',
            tabla_factores='RF_FactCLP_Test',
            instrumento_fpl='Test',
            instrumento_montos_liq='Test',
            nombre_salida='Flujo_Test',
            cod_sub_pro_final='ML_C46_Test',
        )
        assert cfg.moneda == 'CLP'
        assert cfg.codigos_disp == ['TST']
    
    def test_instrumento_es_inmutable(self):
        """Verificar que ConfigInstrumento es inmutable (frozen=True)."""
        cfg = ConfigInstrumento(
            nombre_completo='Test',
            codigos_disp=['TST'],
            codigos_pacto=['TST'],
            moneda='CLP',
            tabla_factores='RF_FactCLP_Test',
            instrumento_fpl='Test',
            instrumento_montos_liq='Test',
            nombre_salida='Flujo_Test',
            cod_sub_pro_final='ML_C46_Test',
        )
        with pytest.raises(AttributeError):
            cfg.moneda = 'CLF'  # No debería permitirse
    
    def test_validacion_moneda_invalida(self):
        """Verificar que moneda inválida genera ValueError."""
        with pytest.raises(ValueError, match="moneda='EUR' inválida"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=['TST'],
                moneda='EUR',  # Inválida
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_codigos_disp_vacio(self):
        """Verificar que codigos_disp vacío genera ValueError."""
        with pytest.raises(ValueError, match="codigos_disp no puede estar vacío"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=[],  # Vacío
                codigos_pacto=['TST'],
                moneda='CLP',
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_codigos_pacto_vacio(self):
        """Verificar que codigos_pacto vacío genera ValueError."""
        with pytest.raises(ValueError, match="codigos_pacto no puede estar vacío"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=[],  # Vacío
                moneda='CLP',
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_tabla_factores_prefijo_invalido(self):
        """Verificar que prefijo de tabla_factores inválido genera error."""
        with pytest.raises(ValueError, match="tabla_factores='INVALID_Tabla' debe empezar"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=['TST'],
                moneda='CLP',
                tabla_factores='INVALID_Tabla',  # Prefijo inválido
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_consistencia_moneda_tabla_factores(self):
        """Verificar que moneda y tabla_factores deben ser consistentes."""
        with pytest.raises(ValueError, match="inconsistente con moneda='CLF'"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=['TST'],
                moneda='CLF',  # CLF
                tabla_factores='RF_FactCLP_Test',  # Pero tabla es CLP
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_nombre_salida_sin_prefijo_flujo(self):
        """Verificar que nombre_salida debe empezar con 'Flujo_'."""
        with pytest.raises(ValueError, match="nombre_salida='Output_Test' debe empezar con 'Flujo_'"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=['TST'],
                moneda='CLP',
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Output_Test',  # Sin prefijo Flujo_
                cod_sub_pro_final='ML_C46_Test',
            )
    
    def test_validacion_cod_sub_pro_sin_prefijo_ml_c46(self):
        """Verificar que cod_sub_pro_final debe empezar con 'ML_C46_'."""
        with pytest.raises(ValueError, match="cod_sub_pro_final='INVALID_Test' debe empezar con 'ML_C46_'"):
            ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['TST'],
                codigos_pacto=['TST'],
                moneda='CLP',
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='INVALID_Test',  # Sin prefijo ML_C46_
            )
    
    def test_warning_codigo_desconocido(self):
        """Verificar que código desconocido genera warning (no error)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = ConfigInstrumento(
                nombre_completo='Test',
                codigos_disp=['NUEVO_CODIGO'],  # Código desconocido
                codigos_pacto=['NUEVO_CODIGO'],
                moneda='CLP',
                tabla_factores='RF_FactCLP_Test',
                instrumento_fpl='Test',
                instrumento_montos_liq='Test',
                nombre_salida='Flujo_Test',
                cod_sub_pro_final='ML_C46_Test',
            )
            # Debe haberse generado un warning
            assert len(w) >= 1
            assert "NUEVO_CODIGO" in str(w[0].message)
    
    def test_filtro_moneda_valido(self):
        """Verificar que filtro_moneda acepta valores válidos."""
        cfg = ConfigInstrumento(
            nombre_completo='Test',
            codigos_disp=['TST'],
            codigos_pacto=['TST'],
            moneda='CLP',
            tabla_factores='RF_FactCLP_Test',
            instrumento_fpl='Test',
            instrumento_montos_liq='Test',
            nombre_salida='Flujo_Test',
            cod_sub_pro_final='ML_C46_Test',
            filtro_moneda='CLP',  # Válido
        )
        assert cfg.filtro_moneda == 'CLP'
    
    def test_filtro_moneda_none_es_valido(self):
        """Verificar que filtro_moneda=None es válido (no filtrar)."""
        cfg = ConfigInstrumento(
            nombre_completo='Test',
            codigos_disp=['TST'],
            codigos_pacto=['TST'],
            moneda='CLP',
            tabla_factores='RF_FactCLP_Test',
            instrumento_fpl='Test',
            instrumento_montos_liq='Test',
            nombre_salida='Flujo_Test',
            cod_sub_pro_final='ML_C46_Test',
            filtro_moneda=None,
        )
        assert cfg.filtro_moneda is None
    
    def test_campo_activo_default_true(self):
        """Verificar que activo=True por defecto."""
        cfg = ConfigInstrumento(
            nombre_completo='Test',
            codigos_disp=['TST'],
            codigos_pacto=['TST'],
            moneda='CLP',
            tabla_factores='RF_FactCLP_Test',
            instrumento_fpl='Test',
            instrumento_montos_liq='Test',
            nombre_salida='Flujo_Test',
            cod_sub_pro_final='ML_C46_Test',
        )
        assert cfg.activo is True


# =============================================================================
# TESTS DE INSTRUMENTOS PREDEFINIDOS
# =============================================================================

class TestInstrumentosPredefinidos:
    """Tests para los instrumentos predefinidos en INSTRUMENTOS."""
    
    def test_existen_6_instrumentos(self):
        """Verificar que existen exactamente 6 instrumentos activos."""
        assert len(INSTRUMENTOS) == 6
    
    def test_instrumentos_esperados_existen(self):
        """Verificar que los 6 instrumentos esperados existen."""
        esperados = ['GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH']
        for instrumento in esperados:
            assert instrumento in INSTRUMENTOS, f"Falta instrumento: {instrumento}"
    
    @pytest.mark.parametrize("instrumento,moneda_esperada", [
        ('GobCLP', 'CLP'),
        ('GobCLF', 'CLF'),
        ('DPF', 'CLP'),
        ('DPR', 'CLF'),
        ('BBC', 'CLP'),
        ('LCH', 'CLF'),
    ])
    def test_moneda_correcta_por_instrumento(self, instrumento: str, moneda_esperada: str):
        """Verificar que cada instrumento tiene la moneda correcta."""
        cfg = INSTRUMENTOS[instrumento]
        assert cfg.moneda == moneda_esperada
    
    def test_gobclp_codigos_correctos(self):
        """Verificar códigos de GobCLP."""
        cfg = INSTRUMENTOS['GobCLP']
        assert 'BCP' in cfg.codigos_disp
        assert 'BTP' in cfg.codigos_disp
        assert 'PDB' in cfg.codigos_disp
    
    def test_gobclf_codigos_correctos(self):
        """Verificar códigos de GobCLF."""
        cfg = INSTRUMENTOS['GobCLF']
        assert 'BCU' in cfg.codigos_disp
        assert 'BTU' in cfg.codigos_disp
        # CER solo en pactos
        assert 'CER' in cfg.codigos_pacto
        assert 'CER' not in cfg.codigos_disp
    
    def test_dpf_incluye_ffm_en_pactos(self):
        """Verificar que DPF incluye FFM en pactos."""
        cfg = INSTRUMENTOS['DPF']
        assert 'FFM' in cfg.codigos_pacto
        assert 'FFM' not in cfg.codigos_disp
    
    def test_lch_combina_lch_y_bbc(self):
        """Verificar que LCH combina LCH y BBC."""
        cfg = INSTRUMENTOS['LCH']
        assert 'LCH' in cfg.codigos_disp
        assert 'BBC' in cfg.codigos_disp
        assert cfg.filtro_moneda == 'CLF'
    
    def test_bbc_filtra_por_clp(self):
        """Verificar que BBC filtra por CLP."""
        cfg = INSTRUMENTOS['BBC']
        assert cfg.filtro_moneda == 'CLP'
    
    def test_todos_instrumentos_son_activos(self):
        """Verificar que todos los instrumentos están activos."""
        for nombre, cfg in INSTRUMENTOS.items():
            assert cfg.activo is True, f"{nombre} debería estar activo"


# =============================================================================
# TESTS DE FUNCIONES DE UTILIDAD
# =============================================================================

class TestObtenerInstrumento:
    """Tests para la función obtener_instrumento()."""
    
    def test_obtener_instrumento_existente(self):
        """Verificar que obtener_instrumento devuelve el instrumento correcto."""
        cfg = obtener_instrumento('GobCLP')
        assert cfg.nombre_completo == 'Gobierno CLP'
    
    def test_obtener_instrumento_inexistente_genera_keyerror(self):
        """Verificar que obtener_instrumento con key inválida genera KeyError."""
        with pytest.raises(KeyError, match="Instrumento 'INEXISTENTE' no existe"):
            obtener_instrumento('INEXISTENTE')
    
    def test_obtener_instrumento_mensaje_incluye_disponibles(self):
        """Verificar que el error incluye la lista de instrumentos disponibles."""
        with pytest.raises(KeyError) as exc_info:
            obtener_instrumento('INEXISTENTE')
        assert "GobCLP" in str(exc_info.value)


class TestListarInstrumentos:
    """Tests para la función listar_instrumentos()."""
    
    def test_listar_instrumentos_retorna_lista(self):
        """Verificar que listar_instrumentos retorna una lista."""
        resultado = listar_instrumentos()
        assert isinstance(resultado, list)
    
    def test_listar_instrumentos_tiene_6_elementos(self):
        """Verificar que hay 6 instrumentos activos."""
        resultado = listar_instrumentos(solo_activos=True)
        assert len(resultado) == 6
    
    def test_listar_instrumentos_incluye_gobclp(self):
        """Verificar que GobCLP está en la lista."""
        resultado = listar_instrumentos()
        assert 'GobCLP' in resultado


class TestObtenerInstrumentosPorMoneda:
    """Tests para la función obtener_instrumentos_por_moneda()."""
    
    def test_instrumentos_clp(self):
        """Verificar instrumentos en CLP."""
        resultado = obtener_instrumentos_por_moneda('CLP')
        assert 'GobCLP' in resultado
        assert 'DPF' in resultado
        assert 'BBC' in resultado
        assert len(resultado) == 3
    
    def test_instrumentos_clf(self):
        """Verificar instrumentos en CLF."""
        resultado = obtener_instrumentos_por_moneda('CLF')
        assert 'GobCLF' in resultado
        assert 'DPR' in resultado
        assert 'LCH' in resultado
        assert len(resultado) == 3
    
    def test_instrumentos_usd_vacio(self):
        """Verificar que no hay instrumentos en USD (aún)."""
        resultado = obtener_instrumentos_por_moneda('USD')
        assert len(resultado) == 0
    
    def test_moneda_invalida_genera_error(self):
        """Verificar que moneda inválida genera ValueError."""
        with pytest.raises(ValueError, match="Moneda 'EUR' inválida"):
            obtener_instrumentos_por_moneda('EUR')


class TestValidarConfiguracionCompleta:
    """Tests para la función validar_configuracion_completa()."""
    
    def test_configuracion_actual_es_valida(self):
        """Verificar que la configuración actual pasa validación."""
        # No debería generar excepción
        resultado = validar_configuracion_completa()
        assert resultado is True
    
    def test_nombres_salida_unicos(self):
        """Verificar que todos los nombre_salida son únicos."""
        nombres = [cfg.nombre_salida for cfg in INSTRUMENTOS.values()]
        assert len(nombres) == len(set(nombres)), "Hay nombre_salida duplicados"
    
    def test_cod_sub_pro_final_unicos(self):
        """Verificar que todos los cod_sub_pro_final son únicos."""
        codigos = [cfg.cod_sub_pro_final for cfg in INSTRUMENTOS.values()]
        assert len(codigos) == len(set(codigos)), "Hay cod_sub_pro_final duplicados"


# =============================================================================
# TESTS DE INTEGRACIÓN
# =============================================================================

class TestIntegracion:
    """Tests de integración para el módulo completo."""
    
    def test_import_desde_init(self):
        """Verificar que se puede importar desde __init__.py."""
        from RF_Modelo_Inversiones.config import (
            INSTRUMENTOS,
            ConfigInstrumento,
            obtener_instrumento,
        )
        assert INSTRUMENTOS is not None
    
    def test_validacion_se_ejecuta_al_importar(self):
        """Verificar que la validación se ejecuta al importar el módulo."""
        # Si llegamos aquí sin error, la validación pasó al importar
        import RF_Modelo_Inversiones.config.instrumentos
        assert True
    
    def test_instrumentos_usables_en_loop(self):
        """Verificar que se puede iterar sobre instrumentos."""
        for nombre, cfg in INSTRUMENTOS.items():
            # Cada instrumento debe tener los atributos básicos
            assert hasattr(cfg, 'moneda')
            assert hasattr(cfg, 'codigos_disp')
            assert hasattr(cfg, 'tabla_factores')


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
