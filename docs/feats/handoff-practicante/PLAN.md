# F25: Handoff al Practicante + Supervisión Remota

## Estado: EN DISEÑO (Sprint S6)

---

## 1. Contexto y Constraints

| Factor | Realidad |
|---|---|
| **Delivery** | ZIP (sin GitLab, sin git remoto) |
| **Internet del practicante** | Mala/inestable |
| **Network inputs** | `\\vmdvorak` — obligatorio, no evitable |
| **Dependencia especial** | `bfa_cl_utilidades` se instala desde `Z:/RF_INSTALADORES/` (drive mapeado a red) |
| **Ejecución** | Diaria, modelos secuenciales, ~5-15 min total |
| **Supervisión** | Remota, se necesita ver logs/errores/benchmark/bottlenecks casi en tiempo real |
| **GCP** | Proyecto `bfa-cl-trade-price-report-dev`, SA: `modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com` |
| **Credencial disponible** | Service account key JSON ya existente en `credenciales/` |

---

## 2. Los 3 Problemas a Resolver

### P1 — Setup Reproducible: "Que funcione al primer intento"

**Complicaciones actuales:**
1. `bfa_cl_utilidades @ file:///Z:/RF_INSTALADORES/bfa-cl-utilidades` — requiere drive Z: mapeado
2. Access ODBC driver (32-bit vs 64-bit, Microsoft Access Database Engine)
3. GCP credentials JSON en `credenciales/`
4. Conda environment con versión específica de Python

**Solución: ZIP autocontenido con scripts de setup**

```
📦 bfa-cl-modelos-diarios-v1.0.zip
├── SETUP.md                          # Guía paso a paso con screenshots
├── DAILY_WORKFLOW.md                  # Qué hacer cada día (1 página)
├── setup_env.bat                     # Script automático: crear conda env + instalar
├── check_env.bat → check_env.py      # Verificador de salud de entorno
├── wheels/
│   └── bfa_cl_utilidades-X.Y.Z.whl   # Dependencia empaquetada como wheel
├── requirements_standalone.txt        # requirements.txt con ref local al .whl
└── (resto del proyecto)
```

**`setup_env.bat`:**
```bat
@echo off
echo === Configurando entorno bfa-cl-modelos-v2 ===
conda create -n bfa-cl-modelos-v2 python=3.10 -y
call conda activate bfa-cl-modelos-v2
pip install wheels\bfa_cl_utilidades-*.whl
pip install -r requirements_standalone.txt
echo === Verificando instalación ===
python check_env.py
pause
```

**`check_env.py` (health check) verificaría:**
- ✅ Python version correcta
- ✅ Todas las dependencias importables (pandas, openpyxl, pyodbc, google-cloud-bigquery, etc.)
- ✅ Access ODBC driver presente (32/64-bit)
- ✅ Conectividad a `\\vmdvorak` (con timeout de 5s)
- ✅ Credenciales GCP válidas (test auth)
- ✅ Permisos de escritura en directorio de trabajo
- ✅ Espacio en disco suficiente (>500MB)
- ✅ Config YAML parseable correctamente

### P2 — Ejecución a Prueba de Errores: "Todo documentado automáticamente"

**Lo que YA existe y funciona:**
- Logger JSONL con timestamps ms + traceback completo + contexto de modelo (`core/logger.py`)
- Snapshot de parámetros por fecha (`core/orquestador.py` → `snapshots/{YYYYMMDD}/`)
- CLI con `--fecha`, `--modelos`, `--cargar-gcp`
- Pre/post hooks: copia local de Access/PML, verificación de integridad
- JSON parameter validation con cache de metadata (F20)

**Lo que FALTA implementar:**

#### a) Reporte de ejecución diario (`core/reporte_ejecucion.py`)

Generado automáticamente al final de cada run:

```json
{
  "fecha_proceso": "2026-03-10",
  "inicio": "2026-03-10T08:15:22.341",
  "fin": "2026-03-10T08:23:45.892",
  "duracion_total_seg": 503.55,
  "hostname": "PC-PRACTICANTE",
  "usuario": "jpractical",
  "python_version": "3.10.16",
  "rama_git": "sprint/S5-optimizacion-pipeline",
  "commit": "4afdd4d",
  "modelos": {
    "mr_prepago_consumo": {
      "status": "OK",
      "inicio": "...", "fin": "...",
      "duracion_seg": 45.2,
      "output_excel": {"path": "...", "size_kb": 234, "sheets": 3, "rows_total": 1850},
      "parametros_source": "JSON",
      "parametros_validacion": "cache_hit",
      "carga_gcp": "OK"
    },
    "ml_mora_consumo": {
      "status": "ERROR",
      "error_type": "FileNotFoundError",
      "error_msg": "\\\\vmdvorak\\... no accesible",
      "duracion_seg": 3.1
    }
  },
  "benchmark": {
    "total_seg": 503.55,
    "modelo_mas_lento": "ml_mora_consumo",
    "comparacion_vs_promedio": "+12%",
    "promedio_historico_seg": 449.6
  },
  "alertas": [
    "ml_mora_consumo falló — red no accesible",
    "duracion total 12% sobre promedio histórico"
  ]
}
```

Más versión humana `reports/{YYYYMMDD}/reporte_ejecucion.md`.

#### b) Benchmark histórico (`data/benchmark/historial.jsonl`)

Cada ejecución agrega una línea JSONL al historial local:
```jsonl
{"fecha":"2026-03-10","total_seg":503.5,"por_modelo":{"mr_prepago_consumo":45.2},"hostname":"PC-X"}
```

Se usa para comparar contra promedio histórico y generar alertas tipo "hoy todo tomó 3× más → probable problema de red".

#### c) Script wrapper simplificado (`run_diario.bat`)

```bat
@echo off
echo === Ejecución diaria de modelos ===
set /p FECHA="Ingrese fecha (YYYY-MM-DD): "
call conda activate bfa-cl-modelos-v2
python main.py --fecha %FECHA% --modelos todos --cargar-gcp
echo === Finalizado ===
pause
```

### P3 — Observabilidad Remota: "Ver sin estar ahí"

**Decisión original: GCS bucket** → ❌ SA no tiene permisos GCS (verificado 2026-03-10)

**Nueva decisión: BigQuery como canal de reportes**

#### Flujo de sync:

```
Practicante ejecuta run_diario.bat
    ↓
Modelos corren → genera reports/{fecha}/reporte_ejecucion.json
    ↓
core/sync_reportes.py inserta en BigQuery:
    tabla: bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion
    row: {fecha, hostname, json_reporte, json_benchmark, alertas, status}
    ↓
Si BQ falla → fallback: guarda local + warning en log
    ↓
Supervisor consulta desde BigQuery console / dashboard Streamlit
```

**Ventajas:**
- SA ya tiene **todos** los permisos BigQuery necesarios
- 0 configuración adicional, funciona inmediatamente
- Dashboard Streamlit ya consulta BQ (solo agregar tab para reportes)
- Histórico de reportes queda en BQ con retención gratuita

**Si en el futuro se consiguen permisos GCS:**
- Se agrega upload de archivos (logs completos, snapshots)
- sync_reportes.py ya tendría la estructura para agregar el canal GCS

---

## 3. Inventario de Infraestructura Actual (codebase snapshot)

### Logging (`core/logger.py`)
- JSONL format: `{ts, level, logger, modelo, msg, exception}`
- Console: human-readable, sin prefijos
- File: `logs/{YYYYMMDD}/modelos.jsonl`
- Print interception: monkey-patches `builtins.print` → JSONL
- Context tracking via `contextvars.ContextVar` (thread-safe)
- GUI: `DynamicStdoutHandler` para tkinter

### Orquestador (`core/orquestador.py`)
- 10 modelos registrados (nombre, módulo, enabled, orden, vuelta 1/2)
- Ejecución secuencial (F21 benchmark confirmó que ThreadPoolExecutor no mejora)
- Pre-hooks: copia PML y Access a cache local
- Post-hooks: verificación integridad + limpieza
- Snapshot de parámetros: `snapshots/{YYYYMMDD}/{modelo}/`
- Carga GCP: BigQuery daily + consolidación histórica

### Entry point (`main.py`)
- CLI args: `--fecha`, `--modelos`, `--gui`, `--cargar-gcp`, `--consolidar-historico`, etc.
- Aliases: `todos`, `primera_vuelta`, `segunda_vuelta`
- Summary table al final de ejecución

### Config
- `config/config_rutas.py`: paths base, `resolver_ruta()` para UNC/relativas/absolutas
- `config/config_rutas_ext_y_archivos.yaml`: rutas de cada modelo (inputs, parámetros, outputs)
- Network: `\\vmdvorak\Riesgo Financiero Folder\...` y `\\vmdvorak\Riesgo Financiero2\...`

### Dependencias (`requirements.txt`)
- Data: pandas, openpyxl, xlrd, pyarrow, xlsxwriter
- GCP: google-cloud-bigquery, google-cloud-storage, google-auth, pandas-gbq
- DB: SQLAlchemy, sqlalchemy-access, pyodbc
- GUI: tkcalendar
- Dashboard: streamlit (manual)
- Custom: `bfa_cl_utilidades @ file:///Z:/RF_INSTALADORES/bfa-cl-utilidades`
- Docs: mkdocs, mkdocs-material

### Outputs
- Excel via `core/excel_output.py` (xlsxwriter preferido, openpyxl fallback)
- BigQuery daily tables (TRUNCATE mode) vía `carga_modelos_gcp/`
- BigQuery historical (append con dedup, force mode con backup CSV)

### GCP
- **Proyecto**: `bfa-cl-trade-price-report-dev`
- **SA**: `modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com`
- **SA key ID**: `9d137fc23b7fb23b7fa5d40a300897279d3fc16b`
- **Client ID**: `105098588849907827966`
- **Dataset BQ**: `bfa_cl_prd_financial_risk_dly_proc_models_hist` (y daily)
- **Credencial**: `credenciales/bfa-cl-trade-price-report-dev-9d137fc23b7f.json`

---

## 4. Verificación de Permisos GCP — RESULTADOS (2026-03-10)

**Service Account:** `modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com`  
**Script:** `tools/test_gcp_permisos.py` | **Reporte:** `reports/gcp_permisos_test.json`  
**Resultado global:** 11 OK / 9 ERROR (5/14 IAM permissions granted)

### ✅ PUEDE HACER

| Servicio | Permiso | Detalle |
|---|---|---|
| **BigQuery** | datasets.create | Crear datasets ✓ |
| **BigQuery** | tables.create | Crear tablas ✓ |
| **BigQuery** | tables.getData | Leer datos ✓ |
| **BigQuery** | jobs.create | Ejecutar queries/load ✓ |
| **Resource Manager** | projects.get | Ver proyecto ✓ (state=ACTIVE) |

**BigQuery pruebas integradas:**
- Listar 20 datasets ✓
- SELECT query ✓
- Crear + eliminar dataset temporal ✓
- Listar tablas de datasets existentes ✓

### ❌ NO PUEDE HACER

| Servicio | Permiso | Error |
|---|---|---|
| **GCS** | storage.buckets.create | 403 Forbidden |
| **GCS** | storage.buckets.list | 403 Forbidden |
| **GCS** | storage.objects.create | 403 Forbidden |
| **GCS** | storage.objects.get | 403 Forbidden |
| **Compute Engine** | compute.instances.create | 403 Forbidden |
| **Compute Engine** | compute.instances.list | 403 Forbidden |
| **Notebooks** | notebooks.instances.create | 403 Forbidden |
| **Notebooks** | notebooks.instances.list | 403 Forbidden |
| **IAM** | iam.serviceAccounts.list | 403 Forbidden |
| **IAM** | getIamPolicy | 403 Forbidden |
| **Service Usage** | list enabled APIs | 403 Forbidden |
| **Cloud Logging** | write/read entries | 403 Forbidden |

### ⚠️ Nota técnica: SSL proxy corporativo
La red corporativa tiene un proxy que intercepta HTTPS. El cert NO está en `certifi`, 
pero SÍ en el system cert store de Windows. El script exporta system certs a PEM y los 
usa como `session.verify` para las REST APIs. Los clientes google-cloud-* (BQ, Storage) 
usan gRPC con su propio transport y no tienen este problema.

### 📋 IMPACTO EN ESTRATEGIA DE OBSERVABILIDAD

**GCS bucket NO es viable** con los permisos actuales del SA.

**Alternativas ordenadas por preferencia:**

| Opción | Pros | Contras |
|---|---|---|
| **A. BigQuery como canal de reportes** | YA funciona, 0 permisos nuevos, dashboard Streamlit ya existe | No sube archivos (solo datos tabulares), requiere diseñar tabla |
| **B. Solicitar roles GCS al equipo GCP** | Solución original del plan, upload archivos | Requiere gestión externa, timeline incierto |
| **C. Carpeta compartida `\\vmdvorak`** | Sin depender de internet | Si la red falla, la observabilidad también |
| **D. Email con adjuntos (SMTP o API)** | Universal, funciona siempre | Requiere configurar SMTP, más complejo |

**Recomendación:** Opción A (BigQuery) como solución inmediata + Opción B como mejora futura.  
BigQuery permite crear una tabla `reportes_ejecucion` donde cada row sea un JSON stringificado  
del reporte completo, consultable desde el dashboard Streamlit o desde cualquier cliente BQ.

---

## 5. Estructura Final del ZIP

```
📦 bfa-cl-modelos-diarios-v1.0/
├── SETUP.md                              # Guía instalación con screenshots
├── DAILY_WORKFLOW.md                     # Guía diaria (1 página)
├── TROUBLESHOOTING.md                    # Problemas comunes + soluciones
├── setup_env.bat                         # Instalación automática env conda
├── check_env.bat → check_env.py          # Verificador de salud
├── run_diario.bat                        # Wrapper ejecución diaria
├── wheels/
│   └── bfa_cl_utilidades-X.Y.Z.whl       # Dependencia offline
├── requirements_standalone.txt           # Sin referencia a Z:
├── core/
│   ├── logger.py                         # (existente) JSONL structured logging
│   ├── orquestador.py                    # (existente) orquestación secuencial
│   ├── excel_output.py                   # (existente) xlsxwriter+openpyxl
│   ├── reporte_ejecucion.py              # NUEVO: generador de reportes JSON+MD
│   ├── health_check.py                   # NUEVO: verificador de entorno
│   └── sync_reportes.py                  # NUEVO: push a GCS + fallback local
├── reports/                              # NUEVO: reportes por fecha
│   └── {YYYYMMDD}/
│       ├── reporte_ejecucion.json
│       └── reporte_ejecucion.md
├── data/
│   ├── cache/                            # (existente) parquet cache, param check
│   └── benchmark/
│       └── historial.jsonl               # NUEVO: benchmark acumulado
├── tools/
│   ├── excel_a_json.py                   # (existente, F20) migración parámetros
│   └── test_gcp_permisos.py              # NUEVO: diagnóstico permisos GCP
├── logs/{YYYYMMDD}/modelos.jsonl         # (existente)
├── snapshots/{YYYYMMDD}/{modelo}/        # (existente)
└── (resto del proyecto)
```

---

## 6. Riesgos y Mitigaciones

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Red `\\vmdvorak` caída | Alta | Health check pre-ejecución, error claro en reporte |
| Practicante modifica código | Media | ZIP de backup rotulado, doc "NO TOCAR" |
| Access ODBC incompatible | Media | Incluir instalador en zip, documentar versión exacta |
| GCP credentials expiran | Baja | Health check verifica, alerta en reporte |
| Disco lleno | Baja | Script limpieza >30 días |
| Internet del practicante muy mala | Alta | Upload GCS es <1MB, fallback local si falla |
| SA no tiene permisos GCS | **CONFIRMADO** | Usar BigQuery como canal alternativo (ya implementado arriba) |

---

## 7. Orden de Implementación Propuesto

1. ~~Verificar permisos GCP del SA~~ ← ✅ HECHO (solo BigQuery funciona)
2. **Reporte de ejecución** (`core/reporte_ejecucion.py`)
3. **Benchmark histórico** (integrado en reporte)
4. **Health check** (`check_env.py`)
5. **Sync a BigQuery** (`core/sync_reportes.py`) — tabla `reportes_ejecucion`
6. **Scripts wrapper** (setup_env.bat, run_diario.bat, check_env.bat)
7. **Empaquetar bfa_cl_utilidades como wheel**
8. **Documentación** (SETUP.md, DAILY_WORKFLOW.md, TROUBLESHOOTING.md)
9. **Build del ZIP final**

---

## 8. Sesión Actual — Decisiones Tomadas

- ✅ Observabilidad remota: **GCS bucket** era el plan → **NO VIABLE** (SA sin permisos GCS)
- ✅ **BigQuery como canal de reportes**: alternativa viable e inmediata (permisos full)
- ✅ Email como fallback: descartado por ahora
- ✅ Git bundle: descartado (practicante no usa git)
- ✅ Carpeta compartida: descartado (depende de red mala)
- ✅ Crear VM/Notebook: **NO VIABLE** (SA sin permisos compute/notebooks)
- ✅ Permisos GCP verificados: solo BigQuery + resourcemanager.projects.get
- 🔄 Decidir: usar BigQuery para reportes (opción A) o solicitar GCS (opción B)
