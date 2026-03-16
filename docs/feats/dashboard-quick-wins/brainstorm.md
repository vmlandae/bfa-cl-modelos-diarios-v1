# 🧠 Brainstorm: Dashboard de Modelos Diarios — Visión Completa

> **Fecha:** 2026-03-12
> **Estado:** Borrador exploratorio — todo vale, nada se descarta aún
> **Objetivo:** Documentar TODAS las ideas de features para el dashboard, organizadas por capacidad y por usuario objetivo. Luego priorizaremos y aterrizaremos.

---

## Tabla de Contenidos

1. [Personas y User Stories](#1-personas-y-user-stories)
2. [Centro de Control de Ejecuciones](#2-centro-de-control-de-ejecuciones)
3. [Explorador de Logs](#3-explorador-de-logs)
4. [Gestión de Parámetros y Snapshots](#4-gestión-de-parámetros-y-snapshots)
5. [Observatorio de Inputs](#5-observatorio-de-inputs)
6. [Analítica de Outputs](#6-analítica-de-outputs)
7. [Tendencias y Series de Tiempo](#7-tendencias-y-series-de-tiempo)
8. [Reproducibilidad y Descargas](#8-reproducibilidad-y-descargas)
9. [Auditoría y Compliance](#9-auditoría-y-compliance)
10. [Salud de Infraestructura](#10-salud-de-infraestructura)
11. [Alertas y Notificaciones](#11-alertas-y-notificaciones)
12. [Calidad de Datos](#12-calidad-de-datos)
13. [Gobierno de Modelos (Model Risk)](#13-gobierno-de-modelos-model-risk)
14. [UX y Arquitectura del Dashboard](#14-ux-y-arquitectura-del-dashboard)
15. [Ideas Moonshot](#15-ideas-moonshot)

---

## 1. Personas y User Stories

### 👩‍💻 Practicante (Operador Diario)
El que ejecuta los modelos cada mañana. Necesita saber si todo salió bien, y si no, dónde falló.

- *"Como practicante, quiero ver de un vistazo si todos los modelos corrieron OK hoy, para saber si puedo ir a tomar café tranquilo."*
- *"Quiero ver el log de un modelo que falló, filtrado y legible, sin tener que abrir archivos JSONL a mano."*
- *"Quiero poder re-ejecutar un modelo específico desde el dashboard si falló."*
- *"Quiero que me diga cuánto se demoró cada modelo y si fue más lento que lo normal."*
- *"Si la interfaz PML no llegó a la red, quiero saberlo ANTES de ejecutar."*
- *"Quiero un botón para descargar el reporte del día en PDF/Excel para mandárselo a mi jefe."*
- *"Quiero ver un checklist de lo que tengo que hacer cada día (¿llegó la interfaz? ¿hay parámetros nuevos? ¿está el accdb actualizado?)."*

### 👨‍💼 Supervisor del Practicante
Revisa que el trabajo se haya hecho correctamente, sin necesariamente ejecutar nada.

- *"Como supervisor, quiero ver un calendario con los días que se ejecutó el proceso y su estado (OK/parcial/error), para detectar gaps."*
- *"Quiero comparar los outputs de hoy vs ayer y entender si las variaciones son razonables."*
- *"Quiero saber QUIÉN ejecutó cada día (hostname, usuario, timestamp)."*
- *"Quiero recibir una alerta si el proceso no se ejecutó antes de las 11am."*
- *"Quiero ver si los parámetros cambiaron respecto a la última vez, y qué cambió exactamente."*
- *"Quiero poder ver el histórico de ejecuciones de la última semana con sus duraciones y estados."*
- *"Si hay un error recurrente en un modelo específico, quiero verlo en una vista de tendencia."*

### 🏦 Gerente de Riesgo Financiero
Necesita información de alto nivel, tendencias, y cumplimiento regulatorio.

- *"Como gerente, quiero un dashboard ejecutivo con KPIs: % de ejecuciones exitosas del mes, tendencias de outputs clave, alertas activas."*
- *"Quiero ver la evolución mensual de métricas clave: amortización total por moneda, saldos NMD, tasas de prepago, tasas de mora."*
- *"Quiero poder generar un reporte mensual automático con las variaciones más significativas."*
- *"Quiero saber si algún modelo tiene drift — si sus outputs se están desviando más de lo esperado."*
- *"Quiero poder comparar los outputs de distintos períodos (mes actual vs mes anterior, trimestre actual vs trimestre anterior)."*
- *"Necesito que el dashboard pueda exportar tablas y gráficos para presentaciones al directorio."*
- *"Quiero ver la descomposición de la variación entre días: ¿cuánto se debe a cambios en la cartera vs cambios en parámetros vs cambios en tasas?"*

### 🔍 Auditor Interno
Necesita trazabilidad completa, evidencia de controles, y capacidad de reconstruir cualquier ejecución pasada.

- *"Como auditor, necesito poder reconstruir exactamente qué inputs, parámetros y código se usaron para generar los outputs de cualquier fecha."*
- *"Quiero ver el diff exacto de parámetros entre dos fechas cualesquiera."*
- *"Necesito un log de auditoría inmutable: quién ejecutó qué, cuándo, con qué parámetros, y qué resultados obtuvo."*
- *"Quiero verificar que los outputs en BigQuery coinciden con los archivos Excel locales."*
- *"Necesito poder descargar el paquete completo de una fecha: interfaz PML, access tables, parámetros, outputs — todo lo necesario para reproducir."*
- *"Quiero ver si hubo re-ejecuciones (--force-historico) y por qué."*
- *"Necesito evidencia de que los backups pre-force se crearon correctamente."*
- *"Quiero un trail de cambios en la configuración YAML y en el código de los modelos."*
- *"¿Se puede demostrar que no hubo manipulación post-ejecución de los outputs?"*

### 📋 Auditor Externo / CMF / Regulador
Necesita evidencia formal de gobierno de modelos, controles, y validación.

- *"Como regulador, necesito ver la documentación de cada modelo, su última fecha de validación, y el inventario de modelos activos."*
- *"Quiero ver métricas de estabilidad de los modelos en el tiempo (backtesting)."*
- *"Necesito evidencia de segregación de funciones: ¿quién desarrolla vs quién ejecuta vs quién valida?"*
- *"Quiero acceso a un reporte de gobierno de modelos con: inventario, dueños, frecuencia, última validación, próxima revisión."*
- *"Necesito ver que los datos de entrada están sujetos a controles de calidad."*

### 🔧 Equipo TI / DevOps
Mantiene la infraestructura, monitorea salud del sistema.

- *"Como DevOps, quiero ver el health check del entorno: Python, conda, ODBC, GCP, red, BigQuery."*
- *"Quiero monitorear el espacio en disco, el tamaño del cache, y los archivos temporales."*
- *"Quiero alertas si BigQuery está inaccesible, si la ruta de red cayó, o si las credenciales GCP expiraron."*
- *"Quiero ver métricas de performance: tiempo de carga BQ, tiempo de lectura Access, tiempo de parsing de la interfaz."*
- *"Quiero saber si hay reportes pendientes de sync (cola _pendientes_sync)."*

### 📊 Model Risk Management (MRM) / Validación
Equipo que valida los modelos periódicamente.

- *"Como MRM, quiero ver series de tiempo de los outputs para detectar anomalías o drift."*
- *"Quiero poder hacer backtesting: comparar las predicciones del modelo con los resultados reales."*
- *"Quiero métricas de estabilidad de los parámetros en el tiempo."*
- *"Quiero poder comparar dos versiones de un modelo (si se cambiara el código)."*
- *"Necesito dashboards de sensibilidad: ¿cómo varían los outputs ante cambios en inputs/parámetros?"*

### 📈 Data Engineer
Mantiene la calidad del pipeline de datos.

- *"Quiero ver la lineage de datos: de dónde viene cada input, cómo se transforma, y a dónde va."*
- *"Quiero alertas de calidad: nulos inesperados, tipos de dato incorrectos, duplicados."*
- *"Quiero ver métricas de volumen: ¿cuántas filas tiene cada tabla? ¿ha cambiado dramáticamente?"*
- *"Quiero monitorear el tamaño de las tablas BQ y los costos asociados."*

---

## 2. Centro de Control de Ejecuciones

### 2.1 Vista Diaria — "Mission Control"
- **Semáforo global del día**: ✅ OK / ⚠️ PARCIAL / ❌ ERROR / ⏳ EN CURSO / 🔘 NO EJECUTADO
- **Tarjetas por modelo** (card grid):
  - Estado (color-coded)
  - Duración (con sparkline de últimos 7 días)
  - Timestamp de inicio y fin
  - Botón "Ver log" → abre el log filtrado de ese modelo
  - Botón "Ver output" → preview del Excel de output
  - Indicador de si se cargó a GCP (dly + hist)
- **Timeline visual**: Gantt chart de la ejecución del día mostrando cada modelo como una barra temporal
- **Comparación automática con día anterior**: Indicar con flechas ↑↓ si fue más rápido/lento

### 2.2 Vista Calendario (Mensual)
- Calendario tipo heatmap con colores por estado del día
- Click en un día → detalle completo de esa ejecución
- Indicadores: días sin ejecución, rachas de éxito, patrones de error
- **Mini-KPIs del mes**: % éxito, duración promedio, modelos más problemáticos

### 2.3 Vista Histórica de Ejecuciones
- Tabla filtrable/sorteable con todas las ejecuciones
- Columnas: fecha, status, duración, modelos OK/error, hostname, usuario, alertas
- Exportable a CSV/Excel
- Filtros: rango de fechas, status, modelo específico con error
- Paginación con lazy loading para miles de registros

### 2.4 Ejecución Remota (Avanzado)
- Botón "Ejecutar modelos" con selección (todos, primera vuelta, segunda vuelta, individual)
- Pre-checks antes de ejecutar: ¿interfaz disponible? ¿access actualizado? ¿env OK?
- Live streaming del log durante la ejecución (WebSocket o polling)
- Posibilidad de cancelar ejecución en progreso
- **Nota:** Requiere un backend servidor — complejidad alta, considerar post-MVP

---

## 3. Explorador de Logs

### 3.1 Visor de Logs JSONL
- **Fuente**: `logs/{YYYYMMDD}/modelos.jsonl`
- **Filtros**:
  - Por fecha (date picker)
  - Por modelo (dropdown o multi-select)
  - Por nivel (DEBUG/INFO/WARNING/ERROR/CRITICAL — checkboxes)
  - Por texto libre (búsqueda en `msg`)
  - Por evento especial (snapshot, carga_gcp, error, etc.)
  - Por rango de tiempo dentro del día
- **Vista**: Tabla coloreada por nivel, con columnas expandibles
- **Detalle expandible**: Click en una fila → muestra exception completo, campos extra (sha256, archivo, etc.)
- **Export**: Descargar logs filtrados como CSV, JSONL, o texto plano

### 3.2 Vista Resumen de Logs
- Conteo de mensajes por nivel (pie chart o bar chart)
- Timeline de mensajes (scatter plot: tiempo vs nivel)
- Top 10 mensajes más frecuentes (agrupados por template)
- Detección de patrones de error recurrentes

### 3.3 Comparación de Logs entre Días
- Side-by-side de logs de dos fechas (filtrados por modelo)
- Diff visual: ¿qué mensajes son nuevos? ¿cuáles desaparecieron?
- Útil para debugging: "ayer funcionó, hoy no — ¿qué cambió?"

### 3.4 Alertas desde Logs
- Reglas configurables: "Si aparece ERROR en modelo X más de 3 veces, marcar como alerta"
- Historial de alertas por modelo
- Integración con notificaciones (email, Teams, Slack — futuro)

---

## 4. Gestión de Parámetros y Snapshots

### 4.1 Explorador de Snapshots
- **Fuente**: `snapshots/manifests/{YYYYMMDD}.json` + `snapshots/store/`
- **Vista por fecha**: Qué parámetros usó cada modelo en una fecha dada
- **Vista por modelo**: Histórico de snapshots de un modelo específico
- **Indicador de cambio**: 🆕 si el archivo es nuevo, 🔄 si cambió vs día anterior, ✅ si es idéntico
- **Detalle**: SHA-256, tamaño, timestamp, ruta en store

### 4.2 Diff de Parámetros
- **Comparación entre dos fechas**: Seleccionar fecha A y fecha B
- **Diff visual** (side-by-side o unified):
  - Para JSON: diff estructurado con highlighting de valores que cambiaron
  - Para Excel: tabla comparativa mostrando celdas que difieren (valor viejo vs nuevo)
  - Para ambos: resumen ejecutivo ("En mora_consumo, la tasa base cambió de 3.5% a 3.8%")
- **Timeline de cambios**: Gráfico mostrando cuándo cambió cada parámetro en el tiempo
- **Impacto del cambio**: Vincular cambio de parámetro con variación en output (correlación)

### 4.3 Descarga de Parámetros
- Descargar snapshot de una fecha específica (Excel/JSON original)
- Descargar comparativo como reporte Excel
- Descargar manifiesto completo del día

### 4.4 Gestión de Parámetros (Avanzado — futuro)
- Formulario para editar parámetros directamente (con workflow de aprobación)
- Versionado formal de parámetros (más allá de snapshots)
- Simulación: "¿Qué pasaría si cambio este parámetro?" (what-if analysis)
- Aprobación dual: maker-checker para cambios de parámetros

---

## 5. Observatorio de Inputs

### 5.1 Estado de Inputs del Día
- Checklist visual:
  - ✅ Interfaz PML: disponible, copiada, MD5 verificado
  - ✅ Access BD_Gestion_RL: disponible, copiada
  - ✅ Access BD_Gestion_RM: disponible, copiada
  - ✅ Parámetros: sin cambios / con cambios (detalle)
  - ⚠️ Access PT_Puente: no encontrado (si aplica)
- **Timestamp de llegada**: ¿A qué hora estuvo disponible cada input?
- **Tamaño y row count**: Para detectar archivos truncados o vacíos

### 5.2 Comparación de Inputs entre Días
- **Interfaz PML**:
  - Row count diario (bar chart temporal)
  - Nuevos productos/instrumentos que aparecen/desaparecen
  - Distribución de monedas, tipos, vencimientos
  - Delta de filas: +150 filas respecto a ayer (-32 CLP, +182 CLF)
- **Access Tables**:
  - Row count por tabla
  - Distribución de columnas clave
  - Nuevos registros vs eliminados
- **Detección de anomalías**: Variación >X% en row count → alerta

### 5.3 Profiling de Inputs
- Estadísticas descriptivas de cada input (min, max, mean, nulls, distribución)
- Comparación de profiling entre dos fechas
- Schema drift detection: ¿cambió alguna columna? ¿tipos de datos distintos?
- **Great Expectations-style**: Reglas de calidad que se verifican automáticamente

### 5.4 Trazabilidad de Origen
- Para cada input, mostrar:
  - Ruta de origen (red)
  - Ruta local (cache)
  - Hash de integridad
  - ¿Se usó cache o se leyó fresh?
  - Tiempo de copia/lectura

---

## 6. Analítica de Outputs

### 6.1 Preview de Outputs del Día
- Para cada modelo: preview de las primeras N filas del Excel de output
- Estadísticas resumen: total de filas, suma de amortización, distribución por moneda
- Indicador vs día anterior: ↑↓ por métrica principal

### 6.2 Comparación de Outputs (Día vs Día)
- **Nivel agregado** (lo que ya existe en el dashboard actual, mejorado):
  - SUM(AMORTIZACION) por MONEDA_ORIGEN y CODIGO_PRODUCTO
  - Pero ahora con más métricas: SALDO, TASA, CUOTAS, etc.
  - Y más dimensiones: por plazo remanente, por tramo de vencimiento
- **Nivel detallado**:
  - Registros nuevos (en t pero no en t-1)
  - Registros eliminados (en t-1 pero no en t)
  - Registros modificados (misma clave, distinto valor)
  - Clave de join configurable por modelo (ej: CODIGO_PRODUCTO + MONEDA_ORIGEN + FECHA_VENCIMIENTO)
- **Diff interactivo**: Tabla con highlighting de cambios, filtrable, exportable
- **Variación absoluta y porcentual** por cada métrica

### 6.3 Validación de Outputs
- Reglas de negocio automáticas:
  - Sum of amortización = saldo inicial (check de consistencia)
  - No hay montos negativos donde no debería
  - Fechas de vencimiento coherentes
  - Códigos de producto válidos (vs catálogo)
- **Semáforo de calidad por modelo**: % de reglas cumplidas
- Histórico de calidad (¿se están degradando los outputs?)

### 6.4 Cross-Model Analysis
- Comparación entre modelos que deberían ser consistentes:
  - Prepago Consumo vs Mora Consumo: ¿las carteras son consistentes?
  - NMD vs LC: ¿los saldos cuadran?
- Sanity checks inter-modelo
- Reconciliación de totales contra fuente maestra (si existe)

---

## 7. Tendencias y Series de Tiempo

### 7.1 Dashboard de Tendencias (Nivel Modelo)
- **Métricas de output en el tiempo** (último mes, trimestre, año):
  - Amortización total por modelo
  - Amortización por moneda
  - Saldo remanente
  - Tasa promedio ponderada
  - Prepago esperado (para modelos de prepago)
  - Tasa de mora esperada (para modelos de mora)
  - Duración promedio
- **Gráficos**: Line charts con bandas de confianza, moving averages
- **Detección de anomalías**: Z-score o IQR sobre la serie temporal
- **Descomposición**: Tendencia + estacionalidad + ruido

### 7.2 Dashboard de Tendencias (Nivel Agregado)
- Total de amortización del banco en el tiempo (todos los modelos sumados)
- Composición por tipo de modelo (prepago vs mora vs NMD vs inversiones)
- Composición por moneda a través del tiempo
- **Stacked area charts** mostrando evolución de la composición

### 7.3 Benchmarks de Performance
- **Fuente**: `data/benchmark/historial.jsonl`
- Duración de ejecución por modelo en el tiempo
- Duración total del pipeline en el tiempo
- Detección de degradación de performance
- Correlación performance vs volumen de datos (¿el pipeline escala?)
- Box plot de tiempos por modelo (mediana, P25, P75, outliers)

### 7.4 Tendencias de Parámetros
- Evolución de parámetros clave en el tiempo (de los snapshots)
- Correlación: cambio de parámetro ↔ cambio de output
- Timeline unificada: parámetros + outputs en un solo gráfico

### 7.5 YoY / MoM / WoW Analysis
- Comparación Year-over-Year (si hay datos)
- Month-over-Month con variación porcentual
- Week-over-Week para detectar patrones semanales
- Reportes automáticos mensuales con las variaciones más significativas

---

## 8. Reproducibilidad y Descargas

### 8.1 Paquete de Reproducibilidad por Fecha
- **Objetivo**: Un auditor selecciona una fecha y descarga TODO lo necesario para reproducir
- **Contenido del paquete** (.zip):
  - Interfaz PML (raw .txt o parquet)
  - Access tables (parquet snapshots de cada tabla)
  - Parámetros (snapshot de cada modelo, Excel + JSON)
  - Manifiesto de snapshots
  - Outputs (Excel de cada modelo)
  - Reporte de ejecución (JSON + MD)
  - Log del día (JSONL)
  - Metadata: versión del código (git commit hash), hostname, usuario, env info
  - README explicando el contenido
- **Almacenamiento**: Idealmente en GCS bucket, descargable desde dashboard
- **Retención**: Definir política (30 días? 1 año? indefinido para parámetros?)

### 8.2 Descarga Selectiva
- Descargar solo inputs de una fecha
- Descargar solo outputs de una fecha
- Descargar solo parámetros de una fecha
- Descargar un modelo específico (inputs + params + output)
- Descargar el log de una fecha
- Descargar el reporte de ejecución

### 8.3 Comparativo Exportable
- Exportar la comparación de outputs entre dos fechas como Excel
- Exportar el diff de parámetros como reporte
- Exportar tendencias como CSV para análisis externo

### 8.4 Bucket de Archivado (GCS)
- Subida automática post-ejecución de los inputs cacheados
- Estructura: `gs://bucket/modelos-diarios/{YYYYMMDD}/inputs/`, `outputs/`, `params/`, `logs/`
- Lifecycle policies: nearline después de 30 días, coldline después de 1 año
- **Catálogo en BigQuery**: tabla con metadata de cada archivo archivado (path, hash, fecha, tamaño)

---

## 9. Auditoría y Compliance

### 9.1 Audit Trail
- **Log inmutable** de todas las acciones:
  - Ejecución de modelos (quién, cuándo, qué modelos, resultado)
  - Carga a GCP (qué tablas, cuántas filas, duración)
  - Force-historico (backup creado?, eliminación, re-inserción)
  - Cambios de parámetros (con diff)
  - Cambios de configuración (YAML)
  - Accesos al dashboard (quién consultó qué)
- **Almacenamiento dual**: BigQuery (queryable) + JSONL local (backup)
- **Integridad**: Hash chain (cada registro incluye hash del anterior) — tamper-evident

### 9.2 Reconciliación BQ vs Local
- Comparar registros en BigQuery daily vs Excel local
- Comparar registros en BigQuery historical vs daily
- Alertar discrepancias
- Reporte de reconciliación descargable

### 9.3 Inventario de Modelos
- Lista de todos los modelos con metadata:
  - Nombre, código, descripción
  - Tipo (prepago, mora, NMD, inversiones, etc.)
  - Vuelta (primera/segunda)
  - Dueño (responsable del modelo)
  - Fecha de última validación
  - Próxima revisión programada
  - Estado (activo, en desarrollo, deprecated)
  - Versión del modelo
  - Documentación asociada
- **Cumple con**: SR-11-7 (Fed), SS-1/13 (CMF Chile), ECB Guide to Internal Models

### 9.4 Evidence Pack para Auditoría
- Generación automática de un "evidence pack" para un período:
  - Calendario de ejecuciones
  - Estadísticas de disponibilidad (% días ejecutados OK)
  - Registro de cambios de parámetros
  - Registro de incidentes y resoluciones
  - Métricas de calidad de datos
  - Registro de re-ejecuciones forzadas con justificación
- Formato: PDF consolidado o Excel con múltiples hojas

### 9.5 Segregación de Funciones
- Tracking de roles: quién desarrolla, quién ejecuta, quién valida
- Alertas si la misma persona ejecuta Y valida
- Dashboard de cumplimiento de SoD (Segregation of Duties)

---

## 10. Salud de Infraestructura

### 10.1 Health Dashboard
- **Fuente**: `tools/check_env.py` (14-point diagnostic), ampliado
- Estado en tiempo real:
  - Python/Conda: ✅/❌
  - Dependencias: ✅/❌ (con lista de outdated)
  - ODBC Access: ✅/❌
  - Red (UNC paths): ✅/❌ (con latencia)
  - GCP credenciales: ✅/❌ (con expiración)
  - BigQuery: ✅/❌ (con latencia de query)
  - Espacio en disco: ✅/⚠️/❌ (con gráfico de uso)
  - Cache size: X MB (con botón de limpieza)
- **Histórico de health checks**: trending de cada check en el tiempo

### 10.2 Monitoreo de Recursos
- Tamaño acumulado de logs (`logs/` folder size)
- Tamaño de snapshots (`snapshots/store/` folder size)
- Tamaño de cache (`data/cache/` folder size)
- Tamaño de backups (`backups_historicos/` folder size)
- Tabla BQ sizes y row counts
- Alertas de umbral (>1GB de logs sin limpiar, etc.)

### 10.3 Cola de Retry
- **Fuente**: `reports/_pendientes_sync/`
- Lista de reportes pendientes de sync a BQ
- Botón manual de retry
- Historial de intentos fallidos con error

### 10.4 Network Dependency Map
- Diagrama visual de dependencias:
  - `\\vmdvorak\...` → PML interface
  - `\\vmdvorak\...` → Access databases
  - BigQuery → daily tables
  - BigQuery → historical tables
  - BigQuery → reportes_ejecucion
- Estado actual de cada conexión (live check)
- Latencia de cada hop

---

## 11. Alertas y Notificaciones

### 11.1 Sistema de Alertas
- **Reglas predefinidas**:
  - Ejecución no realizada (deadline configurable, ej: 11am)
  - Ejecución con errores
  - Ejecución significativamente más lenta que promedio (>50%)
  - Output con variación extrema vs día anterior (>X% configurable)
  - Parámetros cambiaron sin documentación
  - Input con row count anómalo
  - BigQuery sync fallido
  - Espacio en disco bajo
  - Credenciales GCP próximas a expirar
- **Reglas custom**: UI para crear reglas sobre cualquier métrica

### 11.2 Canales de Notificación
- In-app (badge/notification bell en el dashboard)
- Email (integración SMTP o SendGrid)
- Microsoft Teams (webhook)
- Slack (webhook)
- Log (siempre, como fallback)

### 11.3 Escalamiento
- Alerta nivel 1: Practicante (fallo de ejecución)
- Alerta nivel 2: Supervisor (fallo no resuelto en 1 hora)
- Alerta nivel 3: Gerente (fallo no resuelto en 4 horas)
- Configurable por tipo de alerta

### 11.4 Historial de Alertas
- Log de todas las alertas emitidas
- Estado: abierta, reconocida, resuelta
- Quién la reconoció, con qué acción
- Tiempo de resolución (SLA tracking)

---

## 12. Calidad de Datos

### 12.1 Data Quality Scorecard
- Score global por día (0-100%)
- Score por dimensión:
  - **Completitud**: % de campos no-null
  - **Consistencia**: Reglas de negocio cumplidas
  - **Oportunidad**: ¿Llegaron los datos a tiempo?
  - **Unicidad**: ¿Hay duplicados inesperados?
  - **Validez**: ¿Valores dentro de rangos esperados?
- Trending del score en el tiempo

### 12.2 Reglas de Calidad
- Predefinidas por modelo:
  - Prepago: tasa entre 0% y 100%, amortización > 0
  - Mora: tasa entre 0% y 100%, sin negativos
  - NMD: saldos cuadran con totales
  - Inversiones: instrumentos válidos vs catálogo
- Custom: UI para definir reglas SQL-like
- Ejecución automática post-modelo

### 12.3 Linaje de Datos (Data Lineage)
- Diagrama visual:
  ```
  PML Interface (.txt)
    → cache (parquet)
      → Modelo Prepago Consumo
        → Excel output
          → BigQuery daily
            → BigQuery historical
  
  Access BD_Gestion_RL
    → cache (parquet)
      → Modelo NMD
        → Excel output
          → BigQuery daily
  ```
- Click en cualquier nodo → detalle de transformaciones
- Impacto analysis: si cambia un input, ¿qué outputs se afectan?

---

## 13. Gobierno de Modelos (Model Risk)

### 13.1 Inventario de Modelos
- Catálogo completo con metadata (ver 9.3)
- Clasificación por materialidad/riesgo
- Ciclo de vida: desarrollo → validación → producción → retiro
- Due dates para re-validación

### 13.2 Model Performance Monitoring
- **Backtesting** (si hay datos realizados):
  - Prepago: tasa predicha vs tasa real
  - Mora: tasa predicha vs tasa real
  - Gráficos de calibración (predicted vs actual)
  - PSI (Population Stability Index) del input
  - CSI (Characteristic Stability Index) de variables clave

### 13.3 Sensitivity Analysis Dashboard
- Seleccionar modelo + parámetro
- Slide bar para variar el parámetro
- Ver output en tiempo real (requiere re-ejecución parcial o pre-cálculo)
- Tablas de sensibilidad: ΔOutput / ΔParámetro
- Tornado charts: ¿qué parámetro tiene más impacto?

### 13.4 Challenger Models
- Soporte para ejecutar modelo A vs modelo B (champion vs challenger)
- Comparación de outputs
- Tracking de performance relativa en el tiempo
- Útil para validación y para transición a nuevos modelos

---

## 14. UX y Arquitectura del Dashboard

### 14.1 Multi-página
Propuesta de estructura de páginas:

```
📊 Dashboard
├── 🏠 Home / Mission Control
│   ├── Semáforo del día
│   ├── Ejecuciones recientes (últimos 5 días)
│   └── Alertas activas
│
├── 📅 Ejecuciones
│   ├── Vista Calendario
│   ├── Detalle por Día
│   └── Histórico (tabla filtrable)
│
├── 📋 Logs
│   ├── Explorador
│   ├── Resumen por Día
│   └── Comparador (día vs día)
│
├── ⚙️ Parámetros
│   ├── Snapshots por Fecha
│   ├── Diff de Parámetros
│   └── Historial de Cambios
│
├── 📥 Inputs
│   ├── Estado del Día
│   ├── Comparación entre Días
│   └── Profiling / Calidad
│
├── 📤 Outputs
│   ├── Preview del Día
│   ├── Comparación (t vs t-1)
│   ├── Cross-Model Analysis
│   └── Validación / Calidad
│
├── 📈 Tendencias
│   ├── Por Modelo
│   ├── Agregado
│   ├── Benchmarks de Performance
│   └── YoY/MoM Analysis
│
├── 🔍 Auditoría
│   ├── Audit Trail
│   ├── Reconciliación BQ vs Local
│   ├── Inventario de Modelos
│   └── Evidence Pack
│
├── 💾 Reproducibilidad
│   ├── Paquete por Fecha
│   ├── Descargas Selectivas
│   └── Estado del Bucket
│
├── 🏥 Salud
│   ├── Health Check
│   ├── Recursos / Espacio
│   ├── Cola de Retry
│   └── Mapa de Dependencias
│
├── 🔔 Alertas
│   ├── Activas
│   ├── Historial
│   └── Configuración de Reglas
│
└── ⚙️ Configuración
    ├── Usuarios y Roles
    ├── Umbrales de Alerta
    ├── Retención / Limpieza
    └── Conexiones Externas
```

### 14.2 Autenticación y Roles
- Login por usuario (aunque sea básico: user/pass en config o LDAP)
- Roles:
  - **Viewer**: Solo lectura de dashboards
  - **Operator**: Puede ejecutar modelos, descargar
  - **Admin**: Puede configurar, cambiar parámetros
  - **Auditor**: Acceso especial a audit trail y evidence packs
- Session management con timeout

### 14.3 Tecnología
- **Framework**: Streamlit (ya en uso) — excelente para MVP y prototipado rápido
  - Pro: Ya conocido, rápido de desarrollar, integración nativa con pandas/plotly
  - Con: Limitaciones de estado, no escala a muchos usuarios
- **Alternativas futuras**: 
  - Dash (Plotly) — más control sobre layout
  - FastAPI + React — máxima flexibilidad, requiere más desarrollo
  - Grafana — ideal para monitoreo, menos para análisis interactivo
  - Metabase/Superset — ideal para BI sobre datos en BQ

### 14.4 Responsiveness
- Diseño para pantalla de escritorio (principal)
- Versión mobile-friendly para alertas y status rápido (supervisor en reunión)
- Modo oscuro / modo claro

### 14.5 Performance
- Caching agresivo de queries BQ (st.cache_data con TTL)
- Lazy loading de datos pesados
- Paginación server-side para tablas grandes
- Pre-cómputo de métricas de tendencia (batch job nocturno)

---

## 15. Ideas Moonshot

Estas son ideas más ambiciosas, quizás para un futuro lejano, pero que vale la pena documentar.

### 15.1 🤖 Asistente AI Integrado
- Chat integrado en el dashboard: "¿Por qué falló mora_consumo ayer?"
- El chatbot tiene acceso a logs, reports, diffs — responde en lenguaje natural
- Puede sugerir acciones: "El error fue timeout de Access. Prueba re-ejecutar a las 8am cuando hay menos carga."
- Resumen ejecutivo diario generado por LLM: "Hoy se ejecutaron 10 modelos exitosamente. El modelo NMD fue 23% más lento. Los outputs de mora consumo variaron +5.2% en CLP."

### 15.2 📱 Bot de Teams/Slack
- Mensaje automático cada mañana: "✅ Modelos ejecutados OK. Duración: 4m 12s. Ver detalle: [link]"
- Comando: `/modelos status` → resumen del día
- Comando: `/modelos diff prepago_consumo` → variación vs ayer
- Comando: `/modelos logs mora_consumo ERROR` → últimos errores

### 15.3 🔮 Predicción de Fallas
- ML sobre el historial de ejecuciones para predecir fallos
- Features: día de la semana, tamaño de inputs, latencia de red, hora de ejecución
- Alerta preventiva: "Probabilidad alta de fallo en NMD — la tabla Access tiene 3x más registros de lo normal"

### 15.4 📊 Dashboard Público (Data Room)
- Versión limitada del dashboard para compartir con contrapartes externas
- Solo outputs agregados, sin datos sensibles
- Acceso por token con expiración
- Útil para auditorías externas sin dar acceso al sistema completo

### 15.5 🔄 Continuous Validation
- En vez de validación periódica (cada 6 meses), validación continua:
  - Monitoreo automático de drift en inputs y outputs
  - Alerta cuando el modelo se sale de su "zona de confort"
  - Backtesting automático cuando hay datos realizados disponibles
  - Score de confianza del modelo que se actualiza diariamente

### 15.6 📊 Scenario Engine
- "¿Qué pasa si la tasa de referencia sube 100bp?"
- Pre-calcular escenarios base, adverso, severo
- Útil para ICAAP, ILAAP, stress testing regulatorio
- Integración con parámetros de escenarios del regulador

### 15.7 🗺️ Mapa de Calor de la Cartera
- Visualización geoespacial (si hay datos de región/sucursal)
- Concentración de riesgo por región
- Evolución temporal de la concentración

### 15.8 📉 Explicabilidad de Variaciones
- Cuando el output cambia significativamente, descomponer automáticamente:
  - % debido a cambios en la cartera (nuevos préstamos, vencimientos)
  - % debido a cambios en parámetros
  - % debido a cambios en tasas de mercado
  - % residual (no explicado)
- "Waterfall chart" de la variación

### 15.9 🔗 API REST
- Exponer las funcionalidades del dashboard como API
- Endpoints: GET /ejecuciones, GET /outputs/{fecha}/{modelo}, GET /logs, etc.
- Permite integración con otros sistemas del banco
- Documentación Swagger/OpenAPI automática

### 15.10 📦 Modelo como Servicio (MaaS)
- Encapsular cada modelo como un servicio independiente
- API: POST /ejecutar/{modelo} con payload de inputs
- Desacople total de la infraestructura local
- Pre-requisito: containerización (Docker)

### 15.11 🧪 Sandbox/Playground
- Ambiente aislado donde poder ejecutar modelos con inputs modificados
- "¿Qué output tendría prepago_consumo si uso los parámetros de hace 3 meses con los inputs de hoy?"
- No afecta producción, no sube a BQ
- Útil para MRM y para análisis de sensibilidad

### 15.12 📊 Executive Summary Auto-Generated
- Cada fin de mes, generar automáticamente un reporte que incluya:
  - Resumen de ejecuciones (días OK, parciales, error)
  - Tendencias de los KPIs principales
  - Cambios de parámetros del período
  - Incidentes y resoluciones
  - Gráficos clave (amortización, mora, prepago por moneda)
  - Firmable digitalmente como evidencia

---

## Priorización Sugerida (para discusión)

### 🟢 Quick Wins (Alto valor, baja complejidad) — Sprint próximo
1. **Explorador de Logs con filtros** — ya tenemos JSONL, solo es UI
2. **Vista calendario de ejecuciones** — ya tenemos reporte_ejecucion.json
3. **Diff de parámetros entre fechas** — ya tenemos snapshots/manifests
4. **Detalle de ejecución por día** — ya tenemos reportes JSON + MD
5. **Benchmark trending** — ya tenemos historial.jsonl

### 🟡 Medium Effort (Alto valor, complejidad media) — 2-3 sprints
6. **Comparación de outputs mejorada** (más métricas, nivel detallado)
7. **Tendencias mensuales de outputs** (queries a BQ historical)
8. **Health dashboard ampliado** (reutilizar check_env)
9. **Descarga selectiva de inputs/outputs por fecha**
10. **Alertas básicas** (in-app, basadas en reglas predefinidas)
11. **Comparación de inputs entre días** (row count, distribuciones)

### 🔴 High Effort (Alto valor, alta complejidad) — Roadmap
12. **Paquete de reproducibilidad completo** (GCS bucket)
13. **Evidence pack para auditoría**
14. **Data Quality Scorecard**
15. **Autenticación y roles**
16. **Notificaciones externas** (email, Teams)
17. **Backtesting / Model Performance**
18. **Scenario Engine**
19. **AI Assistant**

---

## Decisiones de Diseño (Resueltas 2026-03-12)

- [x] **Framework MVP**: Streamlit multi-page es suficiente. Sin migración por ahora.
- [x] **Fuente de datos principal**: BigQuery (queries en vivo con caching). Archivos locales solo como complemento para datos que aún no están en BQ (logs JSONL, snapshots, health checks).
- [x] **Almacenamiento de inputs para reproducibilidad**: Estrategia de 3 capas:
  1. **GCS** — gold standard, fuente de verdad, persistencia a largo plazo
  2. **Ruta UNC (red)** — acceso compartido para el equipo extendido (ya en uso)
  3. **Caché local** — para ejecución rápida, se sincroniza periódicamente a GCS/UNC
  - Flujo: ejecución lee de caché local → post-ejecución sube a GCS → periódicamente se valida vs UNC
- [x] **Hosting**: Local en cada PC, consumiendo datos de BQ. Esto evita burocracia de permisos/máquinas y da actualizaciones near-real-time. Cada usuario corre `streamlit run` en su máquina y ve los mismos datos porque la fuente es BQ compartida.
  - *Implicancia*: No hay un dashboard "siempre encendido". Cada sesión es efímera. Considerar en futuro despliegue centralizado (Cloud Run, VM compartida).
- [x] **Autenticación**: Diferida. No es necesaria para MVP. Todos los usuarios con acceso al repo y credenciales GCP pueden ver todo. Se implementará cuando haya hosting centralizado.
- [x] **Histórico disponible**: ~3 meses en BQ con inconsistencias y lagunas. Paso a producción de primeros modelos fue hace ~1 mes. El dashboard debe ser tolerante a datos faltantes (no asumir serie continua).
  - *Implicancia para tendencias*: Mostrar lo que hay, con indicadores de "gap" en días sin datos. No extrapolar.
  - *Oportunidad*: Feature futura de carga retroactiva de resultados históricos para llenar gaps.
- [x] **GUI tkinter**: Coexisten. No deprecar la GUI tkinter — el gerente la usa y le gusta. El dashboard es un complemento de observabilidad/analítica, la GUI es para ejecución operativa. Cuando el dashboard demuestre su valor, se evaluará convergencia natural.
  - *Nota*: Eventualmente, si el dashboard incorpora ejecución remota (moonshot 2.4), podría reemplazar la GUI orgánicamente.

---

## Notas Técnicas

### Datos ya disponibles para el dashboard (hoy):
| Fuente | Ubicación | Formato | Uso principal |
|--------|-----------|---------|---------------|
| Logs de ejecución | `logs/{YYYYMMDD}/modelos.jsonl` | JSONL | Log Explorer |
| Reportes de ejecución | `reports/{YYYYMMDD}/reporte_ejecucion.json` | JSON | Mission Control, Calendario |
| Reportes Markdown | `reports/{YYYYMMDD}/reporte_ejecucion.md` | MD | Vista rápida |
| Benchmark history | `data/benchmark/historial.jsonl` | JSONL | Performance trending |
| Snapshot manifests | `snapshots/manifests/{YYYYMMDD}.json` | JSON | Param diffs, audit |
| Snapshot files | `snapshots/store/{modelo}/{hash}.ext` | Excel/JSON | Descarga de params |
| Outputs Excel | `RF_Modelo_*/modelo_output.xlsx` | Excel | Preview, comparación |
| Outputs BQ daily | `report_{modelo}_dly` | BQ table | Comparación, tendencias |
| Outputs BQ hist | `report_{modelo}_hist` | BQ table | Tendencias largas |
| Reportes BQ | `reportes_ejecucion` | BQ table | Calendario remoto |
| Health check | `reports/health_check.json` | JSON | Health dashboard |
| Cache metadata | `data/cache/*.meta.json` | JSON | Input tracking |
| Pending sync | `reports/_pendientes_sync/` | JSON | Retry queue |
| Inversiones CSV | `RF_Modelo_Inversiones/*.CSV` | CSV | Output history |

### Stack técnico actual:
- **Streamlit** para dashboard (ya funcional con 1 page)
- **BigQuery** como data warehouse
- **Python 3.11** + conda
- **pandas** para manipulación de datos
- **plotly** para gráficos (implícito via Streamlit)
- **xlsxwriter** para Excel output

---

> **Siguiente paso:** Priorizar las features, definir MVP, y comenzar a implementar las Quick Wins que mayor impacto tengan para cada tipo de usuario.
