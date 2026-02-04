# Plan de Mejora: draft_ml_inversiones.ipynb

> **Fecha**: 2026-02-03  
> **Objetivo**: Estructurar y documentar el notebook de desarrollo del modelo de inversiones

---

## 1. Estado Actual del Notebook

### 1.1 Estructura Existente
El notebook tiene **34 celdas** organizadas en las siguientes fases:

| # | Sección | Celdas | Estado |
|---|---------|--------|--------|
| 0 | Setup & Carga de Datos | 1-5 | ✅ Funcional |
| 0b | Limpieza Tablas Base | 6-7 | ✅ Funcional |
| 1 | Rama PACTOS | 8-11 | ✅ Funcional |
| 2 | Rama HAIRCUT | 12-16 | ✅ Funcional |
| 3 | Combinación Haircut + Pactos | 17 | ✅ Funcional |
| 4 | Monto a Liquidar | 18-19 | ✅ Funcional |
| 5 | Integración - monto_liq_gob_clp | 20-21 | ✅ Funcional |
| - | Ejecución todos instrumentos | 22-25 | ✅ Funcional |
| - | Comparación vs Access | 26-27 | ✅ Funcional |
| 6 | Pendiente: Pasos 20-27 | 28-34 | 🔄 En desarrollo |

### 1.2 Variables Clave en Memoria

```python
# Diccionarios principales
tablas          # Tablas linkeadas desde Access
queries         # Replicaciones de queries SQL → pandas
flujos          # DataFrames de flujo por instrumento
flujos_access   # Flujos originales de Access para comparación

# DataFrames de secuencia/metadata
df_secuencia    # 27 pasos de la macro en Access
queries_raw     # Todos los SQL del Access
df_maestro      # Información de funciones/queries
```

### 1.3 Progreso de Traducción

**Completado (Pasos 1-19):**
- ✅ RF_PLI_001_CarteraInv → `genera_cartera_inv('disponible')`
- ✅ RF_PLI_001d_CarteraInv_Pcto → `genera_cartera_inv('pacto')`
- ✅ RF_PLI_002-007 → Flujo GobCLP completo
- ✅ RF_PLI_008-014 → Flujo GobCLF completo
- ✅ RF_PLI_015-021 → Flujo DPF completo
- ✅ RF_PLI_022-028 → Flujo DPR completo
- ✅ RF_PLI_029-035 → Flujo BBC completo
- ✅ RF_PLI_036-042 → Flujo LCH completo

**Pendiente (Pasos 20-27):**

| Paso | Query | Tipo | Descripción | Complejidad |
|------|-------|------|-------------|-------------|
| 20 | RF_PLI_045_Gener_Precios_Dia | DDL | Filtrar precios TCRC | ⭐ Trivial |
| 21 | RF_PLI_044e_Modelo_Inversiones_Tabla_Final | DDL | UNION de 12 queries | ⭐⭐⭐ Ya analizado |
| 22 | RF_PLI_047_Limpia_Tabla_Desarrollo_Interna | DELETE | Limpiar tabla destino | ⭐ Trivial |
| 23 | RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML | INSERT | Insertar flujos ML | ⭐⭐ Simple |
| 24 | RF_PLI_048a_..._Add_FFMM | INSERT | Insertar FFMM | ⭐⭐ Simple |
| 25 | RF_PLI_048b_..._Add_HTM | INSERT | Insertar HTM | ⭐⭐ Simple |
| 26 | RF_PLI_048c_..._Add_RT | INSERT | Insertar RT | ⭐⭐ Simple |
| 27 | RF_PLI_050_...Excel | SELECT | Formato final Excel | ⭐⭐⭐ Complejo |

---

## 2. Plan de Restructuración del Notebook

### 2.1 Nueva Estructura Propuesta

```
📓 draft_ml_inversiones.ipynb (restructurado)
│
├── 📋 ÍNDICE Y OVERVIEW
│   ├── Celda 1: Tabla de contenidos interactiva
│   └── Celda 2: Resumen de progreso (pasos completados/pendientes)
│
├── 🔧 SECCIÓN A: SETUP Y CONFIGURACIÓN
│   ├── A.1: Imports y paths
│   ├── A.2: Carga de datos externos (pickles, CSVs)
│   ├── A.3: Limpieza de tablas base (FPL, RF_MontosLiq)
│   └── A.4: Inspección de df_secuencia y queries_raw
│
├── 📊 SECCIÓN B: PIPELINE POR INSTRUMENTO (Pasos 1-19)
│   ├── B.1: Generación de carteras base (disponible + pacto)
│   ├── B.2: Pipeline GobCLP completo con validación
│   ├── B.3: Pipeline genérico para todos los instrumentos
│   └── B.4: Comparación masiva vs Access
│
├── 🏗️ SECCIÓN C: TABLA FINAL DE INVERSIONES (Pasos 20-21)
│   ├── C.1: RF_PLI_045 - Precios del día
│   ├── C.2: Análisis RF_PLI_044e (referencia a documento)
│   └── C.3: Implementación generar_tabla_final()
│
├── 💾 SECCIÓN D: INTEGRACIÓN CON TABLA DESARROLLO (Pasos 22-27)
│   ├── D.1: Limpieza tabla destino
│   ├── D.2: Insert flujos ML (modelo liquidación)
│   ├── D.3: Insert FFMM, HTM, RT
│   └── D.4: Formato final Excel
│
└── ✅ SECCIÓN E: VALIDACIÓN Y EXPORTACIÓN
    ├── E.1: Comparación final completa
    ├── E.2: Métricas de calidad
    └── E.3: Exportación a BigQuery
```

### 2.2 Mejoras de Documentación por Sección

#### Patrón de Documentación para Cada Query

Cada query/paso debe tener:

1. **Celda Markdown de Contexto**:
   ```markdown
   ## B.2.3 RF_PLI_005_CarteraHC - Cartera con Haircut
   
   **SQL Original (Access):**
   ```sql
   SELECT ... FROM ... WHERE ...
   ```
   
   **¿Qué hace?**
   - Descripción en lenguaje natural
   
   **Inputs:**
   - `df_cartera_pond` (de paso anterior)
   - `tablas['RF_FactCLP_Gob']`
   
   **Output:**
   - `queries['RF_PLI_005_CarteraHC']`
   ```

2. **Celda de Código con Logging**:
   ```python
   # RF_PLI_005_CarteraHC - Cartera con Haircut
   queries['RF_PLI_005_CarteraHC'] = generar_cartera_haircut(
       df_cartera_pond=queries['RF_PLI_004_CarteraGobCLP_Pond'],
       df_factores=tablas['RF_FactCLP_Gob'],
       df_fpl=tablas['FPL'],
       filtro_instrumento='Gobierno CLP',
       verbose=True
   )
   print(f"✓ Registros generados: {len(queries['RF_PLI_005_CarteraHC']):,}")
   ```

3. **Celda de Validación** (opcional):
   ```python
   # Validación vs Access
   assert len(queries['RF_PLI_005_CarteraHC']) == len(tablas_access['RF_PLI_005_CarteraHC'])
   ```

---

## 3. Plan de Análisis de Queries Pendientes

### 3.1 Documentos a Crear

Similar a `RF_PLI_044e_Modelo_Inversiones_Tabla_Final_analisis.md`, crear:

| Documento | Queries Cubiertas | Prioridad |
|-----------|-------------------|-----------|
| `analisis_paso_20_precios.md` | RF_PLI_045 | ⭐ Baja (trivial) |
| `analisis_pasos_22_27_tabla_desarrollo.md` | RF_PLI_047-050 | ⭐⭐⭐ Alta |

### 3.2 Análisis de Pasos 20-27

#### Paso 20: RF_PLI_045_Gener_Precios_Dia
```sql
SELECT Fecha, NEMOTECNICO, Instrumento, Precio_Mid 
INTO Precios_Dia
FROM RF_Fecha_Proceso_Carteras 
INNER JOIN RF_Base_Diaria_Precios ON Fecha = Fecha
WHERE Instrumento = "TCRC";
```

**Análisis:** 
- Trivial - solo filtrar precios por instrumento TCRC
- Ya implementado parcialmente en celda 29

**Implementación Python:**
```python
def generar_precios_dia(df_precios, fecha_proceso, instrumento='TCRC'):
    """Filtra precios por fecha e instrumento."""
    return df_precios[
        (df_precios['Fecha'] == fecha_proceso) &
        (df_precios['Instrumento'] == instrumento)
    ][['Fecha', 'NEMOTECNICO', 'Instrumento', 'Precio_Mid']]
```

---

#### Paso 21: RF_PLI_044e_Modelo_Inversiones_Tabla_Final
**Ya documentado en:** `RF_PLI_044e_Modelo_Inversiones_Tabla_Final_analisis.md`

**Resumen:**
- UNION de 12 queries anidadas
- Combina flujos de 6 instrumentos + garantías + pactos
- Requiere implementar: `generar_tabla_final_inversiones()`

---

#### Pasos 22-26: Insert a Tabla Desarrollo Interna

**Patrón común:** DELETE + INSERT INTO

| Paso | Query | Fuente de Datos |
|------|-------|-----------------|
| 22 | DELETE | Limpia RF_Tabla_Desarrollo_Interna |
| 23 | INSERT ML | RF_PLI_Modelo_Inversiones_Final_CLP |
| 24 | INSERT FFMM | RF_PLI_044f_CarteraInv_FFMM |
| 25 | INSERT HTM | RF_PLI_044i_CarteraInv_HTM |
| 26 | INSERT RT | RF_PLI_044g_CarteraInv_RT |

**Análisis:**
- Pasos 24-26 insertan carteras especiales (Fondos Mutuos, HTM, RT) que NO pasan por el modelo de liquidación
- Estos se insertan directamente con sus flujos originales

**¿Por qué no pasan por liquidación?**
- FFMM: Fondos mutuos se liquidan instantáneamente (días_pago = 0)
- HTM: Held-to-Maturity, no se liquidarán antes de vencimiento
- RT: Renta fija en tránsito, ya comprometida

---

#### Paso 27: RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel

**Tipo:** SELECT con renombrado de columnas para formato Excel

**Análisis:**
- Toma RF_PLI_049 (que es una vista sobre RF_Tabla_Desarrollo_Interna)
- Renombra columnas a formato amigable
- Agrega columnas calculadas (PLAZO_PAGO, etc.)

**Columnas de salida (2079 chars de SQL):**
```
FECHA PROCESO, CODIGO_EMPRESA, OPERACION, COD ACT/PAS, MONEDA_ORIGEN,
MONEDA_COMPENSACION, COMPENSACION, COD_PRO, COD_SUB_PRO, FECHA DE PAGO,
PLAZO_PAGO, FLUJO_CAPITAL, FLUJO_INTERES, VP_CAP, VP_INT_CONT, 
PRECIO_MID, FLUJO_CLP
```

---

## 4. Tareas de Implementación

### 4.1 Mejoras Inmediatas al Notebook

- [ ] Agregar celda de índice con hipervínculos
- [ ] Reorganizar celdas en secciones lógicas
- [ ] Agregar markdown explicativo antes de cada paso
- [ ] Estandarizar output de validación

### 4.2 Funciones a Implementar

| Función | Archivo Destino | Prioridad |
|---------|-----------------|-----------|
| `generar_precios_dia()` | pipeline/precios.py | ⭐ Baja |
| `generar_tabla_final_inversiones()` | output/tabla_final.py | ⭐⭐⭐ Alta |
| `generar_cartera_ffmm()` | pipeline/carteras_especiales.py | ⭐⭐ Media |
| `generar_cartera_htm()` | pipeline/carteras_especiales.py | ⭐⭐ Media |
| `generar_cartera_rt()` | pipeline/carteras_especiales.py | ⭐⭐ Media |
| `formatear_para_excel()` | output/formateador.py | ⭐⭐ Media |

### 4.3 Documentos de Análisis a Crear

- [ ] `analisis_pasos_22_27_tabla_desarrollo.md` - Análisis detallado de integración
- [ ] Actualizar `PLAN_IMPLEMENTACION.md` con nuevos pasos

---

## 5. Criterios de Completitud

El notebook estará "completo" cuando:

1. ✅ Los 27 pasos de df_secuencia tengan su equivalente en Python
2. ✅ Cada paso tenga documentación markdown asociada
3. ✅ Comparación automatizada vs outputs de Access
4. ✅ Diferencias < 1 peso en montos totales
5. ✅ Código movido a módulos en `pipeline/` y `output/`
6. ✅ Tests unitarios para nuevas funciones

---

## 6. Próximos Pasos Recomendados

1. **Hoy:** 
   - Commit del análisis actual
   - Agregar sección de índice al notebook
   
2. **Siguiente sesión:**
   - Implementar `generar_tabla_final_inversiones()` basado en análisis de RF_PLI_044e
   - Crear `analisis_pasos_22_27_tabla_desarrollo.md`

3. **Posterior:**
   - Implementar pasos 22-27
   - Tests de integración end-to-end
   - Merge a rama principal cuando validado
