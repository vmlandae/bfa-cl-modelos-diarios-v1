"""
Configuración de instrumentos financieros para el modelo de inversiones.

Este módulo centraliza todos los parámetros de configuración por instrumento,
evitando duplicación entre helpers.py y generador_tabla_final.py.

Uso:
    from config.instrumentos import INSTRUMENTOS, obtener_instrumento
    
    config = INSTRUMENTOS['GobCLP']
    print(config.codigos_disp)  # ['BCP', 'BTP', 'PDB']
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set


# =============================================================================
# CONSTANTES DE VALIDACIÓN
# =============================================================================

MONEDAS_VALIDAS: Set[str] = {'CLP', 'CLF', 'USD'}
"""Monedas soportadas. USD reservado para futuro DPX (depósitos en dólares)."""

PREFIJOS_TABLAS_FACTORES: Set[str] = {'RF_FactCLP_', 'RF_FactCLF_', 'RF_FactUSD_'}
"""Prefijos válidos para tablas de factores de descuento."""

CODIGOS_NEMOTECNICO_CONOCIDOS: Set[str] = {
    # Gobierno
    'BCP', 'BTP', 'PDB',  # CLP
    'BCU', 'BTU', 'CER',  # CLF
    # Bancarios/Corporativos
    'DPF', 'DPR', 'BBC', 'LCH', 'FFM',
    # Futuro: USD
    'DPX',  # TODO: Depósitos en dólares
}
"""Códigos de nemotécnico conocidos (para validación de warnings)."""


# =============================================================================
# DATACLASS DE CONFIGURACIÓN
# =============================================================================

@dataclass(frozen=True)
class ConfigInstrumento:
    """Configuración de un instrumento financiero para liquidación.
    
    Attributes:
        nombre_completo: Nombre descriptivo del instrumento.
        codigos_disp: Códigos de nemotécnico para cartera disponible.
        codigos_pacto: Códigos de nemotécnico para cartera en pacto.
        moneda: Moneda del instrumento ('CLP', 'CLF' o 'USD').
        tabla_factores: Nombre de tabla Access con factores de descuento.
        instrumento_fpl: Nombre usado en tabla RF_FPL_inv_diario.
        instrumento_montos_liq: Nombre usado en tabla RF_MontosLiq.
        nombre_salida: Nombre para el DataFrame de salida (ej: 'Flujo_GobCLP').
        cod_sub_pro_final: Código Cod_Sub_Pro para tabla final.
        filtro_moneda: Moneda para filtrar (None = no filtrar por moneda).
        activo: Si el instrumento está activo (False para futuros/deprecados).
    
    Raises:
        ValueError: Si algún campo no pasa validación.
    """
    nombre_completo: str
    codigos_disp: List[str]
    codigos_pacto: List[str]
    moneda: str
    tabla_factores: str
    instrumento_fpl: str
    instrumento_montos_liq: str
    nombre_salida: str
    cod_sub_pro_final: str
    filtro_moneda: Optional[str] = None
    activo: bool = True
    
    def __post_init__(self):
        """Validaciones al crear la instancia."""
        errores = []
        warnings = []
        
        # --- Validaciones críticas (errores) ---
        
        # Moneda válida
        if self.moneda not in MONEDAS_VALIDAS:
            errores.append(
                f"moneda='{self.moneda}' inválida. Válidas: {MONEDAS_VALIDAS}"
            )
        
        # filtro_moneda válido (si se especifica)
        if self.filtro_moneda is not None and self.filtro_moneda not in MONEDAS_VALIDAS:
            errores.append(
                f"filtro_moneda='{self.filtro_moneda}' inválido. Válidas: {MONEDAS_VALIDAS}"
            )
        
        # Listas no vacías
        if not self.codigos_disp:
            errores.append("codigos_disp no puede estar vacío")
        
        if not self.codigos_pacto:
            errores.append("codigos_pacto no puede estar vacío")
        
        # Strings no vacíos
        campos_requeridos = [
            ('nombre_completo', self.nombre_completo),
            ('tabla_factores', self.tabla_factores),
            ('instrumento_fpl', self.instrumento_fpl),
            ('instrumento_montos_liq', self.instrumento_montos_liq),
            ('nombre_salida', self.nombre_salida),
            ('cod_sub_pro_final', self.cod_sub_pro_final),
        ]
        for nombre_campo, valor in campos_requeridos:
            if not valor or not valor.strip():
                errores.append(f"{nombre_campo} no puede estar vacío")
        
        # Prefijo de tabla_factores válido
        if self.tabla_factores:
            prefijo_valido = any(
                self.tabla_factores.startswith(p) for p in PREFIJOS_TABLAS_FACTORES
            )
            if not prefijo_valido:
                errores.append(
                    f"tabla_factores='{self.tabla_factores}' debe empezar con "
                    f"uno de: {PREFIJOS_TABLAS_FACTORES}"
                )
        
        # Consistencia moneda/tabla_factores
        if self.tabla_factores and self.moneda:
            esperado = f"RF_Fact{self.moneda}_"
            if not self.tabla_factores.startswith(esperado):
                errores.append(
                    f"tabla_factores='{self.tabla_factores}' inconsistente con "
                    f"moneda='{self.moneda}'. Esperado prefijo: '{esperado}'"
                )
        
        # nombre_salida debe empezar con 'Flujo_'
        if self.nombre_salida and not self.nombre_salida.startswith('Flujo_'):
            errores.append(
                f"nombre_salida='{self.nombre_salida}' debe empezar con 'Flujo_'"
            )
        
        # cod_sub_pro_final debe empezar con 'ML_C46_'
        if self.cod_sub_pro_final and not self.cod_sub_pro_final.startswith('ML_C46_'):
            errores.append(
                f"cod_sub_pro_final='{self.cod_sub_pro_final}' debe empezar con 'ML_C46_'"
            )
        
        # --- Validaciones de advertencia (warnings, no bloquean) ---
        
        # Códigos desconocidos
        todos_codigos = set(self.codigos_disp) | set(self.codigos_pacto)
        desconocidos = todos_codigos - CODIGOS_NEMOTECNICO_CONOCIDOS
        if desconocidos:
            warnings.append(
                f"Códigos no reconocidos: {desconocidos}. "
                f"Si es correcto, agregar a CODIGOS_NEMOTECNICO_CONOCIDOS."
            )
        
        # Emitir errores si los hay
        if errores:
            msg = f"ConfigInstrumento '{self.nombre_completo}' inválido:\n"
            msg += "\n".join(f"  - {e}" for e in errores)
            raise ValueError(msg)
        
        # Emitir warnings (no bloquean, solo informan)
        if warnings:
            import warnings as warn_module
            for w in warnings:
                warn_module.warn(f"ConfigInstrumento '{self.nombre_completo}': {w}")


# =============================================================================
# CONFIGURACIÓN DE INSTRUMENTOS
# =============================================================================

INSTRUMENTOS: Dict[str, ConfigInstrumento] = {
    
    # -------------------------------------------------------------------------
    # GOBIERNO
    # -------------------------------------------------------------------------
    
    'GobCLP': ConfigInstrumento(
        nombre_completo='Gobierno CLP',
        codigos_disp=['BCP', 'BTP', 'PDB'],
        codigos_pacto=['BCP', 'BTP', 'PDB'],
        moneda='CLP',
        tabla_factores='RF_FactCLP_Gob',
        instrumento_fpl='Gobierno CLP',
        instrumento_montos_liq='Gobierno CLP',
        nombre_salida='Flujo_GobCLP',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_GOBCLP',
        # Sin filtro_moneda: ya están en CLP por código
    ),
    
    'GobCLF': ConfigInstrumento(
        nombre_completo='Gobierno CLF',
        codigos_disp=['BCU', 'BTU'],
        codigos_pacto=['BCU', 'BTU', 'CER'],  # Nota: incluye CER en pactos
        moneda='CLF',
        tabla_factores='RF_FactCLF_Gob',
        instrumento_fpl='Gobierno CLF',
        instrumento_montos_liq='Gobierno CLF',
        nombre_salida='Flujo_GobCLF',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_GOBCLF',
    ),
    
    # -------------------------------------------------------------------------
    # DEPÓSITOS A PLAZO
    # -------------------------------------------------------------------------
    
    'DPF': ConfigInstrumento(
        nombre_completo='Depósito a Plazo Fijo',
        codigos_disp=['DPF'],
        codigos_pacto=['DPF', 'FFM'],  # Nota: incluye FFM (Fondos Mutuos) en pactos
        moneda='CLP',
        tabla_factores='RF_FactCLP_Banc',
        instrumento_fpl='DPF',
        instrumento_montos_liq='DPF',
        nombre_salida='Flujo_DPF',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_DPFCLP',
    ),
    
    'DPR': ConfigInstrumento(
        nombre_completo='Depósito a Plazo Reajustable',
        codigos_disp=['DPR'],
        codigos_pacto=['DPR'],
        moneda='CLF',
        tabla_factores='RF_FactCLF_Banc',
        instrumento_fpl='DPR',
        instrumento_montos_liq='DPR',
        nombre_salida='Flujo_DPR',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_DPRCLF',
    ),
    
    # TODO: Implementar cuando se tengan depósitos en dólares
    # 'DPX': ConfigInstrumento(
    #     nombre_completo='Depósito a Plazo en Dólares',
    #     codigos_disp=['DPX'],
    #     codigos_pacto=['DPX'],
    #     moneda='USD',
    #     tabla_factores='RF_FactUSD_Banc',
    #     instrumento_fpl='DPX',
    #     instrumento_montos_liq='DPX',
    #     nombre_salida='Flujo_DPX',
    #     cod_sub_pro_final='ML_C46_Inversiones_Financieras_DPXUSD',
    #     activo=False,  # Desactivado hasta implementación
    # ),
    
    # -------------------------------------------------------------------------
    # CORPORATIVOS / BANCARIOS
    # -------------------------------------------------------------------------
    
    'BBC': ConfigInstrumento(
        nombre_completo='Bonos Bancarios Corporativos CLP',
        codigos_disp=['BBC'],
        codigos_pacto=['BBC'],
        moneda='CLP',
        tabla_factores='RF_FactCLP_Banc',
        instrumento_fpl='Corporativo CLP',
        instrumento_montos_liq='Corporativo CLP',
        nombre_salida='Flujo_BBC',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_CORPCLP',
        filtro_moneda='CLP',  # Filtrar solo BBC en CLP (existe BBC en CLF también)
    ),
    
    'LCH': ConfigInstrumento(
        nombre_completo='Letras Crédito Hipotecario + BBC CLF',
        codigos_disp=['LCH', 'BBC'],  # Combina LCH (cuando exista) + BBC en CLF
        codigos_pacto=['LCH', 'BBC'],
        moneda='CLF',
        tabla_factores='RF_FactCLF_Banc',
        instrumento_fpl='Corporativo CLF',
        instrumento_montos_liq='Corporativo CLF',
        nombre_salida='Flujo_LCH',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_LCHR',
        filtro_moneda='CLF',  # Filtrar solo los que están en CLF
    ),
}


# =============================================================================
# CONSTANTES GLOBALES PARA TABLA FINAL
# =============================================================================

COLUMNAS_TABLA_FINAL: List[str] = [
    'Fec_Pro',
    'Cod_Emp',
    'Moneda',
    'Cod_A_P',
    'Cod_Pro',
    'Cod_Sub_Pro',
    'Fec_Pago',
    'Dias_Pago',
    'Cap_Amort',
    'Int_Total_Cont',
    'VP_Cap_Amort',
    'VP_Int_Total_Cont',
]
"""Columnas requeridas para la tabla final de inversiones."""

CODIGO_EMPRESA: str = 'BFA'
"""Código de empresa para Banco Falabella."""

CODIGO_ACTIVO_PASIVO: str = 'A'
"""Código A/P: 'A' = Activo (inversiones son activos)."""

CODIGO_PRODUCTO: str = 'RF_Inversiones_Financieras'
"""Código de producto para inversiones financieras."""


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def obtener_instrumento(nombre: str) -> ConfigInstrumento:
    """Obtiene configuración de un instrumento con validación.
    
    Args:
        nombre: Clave del instrumento ('GobCLP', 'DPF', etc.)
    
    Returns:
        ConfigInstrumento con la configuración.
    
    Raises:
        KeyError: Si el instrumento no existe.
    
    Example:
        >>> config = obtener_instrumento('GobCLP')
        >>> config.moneda
        'CLP'
    """
    if nombre not in INSTRUMENTOS:
        disponibles = listar_instrumentos()
        raise KeyError(
            f"Instrumento '{nombre}' no existe. "
            f"Disponibles: {disponibles}"
        )
    return INSTRUMENTOS[nombre]


def listar_instrumentos(solo_activos: bool = True) -> List[str]:
    """Lista todos los instrumentos disponibles.
    
    Args:
        solo_activos: Si True, solo retorna instrumentos con activo=True.
    
    Returns:
        Lista de nombres de instrumentos.
    
    Example:
        >>> listar_instrumentos()
        ['GobCLP', 'GobCLF', 'DPF', 'DPR', 'BBC', 'LCH']
    """
    if solo_activos:
        return [k for k, v in INSTRUMENTOS.items() if v.activo]
    return list(INSTRUMENTOS.keys())


def obtener_instrumentos_por_moneda(moneda: str) -> Dict[str, ConfigInstrumento]:
    """Filtra instrumentos por moneda.
    
    Args:
        moneda: Moneda a filtrar ('CLP', 'CLF', 'USD').
    
    Returns:
        Dict con instrumentos de esa moneda.
    
    Raises:
        ValueError: Si la moneda no es válida.
    
    Example:
        >>> instrumentos_clp = obtener_instrumentos_por_moneda('CLP')
        >>> list(instrumentos_clp.keys())
        ['GobCLP', 'DPF', 'BBC']
    """
    if moneda not in MONEDAS_VALIDAS:
        raise ValueError(f"Moneda '{moneda}' inválida. Válidas: {MONEDAS_VALIDAS}")
    
    return {
        k: v for k, v in INSTRUMENTOS.items() 
        if v.moneda == moneda and v.activo
    }


def validar_configuracion_completa() -> bool:
    """Valida que toda la configuración sea consistente.
    
    Ejecuta validaciones cruzadas entre instrumentos.
    Útil para tests o al inicio del proceso.
    
    Returns:
        True si todo es válido.
    
    Raises:
        ValueError: Si hay inconsistencias.
    """
    errores = []
    
    # Verificar nombres_salida únicos
    nombres_salida = [v.nombre_salida for v in INSTRUMENTOS.values()]
    if len(nombres_salida) != len(set(nombres_salida)):
        duplicados = [n for n in nombres_salida if nombres_salida.count(n) > 1]
        errores.append(f"nombre_salida duplicados: {set(duplicados)}")
    
    # Verificar cod_sub_pro_final únicos
    codigos = [v.cod_sub_pro_final for v in INSTRUMENTOS.values()]
    if len(codigos) != len(set(codigos)):
        duplicados = [c for c in codigos if codigos.count(c) > 1]
        errores.append(f"cod_sub_pro_final duplicados: {set(duplicados)}")
    
    if errores:
        raise ValueError("Configuración inválida:\n" + "\n".join(f"  - {e}" for e in errores))
    
    return True


# =============================================================================
# VALIDACIÓN AL IMPORTAR
# =============================================================================

# Ejecutar validación completa al importar el módulo
# Esto asegura que cualquier error de configuración se detecte temprano
validar_configuracion_completa()
