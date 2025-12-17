# Changelog

Registro de cambios y actualizaciones del proyecto BFA-CL Modelos Diarios.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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