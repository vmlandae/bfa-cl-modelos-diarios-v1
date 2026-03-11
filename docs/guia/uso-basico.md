# Uso Básico

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-03-11

---

## Ejecución Rápida

La forma más sencilla es doble-click en `run_diario.bat`. Ver [Flujo de Trabajo Diario](DAILY_WORKFLOW.md) para la guía completa.

## Interfaz Gráfica

```bash
python main.py --gui
```

Permite seleccionar modelos, fecha y ejecutar visualmente.

## Línea de Comandos

```bash
# Ejecutar todos los modelos + cargar a GCP
python main.py --fecha 2026-03-11 --modelos todos --cargar-gcp

# Solo primera vuelta
python main.py --fecha 2026-03-11 --modelos primera_vuelta --cargar-gcp

# Solo segunda vuelta
python main.py --fecha 2026-03-11 --modelos segunda_vuelta --cargar-gcp

# Modelo específico
python main.py --fecha 2026-03-11 --modelos mr_prepago_consumo --cargar-gcp

# Solo cargar a GCP (sin ejecutar)
python main.py --fecha 2026-03-11 --solo-carga-gcp todos

# Consolidar histórico
python main.py --fecha 2026-03-11 --consolidar-historico todos

# Consolidar forzando re-inserción (con backup)
python main.py --fecha 2026-03-11 --consolidar-historico todos --force-historico

# Health check del entorno
python main.py --check-env

# Listar modelos
python main.py --listar

# Forzar recarga de cache Access
python main.py --fecha 2026-03-11 --modelos todos --forzar-recarga
```

## Flujo de Ejecución

```mermaid
graph LR
    A[Seleccionar Modelos] --> B[Cargar Datos]
    B --> C[Cargar Parámetros]
    C --> D[Ejecutar Modelo]
    D --> E[Escribir Excel .xlsx]
    E --> F[Cargar a BigQuery]
    F --> G[Generar Reporte]
    G --> H[Sync a BQ]
```

## Outputs

Cada modelo genera:

1. **Archivo Excel** (`.xlsx`) con hojas de resultados y desarrollo
2. **Tabla en BigQuery** con resultados + fecha + metadatos
3. **Reporte de ejecución** en `reports/` (JSON + Markdown)

## Logs

Los logs se guardan en `logs/{YYYYMMDD}/modelos.jsonl` en formato JSONL estructurado con contexto del modelo, nivel, timestamp y mensaje.

```
logs/
├── 2026-01-29_ejecucion.log
└── 2026-01-29_errores.log
```
