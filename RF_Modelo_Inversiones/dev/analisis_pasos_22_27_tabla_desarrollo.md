# Análisis de Pasos 22-27: Integración Tabla Desarrollo

## Contexto del Problema

Los pasos 22-27 del modelo de inversiones corresponden a la **integración final** de todos los flujos calculados en una tabla de desarrollo que luego se exporta a Excel. Esta es la última etapa del proceso.

## Resumen del Flujo

```
Paso 22: DELETE → Limpiar tabla destino
Paso 23: INSERT → Flujos del Modelo de Liquidación (ML)
Paso 24: INSERT → Fondos Mutuos (FFMM)
Paso 25: INSERT → Held-to-Maturity (HTM)
Paso 26: INSERT → Renta en Tránsito (RT)
Paso 27: SELECT → Formatear para Excel
```

---

## Paso 22: RF_PLI_047_Limpia_Tabla_Desarrollo_Interna

### ¿Qué hace?
**Elimina todos los registros de la tabla de desarrollo interna** para prepararla para la nueva carga.

### 💡 En palabras simples:
> "Borra todo lo anterior para cargar datos frescos"

**Tipo:** DELETE (Type32)  
**Longitud SQL:** 595 caracteres

```sql
DELETE RF_Tabla_Desarrollo_Interna.Fec_Pro, 
       RF_Tabla_Desarrollo_Interna.Cod_Emp, 
       RF_Tabla_Desarrollo_Interna.Moneda, 
       RF_Tabla_Desarrollo_Interna.Cod_A_P, 
       RF_Tabla_Desarrollo_Interna.Cod_Pro, 
       RF_Tabla_Desarrollo_Interna.Cod_Sub_Pro, 
       RF_Tabla_Desarrollo_Interna.Fec_Pago, 
       RF_Tabla_Desarrollo_Interna.Dias_Pago, 
       RF_Tabla_Desarrollo_Interna.Cap_Amort, 
       RF_Tabla_Desarrollo_Interna.Int_Total_Cont, 
       RF_Tabla_Desarrollo_Interna.VP_Cap_Amort, 
       RF_Tabla_Desarrollo_Interna.VP_Int_Total_Cont, 
       RF_Tabla_Desarrollo_Interna.Precio_Mid, 
       RF_Tabla_Desarrollo_Interna.Flujo_CLP
FROM RF_Tabla_Desarrollo_Interna;
```

### Implementación Python

En Python, esto es simplemente **no hacer nada** porque creamos DataFrames nuevos cada vez. No hay tabla persistente que limpiar.

```python
# En Python: crear DataFrame vacío como "tabla destino"
df_tabla_desarrollo = pd.DataFrame(columns=[
    'Fec_Pro', 'Cod_Emp', 'Moneda', 'Cod_A_P', 'Cod_Pro', 'Cod_Sub_Pro',
    'Fec_Pago', 'Dias_Pago', 'Cap_Amort', 'Int_Total_Cont', 
    'VP_Cap_Amort', 'VP_Int_Total_Cont', 'Precio_Mid', 'Flujo_CLP'
])
```

---

## Paso 23: RF_PLI_048_Tabla_Desarrollo_Interna_Add_ML

### ¿Qué hace?
**Inserta los flujos del modelo de liquidación** (calculados en pasos 1-21) en la tabla de desarrollo.

### 💡 En palabras simples:
> "Carga los resultados del modelo de liquidación: cuándo y cuánto se va a liquidar de cada instrumento"

**Tipo:** INSERT (Type64)  
**Longitud SQL:** 1,098 caracteres

```sql
INSERT INTO RF_Tabla_Desarrollo_Interna (
    Fec_Pro, Cod_Emp, Moneda, Cod_A_P, Cod_Pro, Cod_Sub_Pro, 
    Fec_Pago, Dias_Pago, Cap_Amort, Int_Total_Cont, 
    VP_Cap_Amort, VP_Int_Total_Cont, Precio_Mid, Flujo_CLP
)
SELECT 
    RF_PLI_Modelo_Inversiones_Final_CLP.Fec_Pro, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Cod_Emp, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Moneda, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Cod_A_P, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Cod_Pro, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Cod_Sub_Pro, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Fec_Pago, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Dias_Pago, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Cap_Amort, 
    RF_PLI_Modelo_Inversiones_Final_CLP.Int_Total_Cont, 
    RF_PLI_Modelo_Inversiones_Final_CLP.VP_Cap_Amort, 
    RF_PLI_Modelo_Inversiones_Final_CLP.VP_Int_Total_Cont, 
    Precios_Dia.Precio_Mid, 
    IIF(RF_PLI_Modelo_Inversiones_Final_CLP.Moneda = 'CLF', 
        RF_PLI_Modelo_Inversiones_Final_CLP.Cap_Amort * Precios_Dia.Precio_Mid, 
        RF_PLI_Modelo_Inversiones_Final_CLP.Cap_Amort) AS Flujo_CLP
FROM RF_PLI_Modelo_Inversiones_Final_CLP 
LEFT JOIN Precios_Dia 
    ON RF_PLI_Modelo_Inversiones_Final_CLP.Fec_Pro = Precios_Dia.Fecha;
```

### Análisis de la Lógica

1. **JOIN con Precios:** Agrega el precio UF del día (`Precio_Mid` de TCRC)
2. **Conversión a CLP:** Si la moneda es CLF, multiplica el capital por el precio UF
3. **Columnas 1:1:** El resto de columnas se copian directamente

### Implementación Python

```python
def agregar_precio_y_flujo_clp(df_inversiones, df_precios_dia):
    """
    Agrega precio UF y calcula flujo en CLP.
    
    Args:
        df_inversiones: RF_PLI_Modelo_Inversiones_Final_CLP
        df_precios_dia: Precios_Dia (filtrado por TCRC)
    
    Returns:
        DataFrame con columnas Precio_Mid y Flujo_CLP agregadas
    """
    # Obtener precio UF del día
    precio_uf = df_precios_dia['Precio_Mid'].iloc[0] if len(df_precios_dia) > 0 else 0
    
    df = df_inversiones.copy()
    df['Precio_Mid'] = precio_uf
    
    # Calcular Flujo_CLP según moneda
    df['Flujo_CLP'] = df.apply(
        lambda row: row['Cap_Amort'] * precio_uf if row['Moneda'] == 'CLF' 
                    else row['Cap_Amort'],
        axis=1
    )
    
    return df
```

---

## Paso 24: RF_PLI_048a_Tabla_Desarrollo_Interna_Add_FFMM

### ¿Qué hace?
**Inserta los flujos de Fondos Mutuos (FFMM)** en la tabla de desarrollo.

### 💡 En palabras simples:
> "Los fondos mutuos NO pasan por el modelo de liquidación porque se pueden liquidar instantáneamente. Se agregan directamente."

**Tipo:** INSERT (Type64)  
**Longitud SQL:** 1,009 caracteres

### ¿Por qué FFMM no pasa por el modelo de liquidación?

Los fondos mutuos tienen características especiales:
- **Liquidez inmediata:** Se pueden rescatar en T+0 o T+1
- **Sin haircut:** No aplica descuento por plazo
- **Sin vencimiento fijo:** No tienen días_vcto como los bonos

### Fuente de Datos

La query toma de `RF_PLI_044f_CarteraInv_FFMM`, que es una vista sobre la cartera filtrada por:
```sql
WHERE Cod_Sub_Pro LIKE '*MUTUOS*'
```

### Implementación Python

```python
def extraer_cartera_ffmm(df_cartera_inv):
    """
    Extrae la cartera de Fondos Mutuos de la cartera de inversiones.
    
    Los FFMM tienen:
    - Cod_Sub_Pro que contiene 'MUTUOS'
    - Liquidación inmediata (Dias_Pago = Dias_Liq o 0)
    """
    return df_cartera_inv[
        df_cartera_inv['Cod_Sub_Pro'].str.contains('MUTUOS', na=False)
    ].copy()
```

---

## Paso 25: RF_PLI_048b_Tabla_Desarrollo_Interna_Add_HTM

### ¿Qué hace?
**Inserta los flujos de instrumentos Held-to-Maturity (HTM)** en la tabla de desarrollo.

### 💡 En palabras simples:
> "Los HTM son bonos que se mantendrán hasta vencimiento. No se liquidarán anticipadamente, así que sus flujos son los contractuales."

**Tipo:** INSERT (Type64)  
**Longitud SQL:** 989 caracteres

### ¿Por qué HTM no pasa por el modelo de liquidación?

Los instrumentos HTM (Held-to-Maturity):
- **Compromiso de no venta:** La entidad decidió mantenerlos hasta vencimiento
- **Tratamiento contable especial:** Se registran a costo amortizado
- **Sin liquidación anticipada:** El modelo de liquidación no aplica

### Fuente de Datos

`RF_PLI_044i_CarteraInv_HTM` filtra por:
```sql
WHERE Cod_Sub_Pro LIKE '*HTM*' OR Cod_Sub_Pro LIKE '*_Liq'
```

### Implementación Python

```python
def extraer_cartera_htm(df_cartera_inv):
    """
    Extrae la cartera de instrumentos Held-to-Maturity.
    
    Los HTM tienen:
    - Cod_Sub_Pro que contiene 'HTM'
    - Flujos contractuales sin liquidación anticipada
    """
    mask_htm = (
        df_cartera_inv['Cod_Sub_Pro'].str.contains('HTM', na=False) |
        df_cartera_inv['Cod_Sub_Pro'].str.endswith('_Liq', na=False)
    )
    return df_cartera_inv[mask_htm].copy()
```

---

## Paso 26: RF_PLI_048c_Tabla_Desarrollo_Interna_Add_RT

### ¿Qué hace?
**Inserta los flujos de Renta en Tránsito (RT)** en la tabla de desarrollo.

### 💡 En palabras simples:
> "La renta en tránsito son instrumentos comprados pero no liquidados aún. Ya están comprometidos."

**Tipo:** INSERT (Type64)  
**Longitud SQL:** 973 caracteres

### ¿Por qué RT no pasa por el modelo de liquidación?

La Renta en Tránsito:
- **Ya está comprometida:** Operaciones cerradas pendientes de liquidación
- **Fecha de pago conocida:** Liquidación en T+2 o fecha acordada
- **Sin decisión de liquidación:** No se puede "liquidar antes" porque ya se vendió/compró

### Fuente de Datos

`RF_PLI_044g_CarteraInv_RT` filtra registros de operaciones en tránsito.

### Implementación Python

```python
def extraer_cartera_rt(df_cartera_inv):
    """
    Extrae la cartera de Renta en Tránsito.
    
    La RT tiene operaciones pendientes de liquidación
    con fecha de pago conocida.
    """
    # Típicamente se identifica por Cod_Sub_Pro o flag específico
    mask_rt = df_cartera_inv['Cod_Sub_Pro'].str.contains('RT|Transito', na=False, case=False)
    return df_cartera_inv[mask_rt].copy()
```

---

## Paso 27: RF_PLI_050_Tabla_Desarrollo_Modelo_Inversiones_Excel

### ¿Qué hace?
**Formatea la tabla de desarrollo para exportación a Excel** con nombres de columnas amigables.

### 💡 En palabras simples:
> "Toma todo lo que calculamos y lo pone bonito para que Excel lo entienda"

**Tipo:** SELECT (DDL - crea tabla)  
**Longitud SQL:** 2,079 caracteres

### Columnas de Salida

| Columna SQL | Nombre Excel | Descripción |
|-------------|--------------|-------------|
| Fec_Pro | FECHA PROCESO | Fecha de proceso |
| Cod_Emp | CODIGO_EMPRESA | Código de empresa |
| Moneda | MONEDA_ORIGEN | Moneda del instrumento |
| Cod_A_P | COD ACT/PAS | Activo/Pasivo |
| Cod_Pro | COD_PRO | Código de producto |
| Cod_Sub_Pro | COD_SUB_PRO | Código de sub-producto |
| Fec_Pago | FECHA DE PAGO | Fecha de pago proyectada |
| Dias_Pago | PLAZO_PAGO | Días hasta el pago |
| Cap_Amort | FLUJO_CAPITAL | Capital a recibir |
| Int_Total_Cont | FLUJO_INTERES | Intereses devengados |
| VP_Cap_Amort | VP_CAP | Valor presente del capital |
| VP_Int_Total_Cont | VP_INT_CONT | Valor presente intereses |
| Precio_Mid | PRECIO_MID | Precio UF del día |
| Flujo_CLP | FLUJO_CLP | Flujo en pesos chilenos |

### Columnas Adicionales Calculadas

```sql
-- Moneda de compensación (mismo que origen para inversiones)
Moneda AS MONEDA_COMPENSACION

-- Flag de compensación
'NO' AS COMPENSACION

-- Operación (siempre INVERSIONES para este modelo)
'INVERSIONES' AS OPERACION
```

### Implementación Python

```python
MAPEO_COLUMNAS_EXCEL = {
    'Fec_Pro': 'FECHA PROCESO',
    'Cod_Emp': 'CODIGO_EMPRESA',
    'Moneda': 'MONEDA_ORIGEN',
    'Cod_A_P': 'COD ACT/PAS',
    'Cod_Pro': 'COD_PRO',
    'Cod_Sub_Pro': 'COD_SUB_PRO',
    'Fec_Pago': 'FECHA DE PAGO',
    'Dias_Pago': 'PLAZO_PAGO',
    'Cap_Amort': 'FLUJO_CAPITAL',
    'Int_Total_Cont': 'FLUJO_INTERES',
    'VP_Cap_Amort': 'VP_CAP',
    'VP_Int_Total_Cont': 'VP_INT_CONT',
    'Precio_Mid': 'PRECIO_MID',
    'Flujo_CLP': 'FLUJO_CLP'
}

def formatear_para_excel(df_tabla_desarrollo):
    """
    Formatea la tabla de desarrollo para exportación a Excel.
    
    Args:
        df_tabla_desarrollo: DataFrame con flujos consolidados
        
    Returns:
        DataFrame con columnas renombradas y adicionales
    """
    df = df_tabla_desarrollo.copy()
    
    # Agregar columnas constantes
    df['OPERACION'] = 'INVERSIONES'
    df['MONEDA_COMPENSACION'] = df['Moneda']
    df['COMPENSACION'] = 'NO'
    
    # Renombrar columnas
    df = df.rename(columns=MAPEO_COLUMNAS_EXCEL)
    
    # Ordenar columnas según formato esperado
    columnas_orden = [
        'FECHA PROCESO', 'CODIGO_EMPRESA', 'OPERACION', 'COD ACT/PAS',
        'MONEDA_ORIGEN', 'MONEDA_COMPENSACION', 'COMPENSACION',
        'COD_PRO', 'COD_SUB_PRO', 'FECHA DE PAGO', 'PLAZO_PAGO',
        'FLUJO_CAPITAL', 'FLUJO_INTERES', 'VP_CAP', 'VP_INT_CONT',
        'PRECIO_MID', 'FLUJO_CLP'
    ]
    
    return df[columnas_orden]
```

---

## Resumen Visual del Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    PASOS 1-21: MODELO LIQUIDACIÓN               │
├─────────────────────────────────────────────────────────────────┤
│  Flujo_GobCLP │ Flujo_GobCLF │ Flujo_DPF │ Flujo_DPR │ ...     │
└───────────────┼───────────────┼───────────┼───────────┼─────────┘
                │               │           │           │
                ▼               ▼           ▼           ▼
         ┌──────────────────────────────────────────────────┐
         │      PASO 21: RF_PLI_044e (UNION ALL)            │
         │      → RF_PLI_Modelo_Inversiones_Final_CLP       │
         └──────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Cartera FFMM  │  │   Cartera HTM   │  │   Cartera RT    │
│   (Paso 24)     │  │   (Paso 25)     │  │   (Paso 26)     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────────────┐
         │      PASO 23: INSERT INTO + JOIN Precios         │
         │      → RF_Tabla_Desarrollo_Interna               │
         └──────────────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────────────┐
         │      PASO 27: Formato Excel                       │
         │      → RF_PLI_050_Tabla_Desarrollo_Modelo_...    │
         └──────────────────────────────────────────────────┘
                              │
                              ▼
                    📊 ARCHIVO EXCEL FINAL
```

---

## Función Consolidada Propuesta

```python
def generar_tabla_desarrollo_completa(
    df_modelo_inversiones: pd.DataFrame,
    df_cartera_ffmm: pd.DataFrame,
    df_cartera_htm: pd.DataFrame,
    df_cartera_rt: pd.DataFrame,
    df_precios_dia: pd.DataFrame,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Genera la tabla de desarrollo completa integrando todos los flujos.
    
    Implementa pasos 22-27 del modelo de Access.
    
    Args:
        df_modelo_inversiones: Flujos del modelo de liquidación (paso 21)
        df_cartera_ffmm: Cartera de fondos mutuos
        df_cartera_htm: Cartera held-to-maturity
        df_cartera_rt: Cartera renta en tránsito
        df_precios_dia: Precios TCRC del día
        
    Returns:
        DataFrame formateado para Excel
    """
    if verbose:
        print("="*60)
        print("GENERANDO TABLA DE DESARROLLO COMPLETA")
        print("="*60)
    
    # Paso 22: "Limpiar" - en Python creamos nuevo DataFrame
    dfs_a_concatenar = []
    
    # Paso 23: Agregar modelo liquidación con precio y flujo CLP
    df_ml = agregar_precio_y_flujo_clp(df_modelo_inversiones, df_precios_dia)
    dfs_a_concatenar.append(df_ml)
    if verbose:
        print(f"  [23] ML (Modelo Liquidación): {len(df_ml):,} registros")
    
    # Paso 24: Agregar FFMM
    if len(df_cartera_ffmm) > 0:
        df_ffmm = agregar_precio_y_flujo_clp(df_cartera_ffmm, df_precios_dia)
        dfs_a_concatenar.append(df_ffmm)
        if verbose:
            print(f"  [24] FFMM: {len(df_ffmm):,} registros")
    
    # Paso 25: Agregar HTM
    if len(df_cartera_htm) > 0:
        df_htm = agregar_precio_y_flujo_clp(df_cartera_htm, df_precios_dia)
        dfs_a_concatenar.append(df_htm)
        if verbose:
            print(f"  [25] HTM: {len(df_htm):,} registros")
    
    # Paso 26: Agregar RT
    if len(df_cartera_rt) > 0:
        df_rt = agregar_precio_y_flujo_clp(df_cartera_rt, df_precios_dia)
        dfs_a_concatenar.append(df_rt)
        if verbose:
            print(f"  [26] RT: {len(df_rt):,} registros")
    
    # Consolidar
    df_tabla_desarrollo = pd.concat(dfs_a_concatenar, ignore_index=True)
    if verbose:
        print(f"\n  Total consolidado: {len(df_tabla_desarrollo):,} registros")
    
    # Paso 27: Formatear para Excel
    df_final = formatear_para_excel(df_tabla_desarrollo)
    if verbose:
        print(f"  [27] Formateado para Excel: {len(df_final):,} registros, {len(df_final.columns)} columnas")
        print("="*60)
    
    return df_final
```

---

## Conclusión

Los pasos 22-27 son esencialmente una **consolidación e integración** de datos:

1. **No hay lógica de negocio compleja** - son principalmente UNIONs e INSERTs
2. **La complejidad está en identificar las fuentes** - FFMM, HTM, RT tienen filtros específicos
3. **El formateo final es mecánico** - renombrar columnas y agregar constantes

En Python, esto se reduce a:
- `pd.concat()` para unir DataFrames
- `df.rename()` para columnas
- Función de conversión CLP para monedas en UF

**Tiempo estimado de implementación:** 2-3 horas incluyendo tests.
