# Análisis de Refactorización: helpers.py y generador_tabla_final.py

## Resumen Ejecutivo

El archivo `helpers.py` tiene **2,109 líneas** y contiene una mezcla de:
1. **Funciones de utilidad para Access** (lectura, cache, pickle)
2. **Pipeline de liquidación de inversiones** (filtros, haircut, pactos)
3. **Configuración de instrumentos** (dict parametrizado)

El archivo `generador_tabla_final.py` tiene **~230 líneas** y se enfoca solo en:
1. **Formatear flujos al esquema estándar**
2. **Generar la tabla final consolidada**

**Problema principal**: Hay duplicación conceptual entre ambos archivos y dentro de `helpers.py` hay patrones repetitivos que pueden unificarse.

---

## Inventario de Funciones en helpers.py

### Categoría 1: Utilidades de Access/IO (~500 líneas)
| Función | Líneas | Propósito |
|---------|--------|-----------|
| `ejecutar_query_access()` | 95-164 | Ejecutar queries SELECT o de acción |
| `compactar_access_db()` | 165-230 | Compactar/reparar BD Access |
| `guardar_tablas_linkeadas_pickle()` | 232-244 | Guardar dict de DataFrames en pickle |
| `leer_tablas_linkeadas()` | 246-282 | Leer tablas linkeadas desde fuentes |
| `check_pickle_tablas_linkeadas()` | 284-302 | Cache con pickle para tablas linkeadas |
| `extraer_tablas_access()` | 304-322 | Extraer tablas específicas de Access |
| `check_pickle_tablas_inversiones()` | 324-347 | Cache con pickle para tablas inversiones |
| `listar_objetos_access()` | 355-410 | Listar tablas y queries de Access |
| `extraer_todas_tablas_access()` | 413-472 | Extraer TODAS las tablas de Access |
| `obtener_sql_queries_access()` | 475-528 | Obtener SQL de queries guardadas |
| `clasificar_query_por_tipo()` | 531-625 | Clasificar query como LECTURA/ESCRITURA |
| `extraer_todas_queries_access()` | 628-749 | Ejecutar queries de lectura |
| `check_pickle_access_prod()` | 752-844 | Cache genérico para Access productivo |
| `ejecutar_query_access_con_cache()` | 847-939 | Ejecutar query individual con cache |
| `listar_queries_cacheadas()` | 942-982 | Listar queries cacheadas por fecha |

### Categoría 2: Generación de Cartera Base (~400 líneas)
| Función | Líneas | Propósito |
|---------|--------|-----------|
| `genera_tabla_RF_base_Completa_Hist()` | 984-1003 | Paso 00: Generar tabla base |
| `genera_cartera_inv_001()` | 1006-1172 | Paso 01b: Cartera inversiones disponible |
| `genera_cartera_inv_pacto()` | 1411-1537 | Cartera inversiones pacto (similar a 001) |

### Categoría 3: Funciones de Cálculo Genéricas (~250 líneas)
| Función | Líneas | Propósito |
|---------|--------|-----------|
| `generar_cartera_instrumento()` | 1204-1231 | Filtrar cartera por instrumento/moneda |
| `generar_monto_total_instrumento()` | 1234-1251 | Agrupar y sumar VP_Flujo |
| `generar_cartera_pond()` | 1177-1201 | Calcular ponderadores |
| `calcular_flujo_liquidacion()` | 1254-1393 | Loop VBA de liquidación diaria |
| `monto_liq_gob_clp()` | 1396-1406 | Alias para compatibilidad |

### Categoría 4: Pipeline de Haircut (~300 líneas)
| Función | Líneas | Propósito |
|---------|--------|-----------|
| `generar_cartera_haircut()` | 1580-1685 | JOIN cartera + factores + FPL |
| `generar_haircut_dia()` | 1689-1722 | Agregar haircut por día |
| `agregar_dia_semana()` | 1726-1775 | Agregar día de semana |
| `combinar_haircut_con_pactos()` | 1783-1836 | LEFT JOIN haircut con pactos |
| `filtrar_monto_liquidar()` | 1844-1880 | Filtrar RF_MontosLiq por instrumento |
| `generar_monto_plazo_pacto()` | 1541-1574 | Agrupar pactos por plazo |

### Categoría 5: Pipeline Orquestador (~230 líneas)
| Función | Líneas | Propósito |
|---------|--------|-----------|
| `generar_flujo_liquidacion_instrumento()` | 1888-2109 | Pipeline completo parametrizado |

---

## Análisis de Duplicación y Patrones Repetitivos

### Patrón 1: `genera_cartera_inv_001()` vs `genera_cartera_inv_pacto()`

Estas dos funciones son **80% idénticas**. Ambas:
1. Filtran por fecha de proceso (JOIN)
2. Filtran por `Cod_Pro` que empieza con "Inversion Financiera"
3. Transforman `Cod_Pro` para fondos mutuos
4. Crean columna `Instrumento` = `Nemotecnico[:3]`

**Diferencias:**
| Aspecto | `genera_cartera_inv_001` | `genera_cartera_inv_pacto` |
|---------|--------------------------|----------------------------|
| Filtro Cod_Sub_Pro | `Disp`, `Disp_Liq`, `MUTUOS` | `Pcto`, `Pcto_Liq` |
| Filtro Nemotecnico | `!= 'LCH'` | (sin filtro) |
| Filtro Clasificacion | `!= 'HTM'` | (sin filtro) |
| Columna extra | - | `Dias_Pacto` |

**Solución propuesta:**
```python
def genera_cartera_inv_base(
    df_base: pd.DataFrame,
    df_fecha: pd.DataFrame,
    tipo: Literal['disponible', 'pacto'],
    verbose: bool = True
) -> pd.DataFrame:
    """Función unificada para cartera disponible o pacto"""
    
    FILTROS = {
        'disponible': {
            'sufijos_cod_sub_pro': ['Disp', 'Disp_Liq', 'MUTUOS'],
            'excluir_lch': True,
            'excluir_htm': True,
            'columnas_extra': []
        },
        'pacto': {
            'sufijos_cod_sub_pro': ['Pcto', 'Pcto_Liq'],
            'excluir_lch': False,
            'excluir_htm': False,
            'columnas_extra': ['Dias_Pacto']
        }
    }
    
    config = FILTROS[tipo]
    # ... resto de lógica unificada
```

**Ahorro estimado:** ~100 líneas (de ~330 a ~230)

---

### Patrón 2: Funciones de Cache con Pickle

Hay **4 funciones** que hacen esencialmente lo mismo:
- `guardar_tablas_linkeadas_pickle()`
- `check_pickle_tablas_linkeadas()`
- `check_pickle_tablas_inversiones()`
- `check_pickle_access_prod()`

Todas siguen el patrón:
1. Buscar pickle existente con glob
2. Si existe, cargar y retornar
3. Si no, extraer datos y guardar pickle

**Solución propuesta:**
```python
def cache_pickle(
    nombre_base: str,
    fecha_proceso: int,
    data_path: Path,
    extractor: Callable[[], dict],
    forzar_recarga: bool = False
) -> dict:
    """Wrapper genérico de cache con pickle"""
    patron = f"{nombre_base}_{fecha_proceso}_*.pkl"
    archivos = list(data_path.glob(patron))
    
    if archivos and not forzar_recarga:
        archivo = max(archivos, key=os.path.getctime)
        with open(archivo, "rb") as f:
            return pickle.load(f)
    
    datos = extractor()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(data_path / f"{nombre_base}_{fecha_proceso}_{timestamp}.pkl", "wb") as f:
        pickle.dump(datos, f)
    
    return datos
```

**Ahorro estimado:** ~150 líneas (de ~200 a ~50)

---

### Patrón 3: Duplicación entre helpers.py y generador_tabla_final.py

Ambos archivos tienen:
- Diccionario `CONFIGURACION_INSTRUMENTOS` (helpers.py) vs `INSTRUMENTOS_CONFIG` (generador_tabla_final.py)
- Columnas estándar definidas
- Lógica de formateo a esquema estándar

**Problema:** Si alguien agrega un instrumento, debe actualizar ambos archivos.

**Solución propuesta:** Centralizar la configuración en un solo archivo `config_instrumentos.py`:

```python
# config_instrumentos.py
INSTRUMENTOS = {
    'GobCLP': {
        'nombre_completo': 'Gobierno CLP',
        'codigos_disp': ['BCP', 'BTP', 'PDB'],
        'codigos_pacto': ['BCP', 'BTP', 'PDB'],
        'moneda': 'CLP',
        'tabla_factores': 'RF_FactCLP_Gob',
        'instrumento_fpl': 'Gobierno CLP',
        'cod_sub_pro_final': 'ML_C46_Inversiones_Financieras_GOBCLP',
        # ... todos los campos unificados
    },
    # ... otros instrumentos
}

COLUMNAS_TABLA_FINAL = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P', 'Cod_Pro', 'Cod_Sub_Pro',
    'Fec_Pago', 'Dias_Pago', 'Cap_Amort', 'Int_Total_Cont', 
    'VP_Cap_Amort', 'VP_Int_Total_Cont'
]
```

---

### Patrón 4: Funciones de Agregación Similares

Varias funciones hacen agregaciones muy similares:
- `generar_monto_total_instrumento()` - GROUP BY + SUM
- `generar_haircut_dia()` - GROUP BY Dia + SUM
- `generar_monto_plazo_pacto()` - GROUP BY Dias_Pacto + SUM

**Solución propuesta:**
```python
def agregar_por_columnas(
    df: pd.DataFrame,
    cols_grupo: list,
    cols_suma: list,
    col_total: str = None,
    nombre: str = ""
) -> pd.DataFrame:
    """Agregación genérica con GROUP BY + SUM"""
    df_agg = df.groupby(cols_grupo)[cols_suma].sum().reset_index()
    
    if col_total:
        df_agg[col_total] = df_agg[cols_suma].sum(axis=1)
        df_agg = df_agg.drop(columns=cols_suma)
    
    if nombre:
        print(f"{nombre}: {len(df_agg):,} registros")
    
    return df_agg
```

**Ahorro estimado:** ~50 líneas

---

## Propuesta de Arquitectura Refactorizada

### Estructura de Archivos Propuesta

```
RF_Modelo_Inversiones/
├── config/
│   └── instrumentos.py          # Configuración centralizada
│
├── io/
│   ├── access_utils.py          # Funciones de Access
│   └── cache.py                 # Sistema de cache genérico
│
├── pipeline/
│   ├── cartera.py               # genera_cartera_inv_base()
│   ├── haircut.py               # Funciones de haircut
│   ├── liquidacion.py           # calcular_flujo_liquidacion()
│   └── orquestador.py           # generar_flujo_liquidacion_instrumento()
│
├── output/
│   └── tabla_final.py           # Generador de tabla final
│
└── ml_inversiones.py            # Script principal (entry point)
```

### Beneficios de la Refactorización

| Aspecto | Antes | Después |
|---------|-------|---------|
| Líneas totales | ~2,340 | ~1,400 (estimado) |
| Archivos | 2 | 8 (más modulares) |
| Duplicación de config | 2 lugares | 1 lugar |
| Funciones de cache | 4 funciones | 1 función genérica |
| Funciones de cartera | 2 funciones similares | 1 función parametrizada |
| Documentación | Dispersa | Por módulo |

---

## Matriz de Funciones: Qué Unificar vs Mantener Separado

### ✅ UNIFICAR (mismo código, diferentes parámetros)

| Funciones Actuales | Función Unificada |
|--------------------|-------------------|
| `genera_cartera_inv_001()` + `genera_cartera_inv_pacto()` | `genera_cartera_inv(tipo='disp'|'pacto')` |
| 4 funciones de cache pickle | `cache_pickle(nombre, extractor)` |
| `CONFIGURACION_INSTRUMENTOS` + `INSTRUMENTOS_CONFIG` | `config/instrumentos.py` |
| `generar_monto_total_instrumento()` + `generar_haircut_dia()` + `generar_monto_plazo_pacto()` | `agregar_por_columnas()` |

### ⚠️ MANTENER SEPARADO (lógica específica)

| Función | Razón |
|---------|-------|
| `calcular_flujo_liquidacion()` | Lógica de negocio compleja (loop VBA) |
| `generar_cartera_haircut()` | JOIN con range (Desde/Hasta) es específico |
| `combinar_haircut_con_pactos()` | LEFT JOIN específico |
| `formatear_flujo_instrumento()` | Formateo a esquema final |
| `generar_tabla_final_inversiones()` | Orquestación del output |

### ❓ EVALUAR (posible eliminación)

| Función | Consideración |
|---------|---------------|
| `monto_liq_gob_clp()` | Alias - ¿realmente se usa? |
| `compactar_access_db()` | Utility - ¿debería estar en bfa_cl_utilidades? |
| `clasificar_query_por_tipo()` | Solo se usa en extracción masiva |

---

## Plan de Implementación Sugerido

### Fase 1: Centralizar Configuración (Bajo riesgo)
1. Crear `config/instrumentos.py` con configuración unificada
2. Importar en ambos archivos
3. Validar que nada se rompe

### Fase 2: Refactorizar Cache (Medio riesgo)
1. Crear `io/cache.py` con función genérica
2. Migrar una función de cache a la vez
3. Validar con tests de regresión

### Fase 3: Unificar Cartera (Alto impacto)
1. Crear `genera_cartera_inv_base()` parametrizada
2. Deprecar funciones originales (mantener como alias)
3. Migrar llamadas gradualmente

### Fase 4: Reorganizar Módulos
1. Crear estructura de carpetas
2. Mover funciones a módulos correspondientes
3. Actualizar imports en notebooks y scripts

---

## Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Líneas de código | 2,340 | < 1,500 |
| Funciones duplicadas | 4+ | 0 |
| Archivos de config | 2 | 1 |
| Cobertura de tests | 0% | > 80% |
| Docstrings completos | ~60% | 100% |

---

## Conclusión

El código actual en `helpers.py` es funcional pero tiene deuda técnica significativa:
- **Duplicación**: 4 funciones de cache, 2 funciones de cartera casi idénticas
- **Acoplamiento**: Configuración duplicada en 2 archivos
- **Tamaño**: 2,109 líneas en un solo archivo dificulta mantenimiento

**Recomendación**: Proceder con refactorización incremental, empezando por centralizar la configuración (Fase 1) que tiene bajo riesgo y alto impacto en mantenibilidad.

¿Quieres que proceda con la implementación de alguna de las fases?
