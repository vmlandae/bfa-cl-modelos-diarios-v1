# Análisis COMPLETO: RF_PLI_044e_Modelo_Inversiones_Tabla_Final

> **Fecha**: 2026-02-04  
> **Estado**: 🔴 CORRECCIÓN del análisis anterior que omitió dependencias críticas

---

## 🚨 Problema Identificado

El análisis anterior (`RF_PLI_044e_Modelo_Inversiones_Tabla_Final_analisis.md`) **omitió completamente** las queries anidadas dentro de `RF_PLI_044c_Modelo_Inversiones_Pacto_FB`, que representan **24 queries adicionales** que generan los montos de pactos "fuera de plazo" (>90 días).

### Dependencias REALES del Paso 21

```
RF_PLI_044e_Modelo_Inversiones_Tabla_Final (entrypoint)
└── RF_PLI_044d_Modelo_Inversiones_Full
    ├── RF_PLI_044_Modelo_Inversiones_Final (7 dependencias - ya analizadas)
    │   ├── RF_PLI_001c_CarteraInv_Gtia
    │   │   └── RF_PLI_001b_CarteraInv_Gtia  ← desde RF_base_Completa_Hist
    │   ├── RF_PLI_008b_CarteraGobCLP_Final  ← desde Flujo_GobCLP
    │   ├── RF_PLI_015b_CarteraGobCLF_Final  ← desde Flujo_GobCLF
    │   ├── RF_PLI_022b_CarteraDPF_Final     ← desde Flujo_DPF
    │   ├── RF_PLI_029b_CarteraDPR_Final     ← desde Flujo_DPR
    │   ├── RF_PLI_036b_CarteraLCH_Final     ← desde Flujo_LCH
    │   └── RF_PLI_043b_CarteraBBC_Final     ← desde Flujo_BBC
    │
    └── RF_PLI_044c_Modelo_Inversiones_Pacto_FB (⚠️ OMITIDO EN ANÁLISIS ANTERIOR)
        └── RF_PLI_044b_Modelo_Inversiones_Pacto_FB
            ├── RF_PLI_003c_Monto_FueraPlazo ← GobCLP pactos >90 días
            │   └── RF_PLI_003b_GobCLP_MontoPlazo_Pacto
            │       └── RF_PLI_002_CarteraGobCLP_Pacto
            │           └── RF_PLI_001d_CarteraInv_Pcto ← RF_base_Completa_Hist
            │
            ├── RF_PLI_010c_Monto_FueraPlazo ← GobCLF pactos >90 días
            │   └── RF_PLI_010b_GobCLF_MontoPlazo_Pacto
            │       └── RF_PLI_009_CarteraGobCLF_Pacto
            │           └── RF_PLI_001d_CarteraInv_Pcto
            │
            ├── RF_PLI_017c_Monto_FueraPlazo ← DPF pactos >90 días
            │   └── RF_PLI_017b_DPF_MontoPlazo_Pacto
            │       └── RF_PLI_016_CarteraDPF_Pacto
            │           └── RF_PLI_001d_CarteraInv_Pcto
            │
            ├── RF_PLI_024c_Monto_FueraPlazo ← DPR pactos >90 días
            │   └── RF_PLI_024b_DPR_MontoPlazo_Pacto
            │       └── RF_PLI_023_CarteraDPR_Pacto
            │           └── RF_PLI_001d_CarteraInv_Pcto
            │
            ├── RF_PLI_031c_Monto_FueraPlazo ← LCH pactos >90 días
            │   └── RF_PLI_031b_LCH_MontoPlazo_Pacto
            │       └── RF_PLI_030_CarteraLCH_Pacto
            │           └── RF_PLI_001d_CarteraInv_Pcto
            │
            └── RF_PLI_038c_Monto_FueraPlazo ← BBC pactos >90 días
                └── RF_PLI_038b_BBC_CLP_MontoPlazo_Pacto
                    └── RF_PLI_037_CarteraBBC_CLP_Pacto
                        └── RF_PLI_001d_CarteraInv_Pcto
```

**Total queries involucradas: 31** (no 12 como se indicó antes)

---

## 📊 Resumen de Todas las Queries

| Nivel | Query | Dependencias | Descripción |
|-------|-------|--------------|-------------|
| 0 | RF_PLI_044e_Modelo_Inversiones_Tabla_Final | 1 | SELECT INTO final |
| 1 | RF_PLI_044d_Modelo_Inversiones_Full | 2 | UNION: Final + Pactos |
| 2 | RF_PLI_044_Modelo_Inversiones_Final | 7 | UNION: 6 flujos + Gtia |
| 2 | RF_PLI_044c_Modelo_Inversiones_Pacto_FB | 1 | Formatear pactos |
| 3 | RF_PLI_001c_CarteraInv_Gtia | 1 | Agregar garantías |
| 3 | RF_PLI_008b a 043b (*_Final) | 0 | Formatear flujos (6 queries) |
| 3 | RF_PLI_044b_Modelo_Inversiones_Pacto_FB | 6 | UNION: 6 montos fuera plazo |
| 4 | RF_PLI_001b_CarteraInv_Gtia | 0 | Filtrar garantías |
| 4 | RF_PLI_003c a 038c (*_Monto_FueraPlazo) | 1 | Filtrar >90 días (6 queries) |
| 5 | RF_PLI_003b a 038b (*_MontoPlazo_Pacto) | 1 | Sumar por Dias_Pacto (6 queries) |
| 6 | RF_PLI_002 a 037 (*_Cartera*_Pacto) | 1 | Filtrar cartera pacto (6 queries) |
| 7 | RF_PLI_001d_CarteraInv_Pcto | 0 | Cartera base con pactos |

---

## 🔍 Análisis de las Queries OMITIDAS

### Nivel 3: RF_PLI_044b_Modelo_Inversiones_Pacto_FB

**¿Qué hace?** UNION de los 6 "Monto_FueraPlazo" (pactos con Dias_Pacto > 90)

```sql
SELECT * FROM RF_PLI_003c_Monto_FueraPlazo
UNION ALL 
SELECT * FROM RF_PLI_010c_Monto_FueraPlazo
UNION ALL 
SELECT * FROM RF_PLI_017c_Monto_FueraPlazo
UNION ALL 
SELECT * FROM RF_PLI_024c_Monto_FueraPlazo
UNION ALL 
SELECT * FROM RF_PLI_031c_Monto_FueraPlazo
UNION ALL 
SELECT * FROM RF_PLI_038c_Monto_FueraPlazo;
```

---

### Nivel 4: RF_PLI_XXXc_Monto_FueraPlazo

**Patrón común:** Filtra pactos con Dias_Pacto > 90 días y agrega moneda.

**Ejemplo (GobCLP):**
```sql
SELECT RF_PLI_003b_GobCLP_MontoPlazo_Pacto.Dias_Pacto, 
       sum(RF_PLI_003b_GobCLP_MontoPlazo_Pacto.Monto) AS Monto, 
       'CLP' AS Moneda
FROM RF_PLI_003b_GobCLP_MontoPlazo_Pacto
WHERE RF_PLI_003b_GobCLP_MontoPlazo_Pacto.Dias_Pacto > 90
GROUP BY RF_PLI_003b_GobCLP_MontoPlazo_Pacto.Dias_Pacto;
```

**Las 6 queries:**
| Query | Instrumento | Moneda |
|-------|-------------|--------|
| RF_PLI_003c_Monto_FueraPlazo | GobCLP | CLP |
| RF_PLI_010c_Monto_FueraPlazo | GobCLF | CLF |
| RF_PLI_017c_Monto_FueraPlazo | DPF | CLP |
| RF_PLI_024c_Monto_FueraPlazo | DPR | CLF |
| RF_PLI_031c_Monto_FueraPlazo | LCH | CLF |
| RF_PLI_038c_Monto_FueraPlazo | BBC | CLP |

---

### Nivel 5: RF_PLI_XXXb_*_MontoPlazo_Pacto

**Patrón común:** Agrupa por Dias_Pacto y suma VP_Cap_Amort + VP_Int_Total.

**Ejemplo (GobCLP):**
```sql
SELECT RF_PLI_002_CarteraGobCLP_Pacto.Dias_Pacto, 
       sum(RF_PLI_002_CarteraGobCLP_Pacto.VP_Cap_Amort + 
           RF_PLI_002_CarteraGobCLP_Pacto.VP_Int_Total) AS Monto
FROM RF_PLI_002_CarteraGobCLP_Pacto
GROUP BY RF_PLI_002_CarteraGobCLP_Pacto.Dias_Pacto
ORDER BY RF_PLI_002_CarteraGobCLP_Pacto.Dias_Pacto;
```

---

### Nivel 6: RF_PLI_XXX_Cartera*_Pacto

**Patrón común:** Filtra cartera base de pactos por tipo de instrumento.

**Ejemplo (GobCLP):**
```sql
SELECT ... FROM RF_PLI_001d_CarteraInv_Pcto
WHERE RF_PLI_001d_CarteraInv_Pcto.Instrumento='BCP' 
   OR RF_PLI_001d_CarteraInv_Pcto.Instrumento='BTP' 
   OR RF_PLI_001d_CarteraInv_Pcto.Instrumento='PDB';
```

**Las 6 queries:**
| Query | Filtro Instrumento |
|-------|-------------------|
| RF_PLI_002_CarteraGobCLP_Pacto | BCP, BTP, PDB |
| RF_PLI_009_CarteraGobCLF_Pacto | BCU, BTU, CER |
| RF_PLI_016_CarteraDPF_Pacto | DPF, FFM |
| RF_PLI_023_CarteraDPR_Pacto | DPR |
| RF_PLI_030_CarteraLCH_Pacto | LCH, BBC (Moneda=CLF) |
| RF_PLI_037_CarteraBBC_CLP_Pacto | BBC (Moneda=CLP) |

---

### Nivel 7: RF_PLI_001d_CarteraInv_Pcto

**Tabla base de cartera con pactos.** Ya la tenemos implementada como `genera_cartera_inv_pacto()`.

```sql
SELECT ... FROM RF_base_Completa_Hist
INNER JOIN RF_Fecha_Proceso_Carteras ON Fecha = Fec_Pro
WHERE (Left(Cod_Pro,20)='Inversion Financiera' Or Left(Cod_Pro,23)='INVERSIONES FINANCIERAS') 
  And (Right(Cod_Sub_Pro,4)='Pcto' Or Right(Cod_Sub_Pro,8)='Pcto_Liq');
```

---

## 📐 Lógica de Negocio Descubierta

### ¿Qué son los "Pactos Fuera de Plazo"?

Los pactos de retrocompra normalmente tienen plazos cortos (1-90 días). El modelo de liquidación ya calcula estos montos dentro del haircut diario.

**PERO:** Cuando un pacto tiene Dias_Pacto > 90, **no entra en el modelo de liquidación** (porque el horizonte de liquidación es 90 días). Estos pactos se agregan directamente a la tabla final como "flujos futuros" que se van a recibir en esas fechas.

### Flujo Conceptual

```
Cartera Base con Pactos (RF_PLI_001d)
        │
        ├── Dias_Pacto ≤ 90 → Entra en modelo de liquidación (haircut día a día)
        │                      └── Se genera en Flujo_GobCLP, etc.
        │
        └── Dias_Pacto > 90 → NO entra en modelo de liquidación
                               └── Se agrega directamente a tabla final
                                   └── RF_PLI_044c_Modelo_Inversiones_Pacto_FB
```

---

## 🔴 Errores en output/tabla_final.py

### Error 1: generar_cartera_pactos() busca df_pactos incorrecto

La función actual espera un `df_pactos` con columnas `Moneda`, `Dias_Pacto`, `Monto`, pero esta tabla **no existe como input externo**. 

**Lo correcto:** Se debe generar desde `RF_PLI_001d_CarteraInv_Pcto` filtrando Dias_Pacto > 90.

### Error 2: Consultar tablas_access es circular

En la celda 48 y 54 del notebook, buscamos tablas como:
- `RF_PLI_001b_TblCartera_RFBFA`
- `RF_PLI_044c_Add_Pactos_FB`
- `RF_PLI_046_Tabla_Final_Inversiones`
- `RF_PLI_050_Gen_Excel_Output`

**Problema:** Estas son tablas **generadas por el modelo de Access**. Si las traemos desde Access, estamos leyendo el output, no traduciéndolo.

**Lo correcto:** 
- Solo debemos leer las **tablas INPUT** (RF_base_Completa_Hist, RF_Base_Diaria_Precios, FPL, RF_FactXXX, RF_MontosLiq)
- Todo lo demás debe ser **generado por Python**

---

## 🔧 Lo Que Hay Que Rehacer

### 1. Queries de Pactos (6 funciones nuevas o 1 parametrizada)

Necesitamos implementar la cadena:
```python
RF_PLI_001d_CarteraInv_Pcto  # ✅ Ya existe: genera_cartera_inv_pacto()
    └── RF_PLI_XXX_Cartera*_Pacto  # ⚠️ Falta: filtrar por instrumento
        └── RF_PLI_XXXb_MontoPlazo_Pacto  # ⚠️ Falta: agrupar por Dias_Pacto
            └── RF_PLI_XXXc_Monto_FueraPlazo  # ⚠️ Falta: filtrar >90 días
```

**Propuesta:** Una sola función parametrizada:

```python
def generar_monto_fuera_plazo_pacto(
    df_cartera_pacto: pd.DataFrame,
    tipo_instrumento: str,
    umbral_dias: int = 90
) -> pd.DataFrame:
    """
    Genera montos de pactos fuera de plazo (>90 días).
    
    Implementa: RF_PLI_XXXc_Monto_FueraPlazo
    """
    ...
```

### 2. UNION de Pactos Fuera de Plazo

```python
def generar_pactos_fuera_plazo_union(
    df_cartera_inv_pacto: pd.DataFrame,
    fecha_proceso: datetime
) -> pd.DataFrame:
    """
    Genera RF_PLI_044b + RF_PLI_044c para los 6 instrumentos.
    """
    ...
```

### 3. Corregir output/tabla_final.py

- `generar_tabla_final_inversiones()` debe recibir `df_cartera_inv_pacto` en lugar de `df_pactos`
- Internamente debe generar los pactos fuera de plazo

### 4. Eliminar lecturas circulares del notebook

La celda 48 y 54 deben comparar vs Access solo para **validación**, no para obtener inputs.

---

## 📊 Impacto en Código Existente

| Archivo | Afectado | Qué Cambiar |
|---------|----------|-------------|
| `output/tabla_final.py` | 🔴 Sí | Agregar generación de pactos >90d |
| `tests/test_tabla_final.py` | 🔴 Sí | Agregar tests para pactos |
| `helpers.py` | 🟡 Menor | Verificar `generar_monto_plazo_pacto()` |
| `pipeline/orquestador.py` | 🟢 No | Flujos OK |
| `draft_ml_inversiones.ipynb` | 🟡 Menor | Corregir celdas circulares |

### Funciones a Agregar:

1. `generar_cartera_pacto_instrumento()` - Filtrar RF_PLI_001d por instrumento
2. `generar_monto_plazo_pacto()` - Sumar VP por Dias_Pacto
3. `generar_monto_fuera_plazo()` - Filtrar Dias_Pacto > 90
4. `generar_pactos_fuera_plazo_completo()` - UNION de los 6 instrumentos

O bien, una función unificada que haga todo en un paso.

---

## ✅ Resumen Ejecutivo

| Aspecto | Estado Anterior | Estado Correcto |
|---------|-----------------|-----------------|
| Queries analizadas | 12 | 31 |
| Pactos fuera de plazo | ❌ Ignorados | ✅ Incluidos |
| Fuente de df_pactos | tablas_access (circular) | Generado desde RF_PLI_001d |
| Umbral pactos | No especificado | >90 días |

**Líneas de código nuevas estimadas:** ~200-300

**Tests nuevos estimados:** ~10-15
