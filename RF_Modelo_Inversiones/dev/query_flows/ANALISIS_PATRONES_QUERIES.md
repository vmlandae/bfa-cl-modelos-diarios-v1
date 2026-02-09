# Análisis de Patrones y Estrategia de Reducción de Queries

**Fecha de análisis**: 2026-02-04

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Total queries únicas** | 70 |
| **Queries parametrizables** | 52 |
| **Funciones Python resultantes** | 9 |
| **Queries no parametrizables** | 18 |
| **Total final estimado** | ~27 unidades de código |
| **Reducción** | **61%** |

---

## Distribución por Tipo de Query

| Tipo | Cantidad | Descripción |
|------|----------|-------------|
| Select | 45 | Query de lectura/transformación |
| DDL | 10 | CREATE/SELECT INTO (crea tablas) |
| Type32 | 7 | DELETE (limpieza de tablas) |
| Type128 | 4 | Query UNION (combina múltiples fuentes) |
| Type64 | 4 | INSERT INTO (agrega registros) |

---

## Distribución por Nivel de Profundidad

| Nivel | Cantidad | Significado |
|-------|----------|-------------|
| 0 | 21 | Entrypoints (queries principales) |
| 1 | 17 | Dependencias directas de entrypoints |
| 2 | 4 | Dependencias de nivel 1 |
| 3 | 8 | Dependencias de nivel 2 |
| 4 | 7 | Dependencias de nivel 3 |
| 5 | 6 | Dependencias de nivel 4 |
| 6 | 6 | Dependencias de nivel 5 |
| 7 | 1 | Dependencias de nivel 6 |

---

## Queries Compartidas (Reutilizadas)

Queries usadas por múltiples entrypoints (oportunidades de función común):

| Query | Nº Entrypoints | Entrypoints |
|-------|----------------|-------------|
| `RF_PLI_001_CarteraInv` | 6 | Pond, Pond, Pond (+3) |
| `RF_PLI_044f_CarteraInv_FFMM` | 2 | FFMM, Excel |
| `RF_PLI_044i_CarteraInv_HTM` | 2 | HTM, Excel |
| `RF_PLI_044g_CarteraInv_RT` | 2 | RT, Excel |

---

## Familias de Queries Detectadas

### Cartera_Instrumentos (18 queries)

- `RF_PLI_002_CarteraGobCLP`
- `RF_PLI_002_CarteraGobCLP_Pacto`
- `RF_PLI_003_CarteraGobCLP_MonTotal`
- `RF_PLI_009_CarteraGobCLF`
- `RF_PLI_009_CarteraGobCLF_Pacto`
- `RF_PLI_010_CarteraGobCLF_MonTotal`
- `RF_PLI_016_CarteraDPF`
- `RF_PLI_016_CarteraDPF_Pacto`
- `RF_PLI_017_CarteraDPF_MonTotal`
- `RF_PLI_023_CarteraDPR`
- `RF_PLI_023_CarteraDPR_Pacto`
- `RF_PLI_024_CarteraDPR_MonTotal`
- `RF_PLI_030_CarteraLCH`
- `RF_PLI_030_CarteraLCH_Pacto`
- `RF_PLI_031_CarteraLCH_MonTotal`
- `RF_PLI_037_CarteraBBC_CLP`
- `RF_PLI_037_CarteraBBC_CLP_Pacto`
- `RF_PLI_038_CarteraBBC_CLP_MonTotal`

### GenerarCartera_Ponderada (6 queries)

- `RF_PLI_004_GenerCartGobCLP_Pond`
- `RF_PLI_011_GenerCartGobCLF_Pond`
- `RF_PLI_018_GenerCartDPF_Pond`
- `RF_PLI_025_GenerCartDPR_Pond`
- `RF_PLI_032_GenerCartLCH_Pond`
- `RF_PLI_039_GenerCartBBC_Pond`

### Limpiar_Flujo (6 queries)

- `RF_PLI_008_LimpiaFlujGobCLP`
- `RF_PLI_015_LimpiaFlujGobCLP`
- `RF_PLI_022_LimpiaFlujDPF`
- `RF_PLI_029_LimpiaFlujDPR`
- `RF_PLI_036_LimpiaFlujLCH`
- `RF_PLI_043_LimpiaFlujBBC`

### Cartera_Final (6 queries)

- `RF_PLI_008b_CarteraGobCLP_Final`
- `RF_PLI_015b_CarteraGobCLF_Final`
- `RF_PLI_022b_CarteraDPF_Final`
- `RF_PLI_029b_CarteraDPR_Final`
- `RF_PLI_036b_CarteraLCH_Final`
- `RF_PLI_043b_CarteraBBC_Final`

### Monto_FueraPlazo (6 queries)

- `RF_PLI_003c_Monto_FueraPlazo`
- `RF_PLI_010c_Monto_FueraPlazo`
- `RF_PLI_017c_Monto_FueraPlazo`
- `RF_PLI_024c_Monto_FueraPlazo`
- `RF_PLI_031c_Monto_FueraPlazo`
- `RF_PLI_038c_Monto_FueraPlazo`

### MontoPlazo_Pacto (6 queries)

- `RF_PLI_003b_GobCLP_MontoPlazo_Pacto`
- `RF_PLI_010b_GobCLF_MontoPlazo_Pacto`
- `RF_PLI_017b_DPF_MontoPlazo_Pacto`
- `RF_PLI_024b_DPR_MontoPlazo_Pacto`
- `RF_PLI_031b_LCH_MontoPlazo_Pacto`
- `RF_PLI_038b_BBC_CLP_MontoPlazo_Pacto`

### Modelo_Inversiones_Final (5 queries)

- `RF_PLI_044_Modelo_Inversiones_Final`
- `RF_PLI_044b_Modelo_Inversiones_Pacto_FB`
- `RF_PLI_044c_Modelo_Inversiones_Pacto_FB`
- `RF_PLI_044d_Modelo_Inversiones_Full`
- `RF_PLI_044e_Modelo_Inversiones_Tabla_Final`

### Agregar_Tabla_Desarrollo (4 queries)

- `RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML`
- `RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM`
- `RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM`
- `RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT`

---

## Estrategia de Parametrización

### Grupos de Queries Parametrizables

### 1. `filtrar_cartera_por_instrumento()`

**Descripción**: Filtra RF_PLI_001_CarteraInv por tipo de instrumento (BCP, BTU, DPF, etc.)

**Reducción**: 5 queries -> 1 función

**Parámetros sugeridos**:

- `tipo_instrumento: str`
- `codigos_instrumento: List[str]`

**Queries actuales que reemplaza** (5):

- `RF_PLI_002_CarteraGobCLP`
- `RF_PLI_009_CarteraGobCLF`
- `RF_PLI_016_CarteraDPF`
- `RF_PLI_023_CarteraDPR`
- `RF_PLI_030_CarteraLCH`

### 2. `calcular_monto_total()`

**Descripción**: Agrupa y suma VP_Cap_Amort + VP_Int_Total por Fec_Pro, Moneda, Cod_Pro

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_origen: str`
- `columnas_grupo: List[str]`

**Queries actuales que reemplaza** (6):

- `RF_PLI_003_CarteraGobCLP_MonTotal`
- `RF_PLI_010_CarteraGobCLF_MonTotal`
- `RF_PLI_017_CarteraDPF_MonTotal`
- `RF_PLI_024_CarteraDPR_MonTotal`
- `RF_PLI_031_CarteraLCH_MonTotal`
- `RF_PLI_038_CarteraBBC_CLP_MonTotal`

### 3. `generar_cartera_ponderada()`

**Descripción**: Calcula ponderador = (VP_Cap + VP_Int) / VP_Flujo_Total

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_cartera: str`
- `tabla_montotal: str`
- `tabla_destino: str`

**Queries actuales que reemplaza** (6):

- `RF_PLI_004_GenerCartGobCLP_Pond`
- `RF_PLI_011_GenerCartGobCLF_Pond`
- `RF_PLI_018_GenerCartDPF_Pond`
- `RF_PLI_025_GenerCartDPR_Pond`
- `RF_PLI_032_GenerCartLCH_Pond`
- `RF_PLI_039_GenerCartBBC_Pond`

### 4. `limpiar_tabla()`

**Descripción**: DELETE FROM tabla (limpieza antes de repoblar)

**Reducción**: 7 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_destino: str`

**Queries actuales que reemplaza** (7):

- `RF_PLI_008_LimpiaFlujGobCLP`
- `RF_PLI_015_LimpiaFlujGobCLP`
- `RF_PLI_022_LimpiaFlujDPF`
- `RF_PLI_029_LimpiaFlujDPR`
- `RF_PLI_036_LimpiaFlujLCH`
- `RF_PLI_043_LimpiaFlujBBC`
- `RF_PLI_047_Limpia_Tabla_Desarrollo_Interna`

### 5. `formatear_cartera_final()`

**Descripción**: Formatea flujo con estructura estándar: Fec_Pro, Cod_Emp, Moneda, Cod_A_P, etc.

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_flujo: str`
- `moneda: str`
- `cod_sub_pro: str`

**Queries actuales que reemplaza** (6):

- `RF_PLI_008b_CarteraGobCLP_Final`
- `RF_PLI_015b_CarteraGobCLF_Final`
- `RF_PLI_022b_CarteraDPF_Final`
- `RF_PLI_029b_CarteraDPR_Final`
- `RF_PLI_036b_CarteraLCH_Final`
- `RF_PLI_043b_CarteraBBC_Final`

### 6. `filtrar_cartera_pacto()`

**Descripción**: Filtra instrumentos con pacto de retroventa

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_origen: str`
- `tipo_instrumento: str`

**Queries actuales que reemplaza** (6):

- `RF_PLI_002_CarteraGobCLP_Pacto`
- `RF_PLI_009_CarteraGobCLF_Pacto`
- `RF_PLI_016_CarteraDPF_Pacto`
- `RF_PLI_023_CarteraDPR_Pacto`
- `RF_PLI_030_CarteraLCH_Pacto`
- `RF_PLI_037_CarteraBBC_CLP_Pacto`

### 7. `calcular_monto_por_plazo()`

**Descripción**: Agrupa montos por días de pacto

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_pacto: str`

**Queries actuales que reemplaza** (6):

- `RF_PLI_003b_GobCLP_MontoPlazo_Pacto`
- `RF_PLI_010b_GobCLF_MontoPlazo_Pacto`
- `RF_PLI_017b_DPF_MontoPlazo_Pacto`
- `RF_PLI_024b_DPR_MontoPlazo_Pacto`
- `RF_PLI_031b_LCH_MontoPlazo_Pacto`
- `RF_PLI_038b_BBC_CLP_MontoPlazo_Pacto`

### 8. `filtrar_monto_fuera_plazo()`

**Descripción**: Filtra montos con Dias_Pacto > 90

**Reducción**: 6 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_monto_plazo: str`
- `dias_limite: int = 90`

**Queries actuales que reemplaza** (6):

- `RF_PLI_003c_Monto_FueraPlazo`
- `RF_PLI_010c_Monto_FueraPlazo`
- `RF_PLI_017c_Monto_FueraPlazo`
- `RF_PLI_024c_Monto_FueraPlazo`
- `RF_PLI_031c_Monto_FueraPlazo`
- `RF_PLI_038c_Monto_FueraPlazo`

### 9. `agregar_a_tabla_desarrollo()`

**Descripción**: INSERT INTO RF_Tabla_Desarrollo_Interna desde diferentes fuentes

**Reducción**: 4 queries -> 1 función

**Parámetros sugeridos**:

- `tabla_origen: str`
- `transformaciones: Dict`

**Queries actuales que reemplaza** (4):

- `RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML`
- `RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM`
- `RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM`
- `RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT`

---

## Plan de Implementación Propuesto

### Fase 1: Funciones Base (Semana 1)

Crear módulo `MODELOS/ML_INVERSIONES/utils/queries_inversiones.py` con:

```python
# Funciones principales a implementar

def limpiar_tabla(df_conexion, tabla: str) -> None:
    """Equivalente a DELETE FROM tabla."""
    pass

def filtrar_cartera_por_instrumento(
    df_cartera: pd.DataFrame,
    codigos_instrumento: List[str]
) -> pd.DataFrame:
    """Filtra cartera por código de instrumento (BCP, BTU, DPF, etc.)."""
    pass

def calcular_monto_total(
    df: pd.DataFrame,
    columnas_grupo: List[str] = ['Fec_Pro', 'Moneda', 'Cod_Pro']
) -> pd.DataFrame:
    """Agrupa y suma VP_Cap_Amort + VP_Int_Total."""
    pass

def generar_cartera_ponderada(
    df_cartera: pd.DataFrame,
    df_monto_total: pd.DataFrame
) -> pd.DataFrame:
    """Calcula ponderador = flujo / flujo_total."""
    pass
```

### Fase 2: Consolidación Flujos (Semana 2)

- Implementar funciones de formateo final
- Consolidar queries de pacto y fuera de plazo
- Tests unitarios para cada función

### Fase 3: Integración (Semana 3)

- Crear pipeline principal `ml_inversiones.py`
- Integrar con orquestador
- Validar outputs vs Access original

---

## Arquitectura Propuesta

```
MODELOS/ML_INVERSIONES/
├── ml_inversiones.py          # Orquestador principal
├── utils/
│   ├── __init__.py
│   ├── queries_inversiones.py  # Funciones parametrizadas
│   ├── transformaciones.py     # Lógica de negocio
│   └── validaciones.py         # Validación de outputs
├── queries/
│   ├── cartera_base.sql        # Query base RF_PLI_001
│   └── modelo_final.sql        # Consolidación final
└── tests/
    └── test_queries.py
```

---

## Métricas de Éxito

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Queries/Funciones | 70 | ~27 | -43 |
| Líneas de código SQL | ~1050 | ~540 | ~500 |
| Tiempo mantenimiento | Alto | Bajo | -70% est. |
| Testabilidad | Nula | Alta | +100% |

---

## Notas Adicionales

1. **Priorizar** las queries compartidas (usadas por múltiples entrypoints)
2. **Validar** cada función contra output original del Access
3. **Documentar** mapeo entre queries Access y funciones Python
4. Considerar **cacheo** de resultados intermedios para optimizar performance
