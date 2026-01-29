# Diagnóstico: Carga de Modelos Legacy a GCP

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-01-29

---

## Resumen Ejecutivo

Esta feature aborda la necesidad de cargar a GCP las tablas de desarrollo de modelos de riesgo financiero que **aún no están implementados en Python**, pero que generan outputs críticos en archivos Excel (`.xlsm`/`.xlsx`) ubicados en carpetas compartidas de red.

---

## Contexto del Problema

### Situación Actual

1. **Modelos implementados en Python**: Los modelos `mr_prepago_*`, `ml_mora_*` y `ml_nmd` ya tienen pipelines Python que:
   - Leen datos de entrada
   - Procesan con parámetros
   - Escriben outputs a Excel
   - Cargan resultados a BigQuery

2. **Modelos legacy (no implementados en Python)**: Existen otros modelos que:
   - Se ejecutan manualmente en Excel/VBA
   - Generan hojas de desarrollo (`DESARROLLO`) con resultados
   - **No tienen carga automatizada a GCP**
   - No tienen trazabilidad histórica centralizada

### Problemas Identificados

| Problema | Impacto | Severidad |
|----------|---------|-----------|
| Sin carga automática a GCP | Datos no disponibles para consumo downstream | Alto |
| Sin histórico centralizado | Imposible hacer análisis temporal o auditorías | Alto |
| Datos en carpetas compartidas | Riesgo de modificación sin control | Medio |
| Dependencia de procesos manuales | Errores humanos, inconsistencias | Medio |

---

## ¿Por qué es importante?

1. **Completitud de datos**: Los modelos legacy generan información tan crítica como los modelos Python. Sin cargarlos a GCP, hay un vacío en la visión consolidada de riesgo.

2. **Auditoría y compliance**: Reguladores pueden requerir históricos de desarrollo de modelos. Sin almacenamiento estructurado, esto es imposible.

3. **Transición gradual**: Mientras se migran estos modelos a Python, la carga automatizada permite:
   - No perder datos durante la transición
   - Comparar outputs legacy vs nuevos pipelines
   - Validar equivalencia antes de deprecar Excel

---

## Solución Propuesta

### Arquitectura de Alto Nivel

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Carpetas Compartidas│     │   Módulo Python  │     │      GCP        │
│  (Excel legacy)     │────▶│   carga_old      │────▶│   BigQuery      │
│                     │     │                  │     │                 │
└─────────────────────┘     └────────┬─────────┘     └─────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │    DuckDB        │
                            │  (histórico      │
                            │   local)         │
                            └──────────────────┘
```

### Componentes

1. **`carga_modelos_gcp/cargar_modelos_old.py`**: Lee Excel de carpetas compartidas, extrae hoja `DESARROLLO`, carga a BigQuery.

2. **`almacenamiento_local/duckdb_manager.py`**: Gestiona base de datos DuckDB para histórico local.

3. **`config/config_modelos_old.yaml`**: Configuración de rutas y metadatos de modelos legacy.

---

## ¿Por qué estas decisiones técnicas?

### ¿Por qué DuckDB y no SQLite?

| Criterio | DuckDB | SQLite |
|----------|--------|--------|
| Modelo de datos | Columnar (OLAP) | Row-based (OLTP) |
| Queries analíticos | 10-100x más rápido | Lento en agregaciones |
| Compresión | ~10x mejor | Básica |
| Append masivo | Muy eficiente | Decente |
| Integración Pandas | Nativa | Requiere conversión |
| Caso de uso | ✅ Series temporales, históricos | ❌ Transacciones frecuentes |

**Conclusión**: Para datos históricos que crecen día a día y se consultan en bulk, DuckDB es objetivamente superior.

### ¿Por qué no migrar los modelos directamente a Python?

1. **Esfuerzo**: Migrar modelos complejos con VBA puede tomar semanas/meses.
2. **Riesgo**: Introducir bugs durante migración apresurada.
3. **Prioridad**: La carga a GCP es urgente; la migración puede ser gradual.
4. **Validación**: Tener datos legacy en GCP permite validar futuras migraciones.

### ¿Por qué histórico local además de GCP?

1. **Redundancia**: Backup local ante fallos de red/GCP.
2. **Velocidad**: Queries locales son más rápidos para análisis exploratorio.
3. **Costos**: Evita queries costosas en BigQuery durante desarrollo.
4. **Debugging**: Facilita comparar datos día a día sin conexión.

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Carpeta compartida inaccesible | Media | Reintentos + logs claros |
| Hoja DESARROLLO no existe | Baja | Validación + skip con warning |
| Formato de datos inconsistente | Media | Schema flexible + validación |
| DuckDB crece demasiado | Baja | Particionamiento + retención |

---

## Referencias

- [DuckDB Documentation](https://duckdb.org/docs/)
- [BigQuery Python Client](https://cloud.google.com/python/docs/reference/bigquery/latest)
- Arquitectura actual: `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py`
