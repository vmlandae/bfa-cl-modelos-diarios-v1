# Quick Wins — Spec Técnica Detallada

> **Fecha:** 2026-03-12
> **Estado:** Borrador para revisión
> **Pre-requisito:** Leer `brainstorm_dashboard_v2.md` para contexto general

---

## Tabla de Contenidos

- [QW-0: Refactor Base — Multi-page Streamlit](#qw-0-refactor-base--multi-page-streamlit)
- [QW-1: Detalle de Ejecución por Día](#qw-1-detalle-de-ejecución-por-día)
- [QW-2: Vista Calendario de Ejecuciones](#qw-2-vista-calendario-de-ejecuciones)
- [QW-3: Explorador de Logs con Filtros](#qw-3-explorador-de-logs-con-filtros)
- [QW-4: Diff de Parámetros entre Fechas](#qw-4-diff-de-parámetros-entre-fechas)
- [QW-5: Benchmark Trending](#qw-5-benchmark-trending)
- [Orden de Implementación](#orden-de-implementación)
- [Dudas Abiertas](#dudas-abiertas)
- [Notas de Diseño Transversales](#notas-de-diseño-transversales)

---

## QW-0: Refactor Base — Multi-page Streamlit

### ¿Por qué primero?
El dashboard actual (`dashboard/app.py`) es un archivo monolítico de ~450 líneas con una sola página.
Antes de agregar features, necesitamos la estructura multi-page para que cada Quick Win sea una página independiente.

### Estructura propuesta

```
dashboard/
├── app.py                    # Entry point (st.set_page_config + navigation)
├── __init__.py
├── pages/
│   ├── 1_🏠_Home.py          # QW-1: Detalle de ejecución (Mission Control lite)
│   ├── 2_📅_Calendario.py    # QW-2: Vista calendario
│   ├── 3_📋_Logs.py          # QW-3: Explorador de logs
│   ├── 4_⚙️_Parametros.py    # QW-4: Diff de parámetros
│   ├── 5_📈_Tendencias.py    # QW-5: Benchmark trending
│   └── 6_📊_Comparacion.py   # Dashboard actual (outputs t vs t-1) movido aquí
├── utils/
│   ├── __init__.py
│   ├── bq_client.py          # Conexión BQ compartida (@st.cache_resource)
│   ├── local_data.py         # Lectura de archivos locales (reports, logs, snapshots)
│   └── theme.py              # Constantes de estilo, colores por estado, etc.
└── __pycache__/
```

### Implementación

1. **`app.py`** se convierte en el entry point mínimo:
   - `st.set_page_config(page_title="Modelos Diarios", layout="wide")`
   - Streamlit multi-page nativo (carpeta `pages/` con archivos numerados)
   - Sidebar global: logo/título + navegación automática de Streamlit

2. **`utils/bq_client.py`** — extraer de `app.py` actual:
   ```python
   @st.cache_resource
   def get_bq_client():
       ruta_cred = cr.obtener_ruta_credenciales_gcp()
       credentials = service_account.Credentials.from_service_account_file(...)
       return bigquery.Client(credentials=credentials, project=PROJECT_ID)
   ```

3. **`utils/local_data.py`** — funciones reutilizables:
   ```python
   def cargar_reporte_ejecucion(fecha: str) -> dict | None
   def listar_fechas_con_reporte() -> list[str]
   def cargar_log_jsonl(fecha: str) -> list[dict]
   def cargar_manifest_snapshot(fecha: str) -> dict | None
   def listar_fechas_con_snapshot() -> list[str]
   def cargar_benchmark_historial() -> list[dict]
   ```

4. **`6_📊_Comparacion.py`** — El dashboard actual se mueve aquí prácticamente intacto, solo reemplazando la conexión BQ por `utils/bq_client.py`.

### Confianza: 🟢 95%
Streamlit multi-page es bien documentado y straightforward. El único riesgo menor es que los emojis en nombres de archivos a veces dan problemas en Windows, pero se puede usar prefijo numérico sin emoji si es necesario.

### Dudas
- **D0.1**: ¿Mantenemos `dashboard/app.py` como entry point o lo renombramos? Streamlit multi-page espera que el entry point sea el archivo raíz y las sub-páginas estén en `pages/`. El comando sería `streamlit run dashboard/app.py`. → **Mi sugerencia**: mantener `app.py` como entry.
- **D0.2**: ¿El `6_📊_Comparacion.py` (dashboard actual) debería ser la página Home para mantener la experiencia actual? ¿O preferimos que Home sea el Mission Control nuevo (QW-1)?
- **D0.3**: Los imports de `config/config_rutas.py` y otros módulos del proyecto: ¿funcionan bien cuando se lanza Streamlit desde `dashboard/`? Actualmente `app.py` hace `sys.path.insert(0, str(Path(__file__).parent.parent))` — esto seguirá funcionando, pero quiero confirmarlo.

---

## QW-1: Detalle de Ejecución por Día

### User Story
*"Como operador/supervisor, quiero ver de un vistazo el resultado completo de la ejecución de hoy (o de cualquier fecha), con estado global, detalle por modelo, tiempos, y si se cargó a GCP."*

### Fuente de Datos

**Primaria: BQ `reportes_ejecucion`** — para datos post-sync
```sql
SELECT fecha_proceso, timestamp, hostname, status_global,
       duracion_total_seg, modelos_ok, modelos_error,
       alertas, reporte_json
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion`
WHERE fecha_proceso = @fecha
ORDER BY timestamp DESC
LIMIT 1
```
El campo `reporte_json` contiene el JSON completo (el mismo que `reporte_ejecucion.json`). Parseándolo obtenemos todo el detalle.

**Fallback: Local `reports/{YYYYMMDD}/reporte_ejecucion.json`** — para datos aún no synced o cuando BQ no es accesible.

### Schema del reporte (campos disponibles)
```
version: "1.0"
fecha_proceso: "2026-03-11"
timestamp: "2026-03-12T13:34:43"        ← cuándo se generó el reporte
hostname: "NWBVLANDAETAT"                ← máquina que ejecutó
status_global: "OK" | "ERROR"
duracion_total_seg: 162.89
modelos_ok: 4
modelos_error: 0
modelos:
  {modelo_key}:
    inicio_ts: "2026-03-12T13:33:15"
    fin_ts: "2026-03-12T13:33:21"
    duracion_seg: 5.24
    status: "OK"
carga_gcp:
  {tabla_dly}: true/false
benchmark:
  total_seg: 162.89
  por_modelo: {modelo: seg}
  modelo_mas_lento: "ml_inversiones"
  promedio_historico_seg: 255.74
  n_ejecuciones_previas: 4
  comparacion_vs_promedio: "-36.3%"
alertas: []
```

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  📅 Fecha: [2026-03-11 ▼]    🖥️ Host: NWBVLANDAETAT       │
│  🕐 Ejecutado: 2026-03-12 13:34                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  STATUS   │  │ DURACIÓN │  │ MODELOS  │  │ vs PROM.  │  │
│  │  ✅ OK    │  │  2m 43s  │  │ 4/4 OK   │  │  -36.3%   │  │
│  │  (verde)  │  │          │  │ 0 error  │  │  (rápido) │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
│                                                             │
│  ── Detalle por Modelo ───────────────────────────────────  │
│                                                             │
│  │ Modelo              │ Status │ Duración │ GCP  │ Inicio │
│  │─────────────────────│────────│──────────│──────│────────│
│  │ 🟢 Prepago CMR      │  OK    │    5.2s  │  ✅  │ 13:33  │
│  │ 🟢 NMD              │  OK    │   12.5s  │  ✅  │ 13:33  │
│  │ 🟢 Línea de Crédito │  OK    │   14.1s  │  ✅  │ 13:33  │
│  │ 🟢 Inversiones      │  OK    │   28.0s  │  ✅  │ 13:34  │
│                                                             │
│  ── Alertas ──────────────────────────────────────────────  │
│  (ninguna alerta para esta ejecución)                       │
│                                                             │
│  📄 [Descargar JSON]  📄 [Descargar MD]  📋 [Ver Log →]   │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Streamlit
- `st.date_input()` — selector de fecha
- `st.columns(4)` → 4 `st.metric()` para los KPIs superiores
- `st.dataframe()` con `column_config` para la tabla de modelos (colores por status)
- `st.download_button()` para JSON y MD
- `st.link_button()` o `st.page_link()` para navegar al Log Explorer con la fecha pre-filtrada
- `st.warning()` / `st.error()` para alertas

### Lógica
1. Al cargar la página, intentar BQ primero → si falla, fallback a local.
2. Fecha por defecto: hoy. Si no hay reporte para hoy, mostrar la fecha más reciente disponible.
3. Si hay múltiples ejecuciones para el mismo día (ej: primera_vuelta + segunda_vuelta), mostrar la más reciente por defecto con un selector para ver las anteriores.
4. El botón "Ver Log →" navega a la página de Logs pre-filtrada por esa fecha.

### Confianza: 🟢 90%
Los datos ya están ahí, el schema es estable y lo conozco. El campo `reporte_json` en BQ contiene todo lo necesario. El riesgo es:
- (5%) El `reporte_json` en BQ podría tener truncamiento si el reporte es muy grande. El schema dice `NULLABLE STRING` sin límite explícito, pero en la práctica BQ strings van hasta 10MB, así que debería estar bien.
- (5%) Múltiples ejecuciones por día: el reporte actual parece ser una por día (la última gana), pero si hay parciales (primera_vuelta separada de segunda_vuelta) necesito entender si se generan reportes separados o uno consolidado.

### Dudas
- **D1.1**: ¿Se genera un solo `reporte_ejecucion.json` por día, o puede haber múltiples (ej: si ejecuto primera_vuelta, luego segunda_vuelta)? Mirando el código, `reporte_ejecucion.py` parece sobrescribir el archivo. Pero en BQ `reportes_ejecucion` podrían haber múltiples filas para la misma `fecha_proceso`. **¿Debería mostrar solo la última ejecución o todas?**
- **D1.2**: El campo `hostname` sirve para identificar QUIÉN ejecutó. Pero ¿hay algún campo de `usuario` (ej: `os.getlogin()`)? Si no, podríamos agregarlo al reporte. El hostname "NWBVLANDAETAT" identifica la máquina pero no necesariamente la persona.
- **D1.3**: ¿Qué modelos se consideran "esperados" para marcar como no-ejecutado (gris) vs ejecutado-ok (verde) vs error (rojo)? Actualmente el reporte solo incluye los modelos que se ejecutaron. Si alguien corre `--modelos segunda_vuelta`, los 6 modelos de primera vuelta no aparecen en el reporte. ¿Deberíamos cruzar con la lista canónica de 10 modelos para mostrar los faltantes en gris?
- **D1.4**: El campo `status_global` solo tiene "OK" o "ERROR". ¿El estado "PARCIAL" y "SIN_MODELOS" que vi en el brainstorm es algo que ya existe o es aspiracional? En los datos reales solo vi "OK".

**Confianza condicional:**
- Si se confirma que hay un reporte por día → 🟢 95%
- Si se confirma que podemos agregar `usuario` al reporte → +2% (para el supervisor story)
- Si conozco la lógica exacta de múltiples ejecuciones → +3%

---

## QW-2: Vista Calendario de Ejecuciones

### User Story
*"Como supervisor, quiero ver un calendario mensual con el estado de cada día (OK/error/no ejecutado), para detectar gaps y tener una vista panorámica del mes."*

### Fuente de Datos

**Primaria: BQ `reportes_ejecucion`**
```sql
SELECT fecha_proceso,
       status_global,
       duracion_total_seg,
       modelos_ok,
       modelos_error,
       timestamp
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion`
WHERE fecha_proceso BETWEEN @fecha_inicio AND @fecha_fin
ORDER BY fecha_proceso, timestamp DESC
```
Una query por mes (o rango seleccionado). Agrupar por `fecha_proceso`, tomar la ejecución más reciente de cada día.

**Fallback: Local** — Escanear `reports/*/reporte_ejecucion.json` (glob).

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  📅 Calendario de Ejecuciones                               │
│  ◀ Febrero 2026 ▶                   [Mes ▼] [Año ▼]       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Lu   Ma   Mi   Ju   Vi   Sa   Do                          │
│ ┌────┬────┬────┬────┬────┬────┬────┐                       │
│ │    │    │    │    │    │    │ 1  │                       │
│ │    │    │    │    │    │    │ ⬜ │                       │
│ ├────┼────┼────┼────┼────┼────┼────┤                       │
│ │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │ 8  │                       │
│ │ ⬜ │ 🟢 │ 🟢 │ 🟢 │ 🟢 │    │    │                       │
│ ├────┼────┼────┼────┼────┼────┼────┤                       │
│ │ 9  │ 10 │ 11 │ 12 │ 13 │ 14 │ 15 │                       │
│ │ 🟢 │ 🟡 │ 🟢 │ ⏳ │    │    │    │                       │
│ │    │    │    │(hoy)│    │    │    │                       │
│ ...                                                         │
│                                                             │
│  Leyenda: 🟢 OK  🟡 Parcial  🔴 Error  ⬜ No ejecutado    │
│           ⏳ Pendiente (hoy, aún sin reporte)               │
│           (gris) Fin de semana / feriado                    │
│                                                             │
│  ── Resumen del Mes ──────────────────────────────────────  │
│  Días hábiles: 22  │  Ejecutados OK: 18  │  Cobertura: 82% │
│  Errores: 1        │  Parciales: 1       │  Sin ejecución: 2│
│  Duración promedio: 4m 15s               │  Racha OK: 7 días│
│                                                             │
│  💡 Click en un día para ver el detalle (→ QW-1)           │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Streamlit
- **Opción A**: Construir el calendario como un grid de `st.columns(7)` con `st.container()` por celda → estilizado con `st.markdown()` + HTML/CSS inline.
- **Opción B**: Usar `plotly.figure_factory` heatmap con un calendarplot.
- **Opción C**: Usar `streamlit-calendar` (component externo) — hay un paquete `streamlit-calendar` pero no sé si está en nuestras deps.
- **Mi preferencia**: **Opción A** — máximo control, sin dependencia extra, y Streamlit lo soporta bien con CSS.

### Lógica
1. Mes actual por defecto. Navegación ◀▶ para cambiar mes.
2. Los **fines de semana** se pintan gris (no se esperan ejecuciones).
3. Los **feriados** (Chile) idealmente también grises. Se puede usar una lista hardcodeada o la librería `holidays` (ya en el ecosistema de pip).
4. Click en un día → navegar a QW-1 con esa fecha. **Limitación Streamlit**: `st.page_link` no pasa parámetros directamente. Solución: usar `st.query_params` o `st.session_state` para pasar la fecha.
5. "Resumen del Mes" son métricas agregadas simples.
6. ⏳ para "hoy" si no hay reporte aún.

### Confianza: 🟡 75%
La lógica es simple, pero la **UI del calendario es la parte tricky**:
- Streamlit no tiene un componente calendario nativo para este propósito.
- Construirlo con `st.columns(7)` funciona pero es verbose y el styling es limitado.
- El click-to-navigate entre páginas con parámetros puede tener fricciones con Streamlit (session_state vs query_params).

**Confianza condicional:**
- Si `st.query_params` funciona bien para inter-page navigation → 🟢 85%
- Si usamos plotly heatmap en vez de grid manual → 🟢 85% (más fácil, menos control visual)
- Si aceptamos un calendario visualmente "bueno pero no perfecto" → 🟢 90%

### Dudas
- **D2.1**: ¿Hay una lista de feriados chilenos que ya se use en algún lado del proyecto? Si no, ¿vale la pena incorporar `holidays` como dependencia o hardcodeamos los del 2026?
- **D2.2**: ¿Los sábados y domingos NUNCA se ejecuta? ¿O hay excepciones (fin de mes, cierre trimestral)?
- **D2.3**: ¿Cuántos meses hacia atrás queremos poder navegar? Si la data en BQ solo tiene ~1 mes, quizás limitar a 3 meses y expandir cuando haya más datos.
- **D2.4**: Para "cobertura" (% días ejecutados OK del total de días hábiles): ¿los modelos se ejecutan TODOS los días hábiles, o hay algún patrón diferente (ej: solo de lunes a viernes, excluyendo feriados bancarios)?

---

## QW-3: Explorador de Logs con Filtros

### User Story
*"Como operador/supervisor, quiero explorar los logs de ejecución de cualquier día, filtrados por modelo y nivel, sin tener que abrir archivos JSONL manualmente."*

### Fuente de Datos

**Primaria: BQ `reportes_ejecucion`** — campo `log_jsonl`
```sql
SELECT log_jsonl
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion`
WHERE fecha_proceso = @fecha
ORDER BY timestamp DESC
LIMIT 1
```
El campo `log_jsonl` contiene el contenido completo del archivo JSONL (hasta 1MB según el schema).

**Fallback: Local `logs/{YYYYMMDD}/modelos.jsonl`** — parsear línea por línea.

### Schema de cada línea JSONL
```json
{
  "ts": "2026-03-12T11:10:33.557",     // ISO timestamp
  "level": "INFO",                       // DEBUG|INFO|WARNING|ERROR|CRITICAL
  "logger": "bfa_modelos.core.orquestador",  // módulo fuente
  "modelo": "mr_prepago_consumo",        // null si es mensaje global
  "msg": "Texto del mensaje"             // puede tener emojis, ANSI codes
}
// Campos opcionales en ciertos eventos:
// "event": "snapshot"
// "sha256": "..."
// "archivo": "..."
// "store_path": "..."
// "is_new": true/false
// "exception": "traceback completo..."
```

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  📋 Explorador de Logs                                      │
│                                                             │
│  📅 Fecha: [2026-03-11 ▼]                                  │
│                                                             │
│  ── Filtros ──────────────────────────────────────────────  │
│  Modelo: [Todos ▼] [mr_prepago_consumo] [ml_nmd] ...       │
│  Nivel:  ☑ INFO  ☑ WARNING  ☑ ERROR  ☐ DEBUG              │
│  Buscar: [________________________] 🔍                      │
│                                                             │
│  ── Resumen ──────────────────────────────────────────────  │
│  Total: 487 líneas │ INFO: 450 │ WARN: 30 │ ERROR: 7       │
│  [pie chart o bar chart pequeño por nivel]                  │
│                                                             │
│  ── Logs ─────────────────────────────────────────────────  │
│  │ Hora     │ Nivel   │ Modelo          │ Mensaje          │
│  │──────────│─────────│─────────────────│──────────────────│
│  │ 11:10:33 │ 🔵 INFO │ prepago_consumo │ Iniciando...     │
│  │ 11:10:34 │ 🔵 INFO │ prepago_consumo │ 90 tasas SMM...  │
│  │ 11:10:48 │ 🟡 WARN │ prepago_consumo │ ⚠️ Tasa > 50%   │
│  │ 11:11:02 │ 🔴 ERR  │ mora_consumo    │ FileNotFound...  │
│  │          │         │                 │ ▼ [Expandir]     │
│  │          │         │                 │  Traceback:      │
│  │          │         │                 │  File "..." L42  │
│  │ ...      │         │                 │                  │
│                                                             │
│  Mostrando 487 de 487 (filtrados)                           │
│  📥 [Descargar filtrado CSV] [Descargar JSONL completo]     │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Streamlit
- `st.date_input()` para fecha
- `st.multiselect()` para modelos (poblado dinámicamente de los valores únicos en el log)
- `st.multiselect()` o checkboxes para niveles (INFO, WARNING, ERROR preseleccionados; DEBUG off por defecto)
- `st.text_input()` para búsqueda de texto libre
- `st.dataframe()` o `st.data_editor()` para la tabla de logs
- `st.expander()` dentro de cada fila para excepciones (o usar un modal)
- `st.download_button()` para exports

### Lógica
1. Cargar JSONL → `pd.DataFrame` → aplicar filtros → mostrar.
2. **Strip ANSI codes** del campo `msg` (los logs contienen colores de consola). Regex: `re.sub(r'\x1b\[[0-9;]*m', '', msg)`.
3. **Parsing robusto**: Cada línea es JSON independiente. Si una línea falla, skipear con log de warning.
4. **Tamaño**: Un JSONL diario podría tener ~500-2000 líneas. No hay problema de performance para `st.dataframe()` con esto. Si fuera >10K líneas (poco probable), considerar paginación.
5. **Pre-filtrado por URL**: Si viene de QW-1 con `?fecha=2026-03-11&modelo=ml_nmd`, aplicar filtros automáticamente al cargar.
6. **Detección de excepciones**: Si `line.get("exception")` existe, mostrar un expander/tooltip.

### Confianza: 🟢 90%
Es la feature más directa: leer JSON, mostrar tabla, aplicar filtros. Todo con Streamlit nativo.

**Riesgos menores:**
- (5%) Performance si el log es muy extenso (~5K+ líneas). Solución: limitar vista a últimas N líneas con opción de "cargar más".
- (3%) ANSI codes en mensajes — fácil de limpiar pero hay que hacerlo.
- (2%) El campo `log_jsonl` de BQ podría estar truncado (<1MB) si una ejecución con muchos modelos genera logs grandes. Fallback a archivo local si se detecta truncamiento.

### Dudas
- **D3.1**: ¿Cuántas líneas tiene un JSONL típico de un día completo (10 modelos)? Si es ~500, no hay problema. Si es ~50K, necesitamos paginación o muestreo. → **Mi estimación**: ~500-2000 para una ejecución de 10 modelos. Los logs de los print-captured de cada modelo pueden ser verbose.
- **D3.2**: ¿Los ANSI color codes están presentes en el JSONL o solo en console output? Mirando los datos, vi mensajes con emojis (📸) pero no estoy 100% seguro de ANSI. → **Suposición**: Sí están (el logger usa un formatter con colores, y el print-capture pasa todo).
- **D3.3**: ¿Queremos el resumen (pie chart por nivel) como parte del MVP o es un nice-to-have dentro de la misma feature?
- **D3.4**: ¿Tiene sentido un botón "Ver solo errores de este modelo" que sea un shortcut de filtro? Para el caso de uso del practicante que necesita debugging rápido.

**Confianza condicional:**
- Si JSONL tiene <2K líneas → 🟢 95% (sin paginación necesaria)
- Si los ANSI codes son consistentes y predecibles → 🟢 93% (fácil limpieza)

---

## QW-4: Diff de Parámetros entre Fechas

### User Story
*"Como supervisor/auditor, quiero comparar los parámetros usados en dos fechas distintas y ver exactamente qué cambió, para entender el impacto de cambios de parámetros en los resultados."*

### Fuente de Datos

**Primaria: Local `snapshots/manifests/{YYYYMMDD}.json`**

No hay manifests en BQ (solo el `reporte_json` que no incluye snapshots). Esto es puramente local.

**Schema del manifest:**
```json
{
  "fecha": "20260311",
  "modelos": {
    "mr_prepago_consumo": {
      "ts_snapshot": "2026-03-12T13:33:15",
      "archivos": {
        "parametros_mr_prepago_consumo.xlsx": {
          "sha256": "abc123...",
          "store": "store/mr_prepago_consumo/abc123.xlsx",
          "size_bytes": 296664,
          "is_new": false
        },
        "parametros_mr_prepago_consumo.json": {
          "sha256": "def456...",
          "store": "store/mr_prepago_consumo/def456.json",
          "size_bytes": 4900,
          "is_new": false
        }
      }
    }
    // ... más modelos
  }
}
```

**Para el diff de contenido:**
- **JSON params**: Leer `snapshots/store/{modelo}/{hash}.json` → diff estructurado
- **Excel params**: Leer `snapshots/store/{modelo}/{hash}.xlsx` → pd.read_excel → diff por celdas
- **Detección rápida de cambio**: Comparar SHA-256. Si es igual → sin cambios. Si difiere → mostrar diff.

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Comparación de Parámetros                               │
│                                                             │
│  📅 Fecha A: [2026-03-10 ▼]   📅 Fecha B: [2026-03-11 ▼]  │
│  Modelo: [Todos ▼]                                          │
│                                                             │
│  ── Resumen de Cambios ───────────────────────────────────  │
│                                                             │
│  │ Modelo              │ Archivos │ Estado                 │
│  │─────────────────────│──────────│────────────────────────│
│  │ mr_prepago_consumo  │  2/2     │ ✅ Sin cambios         │
│  │ ml_mora_consumo     │  3/3     │ 🔄 1 archivo cambió   │
│  │ ml_mora_cae         │  2/2     │ ✅ Sin cambios         │
│  │ ml_nmd              │  2/2     │ 🆕 Nuevo snapshot     │
│  │ ml_inversiones      │  1/1     │ ✅ Sin cambios         │
│  │ ...                 │          │                        │
│                                                             │
│  ── Detalle: ml_mora_consumo ─────────────────────────────  │
│  📄 parametros_ml_mora_consumo.json                         │
│  SHA A: abc123...  →  SHA B: def456...                      │
│                                                             │
│  ┌─────────────────────┬────────────────────┐              │
│  │ Campo               │ Cambio             │              │
│  │─────────────────────│────────────────────│              │
│  │ hojas.FACTORES      │                    │              │
│  │   .GAMMA_1[0]       │ -0.013 → -0.015   │              │
│  │   .GAMMA_2[0]       │  0.025 →  0.028   │              │
│  │ hojas.TASAS          │ (sin cambios)     │              │
│  └─────────────────────┴────────────────────┘              │
│                                                             │
│  📥 [Descargar Param A] [Descargar Param B] [Descargar Diff]│
└─────────────────────────────────────────────────────────────┘
```

### Lógica del Diff

**Nivel 1 — SHA comparison (rápido):**
```python
for modelo in manifesto_a["modelos"]:
    for archivo, meta_a in modelo["archivos"].items():
        meta_b = manifesto_b["modelos"][modelo]["archivos"].get(archivo)
        if meta_b is None:
            # Archivo nuevo o eliminado
        elif meta_a["sha256"] == meta_b["sha256"]:
            # Sin cambios
        else:
            # Cambió → drill down
```

**Nivel 2 — Content diff (para archivos que cambiaron):**
- **JSON**: Usar `deepdiff` (pip) o implementar recursivo propio.
  - `deepdiff.DeepDiff(json_a, json_b)` → tree de cambios.
  - Mostrar como tabla: path, valor_viejo, valor_nuevo.
- **Excel (sin JSON equivalente)**: `pd.read_excel()` + comparar DataFrames.
  - `df_a.compare(df_b)` → DataFrame con diffs.
  - Mostrar celdas que cambiaron con valores old/new highlighted.

**Nivel 3 — Excel visual (nice-to-have):**
- Side-by-side con celdas coloreadas (verde=nuevo, rojo=eliminado, amarillo=modificado).

### Componentes Streamlit
- 2x `st.date_input()` para fecha A y B (con defaults: ayer y hoy)
- `st.selectbox()` para modelo (opción "Todos" por defecto)
- `st.dataframe()` con `column_config` para resumen y detalle
- `st.expander()` por modelo para el drill-down
- `st.download_button()` para descargar archivos originales del store
- `st.json()` para mostrar el JSON completo si se quiere inspeccionar

### Dependencias nuevas potenciales
- `deepdiff` — para diff estructurado de JSONs. **¿Ya está en requirements?** Probablemente no. Alternativa: implementar un diff recursivo propio (más trabajo pero sin dependencia extra).

### Confianza: 🟡 75%
La idea es clara, los datos existen, pero hay complejidad en:
- (10%) El diff de Excel sin JSON equivalente — no todos los modelos tienen JSON extraído (ej: `ml_inversiones` solo tiene `.xlsm`). Para estos, el diff Excel-a-Excel es más complejo (múltiples hojas, filas variables).
- (8%) `deepdiff` es una dependencia nueva. La alternativa propia es factible pero más trabajo.
- (5%) Los manifests solo existen desde que se implementó F02 (~2-3 semanas). Pocos pares de fechas para comparar.
- (2%) El snapshot store es local: si el dashboard corre en otra máquina, no tendría acceso al store. Solo funciona en la máquina que ejecutó (alineado con decisión de hosting local).

### Dudas
- **D4.1**: ¿Cuántos modelos tienen JSON extraído vs solo Excel? De lo que vi: `ml_lc` tiene `.json`, `ml_inversiones` solo `.xlsm`. → **¿Fue la migración F20 parcial?** Necesito saber cuáles tienen JSON para decidir qué tipo de diff ofrecer por modelo.
- **D4.2**: ¿Aceptamos `deepdiff` como dependencia nueva o preferimos implementar un diff propio? → **Mi sugerencia**: `deepdiff` es maduro y estable, vale la pena.
- **D4.3**: ¿Los snapshots de fechas cercanas tienden a ser idénticos (mismo SHA) o hay cambios frecuentes? Si son mayormente idénticos, el resumen de "sin cambios" será el caso común y el drill-down será raro pero importante.
- **D4.4**: ¿El diff de Excel para modelos sin JSON es MVP o lo diferimos? Podría ser un nice-to-have: para el MVP, solo hacer diff de JSONs existentes y para los Excel solo indicar "cambió/no cambió" sin detalle.
- **D4.5**: ¿Los parámetros de `ml_inversiones` (.xlsm con macros) se pueden leer con `pd.read_excel` normalmente? Podría haber hojas con macros que no son data pura.

**Confianza condicional:**
- Si la mayoría de modelos tiene JSON → 🟢 85% (diff de JSON es straightforward)
- Si aceptamos `deepdiff` → +5%
- Si diferimos diff de Excel puro al post-MVP → +5% (reducimos scope)
- Best case: 🟢 95% si todos los supuestos favorables

---

## QW-5: Benchmark Trending

### User Story
*"Como supervisor/operador, quiero ver la evolución del tiempo de ejecución de cada modelo en el tiempo, detectar degradaciones de performance, y entender si el pipeline está escalando bien."*

### Fuente de Datos

**Primaria: Local `data/benchmark/historial.jsonl`**

```json
{"fecha": "2026-03-10", "total_seg": 104.49, "por_modelo": {"mr_prepago_consumo": 12.3, ...}, "hostname": "NWBVLANDAETAT", "status": "OK"}
{"fecha": "2026-03-10", "total_seg": 39.28, "por_modelo": {...}, "hostname": "NWBVLANDAETAT", "status": "ERROR"}
{"fecha": "2026-03-10", "total_seg": 798.95, "por_modelo": {...}, "hostname": "NWBVLANDAETAT", "status": "OK"}
{"fecha": "2026-03-11", "total_seg": 162.89, "por_modelo": {...}, "hostname": "NWBVLANDAETAT", "status": "OK"}
{"fecha": "2026-03-11", "total_seg": 113.48, "por_modelo": {...}, "hostname": "NWBVLANDAETAT", "status": "OK"}
```

**Volume actual**: 5 registros (2 fechas). Crecerá linealmente (~1-3 registros por día hábil).

**Secundaria: BQ `reportes_ejecucion`** — `reporte_json` contiene el benchmark embebido. Esto permitiría trending sin depender de archivo local.

### UI — Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  📈 Benchmark de Performance                                │
│                                                             │
│  📅 Rango: [Último mes ▼]   [2026-02-11] — [2026-03-11]   │
│                                                             │
│  ── Duración Total del Pipeline ──────────────────────────  │
│                                                             │
│     800s ┤          ×                                       │
│          │                                                  │
│     400s ┤                                                  │
│          │                                                  │
│     200s ┤  ×               ×                               │
│     100s ┤      ×(err)          ×                           │
│          └──────────────────────────────  → fecha           │
│           03-10  03-10  03-10  03-11  03-11                 │
│                                                             │
│  ── Duración por Modelo (stacked/grouped) ────────────────  │
│                                                             │
│     [Line chart con una serie por modelo]                   │
│     — prepago_consumo  — mora_consumo  — nmd  — inversiones │
│                                                             │
│  ── Box Plot por Modelo ──────────────────────────────────  │
│                                                             │
│  inversiones |=====[====|=======]=====|                     │
│  nmd         |==[==|==]=|                                   │
│  lc          |==[=|==]=|                                    │
│  prepago_cmr |=[|]=|                                        │
│              0s   20s   40s   60s   80s                     │
│                                                             │
│  ── Tabla Resumen ────────────────────────────────────────  │
│  │ Modelo         │ Media │ Mediana │ Min  │ Max   │ Últim │
│  │────────────────│───────│─────────│──────│───────│───────│
│  │ ml_inversiones │ 28.0s │  28.0s  │ 28s  │  28s  │ 28.0s│
│  │ ml_lc          │ 30.5s │  30.5s  │ 14s  │  54s  │ 14.1s│
│  │ ...            │       │         │      │       │       │
│                                                             │
│  ⚠️ Alerta: ml_lc tuvo un spike de 54s (3.8x su mediana)  │
│                                                             │
│  📥 [Descargar historial CSV]                               │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Streamlit
- `st.selectbox()` para rango temporal (última semana, último mes, último trimestre, custom)
- `st.plotly_chart()` para line charts y box plots
- `st.dataframe()` para tabla resumen
- `st.warning()` para alertas de anomalías
- `st.download_button()` para export

### Lógica
1. Parsear `historial.jsonl` → DataFrame. Expandir `por_modelo` a columnas.
2. Para cada ejecución: fechar + total + desglose por modelo.
3. **Filtro de ejecuciones ERROR**: Mostrar como puntos marcados (×) o en color distinto, pero no incluir en estadísticas de performance (un error puede tener duración baja porque abortó).
4. **Detección de anomalías**: Si duración > mediana * 2 → marcar como anomalía.
5. **Gráficos plotly**:
   - Line chart: `px.line(df, x="fecha", y="total_seg", color="status")`
   - Box plot: `px.box(df_melted, x="modelo", y="duracion_seg")`
   - Opcionalmente: stacked bar por modelo para ver composición del tiempo total.

### Confianza: 🟢 88%
Feature muy directa: leer JSONL, hacer DataFrame, graficar con plotly. Los datos existen y el schema es claro.

**Riesgos:**
- (7%) Con solo 5 registros actuales, los gráficos se verán... escuetos. Los box plots necesitan al menos ~5-10 puntos por modelo para ser útiles. → **Mitigación**: Mostrar lo que hay, con un mensaje tipo "Se requieren más ejecuciones para estadísticas robustas" si n < 10.
- (3%) Múltiples ejecuciones por día con distintos subsets de modelos (ej: primera_vuelta vs segunda_vuelta) complican la comparación. Un punto puede tener 6 modelos y otro 4. → **Mitigación**: Normalizar por set de modelos, o simplemente mostrar todos los puntos y que el usuario filtre.
- (2%) La fuente primaria es local. Si queremos trending cross-machine (supervisor viendo la data de la máquina del practicante), necesitamos BQ como fuente. Los datos están ahí dentro de `reporte_json`, pero parsear JSON dentro de BQ es más lento.

### Dudas
- **D5.1**: ¿Queremos fuente BQ o local para el MVP? → **Mi sugerencia**: Local primero (más rápido, ya existe), con plan de migrar a BQ cuando el historial sea más rich.
- **D5.2**: ¿Cómo manejar ejecuciones parciales (primera_vuelta=6 modelos, segunda_vuelta=4 modelos) en la vista de "duración total"? ¿Sumar ambas del mismo día? ¿Mostrar por separado? → **Mi sugerencia**: Mostrar cada ejecución como un punto independiente, etiquetado con qué modelos incluyó.
- **D5.3**: ¿el box plot por modelo es MVP o nice-to-have? Con 5 registros no aporta mucho. → **Mi sugerencia**: Incluirlo pero con disclaimer de "datos insuficientes" si n < 10.

**Confianza condicional:**
- Si aceptamos datos escuetos al principio con mensaje → 🟢 92%
- Si usamos fuente local (sin BQ parsing) → 🟢 93%

---

## Orden de Implementación

```

QW-0 (Refactor Base)         ← PRE-REQUISITO de todas las demás
  │
  ├── QW-1 (Detalle Ejecución)  ← Más simple, datos más ricos
  │     │
  │     └── QW-2 (Calendario)   ← Depende de QW-1 para el drill-down
  │
  ├── QW-3 (Logs)               ← Independiente, pero link desde QW-1
  │
  ├── QW-5 (Benchmark)          ← Independiente, más simple
  │
  └── QW-4 (Diff Parámetros)    ← Más complejo, puede ir al final
```

**Propuesta de secuencia:**

| Orden | Feature | Dependencia | Justificación |
|-------|---------|-------------|---------------|
| 1 | QW-0 | ninguna | Habilita todo lo demás |
| 2 | QW-1 | QW-0 | Página central, valida el patrón BQ + local |
| 3 | QW-3 | QW-0 | Alto valor para operador, independiente |
| 4 | QW-5 | QW-0 | Rápido de implementar, visualmente impactante |
| 5 | QW-2 | QW-0, QW-1 | Depende de QW-1 para drill-down, UI más compleja |
| 6 | QW-4 | QW-0 | Más complejo, posible dependencia nueva |

---

## Dudas Resueltas (2026-03-13)

| ID | Pregunta | Respuesta |
|----|----------|-----------|
| D0.1 | ¿Mantener app.py como entry point? | ✅ Sí, mantener |
| D0.2 | ¿Home = Mission Control o dashboard actual? | ✅ **Mission Control nuevo** (QW-1) |
| D0.3 | ¿sys.path funciona desde pages/? | ⚠️ Por verificar en implementación. `app.py` ya hace `sys.path.insert(0, BASE_DIR)` |
| D1.1 | ¿Múltiples reportes por día? | ✅ **Sí, cada ejecución es una fila en BQ.** Mostrar TODAS las del día. Local solo guarda la última (overwrite). |
| D1.2 | ¿Agregar campo `usuario`? | ✅ **Sí, agregar.** Actualmente `platform.node()` = hostname, no usuario real. Usar `os.getlogin()` o `getpass.getuser()`. |
| D1.3 | ¿Mostrar modelos no-ejecutados en gris? | ✅ **Sí, cruzar con lista canónica de 10 modelos.** Considerar que puede haber ejecución de 1ra vuelta + 2da vuelta por separado → agregar los modelos ejecutados de TODOS los reportes del día. |
| D1.4 | ¿Status PARCIAL/SIN_MODELOS existen? | ✅ **Sí, existen en código.** OK / PARCIAL / ERROR / SIN_MODELOS. |
| D2.1 | ¿Feriados chilenos disponibles? | ✅ **Sí.** `bfa_cl_utilidades.es_dia_laboral(fecha)` usa `holidays.country_holidays('CL', subdiv='RM')` + feriados bancarios. Ya en deps (`holidays==0.90`). |
| D2.2 | ¿Se ejecuta siempre L-V? | ✅ **Solo días hábiles (L-V excluyendo feriados CL).** Nunca fines de semana. |
| D2.3 | ¿Cuántos meses navegar? | ✅ Sin límite artificial, pero dato real ~3 meses |
| D2.4 | ¿Todos los días hábiles deben tener ejecución? | ✅ **Sí.** |

### Dudas resueltas (2026-03-13, ronda 2)
| ID | Pregunta | Respuesta |
|----|----------|---------|
| D3.1 | Tamaño típico de JSONL | ✅ ~1000 líneas en ejecución normal; máx ~5000 con errores y reprocesos. Sin problema de performance. |
| D3.2 | ¿ANSI codes presentes en JSONL? | ⚠️ Usuario no seguro. Mantenemos limpieza ANSI como precaución. |
| D3.3 | ¿Resumen con pie chart es MVP? | ✅ Sí, incluir. Lo sacamos después si no se ajusta. |
| D3.4 | ¿Shortcut "solo errores"? | ✅ Sí, incluir. |
| D4.1 | ¿Cuántos modelos tienen JSON extraído? | ✅ **9/10 tienen JSON + Excel.** Solo `ml_inversiones` tiene únicamente `.xlsm` (sin JSON). |
| D4.2 | ¿Aceptamos deepdiff? | ✅ Sí, usar `deepdiff`. |
| D4.3 | ¿Los snapshots son mayormente idénticos? | ✅ Sí, mayormente idénticos entre fechas cercanas. |
| D4.4 | ¿Diff de Excel para ml_inversiones es MVP? | ✅ Para MVP solo indicar "cambió/no cambió" (SHA comparison). |
| D4.5 | ¿ml_inversiones .xlsm se lee con pd.read_excel? | ✅ Sí, confirmado en código. Usa `pd.read_excel()` con 6 hojas: FPL, RF_FactCLF_Banc, RF_FactCLF_Gob, RF_FactCLP_Banc, RF_FactCLP_Gob, RF_MontosLiq (hoja "Montos"). |
| D5.1 | ¿Fuente BQ o local benchmarks? | ✅ BQ como primario, con fallback local para días sin BQ. |
| D5.2 | Ejecuciones parciales en benchmarks | ✅ **Sumar todo del mismo día** — cuánto demoran las 10 ejecuciones en total. |
| D5.3 | Box plot con pocos datos | ✅ Incluir con disclaimer. |

---

## Notas de Diseño Transversales

### Patrón de datos: BQ-first con fallback local
```python
# Patrón reutilizable en todas las páginas
def cargar_datos(fecha, bq_query_fn, local_fn):
    """Intenta BQ primero, fallback a local."""
    try:
        df = bq_query_fn(fecha)
        if df is not None and not df.empty:
            return df, "bigquery"
    except Exception as e:
        st.warning(f"⚠️ No se pudo conectar a BigQuery: {e}")
    
    data = local_fn(fecha)
    if data is not None:
        return data, "local"
    
    return None, "none"
```
Cada página muestra un indicator discreto de la fuente de datos (🌐 BQ o 💾 Local).

### Paleta de colores por estado
```python
STATUS_COLORS = {
    "OK":          "#28a745",  # verde
    "PARCIAL":     "#ffc107",  # amarillo
    "ERROR":       "#dc3545",  # rojo
    "SIN_MODELOS": "#6c757d",  # gris
    "PENDIENTE":   "#17a2b8",  # cyan
}
```

### Navegación entre páginas con contexto
```python
# En QW-1, botón "Ver Logs":
if st.button("📋 Ver Log"):
    st.query_params["fecha"] = fecha_str
    st.switch_page("pages/3_📋_Logs.py")

# En QW-3, al cargar:
fecha_param = st.query_params.get("fecha", None)
if fecha_param:
    # Pre-seleccionar fecha del date_input
```

### Caching strategy
```python
# Datos BQ: cache con TTL (los datos no cambian retroactivamente)
@st.cache_data(ttl=300)
def query_bq_reporte(fecha): ...

# Datos locales: cache sin TTL (archivo no cambia una vez escrito)
@st.cache_data
def cargar_jsonl(fecha): ...

# Datos que cambian durante el día (ej: hoy):
@st.cache_data(ttl=60)
def query_bq_reporte_hoy(): ...
```

---

## Resumen de Confianza

| Feature | Confianza Base | Con supuestos favorables | Notas |
|---------|---------------|-------------------------|-------|
| QW-0 (Refactor) | 🟢 95% | 🟢 97% | Straightforward |
| QW-1 (Detalle) | 🟢 90% | 🟢 95% | Necesita confirmar D1.1, D1.4 |
| QW-2 (Calendario) | 🟡 75% | 🟢 90% | UI del calendario es la incógnita |
| QW-3 (Logs) | 🟢 90% | 🟢 95% | Muy directa |
| QW-4 (Diff Params) | 🟡 75% | 🟢 95% | Depende de cobertura JSON, deepdiff |
| QW-5 (Benchmark) | 🟢 88% | 🟢 93% | Datos escuetos por ahora |

**Confianza promedio:** 🟢 85.5% → con supuestos favorables: 🟢 94.2%
