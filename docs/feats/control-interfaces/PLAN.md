# F26 Fase 5+: Control Exploratorio de Interfaces PML (GCP y CMR)

> **Tamano:** L (~5d) . **Asignado:** @vlandaetat . **Sprint:** S3-2026  
> **Rama:** `feature/control-interfaces`  
> **Feature padre:** F26 (Sistema de Reportes Email Multi-Tipo)  
> **Fecha creacion plan:** 2026-03-30  
> **Reemplaza:** `PROCESOS_DIARIOS_MODELOS/main.py` + macros VBA de `.xlsm`

---

## 1. Contexto y motivacion

### Que existe hoy (sistema legacy en OneDrive)

El proceso actual vive en `PROCESOS_DIARIOS_MODELOS/main.py` (fuera de este
repo) y usa:

1. **`schedule`** para polling a las 09:30 (CMR) y 10:02 (GCP)
2. **`lector_interfaces_automatico.py`** que:
   - Hace polling cada 5 min (timeout 3h) sobre ruta UNC
     `\\vmdvorak\Riesgo Financiero Folder\RRFF-GCP\Cartera\input`
   - Lee 2 archivos CSV (fecha_t y fecha_t-1) con pandas
   - Concatena y agrupa por columnas clave (suma AMORTIZACION e INTERES)
   - Escribe resultado en hoja "BD" de un `.xlsm`
   - Ejecuta macro VBA `enviar_correo_Outlook` via COM (DispatchEx)
3. **Macro VBA** dentro del `.xlsm` que:
   - Genera tabla comparativa con MONTO T vs MONTO T-1
   - Calcula DIFERENCIA (MM$) y Delta %
   - Aplica formato condicional (colores rojo/verde/amarillo)
   - Envia correo a `riesgofinanciero@bancofalabella.cl` via Outlook

### Problemas del sistema actual

- **Dependencia de macro VBA:** logica de negocio escondida en `.xlsm`
- **Sin conteo de registros:** solo reporta sumas, no detecta filas faltantes
- **Colores mal calibrados:** umbrales fijos no reflejan la volatilidad
  natural de cada producto (DAP no es igual que DAPM)
- **Sin diagnostico de anomalias:** no explica POR QUE cambio un monto
- **Proceso aislado:** no se integra con el pipeline de modelos diarios
- **Sin modo manual:** si falla, hay que re-ejecutar todo el script

### Que queremos

Migrar esta funcionalidad completa a `bfa-cl-modelos-diarios`:
- **Reemplazar** el `main.py` del OneDrive completamente
- **Eliminar** dependencia de macros VBA para generacion de reporte y envio
- **Agregar** conteo de registros como control adicional
- **Definir** umbrales de tolerancia por producto (no one-size-fits-all)
- **Detectar** automaticamente archivos en ruta UNC (con mecanismo robusto)
- **Modo manual** via boton en dashboard Streamlit
- **Integrar** con infraestructura existente (email_report.py, cache_tablas.py)

---

## 2. Arquitectura propuesta

```
config/config_rutas_ext_y_archivos.yaml
    control_interfaces:                    <-- nueva seccion
        enabled: true
        ruta_unc_base: \\vmdvorak\...\input
        destinatarios: [riesgofinanciero@bancofalabella.cl]
        destinatarios_editable: true
        modo: send
        horario_esperado_cmr: "09:00"
        horario_esperado_gcp: "10:00"
        timeout_alerta_minutos: 90        <-- alerta si no aparece a las 10:30
        polling_intervalo_segundos: 300
        backup:
            enabled: true                 <-- configurable, desactivable
            ruta_destino_gcp: ...
            ruta_destino_cmr: ...
        umbrales: ...                     <-- por producto, ver seccion 5
        interfaces:
            gcp:
                patron: "ProductosMercadoLiquidezGCP{fecha}.txt"
                patron_backup: "ProductosMercadoLiquidezGCP{fecha}_Backup.txt"
                ...
            cmr:
                patron: "ProductosMercadoLiquidezCMR{fecha}.txt"
                ...

core/
    control_interfaces.py                  <-- NUEVO: modulo principal
    email_report.py                        <-- extender con tipo chequeo_interfaces

dashboard/
    pages/
        7_Control_Interfaces.py            <-- NUEVA pagina Streamlit
```

### Flujo de datos

```
Ruta UNC (.txt)
    |
    v
[1. Watcher/Polling] -- detecta disponibilidad de archivos
    |
    v
[2. Copia Local] -- data/cache/raw/interfaces/ (con MD5, metadata JSON)
    |
    v
[3. Lectura + Analisis] -- pandas: agrupacion, conteo, comparacion t vs t-1
    |
    v
[4. Validacion Umbrales] -- por producto, genera alertas con severidad
    |
    v
[5. Diagnostico Anomalias] -- si delta > umbral: buscar registros nuevos/vencidos
    |
    v
[6. Generacion Reporte] -- HTML con tablas, charts PNG (plotly), Excel adjunto
    |
    v
[7. Envio Email] -- via Outlook COM (reutiliza _enviar_outlook de email_report.py)
```

---

## 3. Archivos PML - Estructura detallada

### Estructura real de columnas (verificado 2026-03-30)

Ambos archivos (GCP y CMR) comparten la misma estructura de 37 columnas.
CMR tiene 1 columna adicional: `ORIGEN` (38 total).

| # | Columna | Usada en agrupacion | Usada en analisis |
|---|---------|---------------------|-------------------|
| 0 | FECHA_PROCESO | si (ambos) | si |
| 1 | SISTEMA | si (GCP) | si |
| 2 | CODIGO_EMPRESA | no | no |
| 3 | OPERACION | no | no |
| 4 | COD_ACT_PAS | no | no |
| 5 | MONEDA_ORIGEN | si (GCP) | si |
| 6 | MONEDA_COMPENSACION | no | no |
| 7 | COMPENSACION | no | no |
| 8 | CODIGO_PRODUCTO | si (CMR, legacy) | si |
| 9 | CODIGO_SUBPRODUCTO | si (ambos) | si |
| 10 | DESTINOCREDITO | no | no |
| 11 | FECHA_CREACION | no | no |
| 12 | NUMERO_CUOTA | no | no |
| 13 | FECHA_INICIO_CUOTA | no | no |
| 14 | **FECHA_VENCIMIENTO_CUOTA** | no | **si (diagnostico anomalias)** |
| 15 | FECHA_PAGO | no | no |
| 16 | FECHA_REPRICING | no | no |
| 17 | **AMORTIZACION** | no | **si (suma = Capital)** |
| 18 | **INTERES** | no | **si (suma = Interes)** |
| 19 | INTERES_DEVENGADO | no | no |
| 20 | VP_AMORTIZACION | no | no |
| 21 | VP_INTERES | no | no |
| 22 | FACTOR_DE_RIESGO | no | no |
| 23 | TIPO_CUOTA | no | no |
| 24 | AREA_NEGOCIO | no | no |
| 25 | CODIGO_EJECUTIVO | no | no |
| 26 | CODIGO_ESTRATEGIA | no | no |
| 27 | CLASIFICACION_CONTABLE | no | no |
| 28 | TIPO_TASA | no | no |
| 29 | INDEXADOR | no | no |
| 30 | TASA | no | no |
| 31 | TASA_CF | no | no |
| 32 | SPREAD | no | no |
| 33 | MAYORISTAMINORISTA | no | posible (vistas) |
| 34 | MARCA_CUMPLIMIENTO | no | no |
| 35 | EMPRESA_RELACIONADA | no | no |
| 36 | MODELO_PERFIL | no | no |
| 37 | ORIGEN (solo CMR) | no | no |

**Formato:** CSV con `sep=';'`, `decimal=','`.

### GCP: `ProductosMercadoLiquidezGCP{YYYYMMDD}.txt`

**Verificado con archivo 20260327: 327,738 filas.**

**Valores unicos de SISTEMA (14):**
BONOS (104), CCT (13), COM (91), CRC (17128), CRUGE (110484), CVI (1),
DAP (166448), DAPM (73), DVA (881), HIP (27128), IMV (16), PASHIS (195),
REC (4925), SEL (251)

**Monedas (codigos numericos):**
- `999` = CLP
- `998` = CLF
- `13` = USD

El reporte traduce estos codigos a los nombres legibles CLP/CLF/USD.

**Distribucion SISTEMA x MONEDA (20260327):**

| SISTEMA | 13 (USD) | 998 (CLF) | 999 (CLP) |
|---------|----------|-----------|----------|
| BONOS | - | 74 | 30 |
| CCT | - | - | 13 |
| COM | - | - | 91 |
| CRC | - | - | 17,128 |
| CRUGE | - | 110,484 | - |
| CVI | - | - | 1 |
| DAP | 800 | 3,374 | 162,274 |
| DAPM | 27 | - | 46 |
| DVA | - | - | 881 |
| HIP | - | 27,128 | - |
| IMV | - | - | 16 |
| PASHIS | - | 195 | - |
| REC | - | - | 4,925 |
| SEL | - | - | 251 |

**Agrupacion principal:** `SISTEMA, MONEDA_ORIGEN` (sumando AMORTIZACION e INTERES)

El reporte GCP muestra una tabla pivot: filas = SISTEMA, columnas = moneda
(CLP, CLF, USD), valores = suma de AMORTIZACION (Capital) e INTERES.
Los SISTEMA que no tienen registros en alguna moneda aparecen vacios.

**Seccion VISTAS del reporte (investigado):**
La seccion de Vistas del correo proviene de los SISTEMA `CCT` y `CVI`:

| Fila del reporte | SISTEMA | CODIGO_SUBPRODUCTO | MONEDA_ORIGEN |
|---|---|---|---|
| Cta Cte (201 Personas) | CCT | 201 | 999 (CLP) |
| Cta Vista (202 Personas) | CVI | 202 | 999 (CLP) |
| Cta Cte (501 Mayorista) | CCT | 501 | 999 (CLP) |

El SubTotal y Total del reporte son sumas calculadas:
- SubTotal = CCT(201) + CVI(202)
- Total = SubTotal + CCT(501)

> **Nota:** La seccion VISTAS no es esencial para el core de la feature.
> Se implementara despues de que el analisis principal este funcionando.
> CCT y CVI se excluyen del reporte principal de CAPITAL/INTERES para
> evitar duplicidad (se muestran solo en la seccion VISTAS).

**Nota backup:** El archivo t-1 se lee como `{fecha_t1}_Backup.txt`.

### CMR: `ProductosMercadoLiquidezCMR{YYYYMMDD}.txt`

**Verificado con archivo 20260327: 50,250 filas.**

**Valores unicos:**
- SISTEMA: solo `TC` (1 valor)
- CODIGO_PRODUCTO: solo `TC` (1 valor)
- MONEDA_ORIGEN: solo `999` (CLP) -- CMR es 100% pesos chilenos
- CODIGO_SUBPRODUCTO: 30 valores unicos

**CODIGO_SUBPRODUCTO (30 valores):**
Avance, Avance_Incumplimiento, Avance_Incumplimiento_RENEGOCIADO,
Avance_Mora, Avance_Mora_RENEGOCIADO, Avance_RENEGOCIADO,
Compra, Compra_Incumplimiento, Compra_Incumplimiento_RENEGOCIADO,
Compra_Mora, Compra_Mora_RENEGOCIADO, Compra_RENEGOCIADO,
Revolving_Facturado, Revolving_Facturado_RENEGOCIADO,
Revolving_Incumplimiento_Facturado, Revolving_Incumplimiento_Facturado_RENEGOCIADO,
Revolving_Incumplimiento_Utilizado, Revolving_Incumplimiento_Utilizado_RENEGOCIADO,
Revolving_Mora_Facturado, Revolving_Mora_Facturado_RENEGOCIADO,
Revolving_Mora_Utilizado, Revolving_Mora_Utilizado_RENEGOCIADO,
Revolving_Utilizado, Revolving_Utilizado_RENEGOCIADO,
Super Avance, Super Avance_Incumplimiento, Super Avance_Incumplimiento_RENEGOCIADO,
Super Avance_Mora, Super Avance_Mora_RENEGOCIADO, Super Avance_RENEGOCIADO

**Agrupacion:** `CODIGO_SUBPRODUCTO` (ya que SISTEMA=TC y MONEDA=999 son constantes)
En el reporte, las filas son directamente los CODIGO_SUBPRODUCTO.
Los productos base (TC, Avance, Compra, Revolving, Super Avance) son filas-resumen
que suman los subproductos correspondientes.

**FECHA_VENCIMIENTO_CUOTA:** Confirmada presente. Formato YYYYMMDD.
Ejemplo: 20260320. Disponible para diagnostico de anomalias en ambos archivos.

---

## 4. Fases de implementacion

### Fase 5.1 -- Config YAML + esqueleto `control_interfaces.py`

**Objetivo:** Seccion YAML nueva + modulo base con dataclasses.

**Cambios:**
- Agregar seccion `control_interfaces:` al YAML con toda la config
- Crear `core/control_interfaces.py` con:
  - `InterfazConfig` (dataclass por interfaz: GCP o CMR)
  - `ControlInterfacesConfig` (dataclass global)
  - `cargar_config_interfaces()` -- lee del YAML
  - `ResultadoAnalisis` (dataclass con DataFrame resultado, alertas, metadata)

**Archivos:**
- `config/config_rutas_ext_y_archivos.yaml`
- `core/control_interfaces.py` (nuevo)

### Fase 5.2 -- Deteccion de archivos + copia local

**Objetivo:** Mecanismo robusto de espera y copia local de archivos PML.

**Logica (complementaria a F14/cache_tablas.py):**

1. Verificar accesibilidad de ruta UNC (preflight)
2. Verificar si archivo del dia existe en ruta UNC
3. Verificar si ya existe copia local en `data/cache/raw/interfaces/`
4. Si existe local: comparar MD5 con red
   - Si difiere: **WARNING GRANDE** ("Archivo cambio en red desde la ultima copia")
   - Re-copiar con versionamiento (v{HHMMSS})
5. Si no existe local: copiar de red a local con metadata JSON
6. Repetir para ambos archivos necesarios (fecha_t y fecha_t-1)

**Funciones:**
- `verificar_disponibilidad(tipo: str, fecha: date) -> dict` -- estado de cada archivo
- `copiar_archivos_a_local(tipo: str, fecha: date) -> tuple[Path, Path]` -- retorna rutas locales
- `verificar_integridad_local(tipo: str, fecha: date) -> bool` -- compara MD5

**Archivos:**
- `core/control_interfaces.py`

### Fase 5.3 -- Analisis exploratorio (reemplazo de VBA)

**Objetivo:** Toda la logica de agrupacion, comparacion y conteo en Python puro.

**Analisis para GCP:**

```python
# Lectura
df_t = pd.read_csv(ruta_t, sep=';', decimal=',', ...)
df_t1 = pd.read_csv(ruta_t1, sep=';', decimal=',', ...)

# Agrupacion (Capital = AMORTIZACION, Interes = INTERES)
# Por SISTEMA y MONEDA_ORIGEN
agrupado_t = df_t.groupby(["SISTEMA", "MONEDA_ORIGEN"]).agg(
    CAPITAL=("AMORTIZACION", "sum"),
    INTERES=("INTERES", "sum"),
    REGISTROS=("AMORTIZACION", "count"),
).reset_index()

# Merge t vs t-1
comparacion = pd.merge(agrupado_t, agrupado_t1,
    on=["SISTEMA", "MONEDA_ORIGEN"],
    suffixes=("_T", "_T1"), how="outer").fillna(0)

# Diferencias
comparacion["DIFF_CAPITAL"] = comparacion["CAPITAL_T"] - comparacion["CAPITAL_T1"]
comparacion["DIFF_INTERES"] = comparacion["INTERES_T"] - comparacion["INTERES_T1"]
comparacion["DIFF_REGISTROS"] = comparacion["REGISTROS_T"] - comparacion["REGISTROS_T1"]
comparacion["PCT_CAPITAL"] = ...  # variacion porcentual
comparacion["PCT_INTERES"] = ...
```

**Analisis para CMR:**
- Misma logica pero agrupado por `CODIGO_PRODUCTO, CODIGO_SUBPRODUCTO`
- Fila del reporte = concatenacion: `{CODIGO_PRODUCTO}_{CODIGO_SUBPRODUCTO}`
  si CODIGO_SUBPRODUCTO no es vacio, sino solo `CODIGO_PRODUCTO`

**Analisis adicional: Conteo de registros**
- Conteo total de filas por grupo
- Diferencia absoluta y porcentual de conteo entre t y t-1
- Alerta si el conteo cambia mas de X% (configurable)

**Funciones:**
- `analizar_interfaz_gcp(ruta_t, ruta_t1) -> ResultadoAnalisis`
- `analizar_interfaz_cmr(ruta_t, ruta_t1) -> ResultadoAnalisis`
- `_agrupar_y_comparar(df_t, df_t1, cols_grupo, ...) -> pd.DataFrame`

**Archivos:**
- `core/control_interfaces.py`

### Fase 5.4 -- Umbrales de tolerancia por producto

**Objetivo:** Clasificar cada diferencia como NORMAL, WARNING o CRITICAL
segun el producto.

Ver **seccion 5** de este documento para especificacion detallada.

**Funciones:**
- `evaluar_umbrales(comparacion: pd.DataFrame, tipo: str) -> pd.DataFrame`
  -- agrega columnas `SEVERIDAD_CAPITAL`, `SEVERIDAD_INTERES`
- `_obtener_umbral(producto: str, tipo: str) -> dict` -- lee del YAML

**Archivos:**
- `core/control_interfaces.py`
- `config/config_rutas_ext_y_archivos.yaml`

### Fase 5.5 -- Diagnostico automatico de anomalias

**Objetivo:** Cuando un producto excede el umbral, intentar explicar por que.

**Logica para DAPM (ejemplo):**
1. Delta > umbral -> activar diagnostico
2. Buscar en df_t registros con AMORTIZACION individual > P99 de df_t1
   (registro nuevo muy grande que no estaba ayer)
3. Buscar en df_t1 registros con FECHA_VENCIMIENTO_CUOTA entre t-1 y t
   que no aparecen en df_t (vencimiento de deposito grande)
4. Generar texto explicativo:
   - "Posible causa: N registros nuevos con monto > X MM$ en DAPM"
   - "Posible causa: M registros vencidos (vct entre t-1 y t)"

**Nota:** Esta fase es opcional/incremental. Puede ser placeholder en v1
y refinarse iterativamente. FECHA_VENCIMIENTO_CUOTA **confirmada presente**
en ambos archivos (GCP y CMR), formato YYYYMMDD.

**Funciones:**
- `diagnosticar_anomalia(df_t, df_t1, producto, moneda) -> str | None`

**Archivos:**
- `core/control_interfaces.py`

### Fase 5.6 -- Generacion de reporte HTML + charts + Excel

**Objetivo:** Replicar y mejorar el formato de los correos actuales.

**Formato del email GCP (basado en screenshot):**

```
Asunto: Comparacion Interfaz de Datos al {fecha_t}

[CAPITAL]
+---------+--------+--------+---------+------+   (por moneda: CLP, CLF, USD)
| {fecha} | MONTO T| MONTO T-1| DIFF (MM$)| D% |
+---------+--------+--------+---------+------+
| BONOS   | ...    | ...    | ...     | 0%   |
| CCT     | ...    | ...    | ...     | 0%   |
| ...     |        |        |         |      |
+---------+--------+--------+---------+------+

[INTERES]
(misma estructura)

[VISTAS]
Cta Cte (201 Personas)  | ... | ... | ... | ...
Cta Vista (202 Personas)| ... | ... | ... | ...
SubTotal                | ... | ... | ... | ...
Cta Cte (501 Mayorista) | ... | ... | ... | ...
Total                   | ... | ... | ... | ...

[CONTEO DE REGISTROS]  <-- NUEVO
+---------+--------+--------+---------+
| {fecha} | REG T  | REG T-1| DIFF    |
+---------+--------+--------+---------+
| BONOS   | 12,345 | 12,300 | +45     |
| ...     |        |        |         |
+---------+--------+--------+---------+

Fecha Proceso (T-1): {fecha_t}  (con fecha real, no "t")
Fecha Proceso (T-2): {fecha_t1}
```

**Mejoras sobre el formato actual:**
1. **Colores inteligentes** basados en umbrales por producto (no fijos)
2. **Conteo de registros** como seccion nueva
3. **Indicadores de severidad** (iconos o badges: OK, WARNING, CRITICAL)
4. **Notas de diagnostico** cuando hay anomalia detectada
5. **Formato numerico consistente:** miles con punto, diferencias en MM$
6. **Responsive:** HTML que se ve bien en Outlook desktop y OWA

**Generacion de artefactos:**
- Charts PNG via plotly + kaleido (reutilizar patron de email_report.py)
- Excel adjunto con hojas: Resumen_GCP, Detalle_GCP, Resumen_CMR, Detalle_CMR
- HTML con tablas inline + imagenes CID

**Funciones:**
- `generar_reporte_interfaces(fecha: date, ...) -> ReporteInterfaces`
  (dataclass con html, excel_path, chart_paths, alertas)
- `_construir_html_gcp(comparacion, ...) -> str`
- `_construir_html_cmr(comparacion, ...) -> str`
- `_generar_charts_interfaces(comparacion, ...) -> dict[str, Path]`
- `_generar_excel_interfaces(comp_gcp, comp_cmr, ...) -> Path`

**Archivos:**
- `core/control_interfaces.py`
- Reutilizar `core/email_report._enviar_outlook()` para envio

### Fase 5.7 -- Integracion con main.py y orquestador

**Objetivo:** Ejecutar control de interfaces como paso previo/complementario
a la ejecucion de primera_vuelta.

**Logica en orquestador:**
```python
# Al ejecutar primera_vuelta, antes de los modelos:
# 1. Verificar/copiar archivos PML a local (ya lo hace F14 para GCP)
# 2. Ejecutar analisis de control de interfaces
# 3. Enviar correo si esta habilitado
# Esto es complementario: usa los mismos archivos que cache_tablas.py
```

**Flag CLI nuevo:**
```
python main.py --fecha 2026-03-26 --control-interfaces gcp cmr
python main.py --fecha 2026-03-26 --control-interfaces todos
python main.py --fecha 2026-03-26 --modelos primera_vuelta --cargar-gcp
  # Si auto_control_interfaces: true en YAML -> ejecuta control automaticamente
```

**Integracion con primera_vuelta (complementario a F14):**
- Los modelos de primera vuelta ya leen los archivos PML GCP via
  `cache_tablas.copiar_interfaz_a_local()` y `leer_interfaz_con_cache()`
- El control de interfaces lee los MISMOS archivos locales
- Si el control se ejecuta ANTES de los modelos, asegura que los archivos
  existen y son validos antes de que los modelos los procesen
- Si se ejecuta DESPUES, valida consistencia post-ejecucion

**Archivos:**
- `main.py` -- agregar --control-interfaces flag
- `core/orquestador.py` -- hook pre/post ejecucion

### Fase 5.8 -- Watcher automatico de archivos

**Objetivo:** Mecanismo que detecta automaticamente cuando los archivos
PML aparecen en la ruta UNC y dispara el analisis.

**Diseno:**
- **Polling robusto** (no watchdog): las rutas UNC no soportan bien
  filesystem events
- Configurable: intervalo de polling (default 5 min), hora de inicio,
  hora limite
- Mecanismo de alerta escalonada:
  - Si a las 10:30 (90 min despues de hora esperada CMR) no hay archivos:
    **warning** en log + alerta en dashboard
  - Si a las 11:30 (90 min despues de hora esperada GCP) no hay archivos:
    **warning** en log + alerta en dashboard
  - Futuro: hooks para Teams, escalamiento, etc. (solo placeholder por ahora)

**Implementacion:**
- Thread daemon que se inicia con el orquestador
- Loop: check -> sleep -> check
- Cuando detecta archivos -> dispara pipeline completo (copia + analisis + email)
- Si ya ejecuto y el archivo cambio en red (MD5 diferente) -> re-ejecutar
  analisis y enviar correo de alerta con indicacion de CAMBIO DETECTADO
- Registro de estado en archivo JSON (`data/cache/control_interfaces_estado.json`)
  con campos: ultima_ejecucion, md5_t, md5_t1, resultado, alertas

**Nota:** El watcher es una utilidad adicional. El proceso puede ejecutarse
sin el (via CLI o dashboard). El watcher solo lo automatiza.

**Funciones:**
- `iniciar_watcher(config: ControlInterfacesConfig) -> threading.Thread`
- `detener_watcher()`
- `_loop_watcher(config, estado_path)`

**Archivos:**
- `core/control_interfaces.py`

### Fase 5.9 -- Pagina dashboard Streamlit

**Objetivo:** Pagina `7_Control_Interfaces.py` en el dashboard.

**Contenido:**
1. **Selector de fecha** (default: hoy)
2. **Estado de archivos** -- tabla mostrando disponibilidad por interfaz:
   - Archivo, Ruta UNC, Existe en red, Existe local, MD5 match, Timestamp copia
3. **Boton "Ejecutar Analisis"** -- dispara el pipeline completo
4. **Boton "Enviar Correo"** -- envia el reporte por email
5. **Resultados** -- tablas comparativas con colores por severidad
6. **Alertas** -- lista de anomalias detectadas con severidad y diagnostico
7. **Input editable de destinatarios** -- override del YAML

**Archivos:**
- `dashboard/pages/7_Control_Interfaces.py` (nuevo)

### Fase 5.10 -- Backup management (configurable, desactivable)

**Objetivo:** Replicar el backup de archivos PML del sistema legacy,
pero de manera configurable y desactivable.

**Logica actual (legacy):**
- GCP: copia archivo como `_Backup.TXT`, versiona backups previos
- CMR: no hace backup

**Nueva logica:**
- Configurable en YAML: `backup.enabled: true/false`
- Si habilitado: copia archivo a destino configurable con nombre configurable
- Puede desactivarse en el mediano plazo sin tocar codigo

**Archivos:**
- `core/control_interfaces.py`
- `config/config_rutas_ext_y_archivos.yaml`

---

## 5. Umbrales de tolerancia por producto

### Filosofia

No todos los productos tienen la misma volatilidad diaria natural.
Un +-10% en DAP (cientos de miles de depositos minoristas) es estadisticamente
imposible -> **CRITICAL**. Un +-10% en DAPM (pocos depositos mayoristas grandes)
puede ocurrir si entra o sale un cliente grande -> **WARNING** que requiere
verificacion, pero no es necesariamente error.

### Estructura YAML

```yaml
control_interfaces:
  umbrales:
    # Umbrales por defecto (aplican si el producto no tiene seccion especifica)
    default:
      capital_warning_pct: 5.0     # |delta%| > 5% -> WARNING
      capital_critical_pct: 15.0   # |delta%| > 15% -> CRITICAL
      interes_warning_pct: 5.0
      interes_critical_pct: 15.0
      registros_warning_pct: 5.0
      registros_critical_pct: 20.0

    # Umbrales especificos por producto GCP
    gcp:
      DAP:
        capital_warning_pct: 2.0    # DAP es muy estable (minorista)
        capital_critical_pct: 5.0
        diagnostico_enabled: true   # activar diagnostico automatico
      DAPM:
        capital_warning_pct: 10.0   # DAPM es volatil (mayorista)
        capital_critical_pct: 30.0
        diagnostico_enabled: true
        diagnostico_checks:
          - "registro_nuevo_grande"      # buscar registro nuevo > P99
          - "vencimiento_entre_fechas"   # buscar vencimiento en ventana t-1..t
      BONOS:
        capital_warning_pct: 1.0    # Bonos son estables
        capital_critical_pct: 5.0
      CCT:
        capital_warning_pct: 3.0
        capital_critical_pct: 10.0
      # ... (completar iterativamente con el equipo)

    # Umbrales especificos por producto CMR
    cmr:
      TC:
        capital_warning_pct: 3.0
        capital_critical_pct: 10.0
      # ... (completar iterativamente)
```

### Logica de evaluacion

```
Para cada fila (producto x moneda):
    delta = abs(PCT_CAPITAL)
    umbral = obtener_umbral(producto, tipo)  # tipo = gcp | cmr

    if delta > umbral.critical:
        severidad = CRITICAL  -> rojo fuerte, diagnostico obligatorio
    elif delta > umbral.warning:
        severidad = WARNING   -> amarillo, diagnostico si disponible
    else:
        severidad = OK        -> verde
```

### Colores en el reporte

| Severidad | Color de fondo | Color texto | Descripcion |
|-----------|----------------|-------------|-------------|
| OK | #C8E6C9 (verde claro) | #1B5E20 | Dentro de tolerancia |
| WARNING | #FFF9C4 (amarillo claro) | #F57F17 | Revisar, posible anomalia |
| CRITICAL | #FFCDD2 (rojo claro) | #B71C1C | Alerta, requiere accion inmediata |

---

## 6. Config YAML completa propuesta

```yaml
# En config/config_rutas_ext_y_archivos.yaml, nueva seccion:

control_interfaces:
  enabled: true
  ruta_unc_base: "\\\\vmdvorak\\Riesgo Financiero Folder\\RRFF-GCP\\Cartera\\input"

  # Email
  destinatarios:
    - "riesgofinanciero@bancofalabella.cl"
  modo: "send"                      # "send" | "display"
  auto_con_primera_vuelta: true     # ejecutar automaticamente con primera_vuelta

  # Horarios esperados de llegada de archivos
  horario_esperado_cmr: "09:00"
  horario_esperado_gcp: "10:00"

  # Polling / Watcher
  watcher:
    enabled: false                  # activar para modo automatico
    polling_intervalo_segundos: 300
    timeout_alerta_minutos: 90      # alerta si no llegan a hora + 90min
    timeout_abortar_minutos: 180    # dejar de intentar tras 3h

  # Backup management (legacy, desactivable)
  backup:
    enabled: true
    gcp:
      ruta_destino: "\\\\vmdvorak\\Riesgo Financiero Folder\\RRFF-GCP\\Cartera\\input"
      sufijo_backup: "_Backup.TXT"
    cmr:
      enabled: false                # CMR no hace backup actualmente

  # Interfaces
  interfaces:
    gcp:
      patron_archivo: "ProductosMercadoLiquidezGCP{fecha}.txt"
      patron_archivo_t1: "ProductosMercadoLiquidezGCP{fecha}_Backup.txt"
      columnas: ["FECHA_PROCESO", "SISTEMA", "CODIGO_SUBPRODUCTO", "MONEDA_ORIGEN", "AMORTIZACION", "INTERES", "FECHA_VENCIMIENTO_CUOTA"]
      tipos_datos:
        SISTEMA: str
        CODIGO_SUBPRODUCTO: str
        MONEDA_ORIGEN: str
        AMORTIZACION: float
        INTERES: float
        FECHA_VENCIMIENTO_CUOTA: str
      agrupacion: ["SISTEMA", "MONEDA_ORIGEN"]
      sistemas_vistas: ["CCT", "CVI"]   # se tratan aparte (seccion VISTAS)
      asunto_template: "Comparacion Interfaz de Datos al {fecha}"
    cmr:
      patron_archivo: "ProductosMercadoLiquidezCMR{fecha}.txt"
      patron_archivo_t1: "ProductosMercadoLiquidezCMR{fecha}.txt"  # sin backup
      columnas: ["FECHA_PROCESO", "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO", "AMORTIZACION", "INTERES", "FECHA_VENCIMIENTO_CUOTA"]
      tipos_datos:
        CODIGO_PRODUCTO: str
        CODIGO_SUBPRODUCTO: str
        AMORTIZACION: float
        INTERES: float
        FECHA_VENCIMIENTO_CUOTA: str
      agrupacion: ["CODIGO_SUBPRODUCTO"]   # SISTEMA=TC y MONEDA=999 son constantes
      asunto_template: "Comparacion Interfaz de Datos CMR al {fecha}"

  # Umbrales (ver seccion 5)
  umbrales:
    default:
      capital_warning_pct: 5.0
      capital_critical_pct: 15.0
      interes_warning_pct: 5.0
      interes_critical_pct: 15.0
      registros_warning_pct: 5.0
      registros_critical_pct: 20.0
    gcp:
      DAP:
        capital_warning_pct: 2.0
        capital_critical_pct: 5.0
        diagnostico_enabled: true
      DAPM:
        capital_warning_pct: 10.0
        capital_critical_pct: 30.0
        diagnostico_enabled: true
    cmr: {}   # completar iterativamente
```

---

## 7. Plan de ejecucion (sprints)

| # | Fase | Tamano | Prioridad | Dependencias |
|---|------|--------|-----------|--------------|
| 5.1 | Config YAML + esqueleto | XS | P0 | - |
| 5.2 | Deteccion + copia local | S | P0 | 5.1 |
| 5.3 | Analisis exploratorio | M | P0 | 5.2 |
| 5.4 | Umbrales de tolerancia | S | P1 | 5.3 |
| 5.5 | Diagnostico anomalias | S | P2 | 5.4 |
| 5.6 | Reporte HTML + charts + Excel | M | P0 | 5.3 |
| 5.7 | Integracion main.py + orquestador | S | P0 | 5.6 |
| 5.8 | Watcher automatico | S | P1 | 5.7 |
| 5.9 | Pagina dashboard Streamlit | M | P1 | 5.6 |
| 5.10 | Backup management | XS | P2 | 5.2 |

**Orden de implementacion sugerido:**
1. [5.1 + 5.2] Config + deteccion -> fundamento
2. [5.3 + 5.6] Analisis + reporte -> valor de negocio
3. [5.7] Integracion main.py -> reemplazar legacy
4. [5.4] Umbrales -> mejorar calidad de alertas
5. [5.8 + 5.9] Watcher + dashboard -> automatizacion y UX
6. [5.5 + 5.10] Diagnostico + backup -> refinamiento

---

## 8. Criterios de aceptacion

- [ ] Lectura correcta de ambos archivos PML (GCP y CMR) desde ruta UNC
- [ ] Copia local con verificacion de integridad (MD5)
- [ ] Warning visible si archivo cambio en red tras copia local
- [ ] Agrupacion y comparacion t vs t-1 para capital, interes y conteo de registros
- [ ] Umbrales de tolerancia por producto configurables en YAML
- [ ] Colores de severidad (OK/WARNING/CRITICAL) en reporte HTML
- [ ] Conteo de registros incluido en reporte
- [ ] Email enviado via Outlook COM con HTML + charts PNG + Excel adjunto
- [ ] Destinatarios editables (YAML + override CLI/dashboard)
- [ ] Flag CLI --control-interfaces funcional
- [ ] Pagina dashboard Streamlit con boton de ejecucion manual
- [ ] Backup management configurable y desactivable
- [ ] Reemplaza completamente el main.py del OneDrive

---

## 9. Preguntas abiertas (actualizadas 2026-03-30)

### Resueltas

1. ~~**VISTAS en GCP:**~~ RESUELTO. Viene de SISTEMA=CCT (subprod 201, 501)
   y SISTEMA=CVI (subprod 202), todos con MONEDA_ORIGEN=999.
   No es esencial para el core. Se implementa despues.

2. ~~**FECHA_VENCIMIENTO_CUOTA:**~~ RESUELTO. Confirmado presente en ambos
   archivos (GCP y CMR). Formato YYYYMMDD. Disponible para diagnostico.

3. ~~**Umbrales CMR:**~~ Partimos con los actuales y refinamos despues.

4. ~~**VISTAS en CMR:**~~ RESUELTO. CMR no tiene seccion VISTAS (SISTEMA=TC,
   MONEDA=999, todo es tarjeta de credito).

5. ~~**Frecuencia:**~~ Puede re-ejecutarse si el archivo cambia en red.
   El sistema debe detectar cambios via MD5 y alertar/re-analizar.

### Pendientes

6. **Fila-resumen "TC" en CMR:** El screenshot muestra una primera fila "TC"
   que es la suma total de todos los subproductos. Asumimos que es suma
   calculada en el reporte (a verificar en implementacion).

7. ~~**MONEDA_ORIGEN codigos:**~~ RESUELTO.
   - `999` = CLP, `998` = CLF, `13` = USD
   - GCP: 999 aparece en la mayoria de SISTEMA (no solo CCT/CVI)
   - CMR: todo es 999 (CLP)
   - El reporte traduce los codigos a nombres legibles
   - Constante de mapeo: `MONEDA_MAP = {'999': 'CLP', '998': 'CLF', '13': 'USD'}`

---

## 10. Dependencias tecnicas

- `pandas` -- ya disponible
- `plotly` + `kaleido` -- ya disponibles (usados por email_report.py)
- `pywin32` (win32com) -- ya disponible (Outlook COM)
- `pyyaml` -- ya disponible
- `xlsxwriter` -- ya disponible (via core/excel_output.py)
- No se requieren dependencias nuevas
