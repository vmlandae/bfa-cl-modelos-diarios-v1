# Plan de Implementación: Carga de Modelos Legacy a GCP

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-01-29

---

## Resumen

Este documento detalla el plan de implementación para la feature `carga-modelos-old`, organizado en fases con tareas verificables.

**Duración estimada total:** 2-3 días de desarrollo

---

## Fase 1: Configuración e Infraestructura

**Objetivo:** Establecer la estructura de archivos y dependencias necesarias.

**Duración estimada:** 2-3 horas

### Tareas

- [x] **1.1 Crear rama `feat/carga-modelos-old`**
  - Criterio de éxito: Rama creada y checkout realizado
  - Verificación: `git branch --show-current` muestra `feat/carga-modelos-old`

- [x] **1.2 Crear estructura de directorios**
  - [x] Crear `almacenamiento_local/`
  - [x] Crear `docs/feats/carga-modelos-old/`
  - Criterio de éxito: Directorios existen en el repo
  - Verificación: `ls -la` muestra las carpetas

- [x] **1.3 Agregar dependencias a `requirements.txt`**
  - [x] Agregar `duckdb`
  - Criterio de éxito: `pip install -r requirements.txt` instala DuckDB
  - Verificación: `python -c "import duckdb; print(duckdb.__version__)"`

- [x] **1.4 Actualizar `.gitignore`**
  - [x] Ignorar archivos `.duckdb`
  - [x] Ignorar archivos `.db`
  - Criterio de éxito: Bases de datos locales no aparecen en `git status`
  - Verificación: Crear archivo `.duckdb` y verificar que no se rastrea

- [x] **1.5 Crear archivo de configuración `config/config_modelos_old.yaml`**
  - [x] Definir estructura base
  - [x] Agregar placeholders para modelos
  - Criterio de éxito: YAML válido y parseable
  - Verificación: `python -c "import yaml; yaml.safe_load(open('config/config_modelos_old.yaml'))"`

---

## Fase 2: Módulo DuckDB

**Objetivo:** Implementar el gestor de base de datos local para históricos.

**Duración estimada:** 3-4 horas

### Tareas

- [x] **2.1 Crear `almacenamiento_local/__init__.py`**
  - Criterio de éxito: Módulo importable
  - Verificación: `python -c "import almacenamiento_local"`

- [x] **2.2 Crear `almacenamiento_local/duckdb_manager.py`**
  - [x] Clase `DuckDBManager` con conexión lazy
  - [x] Método `insertar_desarrollo_modelo()`
  - [x] Método `insertar_desarrollo_consolidado()`
  - [x] Método `obtener_historico_modelo()`
  - [x] Método `obtener_historico_consolidado()`
  - [x] Manejo de errores y logging
  - Criterio de éxito: Todas las operaciones CRUD funcionan
  - Verificación: Tests unitarios pasan

- [ ] **2.3 Implementar particionamiento por fecha**
  - [ ] Crear tabla con columna `fecha_carga` como partition key
  - [ ] Documentar estrategia de retención
  - Criterio de éxito: Queries por rango de fechas son eficientes
  - Verificación: `EXPLAIN` muestra partition pruning

- [ ] **2.4 Crear tests unitarios para DuckDB**
  - [ ] Test de inserción individual
  - [ ] Test de inserción batch
  - [ ] Test de consulta histórica
  - [ ] Test de consolidado
  - Criterio de éxito: 100% de tests pasan
  - Verificación: `pytest tests/test_duckdb_manager.py -v`

---

## Fase 3: Módulo de Carga de Modelos Old

**Objetivo:** Implementar la lectura de Excel legacy y carga a GCP.

**Duración estimada:** 4-5 horas

### Tareas

- [x] **3.1 Crear `carga_modelos_gcp/cargar_modelos_old.py`**
  - [x] Clase `CargadorModelosOld`
  - [x] Método `leer_hoja_desarrollo()`
  - [x] Método `cargar_a_bigquery()`
  - [x] Método `procesar_modelo()`
  - [x] Método `procesar_todos_los_modelos()`
  - Criterio de éxito: Puede leer Excel y cargar a BQ
  - Verificación: Datos aparecen en BigQuery

- [ ] **3.2 Completar configuración de modelos en YAML**
  - [ ] Identificar todos los modelos legacy
  - [ ] Obtener rutas de carpetas compartidas
  - [ ] Definir nombres de tablas en BigQuery
  - Criterio de éxito: Todos los modelos configurados
  - Verificación: YAML contiene todas las entradas necesarias

- [ ] **3.3 Implementar validaciones de datos**
  - [ ] Validar que hoja DESARROLLO existe
  - [ ] Validar schema mínimo esperado
  - [ ] Manejar valores nulos/inválidos
  - Criterio de éxito: Errores de datos se loggean pero no crashean
  - Verificación: Proceso completa con warnings en logs

- [ ] **3.4 Integrar con DuckDB para histórico**
  - [ ] Llamar a `DuckDBManager` después de carga exitosa
  - [ ] Insertar en tabla consolidada
  - Criterio de éxito: Datos en BQ y DuckDB son consistentes
  - Verificación: Query en ambos sistemas retorna mismo row count

- [ ] **3.5 Crear tests de integración**
  - [ ] Test con archivo Excel mock
  - [ ] Test de carga a BQ (con mock o sandbox)
  - [ ] Test de flujo completo
  - Criterio de éxito: Tests pasan en CI
  - Verificación: `pytest tests/test_cargar_modelos_old.py -v`

---

## Fase 4: Integración y Orquestación

**Objetivo:** Integrar con el orquestador existente y GUI.

**Duración estimada:** 2-3 horas

### Tareas

- [ ] **4.1 Modificar `core/orquestador.py`**
  - [ ] Agregar opción para cargar modelos old
  - [ ] Manejar errores de manera aislada (un modelo falla, otros continúan)
  - Criterio de éxito: Orquestador puede ejecutar carga old
  - Verificación: `python -m core.orquestador --modelos-old`

- [ ] **4.2 Actualizar GUI (opcional)**
  - [ ] Agregar checkbox para modelos old
  - [ ] Mostrar progreso de carga
  - Criterio de éxito: Usuario puede seleccionar modelos old desde GUI
  - Verificación: Test manual de interfaz

- [ ] **4.3 Documentar uso**
  - [ ] Actualizar README.md
  - [ ] Agregar ejemplos de ejecución
  - Criterio de éxito: Nuevo usuario puede ejecutar sin ayuda
  - Verificación: Review por otro miembro del equipo

---

## Fase 5: Testing y Validación

**Objetivo:** Asegurar calidad y correctitud antes de merge.

**Duración estimada:** 2-3 horas

### Tareas

- [ ] **5.1 Ejecutar suite completa de tests**
  - [ ] Tests unitarios
  - [ ] Tests de integración
  - [ ] Tests end-to-end
  - Criterio de éxito: 100% pass rate
  - Verificación: `pytest --cov=. --cov-report=html`

- [ ] **5.2 Validar datos en BigQuery**
  - [ ] Comparar row counts con fuente
  - [ ] Verificar tipos de datos
  - [ ] Validar fechas de carga
  - Criterio de éxito: Datos consistentes
  - Verificación: Query de validación en BQ

- [ ] **5.3 Validar datos en DuckDB**
  - [ ] Verificar que histórico se acumula
  - [ ] Verificar que no hay duplicados
  - Criterio de éxito: Datos consistentes día a día
  - Verificación: Query de validación local

- [ ] **5.4 Code review**
  - [ ] Solicitar review de al menos 1 persona
  - [ ] Resolver comentarios
  - Criterio de éxito: Aprobación de reviewer
  - Verificación: MR aprobado en GitLab

---

## Fase 6: Deployment

**Objetivo:** Hacer merge y desplegar a producción.

**Duración estimada:** 1 hora

### Tareas

- [ ] **6.1 Merge a main**
  - [ ] Resolver conflictos si existen
  - [ ] Squash commits si es necesario
  - Criterio de éxito: Merge exitoso
  - Verificación: `git log main` muestra commits

- [ ] **6.2 Verificar en producción**
  - [ ] Ejecutar carga de un modelo
  - [ ] Verificar datos en BQ prod
  - Criterio de éxito: Pipeline funciona en prod
  - Verificación: Datos visibles en BQ console

- [ ] **6.3 Comunicar al equipo**
  - [ ] Enviar resumen de cambios
  - [ ] Documentar cómo usar nueva funcionalidad
  - Criterio de éxito: Equipo informado
  - Verificación: Confirmación de recepción

---

## Dependencias Externas

| Dependencia | Responsable | Estado |
|-------------|-------------|--------|
| Rutas de modelos legacy | vlandaetat | ⏳ Pendiente |
| Acceso a carpetas compartidas | Infra/TI | ✅ Confirmado |
| Credenciales GCP | vlandaetat | ✅ Disponibles |
| Permisos BigQuery | Admin GCP | ✅ Configurados |

---

## Notas y Decisiones Pendientes

1. **¿Qué modelos son "old"?** Necesitamos la lista completa con rutas.
2. **¿Retención de datos en DuckDB?** ¿Guardar indefinidamente o rotar cada N meses?
3. **¿Frecuencia de ejecución?** ¿Diaria automática o manual on-demand?

---

## Changelog del Plan

| Fecha | Autor | Cambio |
|-------|-------|--------|
| 2026-01-29 | vlandaetat | Creación inicial del plan |
