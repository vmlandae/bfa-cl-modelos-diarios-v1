# Plan de Implementación: Refactorización RF_Modelo_Inversiones

> **Documento**: Plan de implementación detallado  
> **Fecha**: 2026-02-03  
> **Última actualización**: 2026-02-03  
> **Branch**: `feat/modelo-inversiones`  
> **Estado**: 🚧 EN DESARROLLO (NO PRODUCTIVO)

⚠️ **IMPORTANTE**: Este módulo está en desarrollo activo. Los cambios realizados
aún NO están integrados en producción. La rama `feat/modelo-inversiones` contiene
refactorizaciones que deben ser validadas antes de merge a `main`.

---

## Resumen de Progreso

| Fase | Estado | Progreso | Tests |
|------|--------|----------|-------|
| Fase 1: Centralizar Configuración | ✅ Completada | 100% | 48 tests |
| Fase 2: Refactorizar Cache | ✅ Completada | 100% | 22 tests |
| Fase 3: Unificar Cartera | ✅ Completada | 100% | 36 tests |
| Fase 4: Reorganizar Módulos | ⬜ Pendiente | 0% | - |
| Fase 5: Integración y Tests | 🔄 En progreso | 100% (106 tests) | 106 tests |

**Total tests: 106 pasando** ✅

---

## Fase 1: Centralizar Configuración ✅ COMPLETADA

### 1.1 Crear módulo de configuración
- [x] Crear directorio `RF_Modelo_Inversiones/config/`
- [x] Crear `config/__init__.py` con exports
- [x] Crear `config/instrumentos.py` con dataclass `ConfigInstrumento`

### 1.2 Definir estructura de datos
- [x] Implementar `@dataclass(frozen=True)` para inmutabilidad
- [x] Definir campos: `nombre_completo`, `codigos_disp`, `codigos_pacto`, `moneda`, etc.
- [x] Agregar campo `activo` para instrumentos futuros (DPX)
- [x] Agregar `filtro_moneda` opcional

### 1.3 Implementar validaciones
- [x] Validar monedas válidas: `CLP`, `CLF`, `USD`
- [x] Validar listas no vacías (`codigos_disp`, `codigos_pacto`)
- [x] Validar consistencia `moneda` ↔ `tabla_factores`
- [x] Validar prefijos (`Flujo_`, `ML_C46_`, `RF_Fact`)
- [x] Validar unicidad de `nombre_salida` y `cod_sub_pro_final`
- [x] Warnings para códigos nemotécnico desconocidos

### 1.4 Funciones de utilidad
- [x] `obtener_instrumento(nombre)` con error descriptivo
- [x] `listar_instrumentos(solo_activos=True)`
- [x] `obtener_instrumentos_por_moneda(moneda)`
- [x] `validar_configuracion_completa()` ejecutada al importar

### Criterios de Validación Fase 1
- [x] `from config.instrumentos import INSTRUMENTOS` funciona sin errores
- [x] Autocomplete en IDE funciona: `INSTRUMENTOS['GobCLP'].codigos_disp`
- [x] Tests unitarios pasan: **48 tests en `test_config_instrumentos.py`**
- [x] `helpers.py` actualizado para importar desde `config/` (con fallback)
- [x] `generador_tabla_final.py` actualizado para importar desde `config/`

### Archivos Creados Fase 1
```
RF_Modelo_Inversiones/
├── config/
│   ├── __init__.py           # Exports públicos
│   └── instrumentos.py       # ~350 líneas, dataclass + validaciones
└── tests/
    └── test_config_instrumentos.py  # 48 tests
```

---

## Fase 2: Refactorizar Sistema de Cache ✅ COMPLETADA

### 2.1 Crear módulo de cache genérico

**Archivo**: `RF_Modelo_Inversiones/io/cache.py`

#### Tasks:
- [x] Crear directorio `RF_Modelo_Inversiones/io/`
- [x] Crear `io/__init__.py`
- [x] Crear `io/cache.py`

#### Subtasks para `cache.py`:
- [x] Implementar función `cache_pickle()`:
  ```python
  def cache_pickle(
      nombre_base: str,
      fecha_proceso: Union[int, str, datetime],
      data_path: Path,
      extractor: Callable[[], T],
      forzar_recarga: bool = False,
      max_caches: int = 3,
      verbose: bool = True
  ) -> T
  ```
- [x] Implementar búsqueda de pickle existente con glob
- [x] Implementar lógica de timestamp para archivos nuevos
- [x] Implementar logging opcional con `verbose`
- [x] Agregar docstring con ejemplos de uso
- [x] Implementar `listar_caches()` para administración
- [x] Implementar `invalidar_cache()` para eliminar específico
- [x] Implementar `limpiar_caches()` para limpieza automática
- [x] Implementar decorador `@cached` para uso simplificado

#### Criterios de Validación 2.1:
- [x] `from io.cache import cache_pickle` funciona
- [x] Cache crea archivo con formato `{nombre}_{fecha}_{timestamp}.pkl`
- [x] Cache lee archivo existente si `forzar_recarga=False`
- [x] Cache regenera si `forzar_recarga=True`
- [x] Verbose muestra mensajes informativos
- [x] **22 tests pasando en `test_cache.py`**

---

### 2.2 Sistema de cache implementado ✅

**Resultado**: El nuevo `cache_pickle()` es una función genérica que reemplaza
la lógica duplicada de las 4 funciones anteriores. Las funciones originales
pueden seguir usándose como wrappers que internamente llaman a `cache_pickle()`.

#### Funcionalidades implementadas:
- [x] `cache_pickle()` - Función principal genérica
- [x] `listar_caches()` - Lista caches existentes con metadata
- [x] `invalidar_cache()` - Elimina cache específico
- [x] `limpiar_caches()` - Limpia caches antiguos
- [x] `@cached` - Decorador para caching automático

#### Archivos Creados Fase 2
```
RF_Modelo_Inversiones/
├── io/
│   ├── __init__.py           # Exports públicos
│   └── cache.py              # ~350 líneas, sistema de cache genérico
└── tests/
    └── test_cache.py         # 22 tests
```

### 2.3 Migración de funciones legacy (PENDIENTE para Fase 4)

> ⚠️ **Nota**: La migración de las funciones legacy (`check_pickle_tablas_*`)
se realizará en Fase 4 cuando se reorganicen los módulos. Por ahora, el nuevo
sistema de cache está disponible para nuevo código.

- [ ] Migrar `check_pickle_tablas_linkeadas()` → usar `cache_pickle()`
- [ ] Migrar `check_pickle_tablas_inversiones()` → usar `cache_pickle()`
- [ ] Migrar `check_pickle_access_prod()` → usar `cache_pickle()`
- [ ] Migrar `ejecutar_query_access_con_cache()` → usar `cache_pickle()`
- [ ] Mover utilidades de Access a `io/access_utils.py`

---

## Fase 3: Unificar Funciones de Cartera ✅ COMPLETADA

### 3.1 Crear función unificada `genera_cartera_inv()`

**Archivo**: `RF_Modelo_Inversiones/pipeline/cartera.py`

#### Tasks:
- [x] Crear directorio `RF_Modelo_Inversiones/pipeline/`
- [x] Crear `pipeline/__init__.py`
- [x] Crear `pipeline/cartera.py`

#### Subtasks para `genera_cartera_inv()`:
- [x] Definir tipo `Literal['disponible', 'pacto']` para parámetro
- [x] Extraer lógica común de ambas funciones:
  - [x] JOIN con fecha de proceso
  - [x] Filtro `Cod_Pro.str.startswith('Inversion Financiera')`
  - [x] Transformación fondos mutuos → 'Inversion Financiera Privado'
  - [x] Creación columna `Instrumento = Nemotecnico[:3]`
- [x] Parametrizar diferencias con `FILTROS_CARTERA`:
  ```python
  FILTROS_CARTERA = {
      'disponible': {
          'descripcion': 'Cartera Inversiones Disponible',
          'sufijos_cod_sub_pro': ['Disp', 'Disp_Liq', 'MUTUOS'],
          'longitudes_sufijo': [4, 8, 6],
          'excluir_lch': True,
          'excluir_htm': True,
          'columnas_extra': []
      },
      'pacto': {
          'descripcion': 'Cartera Inversiones Pacto',
          'sufijos_cod_sub_pro': ['Pcto', 'Pcto_Liq'],
          'longitudes_sufijo': [4, 8],
          'excluir_lch': False,
          'excluir_htm': False,
          'columnas_extra': ['Dias_Pacto']
      }
  }
  ```
- [x] Agregar logging verbose con conteos de registros por paso
- [x] Agregar docstring completo con SQL de referencia

#### Criterios de Validación 3.1:
- [x] `genera_cartera_inv(df, df_fecha, 'disponible')` produce mismo resultado que `genera_cartera_inv_001()`
- [x] `genera_cartera_inv(df, df_fecha, 'pacto')` produce mismo resultado que `genera_cartera_inv_pacto()`
- [x] **18 tests en `test_cartera.py`** verifican equivalencia
- [x] Tipos de datos de columnas son idénticos

---

### 3.2 Deprecar funciones originales ✅

- [x] Convertir `genera_cartera_inv_001()` en alias con DeprecationWarning
- [x] Convertir `genera_cartera_inv_pacto()` en alias con DeprecationWarning
- [ ] Actualizar notebooks para usar función nueva (pendiente)
- [ ] Documentar cambio en CHANGELOG (pendiente)

**Implementación de deprecación:**
```python
def genera_cartera_inv_001(df_base, df_fecha, verbose=True):
    """DEPRECADO: Usar genera_cartera_inv(tipo='disponible')"""
    import warnings
    warnings.warn(
        "genera_cartera_inv_001() está deprecado. "
        "Usar genera_cartera_inv(tipo='disponible')",
        DeprecationWarning,
        stacklevel=2
    )
    return genera_cartera_inv(df_base, df_fecha, 'disponible', verbose)
```

#### Criterios de Validación 3.2:
- [x] Código legacy sigue funcionando (retrocompatibilidad)
- [x] Warnings aparecen al usar funciones viejas (verificado con tests)
- [ ] Notebooks actualizados usan función nueva (pendiente)

---

### 3.3 Crear función genérica de agregación ✅

**Archivo**: `RF_Modelo_Inversiones/pipeline/agregaciones.py`

- [x] Crear `pipeline/agregaciones.py`
- [x] Implementar `agregar_por_columnas()`:
  ```python
  def agregar_por_columnas(
      df: pd.DataFrame,
      cols_grupo: Union[str, List[str]],
      cols_suma: Union[str, List[str]],
      col_total: Optional[str] = None,
      ordenar_por: Optional[Union[str, List[str]]] = None,
      nombre_log: str = "",
      verbose: bool = True
  ) -> pd.DataFrame
  ```
- [x] Crear wrappers de conveniencia:
  - [x] `generar_monto_total_instrumento()` → usa `agregar_por_columnas()`
  - [x] `generar_haircut_dia()` → usa `agregar_por_columnas()`
  - [x] `generar_monto_plazo_pacto()` → usa `agregar_por_columnas()`
  - [x] `agregar_vp_flujo()` → conveniencia para VP_Cap_Amort + VP_Int_Total

#### Criterios de Validación 3.3:
- [x] **18 tests en `test_agregaciones.py`** verifican equivalencia
- [x] Mismos resultados que funciones originales
- [x] Reducción de código duplicado mediante función genérica

### Archivos Creados Fase 3
```
RF_Modelo_Inversiones/
├── pipeline/
│   ├── __init__.py           # Exports de cartera y agregaciones
│   ├── cartera.py            # ~307 líneas, genera_cartera_inv() unificada
│   └── agregaciones.py       # ~229 líneas, agregar_por_columnas() genérica
└── tests/
    ├── test_cartera.py       # 18 tests
    └── test_agregaciones.py  # 18 tests
```

---

## Fase 4: Reorganizar Módulos ✅ COMPLETADA

### 4.1 Estructura final de archivos

```
RF_Modelo_Inversiones/
├── __init__.py
├── ml_inversiones.py              # Entry point principal
│
├── config/
│   ├── __init__.py
│   └── instrumentos.py            # ✅ Ya existe
│
├── io/
│   ├── __init__.py
│   ├── access_utils.py            # Funciones de Access
│   └── cache.py                   # Sistema de cache genérico
│
├── pipeline/
│   ├── __init__.py
│   ├── cartera.py                 # genera_cartera_inv()
│   ├── haircut.py                 # ✅ Funciones de haircut
│   ├── liquidacion.py             # ✅ calcular_flujo_liquidacion()
│   ├── agregaciones.py            # agregar_por_columnas()
│   └── orquestador.py             # ✅ generar_flujo_liquidacion_instrumento()
│
├── output/
│   ├── __init__.py
│   └── tabla_final.py             # Generador de tabla final (pendiente)
│
├── dev/                           # Notebooks y archivos de desarrollo
│   ├── helpers.py                 # DEPRECADO - mantener por compatibilidad
│   ├── generador_tabla_final.py   # DEPRECADO
│   └── *.ipynb
│
└── tests/
    ├── __init__.py
    ├── test_config_instrumentos.py # ✅ 48 tests
    ├── test_cache.py               # ✅ 22 tests
    ├── test_cartera.py             # ✅ 18 tests
    ├── test_agregaciones.py        # ✅ 18 tests
    ├── test_haircut.py             # ✅ 17 tests
    ├── test_liquidacion.py         # ✅ 19 tests
    └── test_orquestador.py         # ✅ 16 tests
```

### 4.2 Tasks de migración por módulo

#### Task 4.2.1: Crear `pipeline/haircut.py` ✅
- [x] Mover `generar_cartera_haircut()` - ~90 líneas
- [x] Mover `generar_haircut_dia()` - ~40 líneas
- [x] Mover `agregar_dia_semana()` - ~60 líneas
- [x] Mover `combinar_haircut_con_pactos()` - ~45 líneas
- [x] Mover `filtrar_monto_liquidar()` - ~35 líneas
- [x] Actualizar imports en `pipeline/__init__.py`
- [x] **17 tests en test_haircut.py**

#### Task 4.2.2: Crear `pipeline/liquidacion.py` ✅
- [x] Mover `calcular_flujo_liquidacion()` - ~140 líneas
- [x] Mover `generar_cartera_pond()` - ~60 líneas
- [x] Mover `generar_cartera_instrumento()` - ~50 líneas
- [x] Mover `generar_monto_total_instrumento()` - ~45 líneas
- [x] Agregar constantes COLUMNAS_CARTERA_DISP/PACTO
- [x] Agregar alias deprecado `monto_liq_gob_clp()`
- [x] **19 tests en test_liquidacion.py**

#### Task 4.2.3: Crear `pipeline/orquestador.py` ✅
- [x] Mover `generar_flujo_liquidacion_instrumento()` - ~200 líneas
- [x] Agregar `_obtener_config_instrumento()` con fallback
- [x] Agregar `listar_tipos_instrumento()`
- [x] Agregar `CONFIGURACION_INSTRUMENTOS_FALLBACK` para 6 instrumentos
- [x] Integración con `config/instrumentos.py` (prioridad) o fallback local
- [x] Pipeline de 10 pasos orquestado
- [x] **16 tests en test_orquestador.py**

#### Task 4.2.4: Crear `output/tabla_final.py` (PENDIENTE)
- [ ] Mover contenido de `generador_tabla_final.py`
- [ ] Actualizar para importar desde `config/`
- [ ] Actualizar para importar desde `pipeline/`

#### Criterios de Validación 4.2 ✅:
- [x] Cada módulo importa correctamente
- [x] No hay imports circulares
- [x] `python -c "from RF_Modelo_Inversiones.pipeline import orquestador"` funciona
- [x] **158 tests totales pasando**

### Archivos Creados Fase 4
```
RF_Modelo_Inversiones/
├── pipeline/
│   ├── __init__.py           # Actualizado con nuevos exports (~25 funciones)
│   ├── haircut.py            # ~400 líneas, 5 funciones de haircut
│   ├── liquidacion.py        # ~397 líneas, 4 funciones + constantes + alias
│   └── orquestador.py        # ~409 líneas, pipeline principal parametrizado
└── tests/
    ├── test_haircut.py       # 17 tests
    ├── test_liquidacion.py   # 19 tests
    └── test_orquestador.py   # 16 tests
```

---

### 4.3 Actualizar entry point `ml_inversiones.py`

- [ ] Crear script principal que orquesta todo el proceso
- [ ] Importar desde módulos refactorizados
- [ ] Mantener interfaz CLI existente (si existe)
- [ ] Agregar logging estructurado

#### Criterios de Validación 4.3:
- [ ] `python ml_inversiones.py --fecha 20260131` ejecuta completo
- [ ] Outputs son idénticos a versión anterior
- [ ] Tiempo de ejecución similar (±10%)

---

## Fase 5: Integración y Tests

### 5.1 Escribir tests unitarios

#### Task 5.1.1: Tests para `config/`
- [ ] Test `ConfigInstrumento` validaciones
- [ ] Test `obtener_instrumento()` con key válida
- [ ] Test `obtener_instrumento()` con key inválida
- [ ] Test `listar_instrumentos()`
- [ ] Test `obtener_instrumentos_por_moneda()`
- [ ] Test `validar_configuracion_completa()`

#### Task 5.1.2: Tests para `io/cache.py`
- [ ] Test crear cache nuevo
- [ ] Test leer cache existente
- [ ] Test `forzar_recarga=True`
- [ ] Test con diferentes tipos de datos (dict, DataFrame)

#### Task 5.1.3: Tests para `pipeline/cartera.py`
- [ ] Test `genera_cartera_inv('disponible')` con datos mock
- [ ] Test `genera_cartera_inv('pacto')` con datos mock
- [ ] Test filtros aplicados correctamente
- [ ] Test columnas de salida

#### Task 5.1.4: Tests para `pipeline/liquidacion.py`
- [ ] Test `calcular_flujo_liquidacion()` con caso simple
- [ ] Test edge cases (monto = 0, días negativos)

### 5.2 Tests de integración

- [ ] Test end-to-end con datos de prueba
- [ ] Comparar output con versión anterior (regression test)
- [ ] Test de performance (tiempo de ejecución)

### 5.3 Documentación

- [ ] Actualizar docstrings en todos los módulos
- [ ] Crear `docs/modelos/inversiones.md` con arquitectura
- [ ] Actualizar `README.md` del módulo
- [ ] Documentar breaking changes en `CHANGELOG.md`

#### Criterios de Validación 5.3:
- [ ] `mkdocs serve` muestra documentación sin errores
- [ ] Todos los módulos públicos tienen docstrings
- [ ] Ejemplos de uso en documentación funcionan

---

## Checklist de Validación Final

### Funcionalidad
- [ ] Pipeline completo ejecuta sin errores
- [ ] Outputs son idénticos a versión pre-refactor
- [ ] Todos los 6 instrumentos procesan correctamente

### Calidad de Código
- [ ] `ruff check .` sin errores
- [ ] `mypy .` sin errores críticos
- [ ] Cobertura de tests > 80%

### Documentación
- [ ] Todos los módulos documentados
- [ ] CHANGELOG actualizado
- [ ] Ejemplos de uso actualizados

### Performance
- [ ] Tiempo de ejecución ≤ versión anterior
- [ ] Uso de memoria similar

### Git
- [ ] Commits atómicos por fase
- [ ] PR con descripción detallada
- [ ] Code review completado

---

## Estimación de Esfuerzo

| Fase | Esfuerzo | Riesgo | Dependencias | Estado |
|------|----------|--------|--------------|--------|
| Fase 1 | 4-6 horas | Bajo | - | ✅ Completada |
| Fase 2 | 4-6 horas | Medio | Fase 1 | ✅ Completada |
| Fase 3 | 6-8 horas | Alto | Fases 1, 2 | ✅ Completada |
| Fase 4 | 4-6 horas | Medio | Fases 1-3 | ⬜ Pendiente |
| Fase 5 | 6-8 horas | Bajo | Fases 1-4 | 🔄 En progreso |
| **Total** | **~20 horas** | - | - | **60%** |

---

## Notas y Decisiones

### Decisiones Tomadas
1. **Formato de configuración**: Python dataclasses (no YAML/JSON) por type safety
2. **Monedas soportadas**: CLP, CLF, USD (USD para futuro DPX)
3. **Estrategia de deprecación**: Mantener funciones viejas como alias con warnings
4. **Tests primero**: Cada fase incluye tests antes de continuar
5. **Parametrización**: Usar diccionarios de configuración (FILTROS_CARTERA)

### Riesgos Identificados
1. **Imports circulares**: Mitigar con estructura de dependencias clara
2. **Regresiones**: ✅ Mitigado con 106 tests
3. **Performance**: Pendiente validar con datos reales

### Preguntas Pendientes
- [ ] ¿Eliminar `monto_liq_gob_clp()` o mantener como alias?
- [ ] ¿Mover `compactar_access_db()` a `bfa_cl_utilidades`?
- [ ] ¿Nivel de logging deseado (DEBUG, INFO, WARNING)?

---

## Estado Actual del Desarrollo

⚠️ **IMPORTANTE**: Este módulo está EN DESARROLLO.

### Lo que SÍ está listo:
- ✅ `config/instrumentos.py` - Configuración centralizada con validaciones
- ✅ `io/cache.py` - Sistema de cache genérico
- ✅ `pipeline/cartera.py` - Función unificada de cartera
- ✅ `pipeline/agregaciones.py` - Agregaciones genéricas
- ✅ 106 tests unitarios pasando

### Lo que NO está listo:
- ⬜ Migración de funciones legacy en `helpers.py`
- ⬜ Reorganización de módulos restantes (Fase 4)
- ⬜ Entry point `ml_inversiones.py`
- ⬜ Tests de integración con datos reales
- ⬜ Documentación final

### Estructura actual:
```
RF_Modelo_Inversiones/
├── config/
│   ├── __init__.py
│   └── instrumentos.py      ✅ (48 tests)
├── io/
│   ├── __init__.py
│   └── cache.py             ✅ (22 tests)
├── pipeline/
│   ├── __init__.py
│   ├── cartera.py           ✅ (18 tests)
│   └── agregaciones.py      ✅ (18 tests)
├── tests/
│   ├── __init__.py
│   ├── test_config_instrumentos.py
│   ├── test_cache.py
│   ├── test_cartera.py
│   └── test_agregaciones.py
└── dev/
    ├── helpers.py           📝 (legacy, con imports actualizados)
    ├── generador_tabla_final.py  📝 (legacy)
    └── PLAN_IMPLEMENTACION.md
```

---

## Siguiente Paso

**Recomendación**: Continuar con **Fase 4** (Reorganizar Módulos).

Prioridad:
1. Crear `pipeline/haircut.py` con funciones de haircut
2. Crear `pipeline/liquidacion.py` con cálculo de flujos
3. Crear `pipeline/orquestador.py` para coordinar todo
4. Actualizar `helpers.py` para importar desde nuevos módulos
