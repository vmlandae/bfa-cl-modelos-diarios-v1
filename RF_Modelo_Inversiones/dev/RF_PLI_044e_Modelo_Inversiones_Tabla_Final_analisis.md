# Análisis de RF_PLI_044e_Modelo_Inversiones_Tabla_Final

## Contexto del Problema

El paso 21 del modelo de inversiones (`RF_PLI_044e_Modelo_Inversiones_Tabla_Final`) es una query que depende de manera anidada de otras 11 queries, formando una estructura compleja tipo "spaghetti code". Este documento analiza cada query, identifica patrones problemáticos y propone simplificaciones.

## Resumen de Dependencias

```
RF_PLI_001b_CarteraInv_Gtia
    └── RF_PLI_001c_CarteraInv_Gtia

RF_PLI_008b_CarteraGobCLP_Final
RF_PLI_015b_CarteraGobCLF_Final  
RF_PLI_022b_CarteraDPF_Final
RF_PLI_029b_CarteraDPR_Final
RF_PLI_036b_CarteraLCH_Final
RF_PLI_043b_CarteraBBC_Final
    └── RF_PLI_044_Modelo_Inversiones_Final (UNION de todas las carteras)

RF_PLI_044c_Modelo_Inversiones_Pacto_FB
    └── RF_PLI_044d_Modelo_Inversiones_Full (UNION con pactos)
        └── RF_PLI_044e_Modelo_Inversiones_Tabla_Final (SELECT INTO final)
```

---

## Análisis Detallado de Cada Query

### Explicación en Lenguaje Natural

A continuación se explica **qué hace cada query** de forma clara y sencilla, seguido del código SQL original.

---

### RF_PLI_001b_CarteraInv_Gtia

#### 🎯 ¿Qué hace?
**Filtra las inversiones que están respaldadas con garantía.** 

Toma la tabla base de cartera completa y extrae solo aquellos registros donde:
- El producto sea "Inversión Financiera"
- El sub-producto termine en "Gtia" (garantía) o "Gtia_Liq" (garantía en liquidación)

Además, extrae las primeras 3 letras del nemotécnico para identificar el tipo de instrumento.

#### 💡 En palabras simples:
> "Dame todas las inversiones financieras que tengan garantía, para la fecha que estoy procesando"

**Tipo:** Select  
**Longitud SQL:** 889 caracteres

```sql
SELECT RF_base_Completa_Hist_Input.Fec_Pro, RF_base_Completa_Hist_Input.Cod_Emp, RF_base_Completa_Hist_Input.Moneda, RF_base_Completa_Hist_Input.Cod_Pro, RF_base_Completa_Hist_Input.Cod_Sub_Pro, RF_base_Completa_Hist_Input.Nemotecnico, Left(RF_base_Completa_Hist_Input.Nemotecnico,3) AS Instrumento, RF_base_Completa_Hist_Input.Cap_Amort, RF_base_Completa_Hist_Input.Int_Total_Cont, RF_base_Completa_Hist_Input.Dias_Vcto, RF_base_Completa_Hist_Input.VP_Cap_Amort, RF_base_Completa_Hist_Input.VP_Int_Total, RF_base_Completa_Hist_Input.Dias_Liq

FROM RF_Fecha_Proceso_Carteras INNER JOIN RF_base_Completa_Hist_Input ON RF_Fecha_Proceso_Carteras.Fecha = RF_base_Completa_Hist_Input.Fec_Pro

WHERE Left(RF_base_Completa_Hist_Input.Cod_Pro,20)='Inversion Financiera' And (Right(RF_base_Completa_Hist_Input.Cod_Sub_Pro,4)='Gtia' Or Right(RF_base_Completa_Hist_Input.Cod_Sub_Pro,8)='Gtia_Liq');
```

---

### RF_PLI_001c_CarteraInv_Gtia

#### 🎯 ¿Qué hace?
**Agrupa y suma las inversiones con garantía por días de liquidación.**

Toma el resultado de la query anterior y:
1. Agrupa por fecha, empresa, moneda y días hasta liquidación
2. Suma los montos de capital, intereses y valores presentes
3. Renombra los códigos de producto al formato estándar del modelo

#### 💡 En palabras simples:
> "Consolida todas las garantías: si hay 10 bonos que se liquidan en 5 días, suma sus montos en un solo registro"

**Tipo:** Select  
**Longitud SQL:** 823 caracteres

```sql
SELECT RF_PLI_001b_CarteraInv_Gtia.Fec_Pro, RF_PLI_001b_CarteraInv_Gtia.Cod_Emp, RF_PLI_001b_CarteraInv_Gtia.Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras_Gtia' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_Gtia' AS Cod_Sub_Pro, RF_PLI_001b_CarteraInv_Gtia.Fec_Pro+RF_PLI_001b_CarteraInv_Gtia.Dias_Liq AS Fec_Pago, RF_PLI_001b_CarteraInv_Gtia.Dias_Liq AS Dias_Pago, SUM(RF_PLI_001b_CarteraInv_Gtia.Cap_Amort) AS Cap_Amort, SUM(RF_PLI_001b_CarteraInv_Gtia.Int_Total_Cont) AS Int_Total_Cont, sum(RF_PLI_001b_CarteraInv_Gtia.VP_Cap_Amort) AS VP_Cap_Amort, SUM(RF_PLI_001b_CarteraInv_Gtia.VP_Int_Total) AS VP_Int_Total_Cont

FROM RF_PLI_001b_CarteraInv_Gtia

GROUP BY RF_PLI_001b_CarteraInv_Gtia.Fec_Pro, RF_PLI_001b_CarteraInv_Gtia.Cod_Emp, RF_PLI_001b_CarteraInv_Gtia.Moneda, RF_PLI_001b_CarteraInv_Gtia.Dias_Liq;
```

---

### RF_PLI_008b_CarteraGobCLP_Final

#### 🎯 ¿Qué hace?
**Formatea los flujos de liquidación de Bonos de Gobierno en CLP al esquema estándar.**

Toma la tabla de flujos calculados para bonos de gobierno en pesos (GobCLP) y la convierte al formato uniforme que usa el modelo, agregando:
- Códigos de producto estándar (`ML_C46_Inversiones_Financieras_GOBCLP`)
- Fecha de pago calculada (fecha proceso + días)
- Intereses en 0 (porque son flujos de liquidación, no de devengamiento)

Solo incluye flujos donde el día > 0 y el monto > 0.

#### 💡 En palabras simples:
> "Toma cuánto vamos a liquidar de bonos de gobierno en pesos, día por día, y ponlo en el formato estándar"

**Tipo:** Select  
**Longitud SQL:** 535 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLP' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_GOBCLP' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha + Flujo_GobCLP.Dia AS Fec_Pago, Flujo_GobCLP.Dia AS Dias_Pago, Flujo_GobCLP.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_GobCLP.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_GobCLP, RF_Fecha_Proceso_Carteras

WHERE Flujo_GobCLP.Dia>0 AND Flujo_GobCLP.Monto_Liquidar>0;
```

---

### RF_PLI_015b_CarteraGobCLF_Final

#### 🎯 ¿Qué hace?
**Exactamente lo mismo que la anterior, pero para Bonos de Gobierno en UF (CLF).**

Misma estructura, diferente moneda y sufijo de producto.

#### 💡 En palabras simples:
> "Lo mismo que GobCLP, pero para bonos en UF"

**Tipo:** Select  
**Longitud SQL:** 533 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLF' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_GOBCLF' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+Flujo_GobCLF.Dia AS Fec_Pago, Flujo_GobCLF.Dia AS Dias_Pago, Flujo_GobCLF.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_GobCLF.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_GobCLF, RF_Fecha_Proceso_Carteras

WHERE Flujo_GobCLF.Dia>0 AND Flujo_GobCLF.Monto_Liquidar>0;
```

---

### RF_PLI_022b_CarteraDPF_Final

#### 🎯 ¿Qué hace?
**Formatea los flujos de liquidación de Depósitos a Plazo Fijo (DPF) en CLP.**

Misma lógica que las anteriores, aplicada a depósitos a plazo.

#### 💡 En palabras simples:
> "Cuánto vamos a liquidar de depósitos a plazo en pesos, día por día"

**Tipo:** Select  
**Longitud SQL:** 512 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLP' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_DPFCLP' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+Flujo_DPF.Dia AS Fec_Pago, Flujo_DPF.Dia AS Dias_Pago, Flujo_DPF.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_DPF.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_DPF, RF_Fecha_Proceso_Carteras

WHERE Flujo_DPF.Dia>0 AND Flujo_DPF.Monto_Liquidar>0;
```

---

### RF_PLI_029b_CarteraDPR_Final

#### 🎯 ¿Qué hace?
**Formatea los flujos de liquidación de Depósitos a Plazo Reajustables (DPR) en UF.**

DPR son depósitos a plazo pero denominados en UF (reajustables por inflación).

#### 💡 En palabras simples:
> "Cuánto vamos a liquidar de depósitos reajustables, día por día"

**Tipo:** Select  
**Longitud SQL:** 512 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLF' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_DPRCLF' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+Flujo_DPR.Dia AS Fec_Pago, Flujo_DPR.Dia AS Dias_Pago, Flujo_DPR.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_DPR.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_DPR, RF_Fecha_Proceso_Carteras

WHERE Flujo_DPR.Dia>0 AND Flujo_DPR.Monto_Liquidar>0;
```

---

### RF_PLI_036b_CarteraLCH_Final

#### 🎯 ¿Qué hace?
**Formatea los flujos de liquidación de Letras de Crédito Hipotecario (LCH) en UF.**

LCH son instrumentos corporativos denominados en UF.

#### 💡 En palabras simples:
> "Cuánto vamos a liquidar de letras hipotecarias, día por día"

**Tipo:** Select  
**Longitud SQL:** 513 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLF' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_CORPCLF' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+Flujo_LCH.Dia AS Fec_Pago, Flujo_LCH.Dia AS Dias_Pago, Flujo_LCH.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_LCH.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_LCH, RF_Fecha_Proceso_Carteras

WHERE Flujo_LCH.Dia>0 AND Flujo_LCH.Monto_Liquidar>0;
```

---

### RF_PLI_043b_CarteraBBC_Final

#### 🎯 ¿Qué hace?
**Formatea los flujos de liquidación de Bonos Bancarios Corporativos (BBC) en CLP.**

BBC son bonos emitidos por bancos, denominados en pesos.

#### 💡 En palabras simples:
> "Cuánto vamos a liquidar de bonos bancarios, día por día"

**Tipo:** Select  
**Longitud SQL:** 513 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, 'CLP' AS Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_CORPCLP' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+Flujo_BBC.Dia AS Fec_Pago, Flujo_BBC.Dia AS Dias_Pago, Flujo_BBC.Monto_Liquidar AS Cap_Amort, 0 AS Int_Total_Cont, Flujo_BBC.Monto_Liquidar AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM Flujo_BBC, RF_Fecha_Proceso_Carteras

WHERE Flujo_BBC.Dia>0 AND Flujo_BBC.Monto_Liquidar>0;
```

---

### RF_PLI_044_Modelo_Inversiones_Final

#### 🎯 ¿Qué hace?
**Une todas las carteras de instrumentos en una sola tabla.**

Es un simple `UNION ALL` de las 6 carteras de instrumentos (GobCLP, GobCLF, DPF, DPR, LCH, BBC) más la cartera de garantías.

#### 💡 En palabras simples:
> "Junta todas las piezas: bonos de gobierno, depósitos, letras, y garantías, todo en una sola tabla"

**Tipo:** Type128  
**Longitud SQL:** 384 caracteres

```sql
SELECT * FROM RF_PLI_008b_CarteraGobCLP_Final
UNION ALL 
SELECT * FROM RF_PLI_015b_CarteraGobCLF_Final
UNION ALL 
SELECT * FROM RF_PLI_022b_CarteraDPF_Final
UNION ALL 
SELECT * FROM RF_PLI_029b_CarteraDPR_Final
UNION ALL 
SELECT * FROM RF_PLI_036b_CarteraLCH_Final
UNION ALL 
SELECT * FROM RF_PLI_043b_CarteraBBC_Final
UNION ALL SELECT * FROM RF_PLI_001c_CarteraInv_Gtia;
```

---

### RF_PLI_044c_Modelo_Inversiones_Pacto_FB

#### 🎯 ¿Qué hace?
**Formatea los pactos de retrocompra al esquema estándar.**

Los pactos son operaciones donde el banco vende temporalmente instrumentos con compromiso de recompra. Esta query toma esos pactos y los formatea igual que los otros instrumentos.

#### 💡 En palabras simples:
> "Los pactos también generan flujos de caja futuros, así que los ponemos en el mismo formato"

**Tipo:** Select  
**Longitud SQL:** 633 caracteres

```sql
SELECT RF_Fecha_Proceso_Carteras.Fecha AS Fec_Pro, 1 AS Cod_Emp, RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Moneda, 'ACT' AS Cod_A_P, 'ML_C46_Inversiones_Financieras' AS Cod_Pro, 'ML_C46_Inversiones_Financieras_Pcto' AS Cod_Sub_Pro, RF_Fecha_Proceso_Carteras.Fecha+RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Dias_Pacto AS Fec_Pago, RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Dias_Pacto AS Dias_Pago, RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Monto AS Cap_Amort, 0 AS Int_Total_Cont, RF_PLI_044b_Modelo_Inversiones_Pacto_FB.Monto AS VP_Cap_Amort, 0 AS VP_Int_Total_Cont

FROM RF_Fecha_Proceso_Carteras, RF_PLI_044b_Modelo_Inversiones_Pacto_FB;
```

---

### RF_PLI_044d_Modelo_Inversiones_Full

#### 🎯 ¿Qué hace?
**Une la tabla de instrumentos con la tabla de pactos.**

Simplemente concatena los resultados anteriores.

#### 💡 En palabras simples:
> "Junta los instrumentos normales con los pactos"

**Tipo:** Type128  
**Longitud SQL:** 117 caracteres

```sql
SELECT * FROM RF_PLI_044_Modelo_Inversiones_Final
UNION ALL SELECT * FROM RF_PLI_044c_Modelo_Inversiones_Pacto_FB;
```

---

### RF_PLI_044e_Modelo_Inversiones_Tabla_Final

#### 🎯 ¿Qué hace?
**Crea la tabla física final con todos los datos.**

Es un `SELECT INTO` que toma todo el resultado anterior y lo guarda en una nueva tabla llamada `RF_PLI_Modelo_Inversiones_Final_CLP`.

#### 💡 En palabras simples:
> "Guarda todo el resultado consolidado en una tabla que puedo usar después"

**Tipo:** DDL  
**Longitud SQL:** 130 caracteres

```sql
SELECT RF_PLI_044d_Modelo_Inversiones_Full.* INTO RF_PLI_Modelo_Inversiones_Final_CLP
FROM RF_PLI_044d_Modelo_Inversiones_Full;
```

---

## Resumen Visual del Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATOS DE ENTRADA                              │
├─────────────────────────────────────────────────────────────────┤
│  Flujo_GobCLP  │  Flujo_GobCLF  │  Flujo_DPF  │  ...  │  Pactos │
└───────┬────────┴───────┬────────┴──────┬──────┴───────┴────┬────┘
        │                │               │                    │
        ▼                ▼               ▼                    ▼
┌───────────────────────────────────────────────────────────────┐
│              FORMATEAR AL ESQUEMA ESTÁNDAR                    │
│  (Agregar Fec_Pro, Cod_Emp, Moneda, Cod_Sub_Pro, etc.)       │
└───────────────────────────────────────────────────────────────┘
        │                │               │                    │
        └────────────────┼───────────────┼────────────────────┘
                         │               │
                         ▼               ▼
              ┌──────────────────────────────────┐
              │         UNION ALL                 │
              │   (Concatenar todo)               │
              └──────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────────────────┐
              │   TABLA FINAL DE INVERSIONES     │
              │   RF_PLI_Modelo_Inversiones_     │
              │   Final_CLP                      │
              └──────────────────────────────────┘
```

---

## Problemas Identificados

### 1. **Repetición Excesiva de Columnas**
Las queries listan cada columna individualmente en lugar de usar `SELECT *` o definir listas de columnas reutilizables. Esto genera:
- SQL extremadamente largo (algunas queries superan los 2000 caracteres)
- Dificultad de mantenimiento
- Mayor probabilidad de errores tipográficos

### 2. **Queries Intermedias Innecesarias**
Varias queries solo filtran o renombran columnas sin agregar lógica de negocio real. Por ejemplo:
- `RF_PLI_001b_CarteraInv_Gtia` → `RF_PLI_001c_CarteraInv_Gtia` solo hace transformaciones menores
- Las queries `*_Final` para cada instrumento tienen estructura idéntica

### 3. **Patrón UNION Repetitivo**
`RF_PLI_044_Modelo_Inversiones_Final` hace UNION de 7 queries con estructura casi idéntica, repitiendo las mismas columnas 7 veces.

### 4. **Nomenclatura Inconsistente**
Los sufijos `_Final`, `_Full`, `_Tabla_Final` no tienen un significado claro y consistente.

### 5. **Falta de Parametrización**
Los filtros están hardcodeados en el SQL en lugar de ser parámetros.

---

## Por Qué Alguien Escribió Este Código Así

### Razones Históricas y Técnicas:

1. **Evolución Incremental**: El código probablemente creció orgánicamente. Cada vez que se necesitó un nuevo reporte o modificación, se añadió una nueva query en lugar de refactorizar.

2. **Limitaciones de MS Access**: Access tiene limitaciones para crear vistas parametrizadas o funciones reutilizables, lo que incentiva copiar-pegar queries.

3. **Herencia de Excel**: El patrón de "seleccionar columna por columna" es muy común en usuarios que vienen de Excel, donde cada celda/columna se referencia individualmente.

4. **Falta de Revisión de Código**: En entornos donde no hay code review, el código tiende a acumular deuda técnica.

5. **Optimización Prematura Mal Entendida**: Algunos desarrolladores creen que "ser explícito" (listar cada columna) es mejor que usar `SELECT *`, pero lo llevan al extremo.

6. **Miedo a Romper Cosas**: Con sistemas en producción, es más "seguro" crear una nueva query que modificar una existente.

---

## Estrategia de Simplificación

### Paso 1: Identificar las Columnas Comunes
Todas las queries de cartera (`*_Final`) usan prácticamente las mismas columnas. Definir una lista constante:

```python
COLUMNAS_CARTERA = [
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_Pro', 'Cod_Sub_Pro',
    'Nemotecnico', 'Instrumento', 'VP_Cap_Amort', 'VP_Int_Total',
    'Dias_Vcto', 'Monto_Liquidar', 'Haircut'
]
```

### Paso 2: Crear Función Genérica para Cartera Final
```python
def generar_cartera_final(df_flujo, tipo_instrumento, columnas=COLUMNAS_CARTERA):
    """Genera la tabla final de cartera para cualquier instrumento"""
    df = df_flujo.copy()
    # Agregar columnas faltantes con valores por defecto
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    return df[columnas]
```

### Paso 3: Unificar con un Solo UNION
```python
def generar_modelo_inversiones_final(flujos_por_instrumento):
    """Une todas las carteras en una sola tabla"""
    return pd.concat([
        generar_cartera_final(flujo, inst)
        for inst, flujo in flujos_por_instrumento.items()
    ], ignore_index=True)
```

### Paso 4: Eliminar Queries Intermedias
En lugar de 12 queries anidadas, el flujo simplificado sería:

```
Datos Base → Flujos por Instrumento → UNION Final → Output
```

---

## Herramientas y Tips para Desenredar Código Legacy

### 1. **Análisis de Dependencias**
- Crear un grafo de dependencias (como el que hiciste en el notebook)
- Identificar queries "hoja" (sin dependencias) y queries "raíz" (de las que otros dependen)

### 2. **Comparación de Esquemas**
- Extraer las columnas de cada query
- Identificar columnas comunes vs únicas
- Usar herramientas como `pandas` para comparar estructuras

### 3. **Tests de Regresión**
Antes de simplificar, guardar los outputs actuales:
```python
# Guardar resultado original
resultado_original = ejecutar_query_access('RF_PLI_044e_...')
resultado_original.to_pickle('resultado_original.pkl')

# Después de simplificar, comparar
resultado_nuevo = funcion_simplificada()
assert resultado_nuevo.equals(resultado_original)
```

### 4. **Documentación Progresiva**
- Documentar cada query mientras la analizas
- Crear diagramas de flujo de datos
- Mantener un "diccionario" de términos del dominio

### 5. **Refactoring Incremental**
- No intentar reescribir todo de una vez
- Reemplazar una query a la vez
- Validar después de cada cambio

### 6. **Herramientas Útiles**
- **SQLGlot**: Parser de SQL que permite analizar y transformar queries
- **ERAlchemy**: Genera diagramas ER desde bases de datos
- **DBeaver**: Cliente SQL con análisis de dependencias
- **Python + Pandas**: Para prototipado rápido de la lógica

---

## Conclusión

El código "spaghetti" de Access no es malicioso ni incompetente - es el resultado natural de:
- Herramientas con limitaciones
- Presión por entregar funcionalidad
- Falta de tiempo para refactorizar
- Evolución orgánica sin arquitectura clara

La buena noticia es que la lógica subyacente es simple:
1. Tomar datos de cartera
2. Calcular métricas por instrumento
3. Unir todo en una tabla final

En Python, esto se puede expresar en ~50 líneas de código limpio en lugar de 12 queries anidadas con miles de caracteres de SQL repetitivo.
