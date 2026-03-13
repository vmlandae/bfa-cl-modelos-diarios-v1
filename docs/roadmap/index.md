# Roadmap & Plan de Desarrollo

> **Última actualización:** 2026-03-02  
> **Fuente de verdad:** [`docs/roadmap/roadmap.yaml`](https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/blob/main/docs/roadmap/roadmap.yaml)

---

## Visión General

Plan de mejoras al sistema de modelos diarios, organizado en sprints de ~2 semanas.
Cada feature tiene ID, prioridad, tamaño estimado, dependencias y criterios de aceptación.

```mermaid
gantt
    title Roadmap Modelos Diarios 2026
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section S1: Quick Wins
    F02 Snapshots Parámetros     :done, f02, 2026-02-25, 1d
    F14 Cache Primera Vuelta     :done, f14, 2026-02-26, 2d
    F11 Logging Estructurado     :done, f11, 2026-02-26, 2d
    F16 Idempotencia BQ          :done, f16, 2026-02-27, 2d
    F13 Pre-flight Checks        :f13, 2026-03-03, 2d
    F15 Tests Mínimos            :f15, 2026-03-05, 2d

    section S2: Observabilidad
    F12 Config Unificada         :f12, 2026-03-10, 3d
    F01 Torre de Control         :f01, 2026-03-13, 5d
    Dashboard Quick Wins         :done, dqw, 2026-03-12, 2d
    F09 Alertas Inteligentes     :f09, 2026-03-18, 3d

    section S3: Migración
    F03 Modo Fantasma            :f03, 2026-03-24, 5d
    F17 Parallel Smartness       :f17, 2026-03-31, 3d

    section S4: UX
    F04 Scenario Playground      :f04, 2026-04-07, 10d
    F06 Linaje de Datos          :f06, 2026-04-17, 5d

    section Backlog: Datos & Params
    F18 Carga Históricos         :f18, after f06, 7d
    F19 Carga Modelos Old        :f19, after f18, 5d
    F20 Reestructura Parámetros  :f20, after f19, 10d
```

---

## Sprint 1: Quick Wins & Fundamentos

!!! info "25 Feb — 07 Mar 2026"
    Objetivo: Establecer infraestructura base — logging, caché, snapshots, tests.
    Todas las features son independientes y de bajo riesgo.

### F02 — Máquina del Tiempo: Snapshots de Parámetros { #f02 }

| | |
|---|---|
| **Prioridad** | :material-fire:{ .critical } Crítica |
| **Tamaño** | XS (< 2h) |
| **Estado** | :material-check-circle:{ .done } **Completado** (2026-02-27) |
| **Asignado** | @vlandaetat |
| **Archivos** | `core/orquestador.py` |

Snapshot automático de parámetros Excel antes de cada ejecución. `shutil.copy2` en el orquestador → `snapshots/{YYYYMMDD}/{modelo}/`. Lee rutas de `excel_parametros_input` del YAML. Aborta modelo si la copia falla (`RuntimeError`).

**Criterios de aceptación:**

- [x] Cada ejecución copia los parámetros Excel a `snapshots/{YYYYMMDD}/{modelo}/`
- [ ] No afecta el tiempo de ejecución (< 2s overhead)
- [ ] Funciona para los 10 modelos (verificar `ml_inversiones` con rutas UNC)

---

### F14 — Cache de Primera Vuelta { #f14 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | S (2h — 1d) |
| **Estado** | :material-check-circle:{ .done } **Completado** (2026-02-27) |
| **Asignado** | @vlandaetat |
| **Archivos** | `procesamiento_datos_input/cache_tablas.py`, `core/orquestador.py`, modelos de mora y prepago |

Copia raw `.txt` de red → `data/cache/raw/` con metadata JSON (timestamp, MD5). Hooks pre/post ejecución en orquestador con `threading.Lock`. Verificación post-ejecución detecta cambios en red durante ejecución.

**Criterios de aceptación:**

- [x] Primera lectura del día: copia CSV de red, guarda parquet
- [x] Lecturas siguientes: lee parquet local (~95% más rápido)
- [x] Respeta `CACHE_FORZAR_RECARGA` existente y `--forzar-recarga`
- [x] Verificación post-ejecución con checksum MD5

---

### F13 — Pre-flight Checks { #f13 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | S (2h — 1d) |
| **Estado** | :material-calendar-check: Planificado |
| **Archivos** | `core/preflight.py` (nuevo), `core/orquestador.py` |

Health checks de rutas de red y bases Access ANTES de ejecutar modelos. Evita esperar minutos para descubrir que la red está caída.

**Criterios de aceptación:**

- [ ] Verifica accesibilidad de rutas de red para modelos seleccionados
- [ ] Verifica conexión a bases Access
- [ ] Reporta problemas ANTES de iniciar ejecución
- [ ] Opción para continuar solo con modelos que tienen recursos disponibles

---

### F15 — Testing Mínimo Viable { #f15 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | S (2h — 1d) |
| **Estado** | :material-calendar-check: Planificado |
| **Archivos** | `tests/` (nuevo directorio) |

Tests de nivel 1 que validan configuración sin dependencias externas.

**Criterios de aceptación:**

- [ ] `pytest tests/` pasa sin acceso a red ni Access
- [ ] Valida que todos los módulos del orquestador importan
- [ ] Valida que el YAML de config es consistente con el orquestador

---

### F11 — Logging Estructurado { #f11 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | M (1d — 3d) |
| **Estado** | :material-check-circle:{ .done } **Completado** (2026-02-27) |
| **Asignado** | @vlandaetat |
| **Archivos** | `core/logger.py`, `core/orquestador.py`, `procesamiento_datos_input/cache_tablas.py` |

`core/logger.py` con handler dual: consola (emojis, prefijo `[modelo]`) y JSONL (`logs/{fecha}/modelos.jsonl`). Monkey-patch de `builtins.print` para captura completa. `contexto_modelo()` thread-safe vía `contextvars`.

**Criterios de aceptación:**

- [x] Logger con niveles (DEBUG, INFO, WARNING, ERROR)
- [x] Handler JSON para archivo (`logs/{fecha}/modelos.jsonl`)
- [x] Handler consola human-readable con prefijo `[modelo]`
- [x] Contexto automático: modelo, fecha_proceso (vía `contextvars`)
- [x] Migrar `orquestador.py`, `cache_tablas.py` y `main.py`
- [x] Interceptor `builtins.print` → JSONL (cobertura 100%)

---

### F16 — Ejecución Idempotente { #f16 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | S (2h — 1d) |
| **Estado** | :material-check-circle:{ .done } **Completado** (2026-02-28) |
| **Asignado** | @vlandaetat |
| **Archivos** | `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py`, `core/orquestador.py`, `main.py` |

Flag `--force-historico` para re-inserción segura en tablas históricas BQ. Por defecto omite inserción si datos existen (seguro). Con `--force-historico`: backup CSV → metadata JSON pre-DELETE → DELETE → INSERT → metadata JSON post-INSERT. Backups en `backups_historicos/{YYYYMMDD}/{tabla}/`.

**Criterios de aceptación:**

- [x] Por defecto omite inserción si datos existen
- [x] `--force-historico` activa: backup CSV → DELETE → INSERT
- [x] Backup CSV + metadata JSON antes de DELETE
- [x] Migración completa de `print` → `logger` en `hist.py`
- [ ] Test: re-ejecución con `--force-historico` produce `COUNT(*)` idéntico

---

## Sprint 2: Observabilidad

!!! info "10 Mar — 21 Mar 2026"
    Objetivo: Torre de Control MVP + Config unificada + Alertas.

### F12 — Configuración Unificada { #f12 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | M (1d — 3d) |
| **Dependencias** | — |

Unificar la configuración de modelos (hoy en 3 archivos) en un solo YAML.

---

### F01 — Torre de Control { #f01 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | L (3d — 1 semana) |
| **Dependencias** | F11 |

Streamlit dashboard con estado de ejecución, duración, errores y métricas.

---

### F09 — Alertas Inteligentes { #f09 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | M (1d — 3d) |
| **Dependencias** | F11, F01 |

Sanity checks post-ejecución: variación diaria excesiva, reconciliación fuera de tolerancia.

---

## Sprint 3: Migración & Validación

!!! info "24 Mar — 04 Abr 2026"
    Objetivo: Modo Fantasma para inversiones + optimización paralela.

### F03 — Modo Fantasma { #f03 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | L (3d — 1 semana) |
| **Dependencias** | F15 |

Comparación automática VBA vs Python celda por celda con tolerancias. Empezando por inversiones.

---

### F17 — Parallel Smartness { #f17 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | M (1d — 3d) |
| **Dependencias** | F14 |

Ejecución en 2 fases con pre-carga de caché Access compartido.

---

## Sprint 4: Experiencia de Usuario

!!! info "07 Abr — 25 Abr 2026"
    Objetivo: Playground de escenarios + Linaje de datos.

### F04 — Scenario Playground { #f04 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | XL (1 — 2 semanas) |
| **Dependencias** | F14, F11 |

Streamlit con sliders para modificar parámetros y ver efecto en tiempo real.

---

### F06 — Linaje de Datos { #f06 }

| | |
|---|---|
| **Prioridad** | :material-arrow-down-bold:{ .low } Baja |
| **Tamaño** | L (3d — 1 semana) |
| **Dependencias** | F12 |

Grafo interactivo del flujo de datos generado desde el YAML de configuración.

---

---

## Nuevas Features: Datos & Parámetros

!!! warning "DRAFT — Requiere revisión antes de ejecutar"
    Las features F18, F19 y F20 tienen planes detallados en `docs/feats/`.
    Revisar y aprobar antes de comenzar implementación.

### F18 — Carga Históricos Pre-Python { #f18 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | L (3d — 1 semana) |
| **Estado** | :material-file-document-edit: Draft — pendiente revisión |
| **Plan** | [Plan detallado](../feats/carga-historicos/PLAN.md) |

Reconstruir la serie histórica de outputs de modelos anterior a Python.
Dos fuentes complementarias: (1) Access `RF_Modelos_Liquidez.accdb` y sus respaldos
`YYYYMMDD_RF_Modelos_Liquidez.accdb`; (2) Respaldos Excel diarios en
`Y:\RF_RESPALDO_DIARIO\RF_INPUTS`. Se espera ~95% de coincidencia entre fuentes;
implementar ambas y cruzar.

---

### F19 — Carga Modelos Old { #f19 }

| | |
|---|---|
| **Prioridad** | :material-arrow-up-bold:{ .high } Alta |
| **Tamaño** | L (3d — 1 semana) |
| **Estado** | :material-file-document-edit: Draft — pendiente revisión |
| **Plan** | [Plan v2](../feats/carga-modelos-old/PLAN-v2.md) · [Plan original](../feats/carga-modelos-old/PLAN.md) |

Pipeline diario para leer las tablas de desarrollo de modelos que aún no están
en Python (ejecutados manualmente en Excel/VBA), consolidarlas en DuckDB local
y cargarlas a BigQuery. Trabajo previo existe en `feat/carga-modelos-old`.

---

### F20 — Reestructura Sistema Parámetros y Rutas { #f20 }

| | |
|---|---|
| **Prioridad** | :material-arrow-right-bold:{ .medium } Media |
| **Tamaño** | XL (1 — 2 semanas) |
| **Estado** | :material-file-document-edit: Draft — pendiente revisión |
| **Dependencias** | F02 |
| **Rama** | `feature/reestructura-sistema-parametros-y-rutas` |
| **Plan** | [Plan detallado](../feats/reestructura-parametros/PLAN.md) |

Reemplazar los Excel de parámetros por JSON con schema definido. Soportar tipos
nativos (listas, dicts, strings, números) en vez de las limitaciones tabulares
de Excel. Mantener retrocompatibilidad durante la transición.

---

## Backlog Estratégico

Features de largo plazo, priorizables según contexto de negocio.

| ID | Feature | Tamaño | Dependencias | Etiquetas |
|:---|:--------|:-------|:-------------|:----------|
| F05 | Matadero de Access (SQL→Pandas) | L | — | `migración` `access` |
| F07 | Parámetros como Código (Excel→YAML) | XL | F02 ✅ | `parámetros` `regulatorio` |
| F08 | Copiloto Regulatorio (reportes CMF) | XXL | F01, F09 | `regulatorio` `cmf` |
| F10 | Model API (FastAPI) | XXL | F11 ✅, F12 | `api` `arquitectura` |
| F18 | Carga Históricos Pre-Python | L | — | `datos` `histórico` `access` |
| F19 | Carga Modelos Old (legacy→BQ) | L | — | `datos` `legacy` `bigquery` |
| F20 | Reestructura Parámetros (Excel→JSON) | XL | F02 ✅ | `parámetros` `schema` `json` |

---

## Grafo de Dependencias

```mermaid
graph LR
    F02[✅ F02 Snapshots] --> F07[F07 Params YAML]
    F02 --> F20[F20 Params JSON]
    F14[✅ F14 Cache 1ra Vuelta] --> F17[F17 Parallel]
    F14 --> F04[F04 Playground]
    F11[✅ F11 Logging] --> F01[F01 Torre Control]
    F11 --> F09[F09 Alertas]
    F11 --> F04
    F11 --> F10[F10 API]
    F01 --> F09
    F01 --> F08[F08 Regulatorio]
    F09 --> F08
    F12[F12 Config Unificada] --> F06[F06 Linaje]
    F12 --> F10
    F15[F15 Tests] --> F03[F03 Fantasma]
    F13[F13 Pre-flight]
    F16[✅ F16 Idempotencia]
    F05[F05 Matadero Access]
    F18[F18 Históricos]
    F19[F19 Modelos Old]

    style F02 fill:#1B5E20,color:#fff,stroke:#4CAF50,stroke-width:3px
    style F14 fill:#1B5E20,color:#fff,stroke:#4CAF50,stroke-width:3px
    style F11 fill:#1B5E20,color:#fff,stroke:#4CAF50,stroke-width:3px
    style F16 fill:#1B5E20,color:#fff,stroke:#4CAF50,stroke-width:3px
    style F13 fill:#4CAF50,color:#fff
    style F15 fill:#4CAF50,color:#fff
    style F01 fill:#2196F3,color:#fff
    style F12 fill:#2196F3,color:#fff
    style F09 fill:#2196F3,color:#fff
    style F03 fill:#FF9800,color:#fff
    style F17 fill:#FF9800,color:#fff
    style F04 fill:#9C27B0,color:#fff
    style F06 fill:#9C27B0,color:#fff
    style F05 fill:#757575,color:#fff
    style F07 fill:#757575,color:#fff
    style F08 fill:#757575,color:#fff
    style F10 fill:#757575,color:#fff
    style F18 fill:#E91E63,color:#fff
    style F19 fill:#E91E63,color:#fff
    style F20 fill:#E91E63,color:#fff
```

<div style="display: flex; gap: 1em; margin-top: 0.5em; flex-wrap: wrap;">
  <span style="background: #1B5E20; color: white; padding: 2px 8px; border-radius: 4px;">✅ Completado</span>
  <span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px;">Sprint 1 (pendiente)</span>
  <span style="background: #2196F3; color: white; padding: 2px 8px; border-radius: 4px;">Sprint 2</span>
  <span style="background: #FF9800; color: white; padding: 2px 8px; border-radius: 4px;">Sprint 3</span>
  <span style="background: #9C27B0; color: white; padding: 2px 8px; border-radius: 4px;">Sprint 4</span>
  <span style="background: #757575; color: white; padding: 2px 8px; border-radius: 4px;">Backlog</span>
  <span style="background: #E91E63; color: white; padding: 2px 8px; border-radius: 4px;">Nuevas (F18-F20)</span>
</div>

---

## Cómo Contribuir al Roadmap

Ver [Workflow de Planificación](workflow.md) para detalles sobre cómo proponer, discutir y desarrollar features.

**TL;DR:**

1. Editar `docs/roadmap/roadmap.yaml` en una rama
2. Crear MR con etiqueta `roadmap`
3. Discutir en el MR
4. Merge → el roadmap se actualiza automáticamente en MkDocs
