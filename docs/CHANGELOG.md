# Changelog

Registro de cambios y actualizaciones del proyecto BFA-CL Modelos Diarios.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0-dev] - 2025-12-29 - Mejoras en Documentación y Consolidación de Funciones

### Mejorado
- **Documentación de funciones**: Docstrings comprehensivos implementados para `calcular_flujos_estimados_mora()` en todos los modelos de mora
- **Estándares de documentación**: Documentación técnica unificada con especificaciones detalladas de parámetros, valores de retorno y notas técnicas
- **Claridad funcional**: Explicaciones detalladas del propósito y funcionamiento de las funciones de cálculo de flujos

### Agregado
- **Documentación técnica completa**: 
  - Especificación detallada de `calcular_flujos_estimados_mora()`


### Modificado
- **Función consolidada**: `calcular_flujos_estimados_mora()` ahora procesa amortización e interés simultáneamente
- **Eficiencia mejorada**: Eliminación de duplicación de código mediante consolidación funcional



## [1.1.0-dev] - 2025-12-19 - Consolidación Arquitectónica

### Modificado
- **Consolidación de interfaz de modelos**: Todos los modelos ahora implementan una función `ejecutar_modelo(fecha_proceso) -> bool` unificada
- **Simplificación del orquestador**: Eliminado código de compatibilidad hacia atrás, ahora usa directamente la interfaz unificada
- **Estandarización de manejo de errores**: Patrón uniforme de captura y reporte de errores en todos los modelos
- **Validación consistente de datos**: Verificación estándar de datos vacíos en todos los modelos
- **Optimización de rendimiento**: Eliminación de verificaciones dinámicas en tiempo de ejecución

### Agregado
- **Interfaz unificada**: Función `ejecutar_modelo()` implementada en los 7 modelos del sistema
- **Documentación de funciones**: Docstrings consistentes para todas las funciones ejecutar_modelo
- **Manejo de retorno estándar**: Todos los modelos retornan `True`/`False` para indicar éxito/fallo

### Mejorado
- **Mantenibilidad del código**: Estructura consistente facilita el mantenimiento y debugging
- **Integración con orquestador**: Flujo de ejecución más predecible y eficiente
- **Escalabilidad**: Arquitectura preparada para agregar nuevos modelos fácilmente

#### Modelos Consolidados
- ✅ **RF_Modelo_Mora_Consumo**: `ml_mora_consumo.py`
- ✅ **RF_Modelo_Mora_CAE**: `ml_mora_cae.py`  
- ✅ **RF_Modelo_Mora_Comercial**: `ml_mora_comercial.py`
- ✅ **RF_Modelo_Mora_Hipotecario**: `ml_mora_hipotecario.py`
- ✅ **RF_Modelo_Prepago_CMR**: `mr_prepago_cmr.py`
- ✅ **RF_Modelo_Prepago_Consumo**: `mr_prepago_consumo.py`
- ✅ **RF_Modelo_Prepago_Hipotecario**: `mr_prepago_hipotecario.py`

## [1.0.0-dev] - 2025-12-17 - Estado Inicial (En Desarrollo)

> ⚠️ **Proyecto en Desarrollo Activo**: Este sistema se encuentra actualmente en fase de desarrollo y mejora continua. Las funcionalidades pueden estar sujetas a cambios y optimizaciones.

### Agregado
- **Sistema completo de modelos de riesgo financiero** implementado
- **Orquestador principal** (`core/orquestador.py`) para coordinar ejecución de modelos
- **Interfaz de línea de comandos** con múltiples opciones de ejecución
- **Interfaz gráfica (GUI)** para operación visual del sistema
- **7 Modelos de Machine Learning** implementados:
  - **Modelos de Mora**: CAE, Comercial, Consumo, Hipotecario
  - **Modelos de Prepago**: CMR, Consumo, Hipotecario
- **Integración completa con Google Cloud Platform**:
  - Carga automática a BigQuery (diaria e histórica)
  - Credenciales y autenticación configuradas
- **Sistema de configuración centralizado**:
  - Archivo YAML para rutas externas (`config/config_rutas_ext_y_archivos.yaml`)
  - Módulo de configuración Python (`config/config_rutas.py`)
- **Plantillas Excel** para cada modelo con cálculos específicos
- **Notebooks de desarrollo** (Jupyter) para modelos de prepago
- **Directorios de parámetros** individuales para cada modelo
- **Historial de ejecuciones** para modelos de prepago
- **Archivo principal** (`main.py`) con funcionalidades:
  - Ejecución individual o masiva de modelos
  - Modo solo carga a GCP
  - Listado de modelos disponibles
  - Interfaz gráfica y modo consola
- **Documentación completa del proyecto**:
  - README.md con estructura detallada
  - Instrucciones de uso y configuración
  - Descripción de arquitectura del sistema
- **Configuración de seguridad**:
  - `.gitignore` para proteger credenciales
  - Exclusión de archivos temporales y sensibles
- **Estructura de documentación** (`docs/`) con changelog

### Características del Sistema
- **Ejecución paralela** de múltiples modelos
- **Procesamiento por lotes** de datos financieros
- **Carga automática** de resultados a BigQuery
- **Interfaz dual**: GUI y línea de comandos
- **Configuración flexible** por modelo
- **Integración con librería BFA-CL Utilidades**
- **Soporte para múltiples productos financieros**:
  - Créditos de consumo, comerciales e hipotecarios
  - Créditos automotriz empresas (CAE)
  - Tarjetas de crédito CMR

### Arquitectura Implementada
- **Patrón Orquestador** para coordinación de procesos
- **Separación de responsabilidades** por módulos
- **Configuración centralizada** y parametrizable
- **Integración cloud-native** con GCP
- **Interfaz de usuario modular** (GUI + CLI)

---

## Formato de Entradas

### [Versión] - YYYY-MM-DD

#### Agregado
- Nuevas funcionalidades y características

#### Modificado  
- Cambios en funcionalidades existentes

#### Corregido
- Corrección de bugs y errores

#### Eliminado
- Funcionalidades removidas

#### Seguridad
- Mejoras de seguridad y vulnerabilidades corregidas

---

## Notas

- **Agregado** para nuevas funcionalidades
- **Modificado** para cambios en funcionalidades existentes
- **Deprecated** para funcionalidades que serán removidas pronto
- **Eliminado** para funcionalidades removidas
- **Corregido** para cualquier corrección de bugs
- **Seguridad** en caso de vulnerabilidades

### Ejemplos de entradas:

```markdown
## [1.0.0] - 2025-12-17

### Agregado
- Nuevo modelo ML Mora CAE implementado
- Integración con BigQuery para carga automática
- Interfaz gráfica (GUI) para operación del sistema

### Modificado
- Optimizado rendimiento del orquestador principal
- Mejorada validación de parámetros en modelos de prepago

### Corregido
- Error en carga de configuración YAML
- Bug en procesamiento de fechas en modelo hipotecario

### Seguridad
- Implementadas credenciales encriptadas para GCP
- Agregada validación de acceso a recursos sensibles
```