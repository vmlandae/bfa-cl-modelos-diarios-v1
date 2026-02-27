# Benchmark: Ejecución Paralela vs Secuencial — Primera Vuelta

> **Fecha del benchmark:** 2026-02-27  
> **Fecha de datos:** 2026-02-26  
> **Equipo:** 8 CPUs lógicos, 15.7 GB RAM  
> **Script:** `sandbox/benchmark_paralelo_vs_secuencial.py`

---

## 1. Resultados del Benchmark

### Tiempos por modelo

| Modelo | Paralelo | Secuencial | Ratio |
|---|---:|---:|---:|
| mr_prepago_consumo | 43.4s | 5.7s | 7.6× más lento en paralelo |
| mr_prepago_hipotecario | 68.9s | 20.7s | 3.3× más lento |
| ml_mora_consumo | 111.7s | 59.2s | 1.9× más lento |
| ml_mora_cae | 59.2s | 8.3s | 7.1× más lento |
| ml_mora_hipotecario | 57.4s | 9.2s | 6.2× más lento |
| ml_mora_comercial | 59.8s | 9.5s | 6.3× más lento |
| **Suma individual** | **400.4s** | **112.7s** | |
| **Wall-clock total** | **111.7s** | **112.7s** | |

### Speedup

- **Speedup:** 1.01×  
- **Ahorro absoluto:** 1.0s (insignificante)

### Uso de recursos

| Métrica | Paralelo | Secuencial |
|---|---:|---:|
| CPU promedio | 88.5% | 85.4% |
| CPU máximo | 198.1% | 120.0% |
| Memoria pico | 424 MB | 341 MB |
| Memoria promedio | 390 MB | 321 MB |

---

## 2. Diagnóstico: ¿Por qué el paralelo no funciona?

### El GIL de Python

La causa raíz es el **Global Interpreter Lock (GIL)** de CPython.
`ThreadPoolExecutor` crea hilos del sistema operativo, pero el GIL
solo permite que **un hilo ejecute bytecode Python a la vez**.

Los modelos son **CPU-bound** (cálculos con pandas/numpy, iteraciones
en Python puro). Cuando 6 hilos compiten por el GIL:

- Cada modelo individual tarda **3-7× más** que corriendo solo
- La suma de tiempos individuales explota de 113s a 400s
- El wall-clock queda igual porque todo se serializa detrás del GIL,
  comprimido al tiempo del modelo más lento (ml_mora_consumo ≈ 112s)

### Evidencia

- **CPU máximo 198%** = solo 2 cores efectivos de 8.
  Si hubiera paralelismo real, veríamos ~600-800%.
- **Memoria +83 MB** en paralelo = 6 DataFrames y estructuras
  intermedias cargados simultáneamente, sin beneficio de velocidad.

---

## 3. Análisis interno de cada modelo

### Estructura común

Todos los modelos siguen el mismo flujo:

```
ejecutar_modelo(fecha)
  ├── lectura_parametros_modelo()     # I/O: Excel → DataFrames
  ├── lectura_interfaz_de_datos()     # I/O: parquet caché → DataFrame + filtro
  └── procesamiento_y_guardado()      # Cómputo + I/O escritura xlsm
        ├── preparar/filtrar datos
        ├── cálculo principal (matrices, np.dot, etc.)
        └── escribir resultado a .xlsm
```

### Desglose estimado de tiempo por fase

| Modelo (sec total) | Leer Interfaz | Leer Params (Excel) | Filtrar DF | Cómputo | Escribir xlsm |
|---|:---:|:---:|:---:|:---:|:---:|
| **mr_prepago_consumo** (5.7s) | ~15% | ~10% | ~5% | **~50%** | ~20% |
| **mr_prepago_hipotecario** (20.7s) | ~10% | ~5% | ~5% | **~65%** | ~15% |
| **ml_mora_consumo** (59.2s) | ~5% | **~35%** | ~5% | ~20% | **~35%** |
| **ml_mora_cae** (8.3s) | ~10% | **~25%** | ~2% | ~15% | **~48%** |
| **ml_mora_hipotecario** (9.2s) | ~10% | **~25%** | ~2% | ~15% | **~48%** |
| **ml_mora_comercial** (9.5s) | ~10% | **~25%** | ~2% | ~15% | **~48%** |

> **Nota:** los porcentajes son estimaciones basadas en análisis del
> código, no mediciones con profiler. Un próximo paso sería instrumentar
> cada fase con `time.perf_counter()`.

### Observaciones clave

1. **Lectura de interfaz (parquet):** Después de la primera lectura que
   genera el `.parquet` (2.9 MB), las lecturas subsiguientes son
   casi instantáneas. **No es cuello de botella.**

2. **Lectura de parámetros Excel:** Los modelos de mora leen matrices
   366×366 desde Excel, lo cual es lento. `ml_mora_consumo` lee
   **7 hojas** (5 son matrices 366×366). Esto domina su tiempo.

3. **Escritura xlsm:** `ut.cargar_datos_xlsm()` (openpyxl) es I/O
   intensivo. `ml_mora_consumo` escribe **6 hojas** en **2 archivos**
   xlsm y esto aporta un % muy relevante de su tiempo.

4. **Cómputo puro (numpy):** Solo es dominante en los modelos de
   prepago. En hipotecario la matriz es 366×366 con iteración Python
   por escenario × categoría. En consumo la matriz es 90×90 (rápido).

5. **Filtrado de DataFrames:** Trivial en todos los modelos (<5%).
   Son simples máscaras booleanas sobre un DataFrame ya en memoria.

---

## 4. Propuestas de optimización

### Opción A: Volver a ejecución secuencial

**Complejidad:** Baja  
**Ganancia estimada:** ~1s más lento en wall-clock, pero mucho más simple

| Pro | Contra |
|---|---|
| Sin race conditions, sin locks | Teóricamente ~1s más lento (imperceptible) |
| Logs lineales legibles | |
| -83 MB de RAM pico | |
| Cada modelo individual 3-7× más rápido | |
| Debugging trivial | |

**Implementación:** Cambiar `ThreadPoolExecutor` por un `for` loop
en `ejecutar_modelos_paralelo()`.

**Recomendación:** ✅ **Hacer esto como primer paso.** Elimina toda la
complejidad de threading sin costo de rendimiento.

---

### Opción B: Paralelismo real con `ProcessPoolExecutor`

**Complejidad:** Media-Alta  
**Ganancia estimada:** Potencialmente 2-3× en wall-clock

| Pro | Contra |
|---|---|
| Procesos separados = sin GIL | Cada proceso carga su propia copia de pandas/numpy (~200 MB × 6) |
| Paralelismo real en CPU | Los modelos importan módulos con efectos secundarios (logging, YAML config) |
| | Comunicación inter-proceso es costosa (pickle/serialización) |
| | Complejidad de errors, logs dispersos |
| | Memoria total podría llegar a ~1.5-2 GB |

**Implementación:** Cambiar `ThreadPoolExecutor` por
`ProcessPoolExecutor`. Requiere que los modelos sean "pickle-safe"
y que el logging funcione cross-process.

**Recomendación:** ⚠️ Solo considerar si el wall-clock de 112s es
inaceptable. Costo de implementación alto vs ganancia incierta.

---

### Opción C: Cachear parámetros Excel como Parquet

**Complejidad:** Baja-Media  
**Ganancia estimada:** 30-50% en modelos de mora (especialmente consumo)

Los archivos de parámetros Excel (matrices 366×366) se leen con
`pd.read_excel()` que es notoriamente lento. Podemos aplicar
la misma estrategia F14: leer una vez → guardar como `.parquet`
→ en re-ejecuciones leer parquet.

**Ejemplo:** `ml_mora_consumo` lee 7 hojas Excel. Si las 5 matrices
366×366 se cachean en parquet:
- Primera ejecución: igual (lee Excel + guarda parquet)
- Re-ejecuciones: parquet ~10× más rápido que Excel

| Modelo | Hojas Excel | Matrices 366×366 | Ganancia estimada |
|---|---:|---:|---|
| ml_mora_consumo | 7 | 5 | ~35% del tiempo total |
| ml_mora_cae | 3 | 1 | ~20% |
| ml_mora_hipotecario | 3 | 1 | ~20% |
| ml_mora_comercial | 3 | 1 | ~20% |
| mr_prepago_consumo | 2 | 0 | ~5% (hojas pequeñas) |
| mr_prepago_hipotecario | 2 | 0 | ~5% |

**Implementación:** Crear `leer_parametros_con_cache()` análogo
a `leer_interfaz_con_cache()`. Clave: invalidar solo si el .xlsx
de parámetros cambió (por fecha de modificación del archivo).

**Recomendación:** ✅ **Alto impacto en re-ejecuciones**, bajo riesgo.

---

### Opción D: Compartir el DataFrame de interfaz pre-filtrado

**Complejidad:** Baja  
**Ganancia estimada:** Marginal (~1-2s total)

La idea: en modo secuencial, leer el parquet **una sola vez** al
inicio y pasarlo como argumento a cada modelo, en vez de que cada
uno lea el parquet independientemente.

**Análisis:** El parquet de interfaz pesa 2.9 MB y se lee en <0.5s.
Con 6 modelos leyéndolo secuencialmente = ~3s. Ahorro de ~2.5s si
se lee una sola vez. No es significativo.

**Variación más interesante:** Pre-filtrar los DataFrames por modelo
antes de pasarlos. Esto eliminaría la lectura de parquet Y el filtrado,
pero ambos juntos son <1s por modelo.

**Recomendación:** ⬜ Ganancia muy marginal. Solo implementar si
se refactoriza la interfaz de `ejecutar_modelo()` por otras razones.

---

### Opción E: Optimizar escritura xlsm (openpyxl)

**Complejidad:** Media  
**Ganancia estimada:** 20-40% en modelos de mora

`openpyxl` es el cuello de botella de escritura. Alternativas:

1. **Escribir a `.xlsx` con `xlsxwriter`** (2-5× más rápido que
   openpyxl), luego renombrar a `.xlsm` si no necesita macros
   reales. Incompatible si los xlsm tienen macros VBA.

2. **Eliminar el paso `cargar_datos_xlsm()` si GCP es el destino
   final** — escribir directamente a BigQuery sin xlsm intermedio.

3. **Escribir parquet como output intermedio** y generar xlsm solo
   bajo demanda (ej: con flag `--generar-excel`).

**Recomendación:** ⬜ Evaluar si las macros VBA son realmente necesarias.
Si no, `xlsxwriter` es un quick win. Si GCP es el objetivo,
eliminar xlsm es la solución definitiva.

---

### Opción F: Profile instrumentado por fase

**Complejidad:** Baja  
**Ganancia estimada:** No directa, pero permite priorizar las demás

Antes de optimizar, **medir**. Añadir `time.perf_counter()` al
inicio y fin de cada fase (`leer_params`, `leer_interfaz`, `calcular`,
`escribir`) dentro de cada modelo. Con datos reales podemos:

- Confirmar o desmentir los porcentajes estimados arriba
- Priorizar dónde invertir esfuerzo
- Medir el impacto real de cada optimización

**Implementación:** Decorador o context manager simple que loguee
duración por fase al logger existente.

**Recomendación:** ✅ **Hacer primero**, cuesta 30 minutos y
da visibilidad real.

---

## 5. Plan de acción sugerido (priorizado)

| Prioridad | Acción | Esfuerzo | Impacto |
|:---:|---|---|---|
| 1 | **Instrumentar fases** con `time.perf_counter()` por modelo | 30 min | Visibilidad real |
| 2 | **Cambiar a secuencial** para primera vuelta | 15 min | Simplicidad, -83 MB RAM |
| 3 | **Cachear parámetros Excel** como parquet | 2-3 hrs | -30-50% en mora (re-ejecuciones) |
| 4 | Evaluar eliminar xlsm si GCP es destino final | Decisión | -20-40% en mora |
| 5 | `ProcessPoolExecutor` solo si wall-clock > umbral | 1 día | Potencial 2-3× pero alto costo |

---

## 6. Conclusión

La ejecución paralela con `ThreadPoolExecutor` **no aporta beneficio
medible** en este proyecto debido al GIL de Python. Cada modelo se
ejecuta ~3-7× más lento por la contención de hilos, y el wall-clock
total queda prácticamente igual (1s de diferencia).

El cuello de botella **no es la lectura de la interfaz PML** (ya
optimizada con F14), sino:

- **Lectura de parámetros Excel** (dominante en modelos de mora)
- **Escritura de archivos xlsm** (openpyxl, lento por naturaleza)
- **Cómputo matricial en Python puro** (dominante en prepago hipotecario)

La primera acción concreta debería ser **instrumentar las fases** para
tener datos reales, seguido de **cambiar a secuencial** (gratis en
rendimiento, gran ganancia en simplicidad) y **cachear parámetros
Excel** (alto impacto en re-ejecuciones).
