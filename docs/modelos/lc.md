# Modelo de Línea de Crédito (ML LC)

## Descripción General

El modelo de Línea de Crédito (ML LC) proyecta los flujos de caja futuros para productos de líneas de crédito, utilizando un enfoque de **decay rate** con ajustes estacionales. El modelo calcula la evolución temporal del saldo considerando factores de decaimiento y patrones cíclicos mensuales y bisemanales.

## Ubicación

```
RF_Modelo_Linea_de_Credito/
├── ml_lc.py                    # Implementación principal del modelo
├── ml_lc.xlsm                  # Plantilla Excel para resultados
├── parametros/                 # Parámetros del modelo
│   └── [archivos de parámetros]
└── __pycache__/
```

## Productos Soportados

| Código Modelo | Descripción | Moneda |
|---------------|-------------|--------|
| `LC_CLP` | Línea de Crédito | CLP |

## Arquitectura del Modelo

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│                    ejecutar_modelo()                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              procesar_datos_iniciales()                      │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ cargar_datos_balance│  │  cargar_parametros  │           │
│  └─────────────────────┘  └─────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              tabla_desarrollo_modelo()                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         calculo_estimacion_modelo()                  │    │
│  │  • Cálculo de mu_tenor (factor estacional)          │    │
│  │  • Factores mensual y bisemanal                      │    │
│  │  • Proyección con decay rate                         │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         cargar_ml_lc_egreso()                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Guardado en Excel (DESARROLLO)                  │
└─────────────────────────────────────────────────────────────┘
```

## Metodología

### Fórmula del Modelo

El modelo utiliza la siguiente formulación para proyectar los saldos:

#### 1. Factor de Tenor (μ)

$$\mu_{tenor} = \frac{(fecha_{tenor} - primer\_dia\_mes)}{(ultimo\_dia\_mes - primer\_dia\_mes)}$$

#### 2. Factor Mensual

$$Factor_{mensual} = e^{\gamma_1 \cdot \cos(2\pi \cdot \mu) + \delta_1 \cdot \sin(2\pi \cdot \mu)}$$

#### 3. Factor Bisemanal

$$Factor_{bisemanal} = e^{\gamma_2 \cdot \cos(4\pi \cdot \mu) + \delta_2 \cdot \sin(4\pi \cdot \mu)}$$

#### 4. Factor de Decaimiento

$$Factor_{decaimiento} = \max(0, \lambda + z_{95} \cdot \sigma_{\lambda})$$

Donde:
- $\lambda$ = Decay Rate
- $\sigma_{\lambda}$ = Decay Rate Accuracy
- $z_{95}$ = 1.645 (percentil 95 de la distribución normal)

#### 5. Ratio del Modelo

$$Ratio_{modelo} = \frac{Factor_{mensual,tenor}}{Factor_{mensual,hoy}} \cdot \frac{Factor_{bisemanal,tenor}}{Factor_{bisemanal,hoy}} \cdot e^{-Factor_{decaimiento} \cdot t}$$

#### 6. Proyección

$$Proyección_t = Ratio_{modelo} \cdot Flujo_{total,MO}$$

## Parámetros del Modelo

### Parámetros de Entrada (Hoja FACTORES)

| Parámetro | Descripción | Uso |
|-----------|-------------|-----|
| `GAMMA_1` | Coeficiente coseno del factor mensual | Estacionalidad mensual |
| `DELTA_1` | Coeficiente seno del factor mensual | Estacionalidad mensual |
| `GAMMA_2` | Coeficiente coseno del factor bisemanal | Estacionalidad bisemanal |
| `DELTA_2` | Coeficiente seno del factor bisemanal | Estacionalidad bisemanal |
| `DECAY_RATE` | Tasa de decaimiento base | Velocidad de reducción del saldo |
| `DECAY_RATE_ACURRACY` | Precisión del decay rate | Ajuste estadístico (z_95) |

### Parámetros de Egreso (Hoja LC_EGRESO)

Contiene los flujos de egreso predefinidos para líneas de crédito con columnas:
- `DIAS_AL_VENCIMIENTO_BORRAR`: Días al vencimiento
- Columnas estándar de la tabla de desarrollo

## Funciones Principales

### `ejecutar_modelo(fecha_proceso: datetime) -> bool`

Función principal que orquesta todo el proceso del modelo.

**Parámetros:**
- `fecha_proceso`: Fecha de procesamiento

**Retorna:**
- `True` si la ejecución fue exitosa
- `False` si ocurrió un error

### `cargar_datos_balance(fecha_t: datetime) -> pd.DataFrame`

Carga los datos de balance desde la base de datos MS Access.

**Filtros aplicados:**
- `Cod_Sub_Pro = 'LINEA DE CREDITO'`
- Fecha de proceso específica

**Campos retornados:**
- `FLUJO_MO`: Suma de Capital + Interés
- `AMORTIZACION_MO`: Suma de amortizaciones
- `INTERES_MO`: Suma de intereses

### `calculo_estimacion_modelo(datos_modelo: pd.DataFrame, fecha_proceso: datetime, n_iteraciones: int = 1095) -> pd.DataFrame`

Calcula las proyecciones del modelo para N iteraciones (por defecto 1095 días ≈ 3 años).

**Proceso:**
1. Calcula factores base para la fecha de proceso
2. Itera sobre cada día futuro calculando:
   - Factor mensual del tenor
   - Factor bisemanal del tenor
   - Ratio de dinámicas estacionales
   - Ratio de vintage (decaimiento exponencial)
3. Genera proyecciones y saldos

### `calculadora_mu_tenor(fecha: datetime) -> float`

Calcula el factor μ que representa la posición relativa de una fecha dentro del mes.

**Fórmula:**
```
μ = (fecha - primer_día_mes) / (último_día_mes - primer_día_mes)
```

**Rango:** [0, 1]

## Salidas del Modelo

### Tabla de Desarrollo (Hoja DESARROLLO)

| Campo | Descripción |
|-------|-------------|
| `FECHA_PROCESO` | Fecha de ejecución |
| `CODIGO_EMPRESA` | Código de empresa (1) |
| `COD_ACT/PAS` | ACT para ingresos, PAS para egresos |
| `MONEDA_ORIGEN` | CLP |
| `CODIGO_PRODUCTO` | ML_C46_Linea_de_Credito_Ingreso_Ajustado / Egreso_Ajustado |
| `CODIGO_SUBPRODUCTO` | Igual a CODIGO_PRODUCTO |
| `FECHA_VENCIMIENTO_CUOTA` | Fecha proyectada del flujo |
| `FECHA_PAGO` | Igual a FECHA_VENCIMIENTO_CUOTA |
| `FECHA_REPRICING` | Igual a FECHA_VENCIMIENTO_CUOTA |
| `AMORTIZACION` | Monto del flujo (valor absoluto) |
| `AREA_NEGOCIO` | BALANCE TASAS |
| `CODIGO_ESTRATEGIA` | BALANCE TASAS |
| `CLASIFICACION_CONTABLE` | HTM |
| `TIPO_CUOTA` | 1 |
| `TIPO_TASA` | 1 |

## Configuración

### Archivos de Configuración

```yaml
# config_rutas_ext_y_archivos.yaml
modelos:
  ml_lc:
    ms_access_input: [ruta a BD de gestión]
    excel_output: [ruta al archivo de salida .xlsm]
    excel_parametros_modelo_input: [ruta a parámetros del modelo]
```

## Uso

### Ejecución desde Línea de Comandos

```bash
# Ejecutar modelo para una fecha específica
python main.py --fecha 2026-02-03 --modelos ml_lc

# Ejecutar y cargar a BigQuery
python main.py --fecha 2026-02-03 --modelos ml_lc --cargar-gcp
```

### Ejecución Directa del Script

```bash
cd RF_Modelo_Linea_de_Credito
python ml_lc.py 2026-02-03
```

## Ejemplo de Ejecución

```
============================================================
INICIO DEL PROCESO - MODELO LÍNEA DE CRÉDITO
Fecha de proceso: 03-02-2026
============================================================

[1/3] Procesando datos iniciales del modelo...
      • Ejecutando consulta de datos de balance...
        - Datos de balance cargados: 1 registros
        - Productos encontrados: {'LC_CLP': 1}
          ✓ Datos de balance procesados exitosamente
      • Leyendo parámetros del modelo...
      ✓ Datos iniciales procesados correctamente

[2/3] Generando tabla de desarrollo del modelo...
      • Iniciando cálculo de estimaciones del modelo...
        - Número de iteraciones configurado: 1,095
        - Procesando producto: LC_CLP
          • Parámetros del modelo cargados:
            - Flujo total MO: 1,234,567.89
            - Gamma_1: 0.012345, Delta_1: 0.023456
            - Gamma_2: 0.034567, Delta_2: 0.045678
            - Decay Rate: 0.001234
          • Factores base calculados:
            - Factor mensual hoy: 1.012345
            - Factor bisemanal hoy: 1.034567
            - Factor decaimiento: 0.001456
          ✓ Proyecciones calculadas para 1,095 períodos
          • Calculando saldos del modelo...
          ✓ 1,096 saldos calculados
          ✓ Producto LC_CLP procesado exitosamente
      • Aplicando clasificaciones y códigos...
      • Cargando datos de egresos LC...
      ✓ Tabla de desarrollo generada exitosamente

[3/3] Guardando resultados en Excel...
        - Actualizando archivo principal...
          ✓ Archivo principal actualizado

============================================================
PROCESO FINALIZADO EXITOSAMENTE
Total de registros procesados: 1,150
============================================================
```

## Consideraciones Técnicas

### Dependencias

- `pandas`: Manipulación de datos
- `numpy`: Cálculos numéricos
- `scipy.stats`: Distribución normal (norm.ppf)
- `bfa_cl_utilidades`: Utilidades corporativas (lectura MS Access, carga Excel)

### Validaciones

1. **Datos vacíos**: El modelo valida que existan datos para la fecha de proceso
2. **Parámetros requeridos**: Verifica que todos los parámetros del modelo estén presentes
3. **Productos mapeados**: Solo procesa productos con mapeo válido (LC_CLP)

### Notas de Implementación

- El modelo genera **1095 iteraciones** por defecto (≈ 3 años de proyección diaria)
- Los saldos negativos se clasifican como **egreso (PAS)**
- Los saldos positivos se clasifican como **ingreso (ACT)**
- El último registro incluye la diferencia residual para cuadrar con el flujo total

## Historial de Cambios

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| 1.0.0 | 2026-02-03 | Versión inicial del modelo |
