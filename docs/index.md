# BFA-CL Modelos Diarios

> **Última actualización por:** vlandaetat  
> **Fecha:** 2026-01-29

Bienvenido a la documentación del sistema de **Modelos Diarios de Riesgo Financiero**.

## ¿Qué es este proyecto?

Sistema de ejecución automatizada de modelos de riesgo financiero que:

- 📊 Procesa datos de carteras desde múltiples fuentes
- 🧮 Ejecuta modelos de prepago, mora y NMD
- ☁️ Carga resultados a Google Cloud BigQuery
- 📈 Genera outputs en Excel para análisis

## Inicio Rápido

```bash
# Clonar repositorio
git clone https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios.git

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar interfaz gráfica
python main.py
```

## Modelos Disponibles

| Modelo | Descripción | Estado |
|--------|-------------|--------|
| `mr_prepago_consumo` | Prepago cartera consumo | ✅ Activo |
| `mr_prepago_hipotecario` | Prepago cartera hipotecaria | ✅ Activo |
| `mr_prepago_cmr` | Prepago tarjetas CMR | ✅ Activo |
| `ml_mora_consumo` | Mora cartera consumo | ✅ Activo |
| `ml_mora_cae` | Mora créditos CAE | ✅ Activo |
| `ml_mora_hipotecario` | Mora cartera hipotecaria | ✅ Activo |
| `ml_mora_comercial` | Mora cartera comercial | ✅ Activo |
| `ml_nmd` | Modelo NMD | ✅ Activo |

## Estructura del Proyecto

```
bfa-cl-modelos-diarios/
├── main.py                     # Punto de entrada
├── config/                     # Configuraciones
├── core/                       # Orquestador principal
├── gui/                        # Interfaz gráfica
├── procesamiento_datos_input/  # Carga de datos
├── carga_modelos_gcp/          # Carga a BigQuery
├── RF_Modelo_*/                # Módulos de cada modelo
└── docs/                       # Documentación
```

## Links Útiles

- [Guía de Instalación](guia/instalacion.md)
- [Configuración](guia/configuracion.md)
- [Contribuir](desarrollo/contribuir.md)
