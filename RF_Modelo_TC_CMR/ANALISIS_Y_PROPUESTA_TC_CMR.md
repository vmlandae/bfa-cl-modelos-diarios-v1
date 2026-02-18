# Analisis Completo y Propuesta de Integracion: Modelo TC CMR

> **Autor**: Claude (asistente) + vlandaetat
> **Fecha**: 2026-02-16 (v1), 2026-02-17 (v2 con respuestas confirmadas)
> **Estado**: Respuestas confirmadas - listo para implementacion

---

## 1. Que es el Modelo TC CMR

### 1.1 Proposito de Negocio

El modelo **TC CMR** (Tarjeta de Credito CMR) estima los **flujos de caja futuros esperados (ingresos)** para la cartera de tarjetas de credito CMR de Banco Falabella Chile. En terminos simples: dado el stock actual de deuda en tarjetas, **proyecta cuando y cuanto se espera recibir en pagos**, dia a dia, usando factores historicos de probabilidad de pago por perfil de cliente y dia del mes.

### 1.2 Contexto dentro del Repositorio

Este modelo se suma a los 9 modelos existentes en `bfa-cl-modelos-diarios`:
- 4 modelos de Mora (CAE, Comercial, Consumo, Hipotecario)
- 3 modelos de Prepago (CMR, Consumo, Hipotecario)
- 1 modelo NMD (No Maduracion de Depositos)
- 1 modelo LC (Linea de Credito)

A diferencia de los demas modelos que ya estan integrados, el TC CMR viene de un proceso historico basado en **macros VBA de Excel** + un **script R externo**, que ha sido progresivamente traducido a Python en dos sub-proyectos dentro de `dev/`.

---

## 2. Estado Real del Codigo Existente

> **IMPORTANTE**: Los README de los subdirectorios dev/ no reflejan con precision el estado actual. Esta seccion documenta la realidad confirmada.

### 2.1 Lo que funciona vs lo que no

| Componente | Estado real | Detalle |
|------------|------------|---------|
| Fase 2: Script R (`TC_CMR_ING_V9b.R` reescrito) | **100% funcional y validado** | Unico componente completamente probado y operativo |
| Fase 1: Python (maestro/preparacion) | **Logica correcta, no ejecutable actualmente** | Problemas de dependencias y rutas; no corre en el entorno actual |
| Fase 2: Python (calculo flujos) | **Logica correcta, no ejecutable actualmente** | Mismos problemas de dependencias; requiere testeo |
| Fase 3: Python (post-proceso) | **Parcial, no validado** | ~640 lineas, nunca validado contra produccion |
| `requirements.txt` de ambos proyectos | **Cero confianza** | No son confiables |

### 2.2 Implicaciones para la integracion

- La logica de negocio en Python esta bien, pero requiere **testeo exhaustivo** y **correccion de dependencias/rutas**
- El script R de Fase 2 es la **referencia gold standard** para validacion
- No podemos asumir que el codigo Python corre tal cual; hay que adaptar e ir validando

---

## 3. Arquitectura del Modelo: Las 3 Fases

El modelo opera en 3 fases secuenciales claramente diferenciadas:

```
+-----------------------+     +-----------------------+     +-----------------------+
|   FASE 1              |     |   FASE 2              |     |   FASE 3              |
|   MAESTRO             |---->|   Calculo de Flujos   |---->|   TablaDesarrollo     |
|   (Preparacion)       |     |   (TC_CMR_ING)        |     |   (Post-proceso)      |
|                       |     |                       |     |                       |
|   VBA -> Python       |     |   R -> Python         |     |   VBA -> Python       |
|   (logica OK, no      |     |   (R validado 100%,   |     |   (parcial,           |
|    ejecutable hoy)    |     |    Py requiere test)  |     |    no validado)       |
+-----------------------+     +-----------------------+     +-----------------------+
         |                            |                            |
         v                            v                            v
  INPUT_TC-CMR_              OUTPUT_TC_CMR_              FLUJOS_MODELO_CMR.xlsx
  FAC_ANT.csv                INGRESO_{fecha}.txt        ML_TC_CMR.xlsm (actualizado)
```

### Fase 1: MAESTRO (Preparacion de Datos)
- **Origen**: Macros VBA del archivo `CREA_CARTERA_14P.xlsm` (~1697 lineas VBA, ~800 activas)
- **Estado traduccion Python**: Logica validada contra VBA (match 100% en 3 fechas), pero scripts no ejecutables actualmente por dependencias rotas
- **Ubicacion dev**: `dev/traduccion_py_R_macros_crea_cartera_14p/python/`
- **Que hace**:
  1. Lee la cartera diaria desde archivo TXT (`ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT`)
  2. Aplica "tratamiento": ordena, clasifica registros como N(ormal)/R(eemplazo)/V(encido)
  3. Calcula VENCIMIENTO (dia del mes), RESIDUAL (dias hasta vencimiento), FF (dia facturacion)
  4. Carga 6 carteras historicas T-30 (siempre activo en produccion) + la de fecha proceso
  5. Asigna perfiles de pago (PP: P00-P14) via lookup externo (`tabla_perfiles_pp.csv`)
  6. Genera `INPUT_TC-CMR_FAC_ANT.csv` (40 columnas, ~48,000 registros/dia)

### Fase 2: Calculo de Flujos (TC_CMR_ING)
- **Origen**: Script R `TC_CMR_ING_V9b.R` (~300 lineas)
- **Estado**: R reescrito 100% validado (190,081 filas identicas). Python tiene la logica pero requiere testeo.
- **Ubicacion dev**: `dev/reescritura_codigo_TC_CMR_ING_V9b/`
- **Que hace**:
  1. Lee `INPUT_TC-CMR_FAC_ANT.csv` + `Perfil_Factor.csv`
  2. Filtra: solo producto TC, excluye destinos V y R
  3. Agrega por (FVC, PP, FF) y aplica factor de ajuste global (FG = 0.9165)
  4. Calcula periodos de facturacion (FINI/FIFIN) segun FF
  5. Expande a nivel diario (una fila por dia del periodo)
  6. Calcula revolventes: la porcion no pagada que "rueda" al mes siguiente (REVOL1->REVOL2->REVOL3->REVOL4)
  7. Estima pagos: `PAGO_EST = FLUJO_MES x FACTOR`
  8. Genera `OUTPUT_TC_CMR_INGRESO_{fecha}.txt` (17 columnas, ~190,000 filas)

### Fase 3: TablaDesarrollo (Post-proceso)
- **Origen**: Macro VBA `TablaDesarrollo()` en `CREA_CARTERA_14P.xlsm`
- **Estado traduccion Python**: Parcialmente implementado (~640 lineas, no validado)
- **Ubicacion dev**: `dev/traduccion_py_R_macros_crea_cartera_14p/python/postproceso/`
- **Que hace**:
  1. Lee el output de Fase 2 (`OUTPUT_TC_CMR_INGRESO_{fecha}.txt`)
  2. Genera `FLUJOS_MODELO_CMR.xlsx` (archivo de gestion/validacion, NO sube a BigQuery)
  3. Actualiza `ML_TC_CMR.xlsm` (tabla de desarrollo con formato estandar DESARROLLO para BigQuery)

---

## 4. Lo que Ya Existe (Inventario del Trabajo Previo)

### 4.1 Fase 1 - Traduccion VBA -> Python

**Carpeta**: `dev/traduccion_py_R_macros_crea_cartera_14p/`

| Componente | Archivo | Lineas | Estado |
|------------|---------|--------|--------|
| Entry point CLI | `python/main.py` | ~276 | Logica OK, no ejecutable |
| Orquestador principal | `python/preparacion/maestro.py` | ~937 | Logica OK, no ejecutable |
| Config manager | `python/preparacion/config_manager.py` | ~263 | Logica OK, no ejecutable |
| Carga cartera TXT | `python/preparacion/cargar_cartera.py` | ~299 | Logica OK, no ejecutable |
| Tratamiento (clasificacion) | `python/preparacion/tratamiento.py` | ~350 | Logica OK, no ejecutable |
| Carga carteras T-30 | `python/preparacion/cargar_cartera_t30.py` | ~386 | Logica OK, no ejecutable |
| Generacion parametros | `python/preparacion/generar_parametros.py` | ~399 | Logica OK, no ejecutable |
| Post-proceso (Fase 3) | `python/postproceso/tabla_desarrollo.py` | ~640 | Parcial, no validado |
| Configuracion | `config.yaml` | ~300 | Rutas obsoletas |

**Validacion historica**: Match 100% vs VBA produccion en 3 fechas (47,881 / 49,020 / 48,800 registros). Pero los scripts no corren actualmente por dependencias rotas.

### 4.2 Fase 2 - Reescritura R -> Python

**Carpeta**: `dev/reescritura_codigo_TC_CMR_ING_V9b/`

| Componente | Archivo | Lineas | Estado |
|------------|---------|--------|--------|
| Script R reescrito | `R/main.R` + modulos | ~500 total | **100% validado y funcional** |
| Entry point Python | `python/main_CORRECTO.py` | ~92 | Logica OK, no ejecutable |
| Carga de datos | `python/load_data.py` | ~150 | Logica OK, requiere test |
| Calculo de fechas | `python/calculate_dates.py` | ~144 | Logica OK, requiere test |
| Calculo de flujos | `python/calculate_flows_CORRECTO.py` | ~300 | Logica OK, requiere test |
| Exportacion | `python/export_results_CORRECTO.py` | ~188 | Logica OK, requiere test |
| Utilidades | `python/utils.py` | ~172 | Logica OK, requiere test |

**Validacion**: Script R produce 190,081 filas identicas al original. Python produjo el mismo resultado en su momento pero no corre actualmente.

### 4.3 Fase 3 - Post-proceso (INCOMPLETA)

**Archivos existentes**: `main_postproceso.py` + `postproceso/tabla_desarrollo.py`
- Parcialmente implementado (~640 lineas)
- No validado contra produccion
- Interactua con archivos Excel (openpyxl) para gestionar tablas dinamicas

---

## 5. Datos de Entrada y Salida

### 5.1 Inputs

| Archivo | Origen | Formato | Volumen | Frecuencia |
|---------|--------|---------|---------|------------|
| `ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT` | Cartera diaria CMR desde `\\vmdvorak\Riesgo Financiero Folder\RRFF-GCP\Cartera\input` | TXT delimitado por `;`, latin-1, 36 columnas | ~200 MB | Diario |
| `Perfil_Factor.csv` | Factores de pago historicos, `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/` | CSV `;`, decimales con `,` | ~1.5 MB | Se actualiza periodicamente |
| `tabla_perfiles_pp.csv` | Tabla de lookup perfiles de pago, `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/` | CSV | Pequeno | Se actualiza cuando cambian perfiles |
| `parametros_ml_tc_cmr.xlsx` | Parametros del modelo (incluye FG y otros) | Excel | Pequeno | Actualizacion anual |

> **NOTA**: El archivo TXT de cartera CMR (`ProductosMercadoLiquidezCMR`) es **diferente** al que usan los modelos de mora/prepago (`ProductosMercadoLiquidezGCP`). Misma carpeta, distinto archivo.

### 5.2 Outputs Intermedios (necesarios durante desarrollo)

| Archivo | Generado por | Formato | Volumen |
|---------|-------------|---------|---------|
| `INPUT_TC-CMR_FAC_ANT.csv` | Fase 1 | CSV `;`, 40 columnas | ~48K filas |
| `{fecha}_Parametros_FechasFacturacion_ModeloCMR.txt` | Fase 1 | Texto, fechas de facturacion | Pequeno |
| `OUTPUT_TC_CMR_INGRESO_{fecha}.txt` | Fase 2 | TSV, 17 columnas, decimal `,` | ~190K filas, ~35 MB |

> Todos los outputs intermedios se mantienen durante desarrollo para facilitar validacion. En produccion estable se podra hacer opcional (pasar DataFrames en memoria).

### 5.3 Outputs Finales

| Archivo | Generado por | Formato | Destino |
|---------|-------------|---------|---------|
| `ML_TC_CMR.xlsm` (hoja DESARROLLO) | Fase 3 | Excel con macros | BigQuery tabla `report_ml_tc_cmr_dly` |
| `FLUJOS_MODELO_CMR.xlsx` | Fase 3 | Excel | Solo validacion interna, **NO sube a BigQuery** |

### 5.4 Esquema del Output Final (hoja DESARROLLO)

Basado en el esquema comun a todos los modelos del repo (mismo schema de BigQuery `crear_esquema_base()`). Verificar contra `ML_TC_CMR.xlsm` existente en produccion.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| FECHA_PROCESO | DATE | Fecha de ejecucion |
| CODIGO_EMPRESA | INTEGER | 1 (Banco Falabella) |
| OPERACION | INTEGER | Numero de operacion |
| COD_ACT_PAS | STRING | ACT o PAS |
| MONEDA_ORIGEN | STRING | CLP |
| MONEDA_COMPENSACION | STRING | CLP |
| COMPENSACION | INTEGER | |
| CODIGO_PRODUCTO | STRING | Codigo del producto |
| CODIGO_SUBPRODUCTO | STRING | Codigo subproducto |
| FECHA_CREACION | DATE | |
| NUMERO_CUOTA | INTEGER | |
| FECHA_INICIO_CUOTA | DATE | |
| FECHA_VENCIMIENTO_CUOTA | DATE | Fecha proyectada del flujo |
| FECHA_PAGO | DATE | |
| FECHA_REPRICING | DATE | |
| AMORTIZACION | FLOAT | Monto del flujo |
| INTERES | FLOAT | |
| INTERES_DEVENGADO | FLOAT | |
| VP_AMORTIZACION | FLOAT | |
| VP_INTERES | FLOAT | |
| FACTOR_DE_RIESGO | STRING | |
| TIPO_CUOTA | INTEGER | |
| AREA_NEGOCIO | STRING | |
| CODIGO_EJECUTIVO | STRING | |
| CODIGO_ESTRATEGIA | STRING | |
| CLASIFICACION_CONTABLE | STRING | |
| TIPO_TASA | INTEGER | |
| INDEXADOR | STRING | |
| TASA | FLOAT | |
| TASA_CF | FLOAT | |
| SPREAD | FLOAT | |

---

## 6. Logica de Negocio Clave

### 6.1 Clasificacion de Registros (Fase 1: TRATAMIENTO)

```
CORTE = 17  si (ultimo_dia_mes == 31 AND dia_proceso >= 15)
       16   en otro caso

Para cada cuota:
  VENCIMIENTO = ultimos 2 digitos de FECHA_VENCIMIENTO_CUOTA
  RESIDUAL = FECHA_VENCIMIENTO_CUOTA - FECHA_PROCESO (en dias)

  Si RESIDUAL > CORTE  -> "N" (Normal: cuota vigente)
  Si 0 < RESIDUAL <= CORTE -> "R" (Reemplazo: proxima a vencer, en ventana de facturacion)
  Si RESIDUAL <= 0 -> "V" (Vencido: cuota morosa)
```

### 6.2 Perfiles de Pago (PP)

Los clientes se clasifican en 15 perfiles (P00 = mejor pagador, P14 = peor) segun tabla de lookup externa (`tabla_perfiles_pp.csv` en `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/`). Cada perfil tiene una tabla de factores de pago por dia del mes (`Perfil_Factor.csv`), que indica la probabilidad de que el cliente pague en ese dia especifico.

> **CONFIRMADO**: La tabla de perfiles es un parametro externo, no hardcodeada. El archivo `tabla_perfiles_pp.csv` existe en el disco compartido.

### 6.3 Periodos de Facturacion (Fase 2)

El periodo de facturacion depende del dia de facturacion (FF):

| FF | FINI (inicio periodo) | FIFIN (fin periodo) |
|----|----------------------|---------------------|
| < 15 | FVC - 1 mes + 15 dias | FVC + 14 dias |
| = 15 | FVC - 1 mes + 15 dias (ajuste Feb/Mar) | FVC + 14 dias |
| 20, 25, 30 | FVC - 15 dias | FINI + 1 mes - 1 dia |
| 28 | FVC - 13 dias | FINI + 1 mes - 1 dia |

### 6.4 Calculo de Revolventes (Fase 2)

La porcion no pagada de la deuda "rueda" al siguiente periodo:

```
FREVOL = max(0, 1 - suma_factores_del_periodo)

REVOL1 = SALDO x FREVOL                    (rueda al mes 1)
REVOL2 = REVOL1 x FREVOL_mes1              (rueda al mes 2)
REVOL3 = REVOL2 x FREVOL_mes2              (rueda al mes 3)
REVOL4 = residual no realocado             (se proyecta a 12 meses)
```

### 6.5 Pago Estimado (Fase 2)

```
FLUJO_MES = SALDO + REV1 + REV2 + REV3
FACTOR_normalizado = FACTOR / SUMA_FACTORES  (si suma > 1)
PAGO_EST = FLUJO_MES x FACTOR_normalizado
```

### 6.6 Factor de Ajuste Global (FG = 0.9165)

Todos los saldos se multiplican por 0.9165 (91.65% del nominal). Este es un "factor de garantia" que ajusta la estimacion a la baja. **Se actualiza anualmente** y debe ir en `parametros_ml_tc_cmr.xlsx` para facilitar su actualizacion por el equipo de negocio.

---

## 7. Propuesta de Integracion al Repositorio

### 7.1 Enfoque General

Consolidar las 3 fases en un pipeline orquestado por `ml_tc_cmr.py` con `ejecutar_modelo(fecha_proceso: datetime) -> bool`. Estructura **modular con subcarpetas por fase** (confirmado como aceptable).

### 7.2 Estructura de Archivos Confirmada

```
RF_Modelo_TC_CMR/
+-- __init__.py
+-- ml_tc_cmr.py                    # Punto de entrada: ejecutar_modelo()
+-- ml_tc_cmr.xlsm                  # Plantilla Excel output (hoja DESARROLLO)
+-- preparacion/                    # Fase 1: preparacion de datos
|   +-- __init__.py
|   +-- maestro.py                  # Orquestacion Fase 1
|   +-- cargar_cartera.py           # Carga TXT
|   +-- tratamiento.py              # Clasificacion N/R/V
|   +-- cargar_cartera_t30.py       # Carteras historicas T-30
+-- calculo/                        # Fase 2: calculo de flujos
|   +-- __init__.py
|   +-- calcular_fechas.py          # Periodos facturacion
|   +-- calcular_flujos.py          # Revolventes + pago estimado
+-- postproceso/                    # Fase 3: tabla de desarrollo
|   +-- __init__.py
|   +-- tabla_desarrollo.py         # Formateo output estandar
+-- parametros/
|   +-- parametros_ml_tc_cmr.xlsx   # Parametros del modelo (FG, etc.)
+-- dev/                            # Codigo fuente de referencia (ya existente)
    +-- reescritura_codigo_TC_CMR_ING_V9b/
    +-- traduccion_py_R_macros_crea_cartera_14p/
```

> **NOTA**: `Perfil_Factor.csv` y `tabla_perfiles_pp.csv` viven en el disco compartido (`Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/`), no en el repo. Se referencian via YAML.

### 7.3 Flujo de Ejecucion Confirmado

```python
def ejecutar_modelo(fecha_proceso: datetime) -> bool:
    """
    Ejecuta el pipeline completo del modelo TC CMR.

    0. Copiar archivos de red a directorio local (data/)
       - Cartera TXT
       - Perfil_Factor.csv
       - tabla_perfiles_pp.csv

    Fase 1: Preparacion (MAESTRO)
      - Cargar cartera TXT desde copia local
      - Aplicar tratamiento (clasificacion N/R/V)
      - Cargar 6 carteras T-30 + fecha proceso (siempre activo)
      - Asignar perfiles de pago via tabla_perfiles_pp.csv
      - Generar CSV intermedio (a disco durante desarrollo)

    Fase 2: Calculo de Flujos
      - Leer CSV intermedio + factores de pago
      - Calcular periodos de facturacion
      - Expandir a nivel diario
      - Calcular revolventes
      - Estimar pagos
      - Generar TXT intermedio (a disco durante desarrollo)

    Fase 3: Tabla de Desarrollo
      - Formatear output al esquema estandar (DESARROLLO)
      - Generar FLUJOS_MODELO_CMR.xlsx (validacion, no BigQuery)
      - Guardar en ML_TC_CMR.xlsm (hoja DESARROLLO -> BigQuery)
    """
```

### 7.4 Decisiones de Diseno Confirmadas

| Decision | Resolucion | Razon |
|----------|-----------|-------|
| Estructura | Modular (subcarpetas) | Justificado por complejidad 5-10x mayor que otros modelos |
| Archivos intermedios | Escribir a disco durante desarrollo | Necesarios para validacion; hacer opcional despues |
| FLUJOS_MODELO_CMR.xlsx | Generar | Para validacion; NO sube a BigQuery |
| Copia local de inputs | Si, a directorio `data/` (gitignored) | Mejor performance, evita I/O de red durante procesamiento |
| Secuencia de ejecucion | Secuencia propia, puede ir antes de primera_vuelta | No depende de otros modelos |
| Perfiles de pago | Parametro externo (tabla_perfiles_pp.csv) | No hardcodeado; archivo en disco compartido |
| Factor de ajuste global | En parametros_ml_tc_cmr.xlsx | Se actualiza anualmente |
| SMCC (carteras T-30) | Siempre ON | 6 carteras + fecha proceso |

### 7.5 Adaptaciones Necesarias vs Codigo Existente en dev/

| Aspecto | Codigo actual en dev/ | Adaptacion necesaria |
|---------|----------------------|---------------------|
| Rutas | Hardcodeadas en config.yaml a Z:/ y Y:/ | Migrar a `config_rutas_ext_y_archivos.yaml` del repo |
| Config manager | Clase ConfigManager propia | Integrar con sistema de config del repo (YAML + config_rutas.py) |
| Lectura de inputs | Directo desde red | Copiar a `data/` local primero, luego leer local |
| Output intermedio | CSV + TXT a disco | Mantener a disco durante desarrollo; hacer opcional despues |
| Output final | TXT tab-separated con formato R | Adaptar a hoja DESARROLLO en .xlsm (formato estandar del repo) |
| Modos testing/produccion | Flags CLI propios | Eliminar; el repo ya tiene modo GUI y CLI via orquestador |
| Homologacion VBA | Flags --homologar-* | Eliminar; no necesarios en produccion |
| Encoding latin-1 | Necesario para leer TXT de cartera | Mantener en la lectura de archivos |
| Carga GCP | No implementado | Se hereda del orquestador (ya configurado) |
| Dependencias Python | Rotas actualmente | Resolver como parte de la integracion |
| Tabla perfiles PP | Hardcodeada en maestro.py | Migrar a lectura de tabla_perfiles_pp.csv externa |

---

## 8. Preguntas y Respuestas Confirmadas

### 8.1 Preguntas sobre Datos y Rutas

**P1. Ruta del archivo de cartera diario**: El codigo actual lee de `Y:/RRFF-GCP/Cartera/input/ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT`. Son fuentes distintas a `mr_prepago_cmr`?
- **CONFIRMADO**: Correcto, son fuentes distintas. El prepago CMR usa MS Access; el TC CMR usa archivos TXT directamente.
- **Accion tomada**: YAML corregido con clave `txt_cartera_input`.

**P2. El archivo TXT de cartera es el mismo que usan otros modelos?**
- **CONFIRMADO**: NO es el mismo archivo. La misma carpeta (`\\vmdvorak\Riesgo Financiero Folder\RRFF-GCP\Cartera\input`) contiene archivos con nombres distintos:
  - TC CMR usa: `ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT`
  - Otros modelos (mora/prepago) usan: `ProductosMercadoLiquidezGCP{YYYYMMDD}.TXT`
- **Accion tomada**: YAML incluye tanto la ruta como el patron de nombre de archivo.

**P3. El scaffold YAML tenia ms_access. El TC CMR usa Access?**
- **CONFIRMADO**: TC CMR **NO usa Access en absoluto**. Lee directamente de TXT.
- **Accion tomada**: YAML corregido, se eliminaron `ms_access_input` y `ms_access_tabla_input`.

**P4. Donde vive `Perfil_Factor.csv` en produccion?**
- **CONFIRMADO**: `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/Perfil_Factor.csv`
- **Accion tomada**: Ruta agregada en YAML como `perfil_factor_input`.

**P5. El flag SMCC (carga de carteras T-30) esta siempre ON?**
- **CONFIRMADO**: Siempre ON en produccion.

**P6. Cuantas carteras historicas T-30 hay que cargar?**
- **CONFIRMADO**: 6 carteras T-30 (una por cada FF: 5, 10, 15, 20, 25, 30) mas la de la fecha de proceso. Total: 7 archivos de cartera.

### 8.2 Preguntas sobre la Logica del Modelo

**P7. El factor de ajuste global (FG = 0.9165) cambia?**
- **CONFIRMADO**: Se actualiza anualmente. Debe ir en `parametros_ml_tc_cmr.xlsx` para facilitar actualizacion por el equipo de negocio.

**P8. Los perfiles de pago (P00-P14), como se mapean?**
- **CONFIRMADO**: Es un parametro externo. Existe `tabla_perfiles_pp.csv` en `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/`. NO debe estar hardcodeado.
- **Accion tomada**: Ruta agregada en YAML como `tabla_perfiles_pp_input`.

**P9. El output debe ser SOLO el .xlsm o tambien el TXT intermedio?**
- **CONFIRMADO**: TODOS los outputs intermedios son necesarios durante desarrollo para validacion. El output final para BigQuery es solo el .xlsm (hoja DESARROLLO).

**P10. La Fase 3 convierte el output de Fase 2 al formato estandar?**
- **CONFIRMADO**: Si. Ademas genera `FLUJOS_MODELO_CMR.xlsx` como archivo de validacion/gestion.

### 8.3 Preguntas sobre la Integracion

**P11. Subcarpetas aceptables?**
- **CONFIRMADO**: Si, subcarpetas son aceptables para este modelo dado su mayor complejidad.

**P12. CSV intermedio a disco o en memoria?**
- **CONFIRMADO**: Mantener escritura a disco durante desarrollo para facilitar validacion. Hacer opcional (in-memory) mas adelante cuando este estable.

**P13. Que pasa con FLUJOS_MODELO_CMR.xlsx?**
- **CONFIRMADO**: Se genera para validacion interna pero **NO sube a BigQuery**. Solo `ML_TC_CMR.xlsm` (hoja DESARROLLO) va a BigQuery.

**P14. El modelo va en segunda_vuelta o tiene secuencia propia?**
- **CONFIRMADO**: Secuencia propia. Puede correr antes de primera_vuelta. No depende de otros modelos.

**P15. El schema de BigQuery es el mismo que los demas modelos?**
- **CONFIRMADO**: 95% seguro que usa el mismo schema base (`crear_esquema_base()`). Verificar contra `ML_TC_CMR.xlsm` existente en produccion como paso de validacion.

### 8.4 Preguntas sobre Performance y Operacion

**P16. Tiempo de ejecucion aceptable?**
- **CONFIRMADO**: <10 minutos total seria un game changer. <5 minutos es realista dado que Python es mas rapido que el proceso VBA+R actual.

**P17. Lectura desde red o copia local primero?**
- **CONFIRMADO**: Mejor copiar archivos de red a directorio local (`data/`, gitignored) antes de procesar. Esto aplica como mejora general para todos los modelos del repo.

**P18. Hay dias sin archivo de cartera (fines de semana, feriados)?**
- **CONFIRMADO**: El archivo existe todos los dias (incluyendo fines de semana y feriados), pero el modelo solo procesa dias habiles. Se usa ajuste a dia habil como comportamiento por defecto.

---

## 9. Suposiciones Actualizadas

| # | Suposicion | Estado | Detalle |
|---|-----------|--------|---------|
| S1 | El modelo TC CMR usa archivos TXT, NO MS Access | **CONFIRMADO** | YAML corregido |
| S2 | Misma carpeta que otros modelos pero distinto archivo (CMR vs GCP) | **CONFIRMADO** | Patron: `ProductosMercadoLiquidezCMR` |
| S3 | `Perfil_Factor.csv` vive en disco compartido, no en el repo | **CONFIRMADO** | Ruta en YAML |
| S4 | SMCC (carga T-30) siempre ON en produccion | **CONFIRMADO** | 6 carteras + fecha proceso |
| S5 | La Fase 3 produce hoja DESARROLLO compatible con BigQuery schema | **CONFIRMADO** | Verificar contra .xlsm existente |
| S6 | El factor 0.9165 se actualiza anualmente | **CONFIRMADO** | Va en parametros_ml_tc_cmr.xlsx |
| S7 | El codigo Python de Fase 1 y 2 tiene logica correcta pero no es ejecutable | **CONFIRMADO** | Dependencias rotas, rutas obsoletas |
| S8 | Archivos intermedios necesarios durante desarrollo | **CONFIRMADO** | Hacer opcional despues |
| S9 | La Fase 3 necesita completacion/validacion significativa | **CONFIRMADO** | ~640 lineas parciales, no validado |
| S10 | Output BigQuery usa mismo esquema base | **CONFIRMADO (95%)** | Verificar contra ML_TC_CMR.xlsm |

---

## 10. Riesgos Identificados

| # | Riesgo | Impacto | Mitigacion |
|---|--------|---------|------------|
| R1 | La Fase 3 no esta completamente implementada/validada | Alto | Desarrollar y validar contra produccion |
| R2 | El mapeo de output Fase 2 -> esquema DESARROLLO puede tener gaps | Medio | Validar cada columna contra ML_TC_CMR.xlsm existente |
| R3 | Las rutas de red pueden cambiar o no estar disponibles | Medio | Parametrizar via YAML; copiar a local antes de procesar |
| R4 | Dependencias Python rotas en scripts dev/ existentes | Medio | Resolver durante integracion; no confiar en requirements.txt |
| R5 | Performance al leer TXT de 200MB desde red | Medio | Copiar a local primero (mejora general del repo) |
| R6 | Diferencias sutiles entre output Python vs R/VBA original | Bajo | Validar contra script R (gold standard) |

---

## 11. Mejora General Propuesta para el Repositorio

> **Idea transversal**: Implementar un patron de "copia local antes de procesar" para TODOS los modelos del repositorio. En lugar de leer directamente desde discos de red (Y:/, Z:/, `\\vmdvorak\...`), copiar los archivos necesarios a un directorio local `data/` (que estaria en `.gitignore`) y luego procesar todo leyendo local.
>
> **Beneficios**: Mejor performance, menor dependencia de disponibilidad de red durante procesamiento, facilita testing local.
>
> **Implementacion**: Puede hacerse primero para TC CMR como modelo piloto y luego extender al resto.

---

## 12. Plan de Trabajo (Sin Cronograma)

### Etapa 1: Correccion del scaffold y ajuste de configuracion [COMPLETADA]
- [x] Corregir `config_rutas_ext_y_archivos.yaml` (quitar Access, agregar TXT, agregar params externos)
- [x] Corregir `ml_tc_cmr.py` scaffold para referenciar claves YAML correctas
- [x] Actualizar este documento con respuestas confirmadas
- [ ] Colocar `parametros_ml_tc_cmr.xlsx` en `parametros/` (pendiente: definir contenido del xlsx)

### Etapa 2: Integracion Fase 1 (Preparacion)
- Adaptar modulos de `preparacion/` al sistema de config del repositorio
- Resolver dependencias Python
- Eliminar modos testing/homologacion (no necesarios en produccion)
- Implementar copia local de archivos de red a `data/`
- Migrar tabla de perfiles PP de hardcodeada a lectura de `tabla_perfiles_pp.csv`
- Simplificar/eliminar config_manager (usar el sistema del repo)
- Validar output contra referencia conocida

### Etapa 3: Integracion Fase 2 (Calculo de Flujos)
- Adaptar los modulos de calculo al repositorio
- Resolver dependencias Python
- Leer CSV intermedio generado por Fase 1
- Mantener toda la logica de negocio intacta
- Validar contra output del script R (gold standard)

### Etapa 4: Completar/Reescribir Fase 3 (Post-proceso)
- Completar `tabla_desarrollo.py`
- Asegurar que el output final tiene el esquema DESARROLLO estandar
- Generar `FLUJOS_MODELO_CMR.xlsx` para validacion
- Integrar escritura del .xlsm via openpyxl/bfa_cl_utilidades
- Validar contra output de produccion actual

### Etapa 5: Integracion del orquestador
- Completar `ml_tc_cmr.py` con `ejecutar_modelo()` que orqueste las 3 fases
- Probar ejecucion end-to-end
- Activar en orquestador (`activado: True`)
- Probar carga a BigQuery

### Etapa 6: Validacion final
- Validar output completo vs produccion actual (VBA + R)
- Verificar carga correcta a BigQuery
- Verificar schema contra ML_TC_CMR.xlsm existente
- Actualizar documentacion en `docs/modelos/tc-cmr.md`

---

## 13. Siguientes Pasos Inmediatos

1. ~~Revisar este documento juntos y resolver las preguntas P1-P18~~ **COMPLETADO**
2. ~~Confirmar la estructura (modular vs monolitico)~~ **COMPLETADO: modular**
3. ~~Confirmar las rutas de archivos de entrada/salida~~ **COMPLETADO**
4. **Empezar Etapa 2**: Integrar Fase 1 (Preparacion) adaptando el codigo existente de dev/
5. **En paralelo**: Obtener archivo `ML_TC_CMR.xlsm` de produccion para verificar schema

---

*Documento de trabajo. v2 actualizada con todas las respuestas confirmadas del usuario.*
