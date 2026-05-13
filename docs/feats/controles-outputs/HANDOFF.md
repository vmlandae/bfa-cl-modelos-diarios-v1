# Handoff — Sprint S6-2026 "Controles & Cobertura Dashboard"

> **Fecha:** 2026-05-13
> **Rama:** `feat/sprint-s6-controles` (NO mergeada a `main` todavía)
> **Para:** próximo agente que retome el sprint
> **Por:** agente previo (Claude Code sesión 2026-05-13)
> **Documentos hermanos:** [`PLAN.md`](PLAN.md), [`hallazgos.md`](hallazgos.md), [`docs/roadmap/roadmap.yaml`](../../roadmap/roadmap.yaml) sprint `S6-2026`

---

## 1. Punto de entrada — qué hacer primero

```bash
cd /home/jupyter/bfa-cl-modelos-diarios-v1
git fetch origin
git checkout feat/sprint-s6-controles
git log --oneline -8      # ver los 8 commits del sprint
cat docs/feats/controles-outputs/PLAN.md         # plan completo
cat docs/feats/controles-outputs/hallazgos.md    # diagnóstico inicial
cat docs/feats/controles-outputs/HANDOFF.md      # este archivo
```

Lo más urgente:

1. **El usuario aún NO ha verificado en su PC institucional** (Windows con credenciales BQ). Toda la implementación pasó AST + smokes que no requieren BQ live. Antes de mergear o avanzar, conviene que el usuario corra los 4 smokes de la sección 4 de este handoff.
2. **F29 cuadratura quedó como stub** (reporta INFO). Es la pieza que cierra el caso "error grueso real" (desbalance capital input↔output). Es lo único que falta para que el sprint cumpla 100% sus criterios de aceptación. Fase 4 del PLAN explica cómo seguir.

---

## 2. Contexto que necesitas saber (no está obvio leyendo el código)

### 2.1 El "error grueso" no es lo que parece

En la conversación inicial el usuario habló de "error grueso". Mi primer agente asumió que era `CODIGO_EMPRESA=NaN` (commit `18e15dc`, fix paralelo). **No es eso**. El usuario corrigió a mitad de planificación:

> "no fue un error tan grueso, el error más grueso fue una diferencia de montos entre lo que entraba y lo que salía en capital"

Por eso F29 tiene como check principal `cuadratura_capital` (input PML/Access vs output BQ). Pero el motor entregado solo deja el **stub**. La fase 4 del PLAN.md detalla cómo implementarlo. Si vas a tocar `controles_cuadratura.py`, **lee primero la sección 3 de este handoff** — hay reuso importante con `core/control_interfaces.py:169-178`.

### 2.2 Modelos manuales (no asumir que el orquestador los corre)

`mr_ssv` y `mr_prepago_cmr` se ejecutan **manualmente** hoy:
- **SSV**: input de saldos CORE se hardcodea con `RF_Modelo_MR_SSV/parametros/agregar_core_hardcode.py`. F27 (backlog) planea automatizar. EOM mensual.
- **CMR**: el `.py` automatizado diverge del notebook productivo (ver `docs/feats/cuadre-mr-prepago-cmr/hallazgos.md`: filas MORA descartadas, SMM unit por validar, +210 filas extra). El equipo carga a BQ desde notebook con scripts en `tools/`.

Implicaciones:
- F29 trabaja **post-carga BQ**, no como hook de ejecución. Da igual si la carga vino del orquestador o de un script manual.
- En `config_rutas_ext_y_archivos.yaml` esos dos modelos quedaron con `cuadratura_inputs.{modelo}.tipo: "manual"` → el stub los marca INFO y no genera falsos positivos. Cuando se automaticen, cambiar el `tipo`.

### 2.3 Política CRITICAL es laxa por decisión del usuario

Decisión 2026-05-13: **CRITICAL no degrada `status_global`**. Solo:
- Aparece en `_alertas` del reporte como `[CONTROL CRITICO] ...`.
- Se persiste en BQ `controles_diarios`.
- Aparece en banner del email con `[CRITICO]` prefix en subject.
- Aparece en página `7_Controles` y mini-banner Home del dashboard.

No cambies esto sin pedir al usuario. Razón explícita: prefieren ir "lento y verificado", no quieren que un control nuevo rompa el pipeline diario antes de validar la calibración.

### 2.4 Ritmo del usuario

Preferencia documentada en `memory/feedback_ritmo_trabajo.md`: **NO apurar entregables**. El usuario rechazó el primer plan (parches mismo día) y pidió encajar todo en su workflow estándar:
- Rama dedicada `feat/sprint-sN-...`.
- Sprint formal en `roadmap.yaml`.
- `PLAN.md` + `hallazgos.md` en `docs/feats/{slug}/`.
- Commits convencionales (`feat(area): ...`, `fix(area): ...`, `refactor(area): ...`).
- MR/merges parciales a `main` por feature.

Si propones algo, ofrece dos rutas (rápida vs sprint) y deja que él elija.

### 2.5 No hay credenciales BQ en este entorno

Estoy en un entorno Linux dev sin credenciales BQ. **Todos los tests live (live BQ, Streamlit, Outlook COM) los tiene que correr el usuario en el PC institucional Windows**. Las verificaciones que sí podemos hacer aquí:
- AST parse (`python -c "import ast; ast.parse(open(p).read())"`).
- Imports puros (sin BQ) de los módulos.
- Smoke de helpers que no toquen red.

### 2.6 Convención de tablas BQ (importante para extender)

| Concepto | Patrón |
|---|---|
| Tabla diaria de un modelo | `report_{key_modelo}_dly` |
| Tabla histórica de un modelo | `report_{key_modelo}_hist` |
| Excepción ml_mora_consumo | produce además `report_ml_mora_consumo_renegociado_{dly,hist}` |
| Dataset diario | `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models` |
| Dataset histórico | `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist` |
| Tabla nueva F29 | `bfa_cl_prd_financial_risk_dly_proc_models.controles_diarios` |

La excepción de `ml_mora_consumo` se modela en `core/modelos_registry.py:158` (`_TABLAS_EXTRA`). Si surge otro modelo con tablas extra, agregarlo ahí.

### 2.7 Schema base de outputs

Función `crear_esquema_base()` en `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py:28-61`. Columnas relevantes para F29: `CODIGO_EMPRESA` (NULLABLE en BQ pero invariante = 1), `CODIGO_PRODUCTO`/`CODIGO_SUBPRODUCTO`/`FECHA_PROCESO` (REQUIRED), `AMORTIZACION`, `INTERES`, `MONEDA_ORIGEN`, `MONEDA_COMPENSACION`. **No tocar el schema BQ** — decisión 2026-05-13.

---

## 3. Estado de cada feature

### F28 — Fuente única `core/modelos_registry.py` ✅ completado

**Qué se hizo:**
- `core/modelos_registry.py` (290 líneas, commit `2a2d1a5`).
- API: `listar_modelos`, `tabla_dly`, `tabla_hist`, `tablas_extra_dly/hist`, `todas_las_tablas_dly/hist`, `nombre_legible`, `vuelta`, `metadata`, `modelo_de_tabla`.
- Override `_TABLAS_EXTRA = {"ml_mora_consumo": ["report_ml_mora_consumo_renegociado"]}`.
- Adoptado en: `core/orquestador.py:23-26`, `core/email_report.py:46-58`, `core/reporte_ejecucion.py:97-99`, `main.py:60-64`, `dashboard/utils/theme.py:18-23`, `dashboard/pages/3_Comparacion.py:18-44`.

**Smoke test (siempre pasa, no requiere BQ):**
```bash
python -c "from core.modelos_registry import listar_modelos, todas_las_tablas_hist, tablas_extra_hist
assert len(listar_modelos()) == 11
assert 'mr_ssv' in listar_modelos(vuelta=2)
assert 'report_ml_mora_consumo_renegociado_hist' in todas_las_tablas_hist(vuelta=1)
print('OK')"
```

**Cosas a saber:**
- No hay nada urgente pendiente. Si agregas un modelo nuevo, edita SOLO `core/modelos_registry.py` (y `_TABLAS_EXTRA` si aplica).
- No cambiar el orden de `_MODELOS` sin razón — el campo `orden` define el secuencial de ejecución del orquestador.

### F29 — Motor de controles ⚠️ en-progreso (cuadratura stub)

**Qué se hizo (commit `0e97eff`):**
- `core/controles_outputs.py` (~570 líneas) — motor + 7 checks de output puro + CLI.
- `core/controles_persistence.py` (~190 líneas) — escritura BQ tabla `controles_diarios` particionada por `fecha_proceso` clusterizada por `(modelo, nivel)` + fallback local en `reports/_pendientes_controles/` + `sync_pendientes()`.
- `core/controles_cuadratura.py` (~70 líneas) — **stub**: reporta INFO para todos los modelos según `tipo` configurado.
- Sección `controles:` en `config/config_rutas_ext_y_archivos.yaml` (líneas 256+) con defaults, por_modelo, cuadratura_inputs.
- Hook `OrquestadorModelos.ejecutar_controles_post_carga(modelos, fecha)` en `core/orquestador.py`.
- `ReporteEjecucion.registrar_controles(res)` en `core/reporte_ejecucion.py` — anexa `controles` al JSON y `[CONTROL CRITICO] ...` a `_alertas`. **NO degrada `status_global`**.
- `main.py:298-323` invoca el hook después de carga GCP exitosa.

**Lo que falta — cuadratura real (Fase 4 del PLAN):**
La función `check_cuadratura(modelo, fecha, cfg_controles)` en `core/controles_cuadratura.py:34` actualmente retorna INFO. Para que sea el check útil:

1. **Implementar lectores por `tipo`** (se decide vía `cuadratura_inputs.{modelo}.tipo` en YAML):
   - `pml_gcp`: reutilizar `core/control_interfaces.py:leer_pml_gcp` (línea ~169-178). Toma archivo PML CSV/Excel de red UNC, agrega `SUM(CAPITAL)` y `SUM(INTERES)` por MONEDA.
   - `pml_cmr`: análogo con `leer_pml_cmr`.
   - `access`: nuevo. Lee `.accdb` por ODBC, query `SELECT SUM({columna_capital}), SUM({columna_interes}), MONEDA FROM {ruta_tabla} GROUP BY MONEDA`. Parametrizado en YAML.
   - `manual`: dejar como está (INFO).
   - `no_configurado`: dejar como está (INFO).

2. **Comparar contra output BQ**: `SELECT SUM(AMORTIZACION), SUM(INTERES), MONEDA_ORIGEN FROM report_{modelo}_dly WHERE FECHA_PROCESO = @fecha GROUP BY MONEDA_ORIGEN`.

3. **Generar `CheckResultado`**:
   - `cuadratura_capital_{moneda}`: |Δ%| vs `cfg.cuadratura.tolerancia_pct.{warning,critical}`. Default warning 0.1%, critical 1.0%.
   - `cuadratura_interes_{moneda}`: análogo.
   - Evidencia: `{"capital_input": ..., "capital_output": ..., "delta_abs": ..., "delta_pct": ...}`.

4. **Test contra incidente**: el usuario debe identificar una fecha histórica donde supo que hubo desbalance. Correr el motor sobre esa fecha y verificar que `cuadratura_capital_*` lo marca CRITICAL con un `delta_pct` consistente. Si no se conoce fecha exacta, **forzar test sintético**: insertar fila en `report_ml_mora_consumo_dly` con AMORTIZACION inflada y comparar contra PML real.

**Cosas que noté que pueden complicar Fase 4:**
- `control_interfaces.py` ya tiene 1218 líneas y mucha lógica de severidad CAPITAL/INTERES por SISTEMA/MONEDA. Tentación de reusar: ojo, está orientado a comparar PML t vs t-1, no PML vs output_BQ. Lo que sirve es el **lector de archivos** (línea 169-178), no la lógica de comparación.
- Algunos modelos pasan por **lectura de Access cacheada como parquet** (ver `dashboard/utils/local_data.py` y `RF_Modelo_*/`). Para cuadratura puedes leer el parquet directamente en vez del Access.
- **NMD case-sensitivity**: hay un fix reciente (commit `2793e8c`: `fix(nmd): corregir case-sensitivity en filtro de productos balance`). Si el lector de Access para NMD usa nombres de columna, validar mayúsculas/minúsculas.

**Smoke (sin BQ live):**
```bash
python -c "from core.controles_outputs import ejecutar_controles, ResultadoControles, _CHECKS_REGISTRY
print('checks registrados:', [f.__name__ for f in _CHECKS_REGISTRY])"
```

**Tabla `controles_diarios` no existe todavía**. La primera escritura del motor la crea (idempotente, `crear_tabla_si_no_existe`). Si quieres crearla a mano:
```bash
python -m core.controles_persistence crear-tabla
```

### F30 — Email unificado ✅ completado

**Qué se hizo (commit `595f6cc`):**
- Tipo `unificado` agregado a `_TABLAS_POR_TIPO` (V1+V2 = 12 tablas hist incluyendo `report_mr_ssv_hist` y `report_ml_mora_consumo_renegociado_hist`).
- `_leer_controles_dia(client, fecha)` lee BQ `controles_diarios`.
- `_construir_seccion_salud(df_ctrl, fecha)` → banner (OK/WARN/CRIT) + anexo CRITICAL al inicio del HTML.
- Subject prefix `[CRITICO]` cuando `nivel_global == CRITICAL`.
- CLI `--preview-html`: genera `reports/{YYYYMMDD}/email_preview_{tipo}/index.html` reemplazando `cid:chart_*` por rutas relativas. NO toca Outlook.
- Eliminado `CODIGO_PRODUCTOS` hardcoded (linea 74-83 original) — email ahora cubre TODOS los productos.

**Lo que NO se hizo (pero el PLAN lo menciona):**
- **Refactor estructural de `_construir_html`** en bloques `_html_header/_html_seccion_salud/_html_anexo_criticos/_html_tabla_maestra/_html_secciones_por_modelo/_html_footer`. Quedó como un solo HTML inline. Funciona pero es menos mantenible.
- **Tabla maestra por modelo** (no por producto) con todas las métricas (n_filas, sum_amort por moneda, etc). Hoy sigue siendo tabla pivote producto×moneda como antes.
- **Excel hoja Controles**: el adjunto Excel no incluye una hoja "Controles" con resultados del motor. Se podría agregar en `_generar_excel`.
- **Robustez Outlook**: no se implementó reintentos ni fallback SMTP. Si Outlook COM falla, sigue cayendo igual que antes.
- **Activación de `unificado`**: no se cambió ningún default. Sigue corriendo `primera_vuelta` + `segunda_vuelta` como antes. Para activar el unificado, el usuario tiene que correr explícitamente `python -m core.email_report --tipo unificado` o configurarlo en YAML.

**Smoke (sin BQ live):**
```bash
python -c "
from core.email_report import _construir_seccion_salud, _TABLAS_POR_TIPO
import pandas as pd
assert 'unificado' in _TABLAS_POR_TIPO
df_vacio = pd.DataFrame()
html, nivel = _construir_seccion_salud(df_vacio, '2026-05-12')
assert nivel == 'OK'
print('OK')"
```

**Test live (en PC institucional):**
```bash
python -m core.email_report --fecha 2026-05-12 --tipo unificado --preview-html
# abre reports/20260512/email_preview_unificado/index.html en navegador
```

### F31 — Dashboard Controles ✅ completado

**Qué se hizo (commit `1a42ea8`):**
- `dashboard/pages/7_Controles.py` (~200 líneas) — selector fecha, filtros modelo+nivel, KPI tiles, banner global, matriz pivote modelo×check con semáforos, drill-down expandible con `evidencia_json` formateado, botón "Re-ejecutar controles" (subprocess al motor), config visible al final.
- `dashboard/utils/controles_helpers.py` (~140 líneas) — `cargar_umbrales` (cache 15min), `cargar_controles_bq` (cache 2min), `fechas_con_controles` (cache 15min), `render_banner_salud`, `parsear_evidencia`, mapas NIVEL_COLORS/EMOJI/RANK.
- Banner en `dashboard/pages/1_Home.py:344-350` que linkea a `/Controles` (try/except, no rompe Home si no hay datos).
- Página registrada en `dashboard/app.py:60`.

**Cosas a saber:**
- Si la tabla `controles_diarios` aún no existe, las funciones retornan DataFrame vacío sin romper.
- El botón "Re-ejecutar controles" usa `subprocess.run([sys.executable, "-m", "core.controles_outputs", ...])`. **Requiere que el cwd de Streamlit sea la raíz del repo**. Si el usuario lanza Streamlit desde otro lado, el botón puede fallar.
- El `applymap` en el style del pivote está deprecado en pandas 2.1+; eventualmente cambiar a `.map`.

**Smoke**: solo AST parse en este entorno; live requiere Streamlit + BQ.

### F32 — Performance dashboard ✅ completado

**Qué se hizo (commit `02a9ae3`):**
- `dashboard/app.py`: usa `importlib.util.find_spec()` para chequear plotly y bigquery sin importarlos en boot.
- `dashboard/pages/1_Home.py`: refactor `_consolidar_dia(fecha_iso)` con `@st.cache_data(ttl=120)`. Fallback local incluido adentro. Retorna dict con clave `fuente`.
- `dashboard/pages/2_Logs.py`: `plotly.express` lazy en sección pie chart.
- `dashboard/pages/3_Comparacion.py` (commit `7b83254` + `02a9ae3`): `_comparar(t, t-1)` cacheado TTL 600, `obtener_fechas_disponibles` con LIMIT 60 + TTL 900, columna sintética `MODELO`, filtro de modelos en sidebar, tabla pivote "Por modelo", plotly lazy. **Cubre SSV y todos los productos** (no solo 8).
- `dashboard/pages/4_Benchmark.py`: `_benchmark_pipeline(dias)` cacheado TTL 300 que envuelve carga + parse + agregación. plotly lazy.
- `dashboard/pages/5_Parametros.py`: `DeepDiff` lazy en `_deepdiff_json`.
- `dashboard/pages/6_Email.py`: `plotly.graph_objects` lazy.

**Objetivo F32**: cold-start ≥30% más rápido. **Falta medir** en PC institucional con `time streamlit run dashboard/app.py`.

---

## 4. Plan de verificación pendiente (PC institucional)

El usuario tiene que correr esto en su PC Windows con credenciales BQ:

### V1. Smoke registry (no requiere BQ)
```bash
python -c "
from core.modelos_registry import listar_modelos, todas_las_tablas_hist, tablas_extra_hist
print('modelos:', listar_modelos())
print('V1 tablas:', todas_las_tablas_hist(vuelta=1))
print('V2 tablas:', todas_las_tablas_hist(vuelta=2))
print('extras mora_consumo:', tablas_extra_hist('ml_mora_consumo'))"
```
Esperado: 11 modelos; V1=7 tablas (incluye renegociado); V2=5 (incluye `report_mr_ssv_hist`).

### V2. Cold-start dashboard
```bash
# Antes de cambiar de rama, medir baseline:
git checkout main
time streamlit run dashboard/app.py --server.headless=true
# Ctrl+C tras primer render

git checkout feat/sprint-s6-controles
time streamlit run dashboard/app.py --server.headless=true
```
Objetivo: reducción ≥30% en cold-start.

### V3. Comparativa cubre SSV
Navegar a `Comparación Outputs`, seleccionar fecha con datos de SSV (cualquiera post commit `c9e043d`, 2026-04-27). Confirmar:
- Selector "Explorar tabla" incluye `SSV (EOM)`.
- Sidebar tiene filtro "Modelos" con 11 opciones.
- Gráficos por moneda muestran productos de NMD/LC/Inversiones/SSV/Prepago (no solo los 8 de mora).
- Nueva sección "Por modelo" arriba muestra 11 filas.

### V4. Motor de controles (live BQ)
```bash
# Standalone, sin persistir
python -m core.controles_outputs --fecha 2026-05-12 --no-persist --export-json /tmp/ctrl.json

# Con persistencia (crea tabla controles_diarios si no existe)
python -m core.controles_outputs --fecha 2026-05-12

# Verificar tabla en BQ
python -m core.controles_persistence leer --desde 2026-05-12 --nivel-min OK
```
Esperado: 11 modelos × ~10 checks/modelo. Reporte por consola + JSON con `ResultadoControles`. Persistencia OK.

### V5. Reproducir error grueso (cuando cuadratura esté real)
**No aplicable todavía** (Fase 4 pendiente). Cuando se implemente:
- Identificar fecha histórica con desbalance conocido.
- `python -m core.controles_outputs --fecha {esa_fecha} --modelos {modelo_afectado}`.
- Verificar `cuadratura_capital_{moneda}` marcado CRITICAL.

### V6. Email preview
```bash
python -m core.email_report --fecha 2026-05-12 --tipo unificado --preview-html
# Abrir: reports/20260512/email_preview_unificado/index.html
```
Esperado: HTML con sección de salud al inicio (banner + anexo CRITICAL si los hay), tabla de productos × monedas, secciones por moneda. **No invoca Outlook**.

### V7. Página Controles
Streamlit → navegar a `🛡️ Controles`. Validar:
- Selector de fecha listo (las que tengan datos en `controles_diarios`).
- KPI tiles muestran conteos correctos.
- Matriz pivote con semáforos.
- Drill-down al hacer click en alerta.
- Botón "Re-ejecutar controles" funciona.

### V8. End-to-end pipeline real
```bash
python main.py --modelos primera_vuelta --fecha 2026-05-13 --cargar-gcp
```
Esperado: tras carga GCP exitosa, log muestra "Ejecutando controles post-carga…" + resumen por nivel. Reporte JSON final tiene clave `controles`. Email enviado con sección de salud.

---

## 5. Cosas que noté en el camino (gotchas)

### 5.1 Plan mode y `Write` no disponible para Plan agents

Los Plan agents que lancé devolvieron sus planes como texto, no escritos a archivo, porque en plan mode solo el agente principal puede escribir al plan file. Si usas Plan agents otra vez, indícales explícitamente que devuelvan el plan como texto y tú lo consolidas.

### 5.2 `_VUELTA_2` original NO tenía `mr_ssv`

`core/reporte_ejecucion.py:97-104` original tenía hardcoded:
```python
_VUELTA_2 = frozenset(["mr_prepago_cmr", "ml_nmd", "ml_lc", "ml_inversiones"])
```
**Le faltaba `mr_ssv`**. El refactor a `frozenset(listar_modelos(vuelta=2))` lo agrega. Es un bug latente que se corrige sin mencionarse explícitamente. Mencionarlo en el MR.

### 5.3 `applymap` deprecado

En `dashboard/pages/7_Controles.py:138` usé `.applymap(_style_celda)`. En pandas 2.1+ está deprecado. Reemplazar por `.map(_style_celda)` si el linter se queja. No bloqueante.

### 5.4 git user.email no estaba configurado

El entorno no tenía `git config user.name/email`. Lo configuré **local al repo** (no `--global`) con la identidad del usuario (`Víctor Landaeta Torres <vlandaetat@bancofalabella.cl>`) sacada de commits previos. Si el próximo agente trabaja en otro entorno, puede que tenga que rehacerlo.

### 5.5 Carpeta untracked `carga_modelos_gcp/sql/`

Existe en el repo desde antes (`git status` la marca untracked). Tiene un archivo `svw_report_modelos_dly_respaldo copy.sql`. **No la toqué**. Probablemente sea WIP del usuario para algún view/respaldo. Preguntar antes de mover/borrar.

### 5.6 `_TITULO_POR_TIPO["unificado"]` debe coincidir con `asunto_template`

Si activan `unificado` en YAML, el `asunto_template` debe estar definido bajo `email_report.reportes.unificado.asunto_template`. **No lo agregué al YAML**. Sin esa entrada, cae al default `"Reporte Amortizacion -- {fecha}"` que sirve igual. Pero podría confundir.

### 5.7 El motor crea la tabla BQ en la primera escritura

`controles_persistence.crear_tabla_si_no_existe()` se llama desde `escribir()`. La primera vez que se corra el motor con `persistir=True` (en PC institucional con BQ), creará la tabla. **Si quieres anticiparlo** (ej. para que el dashboard Controles tenga algo antes del primer pipeline):
```bash
python -m core.controles_persistence crear-tabla
```

### 5.8 Tests automatizados — no hay

El repo no tiene una suite de tests (`tests/` solo está en `RF_Modelo_Inversiones/tests/`). Todo lo nuevo se validó con AST parse + smoke imports. Si vas a hacer cambios grandes, considerar agregar un mínimo de pytest para `core/modelos_registry.py` y `core/controles_outputs.py:_CHECKS_REGISTRY`.

### 5.9 Lectura de credenciales GCP

`config.config_rutas.obtener_ruta_credenciales_gcp()` retorna un Path que en este entorno **no existe** (`credenciales/bfa-cl-trade-price-report-dev-9d137fc23b7f.json`). Por eso aquí no se puede testear contra BQ. En el PC institucional debería estar.

### 5.10 Streamlit no en este venv

`pip install streamlit` no está en este Linux. Las páginas se validan con AST. Si necesitas testear render, usa `requirements.txt` del repo (incluye streamlit).

---

## 6. Si el usuario te pide "cerrar el sprint"

Pasos sugeridos (ordenados):

1. **Verificación live por el usuario** (V1-V8 arriba). Anota cualquier ajuste necesario.
2. **Implementar Fase 4 (cuadratura)**:
   - `core/controles_cuadratura.py` con lector `pml_gcp` reutilizando `control_interfaces.py:169-178`.
   - Reproducir error grueso con fecha histórica conocida o test sintético.
   - Marcar F29 como `completado` en `roadmap.yaml`.
3. **Activar `unificado`** en YAML (`email_report.reportes.unificado.enabled: true` + `asunto_template`). Pedir al usuario el subject template deseado.
4. **MR/merge**: crear MR de `feat/sprint-s6-controles` a `main` con descripción que linkee a `PLAN.md` y `HANDOFF.md`. Usar `gh pr create`. Pedir review al equipo.
5. **Limpieza memoria**: si surgieron nuevas preferencias del usuario en el camino, agregar a `memory/feedback_*.md`.

---

## 7. Si el usuario te pide "hacer otra cosa"

Posibles próximos sprints sugeridos (no comprometidos):

- **S7 — Lectores cuadratura**: cerrar Fase 4 de F29 con lectores reales por tipo. Estimado: M (3d).
- **S8 — Refactor email_report estructural**: bloques HTML, tabla maestra por modelo, hoja Controles en Excel, robustez Outlook. Estimado: M (3d).
- **S9 — Hardening BQ writers**: F29 dejó las validaciones en el motor de controles (post-carga). Mover invariantes (CODIGO_EMPRESA=1, monedas, no-NaN required) al writer Python (assertion previa a `load_table_from_dataframe`). Decisión 2026-05-13: diferido. Cuando el usuario lo pida, este es el lugar.
- **F27** (existente backlog) — automatizar saldos CORE SSV. Cuando se cierre, cambiar `mr_ssv` en `cuadratura_inputs` de `manual` a `access` o lo que corresponda.
- **Cuadre CMR** (existente `docs/feats/cuadre-mr-prepago-cmr/`) — cerrar las divergencias notebook vs `.py`. Cuando se cierre, cambiar `mr_prepago_cmr` a `tipo: pml_cmr` en YAML.

---

## 8. Archivos clave para tener a mano

| Archivo | Para qué |
|---|---|
| `core/modelos_registry.py` | Fuente única de modelos. Edita aquí cuando agregues uno. |
| `core/controles_outputs.py` | Motor F29. Catálogo `_CHECKS_REGISTRY` y SQL en `_query_metricas_modelo`. |
| `core/controles_cuadratura.py` | Stub a completar (Fase 4). |
| `core/controles_persistence.py` | Persistencia BQ + fallback local. |
| `config/config_rutas_ext_y_archivos.yaml` | Sección `controles:` con umbrales por defecto y por modelo. |
| `docs/roadmap/roadmap.yaml` | Estado de sprint S6 + F28-F32. |
| `docs/feats/controles-outputs/PLAN.md` | Plan completo del sprint. |
| `docs/feats/controles-outputs/hallazgos.md` | Diagnóstico original (mapeo de gaps). |
| `docs/feats/cuadre-mr-prepago-cmr/hallazgos.md` | Por qué CMR sigue manual. |
| `core/control_interfaces.py` | Patrón de severidad CAPITAL/INTERES + lectores PML (reusar en Fase 4). |
| `dashboard/pages/7_Controles.py` | Página del dashboard. |

---

## 9. TL;DR

- Rama `feat/sprint-s6-controles` lista, 8 commits limpios.
- F28+F30+F31+F32 completados; F29 al 80% (falta cuadratura real).
- El "error grueso" es desbalance capital input↔output, no `CODIGO_EMPRESA=NaN`.
- Política CRITICAL no degrada `status_global` (decisión usuario).
- Tests live pendientes en PC institucional (credenciales BQ).
- Si retomas, lee `PLAN.md` y `hallazgos.md`. Lo más útil es completar `controles_cuadratura.py` (Fase 4 del PLAN).
