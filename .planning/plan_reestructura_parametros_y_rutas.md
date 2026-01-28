# Plan de Reestructuración: Sistema de Parámetros y Rutas

**Fecha de creación:** 2026-01-28  
**Autor:** Victor Landaeta  
**Estado:** En planificación  

---

## 1. Diagnóstico del Estado Actual

### 1.1 Problemas Identificados

#### 🔴 Problema 1: Rutas Absolutas Locales
**Descripción:** Las rutas en `config_rutas_ext_y_archivos.yaml` apuntaban a directorios locales de un usuario específico (`C:\Users\rmunozb\...`).

**Impacto:**
- El código no funciona en otros equipos sin modificación manual
- No hay portabilidad entre desarrolladores
- Dificulta la colaboración y el onboarding de nuevos miembros

**Estado:** ✅ RESUELTO (commit `3480af3`)
- Se cambió a rutas relativas al proyecto
- Se creó función `resolver_ruta()` en `config_rutas.py`

#### 🔴 Problema 2: Rutas a Carpetas Compartidas de Red
**Descripción:** Los datos de entrada provienen de carpetas compartidas (`\\vmdvorak\...`) sin control de versiones.

**Riesgos identificados:**
- Archivos pueden ser modificados sin notificación mientras corren los procesos
- No hay trazabilidad de quién modificó qué y cuándo
- Sin control de versiones = receta para errores de reproducibilidad
- Dependencia de disponibilidad de la red

**Estado:** 🟡 PENDIENTE DE ANÁLISIS
- Requiere evaluación de alternativas (BigQuery, GCS, etc.)
- Posible restricción por compliance que debe validarse

#### 🔴 Problema 3: Formato Excel para Parámetros
**Descripción:** Los parámetros de los modelos se almacenan en archivos Excel (`.xlsx`).

**Problemas del formato Excel:**
- **Ineficiente:** Lectura lenta comparada con formatos nativos
- **Propenso a errores:** 
  - Celdas pueden ser modificadas accidentalmente
  - Formatos de datos inconsistentes (fechas, números)
  - Fórmulas pueden cambiar valores sin ser evidente
- **Sin control de versiones efectivo:** Git no puede hacer diff de archivos binarios
- **Concurrencia:** Problemas cuando múltiples personas editan
- **Validación:** No hay schema que valide la estructura

**Estado:** 🟡 PENDIENTE - Plan propuesto abajo

---

## 2. Propuesta de Solución: Sistema de Parámetros JSON

### 2.1 Filosofía del Diseño

> **Principio clave:** Separar la **fuente de verdad** (JSON versionado) de la **interfaz de usuario** (Excel para visualización).

| Componente | Rol | Editable por analistas |
|------------|-----|------------------------|
| JSON en Git | Fuente de verdad oficial | ❌ No directamente |
| Excel Viewer | Exploración y análisis | ✅ Sí (sin afectar JSON) |
| Excel Editor (opcional) | Modificación controlada | ✅ Con validaciones estrictas |

### 2.2 Ventajas del Enfoque Propuesto

1. **Control de versiones real:** JSON es texto plano, Git puede hacer diff y merge
2. **Trazabilidad completa:** Cada cambio queda registrado con autor, fecha y motivo
3. **Validación automática:** JSON Schema permite validar estructura antes de usar
4. **Respeta la cultura del equipo:** Los analistas siguen usando Excel para explorar
5. **Inmutabilidad controlada:** Los parámetros "productivos" no se modifican accidentalmente
6. **Reproducibilidad:** Se puede saber exactamente qué parámetros se usaron en cada ejecución

### 2.3 Estructura de Archivos Propuesta

```
config/
├── schemas/                              # JSON Schemas para validación
│   ├── parametros_prepago.schema.json
│   ├── parametros_mora.schema.json
│   └── parametros_nmd.schema.json
│
├── parametros/                           # FUENTE DE VERDAD (versionado en Git)
│   ├── mr_prepago_consumo.json
│   ├── mr_prepago_hipotecario.json
│   ├── mr_prepago_cmr.json
│   ├── ml_mora_consumo.json
│   ├── ml_mora_cae.json
│   ├── ml_mora_hipotecario.json
│   ├── ml_mora_comercial.json
│   └── ml_nmd.json
│
└── excel_tools/                          # Herramientas Excel para el equipo
    ├── visor_parametros.xlsm             # Solo lectura - carga JSON para visualizar
    └── editor_parametros.xlsm            # Con controles estrictos (opcional)
```

### 2.4 Formato JSON Propuesto

```json
{
  "$schema": "./schemas/parametros_prepago.schema.json",
  "metadata": {
    "modelo": "mr_prepago_consumo",
    "version": "1.0.0",
    "fecha_actualizacion": "2026-01-28",
    "autor": "vlandaetat",
    "descripcion": "Parámetros calibración Q1 2026",
    "aprobado_por": "rmunozb"
  },
  "parametros": {
    "SMM_MODELO": {
      "CONSUMO": [0.01, 0.012, 0.015, ...],
      "AUTOMOTRIZ": [0.008, 0.009, ...],
      "REFINANCIADO": [...],
      "RENEGOCIADO": [...],
      "CONSOLIDADO": [...]
    },
    "ESCENARIOS": {
      "1": {
        "DESCRIPCION": "BASE",
        "PHI": 1.0
      },
      "2": {
        "DESCRIPCION": "ESTRES_LEVE",
        "PHI": 1.15
      },
      "3": {
        "DESCRIPCION": "ESTRES_SEVERO",
        "PHI": 1.35
      }
    }
  }
}
```

### 2.5 Excel Viewer - Opciones de Implementación

#### Opción A: Power Query (Recomendada)
- Excel conecta al JSON vía "Get Data > From File > From JSON"
- Refresh manual o automático
- **Pros:** Nativo de Excel, sin código VBA
- **Contras:** Requiere que la ruta al JSON sea accesible

#### Opción B: Macro VBA
- Botón "Cargar JSON" que lee y despliega en hojas
- **Pros:** Más control, puede agregar validaciones visuales
- **Contras:** Requiere mantener código VBA

#### Opción C: Script Python genera Excel
- Script que lee JSON y genera Excel de reporte
- **Pros:** Automatizable, integrable en pipeline
- **Contras:** No es "en vivo", genera archivo estático

### 2.6 Excel Editor Controlado (Opcional)

Si se implementa, debe incluir:

1. **Validaciones antes de escribir:**
   - Tipos de datos correctos
   - Rangos válidos (ej: PHI entre 0.5 y 2.0)
   - Longitudes correctas de vectores

2. **Sistema de backup:**
   - Copia automática del JSON anterior antes de sobrescribir
   - Nombrado con timestamp: `mr_prepago_consumo_backup_20260128_153045.json`

3. **Logging de cambios:**
   - Registro de quién cambió qué y cuándo
   - Archivo `parametros_changelog.log`

4. **Flujo de aprobación (opcional):**
   - Cambios van a archivo `_pending.json`
   - Requiere revisión antes de ser oficial

---

## 3. Flujo de Trabajo Propuesto

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO NORMAL DE EJECUCIÓN                         │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐         ┌──────────────────┐         ┌──────────────┐
    │   JSON en Git   │────────▶│  Modelo Python   │────────▶│  Output/BQ   │
    │ (fuente verdad) │         │   (ejecución)    │         │              │
    └────────┬────────┘         └──────────────────┘         └──────────────┘
             │
             │ copia al iniciar (snapshot)
             ▼
    ┌─────────────────┐
    │   logs/params/  │  ← Snapshot de parámetros usados en cada ejecución
    │   2026-01-28/   │    para reproducibilidad
    └─────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE ANÁLISIS (ANALISTAS)                       │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │   JSON en Git   │
    │ (fuente verdad) │
    └────────┬────────┘
             │
             │ lee (solo lectura)
             ▼
    ┌─────────────────┐
    │  Excel Viewer   │  ← Analistas exploran, analizan, simulan
    │  (read-only)    │    SIN modificar la fuente
    └─────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE MODIFICACIÓN (CONTROLADO)                       │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
    │  Excel Editor   │────▶│   Validación     │────▶│  Nuevo JSON +       │
    │  (controlado)   │     │   + Backup       │     │  Commit + PR/MR     │
    └─────────────────┘     └──────────────────┘     └─────────────────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────────┐
                                                     │  Revisión y merge   │
                                                     │  a main             │
                                                     └─────────────────────┘
```

---

## 4. Plan de Implementación

### Fase 1: Migración de Parámetros a JSON ⏳
**Duración estimada:** 1-2 semanas

| Tarea | Descripción | Prioridad |
|-------|-------------|-----------|
| 1.1 | Crear JSON Schemas para cada tipo de modelo | Alta |
| 1.2 | Convertir Excel de parámetros a JSON (un modelo piloto) | Alta |
| 1.3 | Crear `CargadorParametrosJSON` en Python | Alta |
| 1.4 | Migrar resto de modelos | Media |
| 1.5 | Crear tests de validación de schemas | Media |

### Fase 2: Herramientas Excel 📊
**Duración estimada:** 1 semana

| Tarea | Descripción | Prioridad |
|-------|-------------|-----------|
| 2.1 | Crear Excel Viewer con Power Query | Alta |
| 2.2 | Documentar uso del Viewer para el equipo | Alta |
| 2.3 | (Opcional) Crear Excel Editor con VBA | Baja |

### Fase 3: Sistema de Trazabilidad 📝
**Duración estimada:** 1 semana

| Tarea | Descripción | Prioridad |
|-------|-------------|-----------|
| 3.1 | Implementar snapshot de parámetros por ejecución | Media |
| 3.2 | Agregar logging de parámetros usados | Media |
| 3.3 | Crear script de comparación de parámetros entre fechas | Baja |

### Fase 4: Evaluación de Fuentes de Datos 🔍
**Duración estimada:** Por definir

| Tarea | Descripción | Prioridad |
|-------|-------------|-----------|
| 4.1 | Evaluar viabilidad de migrar inputs a BigQuery/GCS | Media |
| 4.2 | Validar restricciones de compliance | Alta |
| 4.3 | Proponer solución para datos de red | Media |

---

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Resistencia al cambio por parte del equipo | Media | Alto | Mantener Excel como interfaz, comunicar beneficios |
| Errores en migración de parámetros | Media | Alto | Validación exhaustiva, período de paralelo |
| Dependencia de red para datos input | Alta | Alto | Evaluar alternativas cloud, cachés locales |
| Complejidad adicional del sistema | Baja | Medio | Documentación clara, automatización |

---

## 6. Métricas de Éxito

- [ ] 100% de parámetros migrados a JSON
- [ ] Cero errores por modificación accidental de parámetros
- [ ] Tiempo de setup para nuevo desarrollador < 30 minutos
- [ ] Capacidad de reproducir cualquier ejecución histórica
- [ ] Equipo de analistas adoptando el Viewer sin fricción

---

## 7. Preguntas Abiertas

1. **¿Los parámetros cambian con qué frecuencia?** 
   - Si es diario/semanal → Excel Editor tiene más sentido
   - Si es mensual/trimestral → Edición directa de JSON por desarrollador

2. **¿Hay restricciones de compliance para los datos de red?**
   - Necesario validar antes de proponer alternativas cloud

3. **¿Se requiere aprobación formal para cambios de parámetros?**
   - Podría implementarse flujo de PR/MR obligatorio

---

## Historial de Cambios de este Documento

| Fecha | Autor | Cambio |
|-------|-------|--------|
| 2026-01-28 | vlandaetat | Creación inicial del documento |
