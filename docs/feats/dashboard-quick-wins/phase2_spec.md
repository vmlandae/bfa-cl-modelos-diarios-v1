# Dashboard Phase 2 — Spec Técnica

> **Fecha:** 2026-03-13
> **Estado:** Borrador para revisión
> **Pre-requisito:** Quick Wins Phase 1 completados (QW-0 a QW-5, excepto QW-2)
> **Referencia:** [`brainstorm.md`](brainstorm.md) para visión completa, [`quick_wins_spec.md`](quick_wins_spec.md) para Phase 1

---

## Tabla de Contenidos

- [Contexto: Estado actual vs Brainstorm](#contexto-estado-actual-vs-brainstorm)
- [Cruce con Roadmap existente](#cruce-con-roadmap-existente)
- [P2-1: Vista Calendario de Ejecuciones](#p2-1-vista-calendario-de-ejecuciones)
- [P2-2: Observatorio de Inputs](#p2-2-observatorio-de-inputs)
- [P2-3: Tendencias de Outputs](#p2-3-tendencias-de-outputs)
- [P2-4: Alertas In-App](#p2-4-alertas-in-app)
- [P2-5: Health Dashboard](#p2-5-health-dashboard)
- [P2-6: Reproducibilidad — Descargas Selectivas](#p2-6-reproducibilidad--descargas-selectivas)
- [P2-7: Navegación Inter-Página con Contexto](#p2-7-navegación-inter-página-con-contexto)
- [P2-8: Reporte Email de Amortización (Primera Vuelta)](#p2-8-reporte-email-de-amortización-primera-vuelta)
- [Orden de Implementación](#orden-de-implementación)
- [Dudas Abiertas](#dudas-abiertas)

---

## Contexto: Estado actual vs Brainstorm

### Lo que ya existe (Phase 1)

| Capacidad del Brainstorm | Cobertura | Página |
|---|---|---|
| 2.1 Mission Control (vista diaria) | ✅ Completa | 1_Home.py |
| 2.2 Vista Calendario | ❌ Pendiente | — |
| 2.3 Vista Histórica de Ejecuciones | ⚠️ Parcial (Home muestra la última, no tabla filtrable) | 1_Home.py |
| 3.1 Visor de Logs JSONL | ✅ Completa | 2_Logs.py |
| 3.2 Vista Resumen de Logs | ⚠️ Parcial (pie chart sí, timeline y dedup no) | 2_Logs.py |
| 4.2 Diff de Parámetros | ✅ Completa (JSON), ⚠️ Solo SHA para Excel | 5_Parametros.py |
| 6.2 Comparación de Outputs | ✅ Funcional (t vs t-1, UNION 11 tablas) | 3_Comparacion.py |
| 7.3 Benchmarks de Performance | ✅ Completa | 4_Benchmark.py |

### Lo que NO se ha tocado del brainstorm

| Sección | Capacidades | Prioridad sugerida P2 |
|---|---|---|
| 2.2 Calendario | Grid mensual + click drill-down | 🟢 Alta — QW-2 original |
| 5. Observatorio de Inputs | Checklist inputs, row counts, anomalías | 🟢 Alta — operador daily |
| 6.1 Preview de Outputs | Resumen estadístico + ↑↓ vs ayer | 🟡 Media |
| 7.1-7.2 Tendencias de Outputs | Series temporales de métricas de output | 🟢 Alta — gerente story |
| 10.1 Health Dashboard | Conexiones, disco, credenciales, ODBC | 🟡 Media — TI story |
| 11.1 Alertas | Reglas predefinidas, in-app | 🟢 Alta — supervisor story |
| 8.2 Descargas Selectivas | Inputs/outputs/params por fecha | 🟡 Media — auditor story |
| 3.3 Comparación de Logs | Side-by-side de 2 fechas | 🔵 Baja |
| 4.3-4.4 Gestión de Parámetros | Descarga, timeline, versionado | 🔵 Baja |
| 9 Auditoría completa | Audit trail, reconciliación, evidence pack | 🔴 Post-P2 |
| 13 Gobierno de Modelos | Inventario, backtesting, PSI/CSI | 🔴 Post-P2 |
| 15 Moonshots | AI assistant, Teams bot, scenario engine | 🔴 Post-P2+ |

---

## Cruce con Roadmap existente

Varias features del brainstorm tienen equivalentes directos en el roadmap de `docs/roadmap/index.md`. Conviene fusionarlas para no duplicar esfuerzo.

| Feature Roadmap | Feature Dashboard Brainstorm | Relación | Recomendación |
|---|---|---|---|
| **F01 — Torre de Control** | §2.1-2.3 Centro de Control | **Duplicado directo** | ✅ Phase 1 ya entregó esto. F01 se puede marcar done o redirigir a P2 (calendario + histórico filtrable). |
| **F09 — Alertas Inteligentes** | §11 Alertas y Notificaciones | **Solapamiento fuerte** | 🔄 P2-4 (Alertas In-App) cubre la mitad UI. F09 cubre la mitad de reglas de negocio (sanity checks post-ejecución). **Fusionar**: F09 provee las reglas, el dashboard las muestra. |
| **F04 — Scenario Playground** | §15.11 Sandbox/Playground, §13.3 Sensitivity Analysis | **Equivalente** | ⏸️ Mantener en S4. No es P2. Pero el dashboard P2 puede preparar el terreno (selector de params + re-ejecución parcial). |
| **F06 — Linaje de Datos** | §12.3 Data Lineage, §5.4 Trazabilidad de Origen | **Equivalente** | ⏸️ Mantener en S4. F06 genera el grafo desde el YAML; el dashboard lo visualiza. |
| **F12 — Config Unificada** | §14 UX/Arquitectura (sidebar global) | **Complementario** | F12 unifica YAML → el dashboard lee ese YAML para lista de modelos, rutas, etc. F12 no es dashboard per se, pero lo habilita. |
| **F13 — Pre-flight Checks** | §5.1 Estado de Inputs del Día, §10.1 Health Dashboard | **Solapamiento parcial** | 🔄 F13 ejecuta los checks; P2-5 (Health Dashboard) los visualiza. F13 como backend, P2-5 como frontend. |
| **F03 — Modo Fantasma** | §6.3 Validación de Outputs | **Complementario** | F03 genera los datos de comparación VBA vs Python; el dashboard podría mostrarlos en una página dedicada (post-P2). |

### Recomendaciones de merge

1. **Cerrar F01**: Phase 1 del dashboard ya entrega lo que F01 describía. Reasignar scope restante (calendario, histórico) a P2.
2. **Fusionar F09 ↔ P2-4**: Las reglas de negocio de F09 (variación excesiva, reconciliación) se convierten en los checks que alimentan el panel de Alertas del dashboard.
3. **Fusionar F13 ↔ P2-5**: Los pre-flight checks de F13 se convierten en la vista de Health Check del dashboard, con botón de "ejecutar check ahora".

---

## P2-1: Vista Calendario de Ejecuciones

> *Originalmente QW-2. Diferida de Phase 1 por complejidad UI.*

### User Story
*"Como supervisor, quiero ver un calendario mensual con el estado de cada día (OK/parcial/error/no ejecutado), para detectar gaps y ver de un vistazo la salud operativa del mes."*

### Fuente de Datos

**BQ `reportes_ejecucion`** — ya se usa en Home:
```sql
SELECT fecha_proceso, status_global, duracion_total_seg
FROM `{PROJECT_ID}.{DATASET_DLY}.reportes_ejecucion`
WHERE fecha_proceso BETWEEN @inicio AND @fin
ORDER BY fecha_proceso, timestamp
```

Consolidar por día usando la misma lógica de `_consolidar_dia()` de Home.

**Feriados**: `bfa_cl_utilidades.es_dia_laboral(fecha)` — ya en deps.

### Enfoque UI: Plotly Heatmap Calendar

En Phase 1 se pospuso por la complejidad de armar un calendario con `st.columns(7)`. La alternative que recomiendo ahora:

**Opción A — Plotly Heatmap (calendarplot)**:
- Usar `go.Heatmap` con un grid de 7×5 (semana × días).
- Cada celda con color (OK=verde, PARCIAL=amarillo, ERROR=rojo, no-ejecutado=blanco, feriado/fds=gris).
- `customdata` para hover con detalle (duración, modelos OK/error).
- Click → `st.session_state["fecha_calendario"] = fecha` → redirigir a Home.

**Opción B — HTML/CSS calendar**:
- Renderizar con `st.markdown(html, unsafe_allow_html=True)`.
- Más control visual, menos interactividad.
- Click requiere formulario o `st.query_params`.

### KPIs del mes
- Días hábiles: N
- Ejecutados OK: N (%)
- Parciales: N
- Errores: N
- Sin ejecución: N
- Duración promedio: Xs
- Racha actual: N días OK
- Cobertura: X%

### Navegación drill-down
- Click en día → `st.switch_page("pages/1_Home.py")` con `st.query_params["fecha"] = fecha`.
- Requiere que Home lea `st.query_params` para pre-cargar fecha (ver P2-7).

### Confianza: 🟡 78%

**Riesgos:**
- (12%) Plotly heatmap calendar no es trivial — el posicionamiento de texto (día del mes) dentro de celdas requiere trabajo. `plotly_calplot` existe como librería pero puede no tener la granularidad que queremos.
- (5%) Click-to-navigate entre páginas Streamlit sigue con fricciones (session_state vs query_params timing).
- (5%) Meses con pocas ejecuciones se verán vacíos. Necesitamos el indicador de gaps.

**Confianza condicional:**
- Si usamos HTML/CSS en vez de plotly → 🟢 85% (más fácil de implementar, menos interactivo)
- Si aceptamos calendarplot/plotly_calplot como dep → 🟢 83%
- Si simplificamos a una tabla resumen (no visual calendario) → 🟢 95%

### Dudas
- **D-P2-1.1**: ¿Preferimos un calendario visual real (grid tipo Google Calendar) o una vista tipo tabla resumen (filas = días, columnas = métricas)? La tabla es más fácil y funcional, pero menos visual.
- **D-P2-1.2**: ¿Cuántos meses navegables? Datos significativos empiezan ~2026-02-25. ¿Limitamos a 3 meses o sin límite?
- **D-P2-1.3**: ¿Incluimos detalle de duración en el calendario (ej: mini-bar en cada celda) o solo color de estado?

---

## P2-2: Observatorio de Inputs

> *Brainstorm §5. Feature nueva — no estaba en Phase 1.*

### User Story
*"Como practicante, quiero ver antes de ejecutar si todos los inputs del día están disponibles y en buen estado (interfaz PML, Access, parámetros), y como supervisor, quiero ver si hubo anomalías en los inputs (row count diferente, archivos truncados)."*

### Sub-features

#### A) Checklist Pre-ejecución (relacionado con F13 Pre-flight)

Fuente: `reports/health_check.json` + verificación en vivo.

```
┌─────────────────────────────────────────────────────────────┐
│  📥 Estado de Inputs — 2026-03-13                           │
│                                                             │
│  ── Interfaces ─────────────────────────────────────────── │
│  ✅ PML Interface     │ 3,847 filas │ 12.4 MB │ 08:02     │
│  ✅ BD_Gestion_RL     │ accesible   │ 842 MB  │ 07:55     │
│  ✅ BD_Gestion_RM     │ accesible   │ 156 MB  │ 07:55     │
│  ⚠️ PT_Puente         │ no encontrado (¿aplica hoy?)      │
│                                                             │
│  ── Parámetros ──────────────────────────────────────────  │
│  ✅ Sin cambios vs ayer (9/10 modelos idénticos)           │
│  🔄 ml_mora_consumo: GAMMA_1[0] cambió (-0.013 → -0.015) │
│                                                             │
│  ── Cache ────────────────────────────────────────────────  │
│  💾 Cache del día: No generado aún (se creará al ejecutar) │
│  💾 Cache ayer: 45 tablas, 1.2 GB, válido                 │
└─────────────────────────────────────────────────────────────┘
```

#### B) Comparación de Inputs entre Días

Fuente: `data/cache/` metadata JSONs + BQ si hubiera pipeline de conteo.

- Row count de interfaz PML: ¿cuántas filas hoy vs ayer? ¿Δ > 5%?
- Row count de tablas Access: conteo por tabla clave.
- Detección de archivos truncados (tamaño < 50% del promedio).

### Implementación

**Opción pragmática**: Reutilizar `tools/check_env.py` (14-point diagnostic) como backend. El check_env.py ya verifica:
1. Python versión
2. Dependencias pip
3. Archivos de credenciales
4. Rutas de red
5. Conexión Access ODBC
6. BigQuery
7. Estructura de directorios

El dashboard invoca estas checks y muestra resultados.

**Opción avanzada**: Leer los `.meta.json` del cache (generados por F14) para obtener timestamps, row counts y hashes de cada input cacheado.

### Confianza: 🟡 70%

**Riesgos:**
- (15%) Verificar acceso a Access/ODBC en vivo desde Streamlit → ¿es seguro? El driver ODBC podría bloquear. Las comprobaciones de red (UNC paths) pueden tener timeout largo si la red está lenta.
- (8%) Los `.meta.json` del cache no tienen row count de cada tabla Access individual — solo del archivo parquet consolidado. Necesitaríamos o extender la metadata de cache o hacer queries directas (lento).
- (5%) `health_check.json` solo se genera al ejecutar `check_env.py`, no en tiempo real. ¿Ejecutamos el check cada vez que se abre la página? → timeout potencial.
- (2%) La interfaz PML llega a una hora variable. Si el practicante abre el dashboard a las 7:30 y la PML llega a las 8:00, el check dará falso negativo.

**Confianza condicional:**
- Si nos limitamos a mostrar `health_check.json` ya generado → 🟢 88% (sin checks en vivo)
- Si agregamos check en vivo con timeout de 5s por recurso → 🟡 75%
- Si fusionamos con F13 Pre-flight como backend compartido → 🟢 82%

### Dudas
- **D-P2-2.1**: ¿Queremos checks en vivo al abrir la página (riesgo de timeout) o solo mostrar el último `health_check.json` (estático pero seguro)?
- **D-P2-2.2**: ¿Los `.meta.json` del cache tienen la información suficiente para row counts por tabla, o solo hay metadata a nivel de archivo?
- **D-P2-2.3**: ¿El `check_env.py` actual es importable como módulo Python, o es solo un script de consola? → Determina si podemos llamar sus checks programáticamente.
- **D-P2-2.4**: ¿Hay un momento fijo del día donde se garantiza que los inputs estén disponibles? (ej: "la PML siempre llega antes de las 8:30"). Esto afecta la lógica del semáforo "pendiente vs no disponible".
- **D-P2-2.5**: ¿Los row counts de la interfaz PML varían mucho día a día? Si la variación normal es ±2%, un umbral de alerta del 5% es razonable. Si varía ±20%, necesitamos otro enfoque.

---

## P2-3: Tendencias de Outputs

> *Brainstorm §7.1-7.2. Feature nueva — alto valor para gerente/supervisor.*

### User Story
*"Como gerente, quiero ver cómo evolucionan las métricas clave de los outputs (amortización total, por moneda, por modelo) en el tiempo, para detectar tendencias, anomalías, y tener datos para presentaciones."*

### Fuente de Datos

**BQ Historical tables** — las mismas 11 tablas de 3_Comparacion.py, pero ahora como serie temporal:
```sql
SELECT fecha_proceso,
       MONEDA_ORIGEN,
       SUM(AMORTIZACION) AS total_amort
FROM `{PROJECT_ID}.{DATASET_HIST}.report_{modelo}_hist`
WHERE fecha_proceso BETWEEN @inicio AND @fin
GROUP BY fecha_proceso, MONEDA_ORIGEN
ORDER BY fecha_proceso
```

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  📈 Tendencias de Outputs                                   │
│                                                             │
│  Rango: [Último mes ▼]  Modelo: [Todos ▼]  Moneda: [CLP ▼]│
│                                                             │
│  ── Amortización Total por Modelo ────────────────────────  │
│  [Stacked area chart: 10 modelos apilados, x=fecha]        │
│                                                             │
│  ── Amortización por Moneda ──────────────────────────────  │
│  [Line chart: CLP, CLF, USD — con eje dual si difieren]    │
│                                                             │
│  ── Variación Diaria (%) ─────────────────────────────────  │
│  [Bar chart: Δ% día vs día anterior, color=verde/rojo]     │
│                                                             │
│  ── Tabla Resumen ────────────────────────────────────────  │
│  │ Modelo         │ Última  │ Promedio │ Δ% WoW │ Δ% MoM │
│  │────────────────│─────────│──────────│─────────│────────│
│  │ Prepago Consumo│ 1,234 M │ 1,198 M │  +3.0%  │  -1.2% │
│  │ Mora Consumo   │   89 M  │   91 M  │  -2.2%  │  +0.5% │
│  │ ...            │         │          │         │        │
│                                                             │
│  📥 [CSV] [Excel]                                           │
└─────────────────────────────────────────────────────────────┘
```

### Implementación

1. Reutilizar la UNION ALL de 3_Comparacion.py pero con GROUP BY fecha_proceso.
2. Caching con TTL largo (300s) — los datos históricos no cambian.
3. Opción de seleccionar modelo individual o "todos" (stacked).
4. Selector de métricas: amortización, saldo, #filas (lo que esté disponible por modelo).
5. Detección de anomalías: Calcular z-score sobre ventana móvil de 20 días. Si |z| > 2 → marcar punto.

### Relación con 3_Comparacion.py

`3_Comparacion.py` ya tiene la query UNION y el parsing. Tendencias es una extensión natural:
- Comparación: 2 fechas, tabla de diff.
- Tendencias: N fechas, gráfico temporal.
- **Opción**: Fusionar ambas en una sola página con tabs ("Comparar 2 fechas" | "Ver tendencia") o mantener separadas.

### Confianza: 🟢 82%

**Riesgos:**
- (8%) Query pesada: UNION ALL de 11 tablas × 90 días → puede ser lenta. Mitigación: cache agresivo, limitar fechas, o crear vista materializada en BQ.
- (5%) No todas las tablas hist tienen los mismos campos. La AMORTIZACION debería existir en todas, pero otras métricas (tasa, plazo) varían. Necesitamos un mapping por modelo.
- (3%) Los datos hist empezaron ~2026-02 con gaps. Series con huecos generan gráficos engañosos. Mitigación: interpolar o marcar gaps explícitamente.
- (2%) Escala: amortización en CLP es millones, en CLF es miles. Ejes duales o normalización necesaria.

**Confianza condicional:**
- Si solo graficamos AMORTIZACION (campo universal) → 🟢 90%
- Si creamos vista materializada en BQ → 🟢 88% (perf asegurada)
- Si aceptamos gaps visibles sin interpolación → 🟢 87%

### Dudas
- **D-P2-3.1**: ¿Qué métricas del output son universales a todos los modelos? AMORTIZACION parece serlo. ¿Hay otras? (SALDO, TASA, N_REGISTROS)
- **D-P2-3.2**: ¿El gerente necesita ver tendencias en moneda local (CLP) o también en UF/CLF? ¿Con tipo de cambio fijo o del día?
- **D-P2-3.3**: ¿Fusionamos con 3_Comparacion.py (tabs en la misma página) o página separada? → Preservar ambas parece más claro dado que sirven a flows distintos.
- **D-P2-3.4**: ¿Cuántos días hacia atrás es el rango útil? Si los hist tienen solo ~3 semanas de datos limpios, un selector de 90 días mostrará mayormente vacío. ¿Ajustamos el default al rango con datos?
- **D-P2-3.5**: ¿Queremos variación WoW/MoM calculada automáticamente o solo la serie y que el usuario compare visualmente?

---

## P2-4: Alertas In-App

> *Brainstorm §11. Fusionable con F09 — Alertas Inteligentes del roadmap.*

### User Story
*"Como supervisor, quiero ver en el dashboard una lista de alertas activas basadas en reglas predefinidas (ejecución fallida, variación excesiva de output, performance degradada), sin necesidad de revisar cada página individualmente."*

### Alcance P2 (MVP de alertas)

**En scope:**
- Panel de alertas en sidebar o en Home (badge con contador).
- Reglas predefinidas (hardcoded, no configurables por UI aún).
- Alertas generadas al cargar el dashboard (no real-time push).

**Fuera de scope (post-P2):**
- Notificaciones externas (email, Teams, Slack).
- Reglas configurables por UI.
- Escalamiento automático.
- Historial de alertas con ACK/resolución.

### Reglas predefinidas (P2)

| # | Regla | Fuente | Umbral | Severity |
|---|---|---|---|---|
| R1 | Ejecución no realizada hoy (día hábil) | BQ reportes | Sin registro para hoy pre-11:00 | 🔴 Error |
| R2 | Ejecución con status ERROR | BQ reportes | status_global = ERROR | 🔴 Error |
| R3 | Ejecución PARCIAL (no todos los modelos) | BQ reportes | modelos_ok < 10 | 🟡 Warning |
| R4 | Duración > 2× mediana histórica | BQ benchmark | total_seg > 2 * mediana(últimos 20) | 🟡 Warning |
| R5 | Variación de output > 10% | BQ hist | |Δ_amort_pct| > 10% vs día anterior | 🟡 Warning |
| R6 | Sync a BQ pendiente > 4h | Local _pendientes_sync/ | archivos con age > 4h | 🟡 Warning |
| R7 | Parámetros cambiaron | Snapshots manifest | SHA diff vs día anterior ≠ ∅ | 🔵 Info |

### UI

**Opción A — Badge en sidebar**:
```
Sidebar:
🏠 Home
📋 Logs
📊 Comparación
📈 Benchmark
⚙️ Parámetros
────────────────
🔔 Alertas (3)   ← badge con count
```
Click → expande panel con lista de alertas, cada una con link a la página relevante.

**Opción B — Sección en Home**:
Debajo de las tarjetas de modelos, un bloque colapsable:
```
⚠️ 3 Alertas Activas
├── 🔴 Ejecución de 2026-03-13 con ERROR (ml_inversiones timeout)
├── 🟡 NMD 48% más lento que mediana (140s vs 95s promedio)
└── 🔵 Parámetros de mora_consumo cambiaron hoy
```

### Implementación

```python
# Pseudocódigo del motor de alertas
def evaluar_alertas(fecha: date) -> list[Alerta]:
    alertas = []
    # R1: Ejecución no realizada
    reporte = cargar_reporte_bq(fecha)
    if reporte is None and es_dia_laboral(fecha) and ahora.hour >= 11:
        alertas.append(Alerta("error", "Ejecución no realizada", f"No hay reporte para {fecha}"))
    # R2-R3: Status
    if reporte and reporte["status_global"] == "ERROR": ...
    # R4: Benchmark
    mediana = calcular_mediana_benchmark(ultimos_20_dias)
    if reporte and reporte["duracion_total_seg"] > 2 * mediana: ...
    # R5: Variación output
    delta = calcular_delta_output(fecha, fecha - 1)
    if abs(delta) > 0.10: ...
    # R6: Sync pendiente
    pendientes = listar_pendientes_sync()
    if any(age > timedelta(hours=4) for age in pendientes): ...
    # R7: Parámetros
    if params_cambiaron(fecha): ...
    return alertas
```

Motor de alertas en un módulo compartido (`dashboard/utils/alertas.py`) que cada página puede consultar.

### Relación con F09

F09 del roadmap es "Alertas Inteligentes: sanity checks post-ejecución". La propuesta es:
- **F09 backend** (`core/alertas.py`): Define las reglas de negocio y las evalúa durante/después de la ejecución del pipeline. Escribe alertas al `reporte_json`.
- **P2-4 frontend** (`dashboard/utils/alertas.py` + UI): Lee las alertas del reporte + evalúa reglas dashboard-only (R1 no-ejecutado, R6 sync pendiente). Muestra en la UI.
- **Merge point**: El campo `alertas` del `reporte_json` ya existe. F09 enriquece qué se escribe ahí; P2-4 lo lee y agrega las suyas propias.

### Confianza: 🟡 73%

**Riesgos:**
- (12%) R5 (variación de output) requiere query a 11 tablas hist para calcular delta — lenta. Mitigación: pre-calcular en el reporte de ejecución, o cache largo.
- (8%) Timing de R1: "No hay reporte para hoy" depende de la hora. Si el dashboard se abre a las 7am y la ejecución es a las 9am, falsa alarma. Necesitas un deadline configurable.
- (5%) Alertas en sidebar requieren evaluación al cargar app.py (antes de cualquier página). Esto agrega latencia al startup.
- (2%) Sin persistencia de estado "ya vi esta alerta" — reaparece cada reload.

**Confianza condicional:**
- Si diferimos R5 (variación output) a post-P2 → 🟢 82%
- Si usamos Opción B (sección en Home, no sidebar global) → 🟢 80% (evita latencia startup)
- Si reutilizamos el campo `alertas` del reporte como fuente principal → 🟢 85%

### Dudas
- **D-P2-4.1**: ¿Sidebar global o sección en Home? Sidebar es más visible pero agrega complejidad (evaluar antes de renderizar cualquier página). Home es más simple pero el usuario tiene que navegar ahí.
- **D-P2-4.2**: ¿El campo `alertas` del `reporte_json` ya contiene alertas de benchmark? → Sí, desde el fix de `_calcular_benchmark()`. ¿Qué otras alertas queremos que el pipeline genere vs que el dashboard evalúe?
- **D-P2-4.3**: ¿Deadline para R1 (ejecución no realizada)? ¿11:00? ¿Configurable? ¿O la dejamos fuera del MVP y solo mostramos alertas post-ejecución?
- **D-P2-4.4**: ¿Los umbrales (2× mediana, 10% variación, 4h sync) son razonables? ¿Hay criterio de negocio para esto?

---

## P2-5: Health Dashboard

> *Brainstorm §10. Complementario con F13 Pre-flight Checks.*

### User Story
*"Como DevOps/operador, quiero ver el estado de salud del entorno de ejecución (Python, Access, red, GCP, disco) para diagnosticar problemas antes de que afecten la ejecución."*

### Fuente de Datos

**`reports/health_check.json`** — generado por `tools/check_env.py`:
```json
{
  "timestamp": "2026-03-13T08:15:00",
  "checks": {
    "python_version": {"status": "ok", "detail": "3.11.14"},
    "conda_env": {"status": "ok", "detail": "bfa-cl-modelos-v2"},
    "odbc_access": {"status": "ok", "detail": "Microsoft Access Driver"},
    "rutas_red": {"status": "warning", "detail": "2/3 accesibles"},
    "gcp_credentials": {"status": "ok", "detail": "expires 2027-01-15"},
    "bigquery": {"status": "ok", "detail": "latency 1.2s"},
    "disk_space": {"status": "ok", "detail": "45 GB free"}
  }
}
```

**Complementar con:**
- Tamaño de carpetas: `du -sh logs/ snapshots/ data/cache/ backups_historicos/`
- Cola de retry: `reports/_pendientes_sync/` file count + age
- Credenciales: fecha de expiración del service account JSON

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  🏥 Salud del Entorno                                       │
│                                                             │
│  Último check: 2026-03-13 08:15  [🔄 Ejecutar check ahora] │
│                                                             │
│  ✅ Python 3.11.14 (conda: bfa-cl-modelos-v2)              │
│  ✅ ODBC Access: Microsoft Access Driver (*.mdb, *.accdb)   │
│  ✅ BigQuery: ok (1.2s latencia)                            │
│  ✅ GCP Credenciales: válidas (expiran 2027-01-15)          │
│  ⚠️ Rutas de red: 2/3 accesibles                           │
│     ❌ \\vmdvorak\...\PT_Puente — timeout                  │
│  ✅ Disco: 45 GB libres                                     │
│                                                             │
│  ── Uso de Almacenamiento ────────────────────────────────  │
│  logs/          │ ████████░░ │  234 MB │ 15 fechas          │
│  snapshots/     │ ██░░░░░░░░ │   48 MB │ 15 manifests       │
│  data/cache/    │ ████████████│ 1.2 GB │ 45 tablas          │
│  backups_hist/  │ █░░░░░░░░░ │   12 MB │ 3 backups          │
│                                                             │
│  ── Cola de Sync ─────────────────────────────────────────  │
│  📤 0 reportes pendientes de sync a BigQuery                │
└─────────────────────────────────────────────────────────────┘
```

### Implementación

1. **Lectura estática**: Leer `health_check.json` y mostrar resultados.
2. **Botón "Ejecutar check"**: Invocar `check_env.py` como subprocess y mostrar resultado.
3. **Storage metrics**: `pathlib.Path.stat()` recursivo sobre las carpetas clave.
4. **Sync queue**: Contar archivos en `_pendientes_sync/`.

### Confianza: 🟢 85%

**Riesgos:**
- (8%) El botón "Ejecutar check ahora" corre un subprocess — si `check_env.py` tiene timeout largo (ej: red caída), bloquea la UI. Mitigación: timeout de 15s, ejecutar en thread.
- (5%) `check_env.py` podría no ser importable como módulo (solo script). Verificar estructura.
- (2%) Storage metrics en Windows con `pathlib` son lentas para carpetas grandes. Mitigación: cache 60s.

**Confianza condicional:**
- Si `check_env.py` es importable → 🟢 90%
- Si solo mostramos JSON estático (sin botón live) → 🟢 93%

### Dudas
- **D-P2-5.1**: ¿`check_env.py` es importable como módulo o es puramente `__main__` script? → Determina si podemos invocar checks individuales.
- **D-P2-5.2**: ¿El `health_check.json` se actualiza automáticamente en cada ejecución del pipeline, o solo cuando se corre `check_env.py` manualmente?
- **D-P2-5.3**: ¿Queremos mostrar el tamaño de las tablas BQ (row count, bytes)? → Implica query a `INFORMATION_SCHEMA.TABLE_STORAGE`, lo cual agrega complejidad pero es muy útil para el data engineer.

---

## P2-6: Reproducibilidad — Descargas Selectivas

> *Brainstorm §8.2. Valor alto para auditor.*

### User Story
*"Como auditor/supervisor, quiero poder descargar desde el dashboard los artefactos de una fecha específica (reporte, log, parámetros, outputs) para documentación o análisis offline."*

### Alcance P2

No es el "paquete de reproducibilidad completo" del brainstorm (§8.1 con GCS bucket), sino descargas puntuales de lo que ya existe localmente.

### Descargas por tipo

| Artefacto | Fuente | Formato | Desde página |
|---|---|---|---|
| Reporte ejecución | reports/{fecha}/ | JSON + MD | Home |
| Log del día | logs/{fecha}/ | JSONL + CSV filtrado | Logs |
| Parámetros (snapshot) | snapshots/store/ | JSON + Excel original | Parámetros |
| Manifest del día | snapshots/manifests/ | JSON | Parámetros |
| Output Excel de modelo | RF_Modelo_*/ | Excel | Comparación |
| Benchmark historial | data/benchmark/ | CSV | Benchmark |

### Implementación

Varios de estos downloads ya existen parcialmente:
- **Logs**: `2_Logs.py` ya tiene `st.download_button` para CSV filtrado. ✅
- **Benchmark**: `4_Benchmark.py` podría tener download del historial. ⚠️ No existe aún.
- **Home**: Agregar botón para descargar `reporte_ejecucion.json` y `.md`. ⚠️ No existe aún.
- **Parámetros**: Agregar botón para descargar manifest y archivos del store. ⚠️ No existe aún.

Para cada botón: `st.download_button` con el contenido leído de disco. Trivial.

**Descarga en ZIP** (nice-to-have): "Descargar todo de esta fecha" → `.zip` con reporte + log + manifest + parámetros. Usar `io.BytesIO` + `zipfile`.

### Confianza: 🟢 92%

Extremadamente simple. Solo `st.download_button` + lectura de archivos locales.

**Riesgo único (8%)**: Los outputs Excel de modelos están en subcarpetas (`RF_Modelo_*/`) y pueden ser pesados (~5-20 MB cada uno). Un ZIP de todo podría ser >100 MB. → Limitar a artefactos livianos (reporte, log, params) para el "download all".

### Dudas
- **D-P2-6.1**: ¿Agregamos un botón "Descargar todo" (ZIP) o solo botones individuales por artefacto? El ZIP es más útil para auditores pero puede ser lento/pesado.
- **D-P2-6.2**: ¿Los outputs Excel de los modelos se descargan desde este dashboard o se accede a ellos por otra vía? Si se incluyen, ¿solo el último día o seleccionable?

---

## P2-7: Navegación Inter-Página con Contexto

> *No es una "feature visible" sino una mejora transversal de UX.*

### Objetivo

Permitir que las páginas se comuniquen contexto entre sí:
- Home → "Ver logs de este día" → Logs pre-filtrado
- Home → "Ver benchmark" → Benchmark con fecha resaltada
- Calendario → click en día → Home con esa fecha
- Alertas → click en alerta → página relevante con contexto

### Implementación

Streamlit 1.30+ soporta `st.query_params` (dict-like):
```python
# En Home, al hacer click en "Ver logs":
st.query_params["fecha_proceso"] = "2026-03-13"
st.query_params["modelo"] = "ml_inversiones"
st.switch_page("pages/2_Logs.py")

# En Logs, al cargar:
params = st.query_params
if "fecha_proceso" in params:
    # Pre-seleccionar en el date_input
```

### Páginas que necesitan leer query_params

| Página | Params que lee | Desde |
|---|---|---|
| 1_Home.py | `fecha` | Calendario (P2-1) |
| 2_Logs.py | `fecha_proceso`, `modelo`, `nivel` | Home, Alertas |
| 4_Benchmark.py | `fecha` | Home, Alertas |
| 5_Parametros.py | `fecha_a`, `fecha_b`, `modelo` | Home, Alertas |

### Confianza: 🟢 90%

Streamlit `query_params` + `switch_page` es API estable desde 1.30. El riesgo menor (10%) es que `date_input` no acepta string como default directamente — requiere parseo a `datetime.date`.

### Dudas
- **D-P2-7.1**: ¿Preferimos `st.query_params` (URL-based, shareable) o `st.session_state` (in-memory, se pierde al recargar)? → Query params es más robusto y permite compartir URLs. Pero session_state es más simple para flujos internos.

---

## P2-8: Reporte Email de Amortización (Primera Vuelta)

> *Feature nueva. Reemplaza un control legacy donde se generaban charts de amortización por subproducto/moneda en Excel VBA y se enviaban vía macro de Outlook. Ahora con charts Plotly de mejor calidad, enfocado solo en primera vuelta (modelos productivos).*

### User Story
*"Como supervisor de Riesgo Financiero, quiero recibir por email un reporte con los gráficos de amortización por subproducto y moneda de los modelos de primera vuelta, comparando el día procesado vs el día anterior, para tener visibilidad diaria sin necesidad de abrir el dashboard."*

### Contexto

- **Primera vuelta** = los 6 modelos productivos: `mr_prepago_consumo`, `mr_prepago_hipotecario`, `ml_mora_consumo`, `ml_mora_cae`, `ml_mora_hipotecario`, `ml_mora_comercial`.
- Incluye **`report_ml_mora_consumo_renegociado_hist`** como sub-tabla de mora_consumo.
- Segunda vuelta (`mr_prepago_cmr`, `ml_nmd`, `ml_lc`, `ml_inversiones`) queda **excluida** — su cadena productiva aún pasa por Excel+Access.
- El reporte legacy usaba macros VBA de Outlook que ya no están activas (.xlsm con VBA vacío).

### Scope de Datos

**7 tablas hist (primera vuelta)**:

| Tabla BQ hist | Modelo |
|---|---|
| `report_mr_prepago_hipotecario_hist` | Prepago Hipotecario |
| `report_mr_prepago_consumo_hist` | Prepago Consumo |
| `report_ml_mora_consumo_hist` | Mora Consumo |
| `report_ml_mora_consumo_renegociado_hist` | Mora Consumo Renegociado |
| `report_ml_mora_cae_hist` | Mora CAE |
| `report_ml_mora_hipotecario_hist` | Mora Hipotecario |
| `report_ml_mora_comercial_hist` | Mora Comercial |

**8 códigos producto** (mismos de 3_Comparación):
`ML_C46_MORA_CREDITO_CONSUMO`, `ML_C46_MORA_CREDITO_RENEGOCIADO`, `ML_SCSA_Contingente_Derivados`, `ML_C46_MORA_CREDITO_COMERCIAL`, `ML_C46_MORA_CREDITO_HIPOTECARIO`, `ML_Contingente_Derivados`, `MT_R13_HIPOTECARIO_BASE`, `MT_R13_CONSUMO_BASE`.

**3 monedas**: CLP, CLF, USD.

### Arquitectura

```
run_diario.bat  (post-ejecución primera_vuelta)
    │
    ▼
core/email_report.py
    ├── consulta BQ: SUM(AMORTIZACION) por moneda × producto (t y t-1)
    ├── genera charts Plotly → PNG vía kaleido
    ├── genera Excel resumen (xlsxwriter con tablas + charts nativos)
    ├── compone email HTML (tablas resumen + PNGs embebidos como CID)
    └── envía vía Outlook COM (win32com.client)
         ├── modo Send (default)
         └── modo Display (configurable, para revisión manual)
```

### Mecanismo de Envío: Outlook COM (pywin32)

**¿Por qué Outlook COM y no SMTP?**
- `pywin32==311` ya instalado y **probado** — sesión Outlook activa: *Victor Landaeta Torres*.
- No requiere configurar servidor SMTP, OAuth2, ni app passwords.
- Las políticas corporativas de Falabella bloquean auth básica SMTP; Outlook COM usa la sesión ya autenticada.
- Alternativa SMTP se mantiene como plan B si el entorno cambia a Linux o servicio sin escritorio.

**Código base**:
```python
import win32com.client

def enviar_reporte_outlook(
    destinatarios: list[str],
    asunto: str,
    cuerpo_html: str,
    adjuntos: list[str],
    modo: str = "send",  # "send" | "display"
) -> None:
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = "; ".join(destinatarios)
    mail.Subject = asunto
    mail.HTMLBody = cuerpo_html
    for ruta in adjuntos:
        mail.Attachments.Add(str(ruta))
    if modo == "display":
        mail.Display()  # abre ventana Outlook para revisión
    else:
        mail.Send()     # envío directo
```

### Charts

**Tecnología**: Plotly → PNG vía `kaleido` (confirmado instalado).

Se generan 3 charts (uno por moneda), cada uno con barras agrupadas t vs t-1 por código de producto. Mismo estilo visual de `3_Comparacion.py` pero:
- Paleta corporativa mejorada.
- Anotaciones de Δ% sobre cada par de barras.
- Tamaño optimizado para email (800×500 px).
- Exportados a PNG con `fig.to_image(format="png", width=800, height=500)`.

**Además**: un Excel adjunto con detalle completo (tablas por moneda, diferencias absolutas y %).

### Cuerpo del Email (HTML)

```html
<html>
<body>
  <h2>Reporte Amortización Primera Vuelta — {fecha}</h2>
  <p>Comparación vs día anterior ({fecha_anterior})</p>

  <!-- Métricas resumen -->
  <table>
    <tr><th>Moneda</th><th>Total t</th><th>Total t-1</th><th>Δ%</th></tr>
    <tr><td>CLP</td><td>1,234,567</td><td>1,220,000</td><td style="color:green">+1.19%</td></tr>
    ...
  </table>

  <!-- Charts embebidos como CID -->
  <h3>CLP</h3>
  <img src="cid:chart_clp">
  <h3>CLF</h3>
  <img src="cid:chart_clf">
  <h3>USD</h3>
  <img src="cid:chart_usd">

  <p>Detalle completo en el Excel adjunto.  Generado automáticamente por bfa-cl-modelos-diarios.</p>
</body>
</html>
```

Para embeber imágenes como CID en Outlook COM, se usa `.Attachments.Add()` con `PropertyAccessor` para setear `PR_ATTACH_CONTENT_ID`.

### Configuración

En `config/config_rutas_ext_y_archivos.yaml` (o un nuevo `config/email_report.yaml`):

```yaml
email_report:
  enabled: true
  destinatarios:
    - "supervisor.riesgo@falabella.com"
    - "gerencia.riesgo@falabella.com"
  modo: "send"  # "send" | "display"
  auto_post_ejecucion: false  # true = envía automáticamente después de primera_vuelta
  asunto_template: "Reporte Amortización Primera Vuelta — {fecha}"
```

- **`destinatarios`**: lista fija en YAML, modificable sin tocar código.
- **`modo`**: `send` por defecto (envío directo), `display` para revisión manual.
- **`auto_post_ejecucion`**: `false` por defecto. Si `true`, `run_diario.bat` invoca el reporte automáticamente tras primera_vuelta.

### Integración con run_diario.bat

```batch
REM === Después de primera_vuelta ===
echo.
echo Enviar reporte de amortizacion por email?
echo [1] Si, enviar ahora
echo [2] No, saltar
set /p email_choice= Opcion:
if "%email_choice%"=="1" (
    python -m core.email_report --fecha %FECHA_PROCESO%
)
```

Si `auto_post_ejecucion: true` en el YAML → salta el menú y envía directamente.

### Módulos a crear/modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `core/email_report.py` | **CREAR** | Motor principal: query BQ, charts, Excel, email |
| `config/config_rutas_ext_y_archivos.yaml` | MODIFICAR | Agregar sección `email_report` |
| `run_diario.bat` | MODIFICAR | Agregar paso opcional post-primera_vuelta |
| `requirements.txt` | MODIFICAR | Agregar `kaleido` |

### Dependencias

| Paquete | Estado | Uso |
|---|---|---|
| `pywin32==311` | ✅ Instalado | Outlook COM |
| `kaleido` | ✅ Instalado | Plotly → PNG |
| `plotly==6.6.0` | ✅ Instalado | Charts |
| `xlsxwriter==3.2.9` | ✅ Instalado | Excel adjunto |
| `google-cloud-bigquery` | ✅ Instalado | Query datos |

No requiere dependencias nuevas (kaleido ya fue instalado, agregar a requirements.txt para formalizar).

### Confianza: 🟢 88%

**Riesgos:**
- (5%) Algunas políticas corporativas de Outlook bloquean `.Send()` programático y fuerzan `.Display()`. Mitigación: el modo `display` ya está como fallback configurable.
- (3%) El embedding de imágenes CID en Outlook COM requiere manipular `PropertyAccessor` — es API Win32 estable pero verbosa. Alternativa: adjuntar imágenes y referenciar como archivo.
- (2%) `kaleido` en Windows puede tener slowness en el primer render (~3-5s de startup). Renders subsiguientes son rápidos.
- (2%) Si Outlook no está abierto al momento de `.Send()`, COM lo abre automáticamente pero puede demorar ~10s. No es bloqueante.

**Confianza condicional:**
- Si `.Send()` está bloqueado por política → caemos a `.Display()`, confianza se mantiene 🟢 85%.
- Si kaleido falla → caemos a `matplotlib` para PNGs, confianza 🟢 82%.
- Si Outlook COM falla completamente → generamos solo el Excel con charts nativos y lo dejamos en disco sin enviar. El usuario lo adjunta manualmente. Confianza 🟢 80%.

### Dudas
- **D-P2-8.1**: ¿Los 8 códigos de producto cubren exactamente los outputs de primera vuelta, o hay productos que solo generan segunda vuelta? Necesitamos validar el mapping tabla ↔ código producto para no incluir datos de segunda vuelta en los charts.
- **D-P2-8.2**: ¿La lista de destinatarios del YAML puede incluir distribution lists (DL) de Outlook, o solo direcciones individuales?
- **D-P2-8.3**: ¿Se requiere CC/BCC además de TO?
- **D-P2-8.4**: ¿El email debe incluir un resumen textual ("todo OK" / "se detectaron variaciones >10%") además de los charts, para que el supervisor pueda leer desde el celular sin abrir el adjunto?

---

## Orden de Implementación

```
P2-7 (Navegación)          ← Transversal, habilita drill-downs
  │
  ├── P2-1 (Calendario)    ← UI compleja pero datos ya existen
  │
  ├── P2-6 (Descargas)     ← Trivial, alto impacto para auditor
  │
  └── P2-4 (Alertas)       ← Motor + UI, fusionar con F09
        │
        └── P2-5 (Health)  ← Beneficia de alertas (R6 sync pendiente)

P2-3 (Tendencias)          ← Independiente, query pesada
P2-2 (Inputs)              ← Depende de F13 como backend

P2-8 (Email Report)        ← Independiente del dashboard, vive en core/
                              Reutiliza query de 3_Comparacion (BQ hist)
                              Se integra en run_diario.bat
```

**Propuesta de secuencia:**

| Orden | Feature | Dependencia | Complejidad | Valor |
|---|---|---|---|---|
| 1 | P2-7 Navegación | Ninguna | XS | Habilita todo |
| 2 | P2-6 Descargas | Ninguna | XS | Alto (auditor) |
| 3 | P2-1 Calendario | P2-7 | M | Alto (supervisor) |
| 4 | P2-3 Tendencias | Ninguna | M | Alto (gerente) |
| 5 | P2-4 Alertas | F09 parcial | L | Alto (todos) |
| 6 | P2-5 Health | F13 parcial | M | Medio (TI) |
| 7 | P2-2 Inputs | F13, cache meta | L | Medio (operador) |
| 8 | **P2-8 Email Report** | **Ninguna** | **M** | **Alto (supervisor)** |

---

## Dudas Abiertas

### Transversales
- **D-T.1**: ¿Cuánto tiempo dedicamos a P2 antes de volver al roadmap (F13, F15, F12)? ¿Es un sprint dedicado o intercalamos?
- **D-T.2**: ¿El dashboard debería tener tests? Un `test_alertas.py` que valide las reglas contra datos mock, por ejemplo.
- **D-T.3**: ¿Los CSV de inversiones en `RF_Modelo_Inversiones/*.CSV` son la misma data que las tablas hist de BQ? Si sí, podríamos usarlos como fuente de tendencias para ese modelo sin query BQ.

### Resumidas de cada feature

| Feature | Dudas clave |
|---|---|
| P2-1 Calendario | ¿Grid visual o tabla? ¿Cuántos meses? |
| P2-2 Inputs | ¿Check en vivo o estático? ¿Row counts disponibles? |
| P2-3 Tendencias | ¿Qué métricas universales? ¿Fusionar con Comparación? |
| P2-4 Alertas | ¿Sidebar o Home? ¿Deadline para R1? ¿Umbrales? |
| P2-5 Health | ¿check_env importable? ¿Actualización automática? |
| P2-6 Descargas | ¿ZIP todo o individual? |
| P2-7 Navegación | ¿query_params o session_state? |
| P2-8 Email Report | ¿Mapping tabla↔producto? ¿DL Outlook? ¿CC/BCC? ¿Resumen textual? |

---

## Resumen de Confianza

| Feature | Confianza Base | Con supuestos favorables | Complejidad |
|---|---|---|---|
| P2-7 Navegación | 🟢 90% | 🟢 95% | XS |
| P2-6 Descargas | 🟢 92% | 🟢 97% | XS |
| P2-1 Calendario | 🟡 78% | 🟢 85% | M |
| P2-3 Tendencias | 🟢 82% | 🟢 90% | M |
| P2-4 Alertas | 🟡 73% | 🟢 85% | L |
| P2-5 Health | 🟢 85% | 🟢 93% | M |
| P2-2 Inputs | 🟡 70% | 🟢 82% | L |
| **P2-8 Email Report** | **🟢 88%** | **🟢 88%** | **M** |

**Confianza promedio:** 🟢 82.4% → con supuestos favorables: 🟢 89.5%
