# Cuadre MR Prepago CMR -- notebook productivo vs `mr_prepago_cmr.py`

> Estado: 2026-04-27  
> Contexto: el cuadre fila a fila entre el productivo (`Generador_Prepago_TC_CMR_Productivo.ipynb`) y el modelo nuevo del repo (`RF_Modelo_Prepago_CMR/mr_prepago_cmr.py`) muestra ~210 filas extra en el modelo nuevo y diferencias de saldos relevantes para 2026-04-24. Hoy se subio el productivo a BQ "tal cual" (parche temporal) para no bloquear la migracion GCP.

## 1. Resumen ejecutivo

- El **nucleo matematico** (matriz de prepago `f[i,j]`, vector de supervivencia, separacion capital/interes) es **identico** en ambas implementaciones. Si los inputs fueran iguales, los resultados deberian cuadrar al centavo.
- Las diferencias provienen de **como se preparan los inputs antes** de llamar al modelo y, posiblemente, de una **diferencia de unidad en SMM** que hay que confirmar con metodologias.
- Plan de corto plazo: copiar `mr_prepago_cmr.py` a `mr_prepago_cmr_dev_v0.py` y dejarlo como traduccion 1:1 del notebook al repo (sin tocar el flujo del orquestador). Asi tenemos algo controlado y replicable, y desde ahi iteramos hasta cuadrar al centavo.

## 2. Componentes equivalentes (no son fuente de diferencia)

| Componente | Notebook | `mr_prepago_cmr.py` |
|---|---|---|
| Lectura Access | `SELECT * FROM RF_BD_Gestion_RM WHERE Cod_Pro='TARJETA DE CREDITO'` | igual, via cache parquet |
| Renombre columnas | `Fec_Pro -> FECHA_PROCESO`, etc. | identico |
| Matriz `f[i,j]` triangular | doble loop con prepago en diagonal | doble loop equivalente |
| Vector de supervivencia para interes | `Vector_CX = cumprod(1 - F*SMM)` desplazado | `factor_ajuste_interes = insert(cumprod[:-1], 0, 1.0)` |
| Flujo total | `diag(matriz)` | `np.diag(f)` |
| Interes ajustado | `max(Vector_CX[i] * I_i, 0)` | `np.maximum(0, interes * factor_ajuste)` |
| Capital | `Vector_Prepago - Interes_ajustado` | `flujo_total - flujo_interes` |

## 3. Diferencias funcionales (estas SI explican el descuadre)

### 3.1. Mapeo del dia de facturacion 28/29 -> 30

- **Notebook:** `df['Dia_F'] = df['Dia_F'].replace({28: 30, 29: 30})` siempre, para todos los productos.
- **`mr_prepago_cmr.py`:** solo aplica `28 -> 30` cuando `GLOSA == "SAV"` y `mes == 2`. El resto del tiempo el dia 28/29 forma su propio bucket de facturacion.

**Impacto:** el modelo nuevo genera 1-2 grupos extra por subproducto, escenario y dia. Es la fuente principal del +210 filas observado en BQ.

**Interpretacion:** el ciclo de facturacion CMR es el dia 30; cuando el mes es corto, el cargo cae el 28 o 29. Conceptualmente, el notebook trata correctamente esos dias como parte del mismo ciclo. El nuevo los fragmenta.

**Veredicto provisional:** el notebook es mas correcto para el ciclo CMR.

### 3.2. Construccion del calendario para la matriz `N x 90`

- **Notebook:** `groupby('FECHA_VENCIMIENTO_CUOTA')` directo sobre datos reales. `N` = numero de fechas con saldo. Sin huecos artificiales.
- **`mr_prepago_cmr.py`:** construye un vector de 200 meses futuros desde `fecha_ini`, hace `merge LEFT` contra los datos reales, rellena con cero, trunca al ultimo no-cero o al periodo 90.

**Impacto:** cuando hay meses sin flujo entre meses con flujo, el nuevo aplica `SMM` sobre saldos que el notebook no tiene en su matriz. Filas que aparecen como "solo_bq" en el cuadre.

**Interpretacion:** SMM (Single Monthly Mortality) **es** una tasa mensual; en teoria deberia aplicarse mes a mes aunque no haya flujo. En CMR los flujos son mensuales por construccion del producto, asi que en la practica no deberia haber huecos y ambos enfoques deberian dar lo mismo. La divergencia surge en bordes (ej. ultimo periodo, primera fecha post-`fecha_t`).

**Veredicto provisional:** indeterminado. Requiere conversacion con metodologias para fijar la convencion.

### 3.3. Cuotas MORA con fecha vencida

- **Notebook:** detecta `*MORA*` en `CODIGO_SUBPRODUCTO`, fuerza `Plazo_Antiguo='NO'` y las concatena a `df_NO_sav`. Es decir, **incluye** las cuotas con `Fec_Vcto < Fec_Pro`.
- **`mr_prepago_cmr.py`:** no tiene logica especial para MORA, pero el `merge` contra `fechas_vector_smm[fechas > fecha_t]` **descarta** cualquier cuota vencida.

**Impacto:** capital en mora se pierde en el modelo nuevo. Reduce filas y monto AMORTIZACION en algunos grupos.

**Interpretacion:** la cuota MORA vencida representa un saldo que el banco aun no cobra. Desde la perspectiva de riesgo de tasa, ese capital sigue ahi. El notebook lo modela como si venciera "ahora". El nuevo lo ignora.

**Veredicto provisional:** el notebook es mas correcto.

### 3.4. SMM como porcentaje vs decimal (HIPOTESIS A VALIDAR)

- **Notebook (SAV):** `SMM_SAV = 0.7866; SMM = SMM_SAV / 100  # = 0.007866 mensual`.
- **`mr_prepago_cmr.py`:** lee `smm_modelo[sub_producto]` desde `parametros_mr_prepago_cmr.xlsx` hoja `SMM_PREPAGO` y lo usa **directo** sin dividir.

**Riesgo:** si el Excel de parametros tiene los valores como porcentaje (`0.7866`), el modelo nuevo aplica un SMM 100x el correcto -> sobre-amortiza fuertemente.

**Accion:** abrir `RF_Modelo_Prepago_CMR/parametros/parametros_mr_prepago_cmr.xlsx` -> hoja `SMM_PREPAGO` y verificar la unidad.

### 3.5. Diferencias menores

| Tema | Notebook | `mr_prepago_cmr.py` |
|---|---|---|
| `CODIGO_EMPRESA` | `3` | `1` |
| Mapeo SAV/NO_SAV | `startswith('SUPER AVANCE')` heuristica | dict explicito; lanza error con codigo nuevo |
| Validacion dias permitidos | no valida | valida (no incluye 29 en el set) |
| Escenarios | hardcoded `[1.0, 0.8, 1.2]` con codigos `BASE/UP/DOWN` | leidos de Excel `parametros` hoja `ESCENARIO` |
| Snapshot historico | si guarda `Prepago_CMR_Historia/{fecha}_Prepago_TC_CMR.xlsx` | NO lo guarda (regresion) |
| Variable `Plazo_Antiguo` | calculada pero solo se invoca con `"NO"` (codigo muerto) | no existe |

## 4. Aspectos cuestionables del notebook (no son bugs, pero conviene anotarlos)

1. `Plazo_Antiguo` se calcula y nunca se usa con `"SI"`. Codigo muerto.
2. `Fechas_Facturacion = df.Dia_F.unique()` se usa para SAV y NO_SAV; si SAV no tiene un dia que NO_SAV si, se itera vacio (resultado vacio silencioso, ineficiente).
3. `df_vcdos_mora["Plazo_Antiguo"] = "NO"` dispara `SettingWithCopyWarning` (slice de slice).
4. `pd.concat([df_desarrollo], ignore_index=True)` con un solo DF no aporta.
5. `CODIGO_EMPRESA = 3` esta hardcoded sin justificacion documentada.

## 5. Hipotesis ordenadas por probabilidad de impacto

| # | Hipotesis | Tipo | Probabilidad | Esfuerzo de validar |
|---|---|---|---|---|
| H1 | Dias 28/29 fragmentados en buckets propios (no SAV-feb) generan ~210 filas extra | confirmada (visible en log) | alta | bajo |
| H2 | Cuotas MORA vencidas descartadas restan AMORTIZACION en NO_SAV | razonada del codigo | alta | medio (correr cuadre con fix) |
| H3 | SMM esta en porcentaje en `parametros_mr_prepago_cmr.xlsx` y se usa sin dividir | sospecha | media | bajo (abrir Excel) |
| H4 | `CODIGO_EMPRESA = 1` vs `3` causa filas marcadas como diferentes | razonada | media | bajo |
| H5 | Calendario de 200 meses + merge LEFT introduce filas con flujo cero al final | razonada | media | medio |
| H6 | Diferencia de unidad de los escenarios PHI | sospecha | baja | bajo |

## 6. Caminos posibles

### Camino A -- Parche pragmatico (HOY): subir el Excel productivo a BQ

- Estado: implementado en `tools/cargar_prepago_cmr_productivo.py`.
- Pro: desbloquea la migracion GCP sin esperar.
- Contra: no soluciona el problema de fondo; cada dia hay que recordar correr el parche.

### Camino B -- Replica fiel del notebook en el repo (SIGUIENTE)

- Crear `mr_prepago_cmr_dev_v0.py` que sea una traduccion linea a linea del notebook al estilo del repo (rutas via `config_rutas`, lectura via `leer_tabla_con_cache`, escritura via `guardar_excel`).
- Mantener el `mr_prepago_cmr.py` actual intacto para no romper el flujo existente.
- Asignar el modelo `mr_prepago_cmr_dev_v0` en el orquestador como modelo paralelo (o con flag) para correrlo en sombra y comparar contra notebook hasta cuadrar al centavo.
- Una vez cuadrado, decidir si reemplaza al `mr_prepago_cmr.py` actual o si convive.

### Camino C -- Arreglar `mr_prepago_cmr.py` con los cambios funcionales

- Aplicar H1 + H2 + H3/H4 (segun validacion con metodologias).
- Pro: el codigo nuevo conserva sus mejoras (escenarios parametrizados, mapeo defensivo, etc.).
- Contra: si la validacion con metodologias toma tiempo, sigue habiendo descuadre.

### Camino D -- Decidir explicitamente que el modelo nuevo "manda"

- Documentar las diferencias 3.1, 3.2, 3.3 como decisiones intencionales y formalizarlas con metodologias.
- Pro: aprovecha las mejoras de SMM mensual continuo.
- Contra: cambia el resultado historico; necesita aprobacion formal.

## 7. Decision actual

- Avanzar con **Camino B**: `mr_prepago_cmr_dev_v0.py` como replica fiel del notebook integrada al repo.
- Mantener `mr_prepago_cmr.py` como esta. Pendiente Camino C/D una vez tengamos validacion con metodologias sobre H3, H4 y la conceptualidad de 3.1/3.2/3.3.
