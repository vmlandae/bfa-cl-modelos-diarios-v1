# Modelo TC CMR (ML TC CMR)

## Descripcion General

El modelo TC CMR (Tarjeta de Credito CMR) proyecta los flujos de caja futuros esperados (ingresos) para la cartera de tarjetas de credito CMR. Dado el stock actual de deuda en tarjetas, estima cuando y cuanto se espera recibir en pagos, dia a dia, usando factores historicos de probabilidad de pago por perfil de cliente y dia del mes.

## Ubicacion

```
RF_Modelo_TC_CMR/
+-- __init__.py
+-- ml_tc_cmr.py               # Implementacion principal del modelo
+-- ml_tc_cmr.xlsm             # Plantilla Excel para resultados (hoja DESARROLLO)
+-- preparacion/               # Fase 1: preparacion de datos
|   +-- maestro.py             # Orquestacion Fase 1
|   +-- cargar_cartera.py      # Carga TXT cartera CMR
|   +-- tratamiento.py         # Clasificacion N/R/V
|   +-- cargar_cartera_t30.py  # Carteras historicas T-30
+-- calculo/                   # Fase 2: calculo de flujos
|   +-- calcular_fechas.py     # Periodos facturacion
|   +-- calcular_flujos.py     # Revolventes + pago estimado
+-- postproceso/               # Fase 3: tabla de desarrollo
|   +-- tabla_desarrollo.py    # Formateo output estandar
+-- parametros/                # Parametros del modelo
|   +-- parametros_ml_tc_cmr.xlsx
+-- dev/                       # Codigo fuente de referencia
```

## Arquitectura del Modelo

### Pipeline de 3 Fases

```
+-----------------------+     +-----------------------+     +-----------------------+
|   FASE 1              |     |   FASE 2              |     |   FASE 3              |
|   MAESTRO             |---->|   Calculo de Flujos   |---->|   TablaDesarrollo     |
|   (Preparacion)       |     |   (TC_CMR_ING)        |     |   (Post-proceso)      |
+-----------------------+     +-----------------------+     +-----------------------+
         |                            |                            |
         v                            v                            v
  INPUT_TC-CMR_              OUTPUT_TC_CMR_              ML_TC_CMR.xlsm
  FAC_ANT.csv                INGRESO_{fecha}.txt        FLUJOS_MODELO_CMR.xlsx
```

### Fase 1: Preparacion (MAESTRO)
- Carga cartera diaria TXT (`ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT`)
- Clasifica registros: Normal / Reemplazo / Vencido
- Carga 6 carteras historicas T-30 + fecha proceso
- Asigna perfiles de pago (P00-P14) via tabla externa

### Fase 2: Calculo de Flujos
- Filtra por producto TC, excluye destinos V y R
- Aplica factor de ajuste global (FG, actualizado anualmente)
- Calcula periodos de facturacion y expande a nivel diario
- Calcula revolventes (porcion no pagada que rueda al periodo siguiente)
- Estima pagos: `PAGO_EST = FLUJO_MES x FACTOR`

### Fase 3: Tabla de Desarrollo
- Formatea output al esquema estandar DESARROLLO (para BigQuery)
- Genera FLUJOS_MODELO_CMR.xlsx (validacion interna)
- Actualiza ML_TC_CMR.xlsm (hoja DESARROLLO -> BigQuery)

## Datos de Entrada

| Archivo | Formato | Origen |
|---------|---------|--------|
| `ProductosMercadoLiquidezCMR{YYYYMMDD}.TXT` | TXT `;` latin-1 | Red: `\\vmdvorak\...\RRFF-GCP\Cartera\input` |
| `Perfil_Factor.csv` | CSV `;` | Red: `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/` |
| `tabla_perfiles_pp.csv` | CSV | Red: `Z:/RF_PROCESOS/RF_Modelos/RF_Modelo_TC_CMR/` |
| `parametros_ml_tc_cmr.xlsx` | Excel | Local: `parametros/` |

> **Nota**: El archivo TXT de cartera CMR es diferente al que usan otros modelos (CMR vs GCP). Misma carpeta, distinto nombre.

## Funciones Principales

### `ejecutar_modelo(fecha_proceso: datetime) -> bool`

Funcion principal que orquesta las 3 fases del pipeline.

**Parametros:**
- `fecha_proceso`: Fecha de procesamiento

**Retorna:**
- `True` si la ejecucion fue exitosa
- `False` si ocurrio un error

## Configuracion

### Archivos de Configuracion

```yaml
# config_rutas_ext_y_archivos.yaml
modelos:
  ml_tc_cmr:
    txt_cartera_input: [ruta a carpeta de carteras TXT]
    txt_cartera_pattern: "ProductosMercadoLiquidezCMR{fecha}.TXT"
    perfil_factor_input: [ruta a Perfil_Factor.csv]
    tabla_perfiles_pp_input: [ruta a tabla_perfiles_pp.csv]
    excel_parametros_modelo_input: "RF_Modelo_TC_CMR/parametros/parametros_ml_tc_cmr.xlsx"
    excel_output: "RF_Modelo_TC_CMR/ml_tc_cmr.xlsm"
    excel_flujos_output: "RF_Modelo_TC_CMR/FLUJOS_MODELO_CMR.xlsx"
```

## Uso

### Ejecucion desde Linea de Comandos

```bash
# Ejecutar modelo para una fecha especifica
python main.py --fecha 2026-02-16 --modelos ml_tc_cmr

# Ejecutar y cargar a BigQuery
python main.py --fecha 2026-02-16 --modelos ml_tc_cmr --cargar-gcp
```

## Dependencias

- `pandas`: Manipulacion de datos
- `numpy`: Calculos numericos
- `openpyxl`: Escritura de archivos Excel
- `bfa_cl_utilidades`: Utilidades corporativas

## Historial de Cambios

| Version | Fecha | Descripcion |
|---------|-------|-------------|
| 0.1.0 | 2026-02-16 | Scaffold inicial del modelo |
| 0.1.1 | 2026-02-17 | Correccion YAML (TXT en vez de Access), documentacion actualizada |
