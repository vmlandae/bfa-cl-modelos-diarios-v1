# Análisis: ¿Cómo almacenar la configuración de instrumentos?

## Contexto del Problema

La configuración actual de `CONFIGURACION_INSTRUMENTOS` contiene:
- **Datos estáticos**: códigos, nombres, monedas
- **Referencias a nombres de tablas Access**: `tabla_factores`, `instrumento_fpl`
- **Códigos de salida**: `cod_sub_pro_final`

**No contiene** (actualmente):
- Funciones o lambdas
- Lógica condicional
- Cálculos

Esto es importante porque determina qué formatos son viables.

---

## Opciones Analizadas

### Opción 1: Python Dict (.py)
```python
# config/instrumentos.py
CONFIGURACION_INSTRUMENTOS = {
    'GobCLP': {
        'codigos_disp': ['BCP', 'BTP', 'PDB'],
        'moneda': 'CLP',
        ...
    }
}
```

### Opción 2: JSON (.json)
```json
{
  "GobCLP": {
    "codigos_disp": ["BCP", "BTP", "PDB"],
    "moneda": "CLP"
  }
}
```

### Opción 3: YAML (.yaml)
```yaml
GobCLP:
  codigos_disp: [BCP, BTP, PDB]
  moneda: CLP
```

### Opción 4: TOML (.toml)
```toml
[GobCLP]
codigos_disp = ["BCP", "BTP", "PDB"]
moneda = "CLP"
```

### Opción 5: Excel (.xlsx)
| instrumento | codigos_disp | codigos_pacto | moneda | tabla_factores |
|-------------|--------------|---------------|--------|----------------|
| GobCLP | BCP,BTP,PDB | BCP,BTP,PDB | CLP | RF_FactCLP_Gob |

### Opción 6: CSV
```csv
instrumento,codigos_disp,codigos_pacto,moneda,tabla_factores
GobCLP,"BCP,BTP,PDB","BCP,BTP,PDB",CLP,RF_FactCLP_Gob
```

---

## Matriz de Comparación Detallada

| Criterio | Python | JSON | YAML | TOML | Excel | CSV |
|----------|--------|------|------|------|-------|-----|
| **Legibilidad** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Edición por usuarios no-técnicos** | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Comentarios inline** | ✅ | ❌ | ✅ | ✅ | ✅ (celdas) | ❌ |
| **Listas nativas** | ✅ | ✅ | ✅ | ✅ | ❌ (separador) | ❌ |
| **Validación de tipos** | ✅ (runtime) | ❌ | ❌ | ✅ | ❌ | ❌ |
| **IDE autocomplete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Control de versiones (git diff)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Dependencias externas** | Ninguna | Ninguna | PyYAML | tomli/tomllib | openpyxl | Ninguna |
| **Soporte en Python 3.11+** | Nativo | Nativo | Requiere pkg | **Nativo** | Requiere pkg | Nativo |
| **Extensible a lógica** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Análisis Profundo por Criterio

### 1. Consistencia con el Proyecto Actual

El proyecto **ya usa YAML** para configuración:
```yaml
# config/config_rutas_ext_y_archivos.yaml
modelos:
  mr_prepago_consumo:
    interfaz_datos_input: "\\\\vmdvorak\\..."
```

**Argumento a favor de YAML**: Mantiene consistencia con el patrón existente.

**Contra-argumento**: El YAML existente es para rutas simples (strings), no para estructuras complejas con listas anidadas.

---

### 2. ¿Quién edita esta configuración?

#### Si la editan desarrolladores Python:
- **Python dict o YAML** son ideales
- Pueden usar IDE con validación

#### Si la editan analistas/usuarios de negocio:
- **Excel** es claramente superior
- No necesitan saber programar
- Pueden agregar instrumentos sin tocar código

#### Realidad probable:
Los instrumentos financieros (GobCLP, DPF, etc.) **cambian muy poco**. La última vez que se agregó uno fue probablemente hace años.

**Conclusión**: La facilidad de edición es menos crítica de lo que parece.

---

### 3. Complejidad de las Listas

El config tiene listas:
```python
'codigos_disp': ['BCP', 'BTP', 'PDB']
```

#### En JSON:
```json
"codigos_disp": ["BCP", "BTP", "PDB"]
```
✅ Funciona perfecto, parsing nativo.

#### En YAML:
```yaml
codigos_disp: [BCP, BTP, PDB]
# o también:
codigos_disp:
  - BCP
  - BTP
  - PDB
```
✅ Funciona perfecto, más legible.

#### En Excel:
```
| codigos_disp |
| BCP,BTP,PDB  |
```
⚠️ Requiere parsing manual: `str.split(',')` → propenso a errores con espacios.

#### En CSV:
```csv
"BCP,BTP,PDB"
```
⚠️ Mismo problema que Excel, peor legibilidad.

---

### 4. Comentarios y Documentación

La configuración actual tiene comentarios valiosos:
```python
'codigos_pacto': ['BCU', 'BTU', 'CER'],     # Nota: incluye CER en pactos
'filtro_moneda': None,                       # No filtrar por moneda (ya están en CLP)
```

| Formato | Soporte Comentarios |
|---------|---------------------|
| Python | `# comentario` ✅ |
| JSON | ❌ No soporta |
| YAML | `# comentario` ✅ |
| TOML | `# comentario` ✅ |
| Excel | Celda de "notas" o columna extra |
| CSV | ❌ No soporta |

**Si los comentarios son importantes, JSON y CSV quedan descartados.**

---

### 5. Validación y Type Safety

#### Con Python:
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ConfigInstrumento:
    codigos_disp: List[str]
    moneda: str
    filtro_moneda: Optional[str] = None
```
✅ El IDE valida tipos, autocomplete funciona.

#### Con JSON/YAML:
```python
config = yaml.safe_load(open('config.yaml'))
# config['GobCLP']['codigo_disp']  # Typo! No se detecta hasta runtime
```
❌ Sin validación estática, errores silenciosos.

#### Solución híbrida (JSON Schema):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "properties": {
    "codigos_disp": {"type": "array", "items": {"type": "string"}}
  }
}
```
⚠️ Agrega complejidad, requiere tooling adicional.

---

### 6. Extensibilidad Futura

¿Qué pasa si en el futuro necesitas lógica condicional?

```python
# Ejemplo hipotético: validación custom por instrumento
CONFIGURACION_INSTRUMENTOS = {
    'GobCLP': {
        'codigos_disp': ['BCP', 'BTP', 'PDB'],
        'validar': lambda df: df['Moneda'] == 'CLP',  # ← Imposible en JSON/YAML
    }
}
```

| Formato | Soporta Funciones |
|---------|-------------------|
| Python | ✅ Sí |
| JSON | ❌ No |
| YAML | ⚠️ Con tags custom (hack) |
| Excel | ❌ No |

**Realidad**: La configuración actual NO tiene funciones y probablemente no las necesite. Este es un argumento teórico más que práctico.

---

### 7. Diffs en Git

Cuando alguien modifica la configuración, ¿qué tan fácil es ver el cambio?

#### Python/JSON/YAML/TOML:
```diff
- 'codigos_disp': ['BCP', 'BTP', 'PDB'],
+ 'codigos_disp': ['BCP', 'BTP', 'PDB', 'NEW'],
```
✅ Diff limpio, fácil de revisar en PR.

#### Excel:
```
Binary file changed
```
❌ Imposible ver qué cambió sin abrir el archivo.

**Si usan Git y code review, Excel es problemático.**

---

## Recomendación por Escenario

### Escenario A: "Quiero máxima simplicidad, consistencia con el proyecto"
**→ YAML**

```yaml
# config/instrumentos.yaml
GobCLP:
  nombre_completo: Gobierno CLP
  codigos_disp: [BCP, BTP, PDB]
  codigos_pacto: [BCP, BTP, PDB]
  filtro_moneda: null  # No filtrar, ya están en CLP
  tabla_factores: RF_FactCLP_Gob
  instrumento_fpl: Gobierno CLP
  moneda: CLP
  cod_sub_pro_final: ML_C46_Inversiones_Financieras_GOBCLP
```

**Carga en Python:**
```python
import yaml
from pathlib import Path

def cargar_config_instrumentos() -> dict:
    ruta = Path(__file__).parent / 'instrumentos.yaml'
    with open(ruta, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

**Pros:**
- Consistente con `config_rutas_ext_y_archivos.yaml`
- Soporta comentarios
- Legible sin conocer Python

**Contras:**
- Requiere `PyYAML` (ya está instalado en el proyecto)
- Sin validación de tipos estática

---

### Escenario B: "Quiero type safety y autocomplete en IDE"
**→ Python con dataclasses**

```python
# config/instrumentos.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ConfigInstrumento:
    nombre_completo: str
    codigos_disp: List[str]
    codigos_pacto: List[str]
    tabla_factores: str
    instrumento_fpl: str
    moneda: str
    cod_sub_pro_final: str
    filtro_moneda: Optional[str] = None

INSTRUMENTOS = {
    'GobCLP': ConfigInstrumento(
        nombre_completo='Gobierno CLP',
        codigos_disp=['BCP', 'BTP', 'PDB'],
        codigos_pacto=['BCP', 'BTP', 'PDB'],
        tabla_factores='RF_FactCLP_Gob',
        instrumento_fpl='Gobierno CLP',
        moneda='CLP',
        cod_sub_pro_final='ML_C46_Inversiones_Financieras_GOBCLP',
    ),
    # ...
}
```

**Pros:**
- IDE autocomplete: `config.codigos_disp` funciona
- Errores de typo detectados al importar
- Documentación integrada con docstrings

**Contras:**
- Más verboso
- Solo editable por quien sabe Python

---

### Escenario C: "Los analistas deben poder editar sin tocar código"
**→ Excel + validación**

```
📁 config/
   └── instrumentos.xlsx
```

| instrumento | nombre_completo | codigos_disp | codigos_pacto | moneda | tabla_factores | notas |
|-------------|-----------------|--------------|---------------|--------|----------------|-------|
| GobCLP | Gobierno CLP | BCP;BTP;PDB | BCP;BTP;PDB | CLP | RF_FactCLP_Gob | Sin filtro moneda |

**Carga en Python:**
```python
import pandas as pd

def cargar_config_instrumentos() -> dict:
    df = pd.read_excel('config/instrumentos.xlsx')
    config = {}
    for _, row in df.iterrows():
        config[row['instrumento']] = {
            'nombre_completo': row['nombre_completo'],
            'codigos_disp': row['codigos_disp'].split(';'),
            'codigos_pacto': row['codigos_pacto'].split(';'),
            # ...
        }
    return config
```

**Pros:**
- Cualquier analista puede editarlo
- Visual, familiar para usuarios de negocio
- Puede tener validaciones de Excel (dropdown, etc.)

**Contras:**
- Git diff binario
- Parsing de listas con `.split()`
- Más propenso a errores de formato

---

### Escenario D: "Estándar moderno sin dependencias extra"
**→ TOML (Python 3.11+)**

```toml
# config/instrumentos.toml
[GobCLP]
nombre_completo = "Gobierno CLP"
codigos_disp = ["BCP", "BTP", "PDB"]
codigos_pacto = ["BCP", "BTP", "PDB"]
moneda = "CLP"
tabla_factores = "RF_FactCLP_Gob"
# Nota: sin filtro_moneda porque ya están en CLP
```

**Carga en Python 3.11+:**
```python
import tomllib  # ¡Incluido en stdlib desde 3.11!
from pathlib import Path

def cargar_config_instrumentos() -> dict:
    ruta = Path(__file__).parent / 'instrumentos.toml'
    with open(ruta, 'rb') as f:
        return tomllib.load(f)
```

**Pros:**
- Sin dependencias externas (Python 3.11+)
- Soporta comentarios
- Muy popular para configuración (pyproject.toml, etc.)

**Contras:**
- Menos conocido que YAML por algunos usuarios
- Solo lectura con `tomllib` (escribir requiere `tomli-w`)

---

## Matriz de Decisión Final

| Si tu prioridad es... | Usa |
|-----------------------|-----|
| Consistencia con el proyecto actual | **YAML** |
| Type safety y autocomplete | **Python dataclasses** |
| Edición por usuarios no-técnicos | **Excel** |
| Cero dependencias (Python 3.11+) | **TOML** |
| Simplicidad máxima | **JSON** (sin comentarios) |

---

## Mi Recomendación Personal

Dado el contexto de este proyecto:

1. **Ya usan YAML** para otras configuraciones
2. **Los instrumentos cambian raramente** (no necesitan edición constante por usuarios)
3. **El código es mantenido por desarrolladores** (no analistas)
4. **PyYAML ya está instalado** (lo usa `mkdocs.yml`)

### → Recomiendo: **YAML + función de validación**

```yaml
# RF_Modelo_Inversiones/config/instrumentos.yaml
# Configuración de instrumentos para modelo de inversiones
# Última actualización: 2026-02-03
# Mantener sincronizado con tablas Access

GobCLP:
  nombre_completo: Gobierno CLP
  codigos_disp: [BCP, BTP, PDB]
  codigos_pacto: [BCP, BTP, PDB]
  filtro_moneda: null  # Ya filtrados por código
  tabla_factores: RF_FactCLP_Gob
  instrumento_fpl: Gobierno CLP
  instrumento_montos_liq: Gobierno CLP
  moneda: CLP
  nombre_salida: Flujo_GobCLP
  cod_sub_pro_final: ML_C46_Inversiones_Financieras_GOBCLP
```

Con una función de carga que valide:

```python
# RF_Modelo_Inversiones/config/cargar_config.py
import yaml
from pathlib import Path
from typing import Dict, Any

CAMPOS_REQUERIDOS = [
    'nombre_completo', 'codigos_disp', 'codigos_pacto',
    'tabla_factores', 'moneda', 'cod_sub_pro_final'
]

def cargar_config_instrumentos() -> Dict[str, Dict[str, Any]]:
    """Carga y valida configuración de instrumentos desde YAML."""
    ruta = Path(__file__).parent / 'instrumentos.yaml'
    
    with open(ruta, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Validación básica
    for instrumento, params in config.items():
        faltantes = [c for c in CAMPOS_REQUERIDOS if c not in params]
        if faltantes:
            raise ValueError(
                f"Instrumento '{instrumento}' falta campos: {faltantes}"
            )
    
    return config
```

---

## ¿Cuándo reconsiderar?

Cambiaría a **Excel** si:
- El equipo de negocio pide agregar instrumentos frecuentemente
- Hay rotación de personal técnico y necesitan algo visual

Cambiaría a **Python dataclasses** si:
- Empiezan a tener bugs por typos en nombres de campos
- Necesitan lógica condicional por instrumento

Cambiaría a **TOML** si:
- Migran a Python 3.11+ y quieren eliminar PyYAML

---

## Conclusión

No hay una respuesta "correcta" universal. La decisión depende de:
1. **Quién mantiene el código** (devs vs analistas)
2. **Con qué frecuencia cambia** (raro vs frecuente)
3. **Qué herramientas ya usan** (YAML ya está presente)

Para este proyecto específico, **YAML** es la opción más pragmática porque mantiene consistencia y ya tienen la dependencia instalada.

¿Tienes alguna preferencia o restricción que deba considerar?
