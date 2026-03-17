# BFA-CL Modelos Diarios

> **Ultima actualizacion por:** vlandaetat  
> **Fecha:** 2026-03-17

Bienvenido a la documentacion del sistema de **Modelos Diarios de Riesgo Financiero**.

## Que es este proyecto?

Sistema de ejecucion automatizada de modelos de riesgo financiero que:

- Procesa datos de carteras desde multiples fuentes
- Ejecuta modelos de prepago, mora, NMD, linea de credito e inversiones
- Carga resultados a Google Cloud BigQuery
- Genera outputs en Excel para analisis
- Dashboard Streamlit con 6 paginas para monitoreo y operacion
- Reportes email automaticos via Outlook COM con charts por modelo

## Inicio Rápido

=== "Practicante (ZIP)"

    ```
    1. Descomprimir ZIP en C:\Users\TU_USUARIO\code\
    2. Doble-click en setup_env.bat
    3. Doble-click en check_env.bat (verificar 14/14 OK)
    4. Doble-click en run_diario.bat
    ```

    Ver [Guía de Setup Completa](guia/SETUP.md) para más detalles.

=== "Desarrollador (Git)"

    ```bash
    git clone https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios.git
    conda create -n bfa-cl-modelos-v2 python=3.11 -y
    conda activate bfa-cl-modelos-v2
    pip install -r requirements.txt
    pip install vendor/bfa_cl_utilidades-1.0.4-py3-none-any.whl
    python main.py --check-env
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
| [`ml_lc`](modelos/lc.md) | Línea de Crédito | ✅ Activo |
| [`ml_inversiones`](modelos/inversiones.md) | Modelo Inversiones | ✅ Activo |

## Estructura del Proyecto

```
bfa-cl-modelos-diarios/
├── main.py                     # Punto de entrada
├── setup_env.bat               # Instalación automática
├── run_diario.bat              # Ejecución diaria interactiva
├── check_env.bat               # Verificación de entorno
├── config/                     # Configuraciones
├── core/                       # Motor del sistema
│   ├── orquestador.py          # Orquestacion de modelos
│   ├── logger.py               # Logging JSONL + consola
│   ├── excel_output.py         # Escritura Excel (xlsxwriter)
│   ├── email_report.py         # Reportes email multi-tipo (F26)
│   ├── reporte_ejecucion.py    # Reportes + benchmark (F25)
│   └── sync_reportes.py        # Sync reportes a BigQuery (F25)
├── dashboard/                  # Dashboard Streamlit (6 paginas)
│   ├── app.py                  # Entry point (st.navigation)
│   └── pages/                  # Home, Logs, Comparacion, Benchmark, Parametros, Email
├── gui/                        # Interfaz grafica
├── procesamiento_datos_input/  # Carga de datos + caché
├── carga_modelos_gcp/          # Carga a BigQuery (daily + hist)
├── RF_Modelo_*/                # Módulos de cada modelo
├── vendor/                     # bfa_cl_utilidades .whl
├── tools/                      # Scripts de utilidad
├── logs/                       # Logs JSONL por fecha
├── reports/                    # Reportes de ejecución
├── snapshots/                  # Snapshots de parámetros (F02)
└── docs/                       # Documentación
```

## Links Utiles

- [Guia de Instalacion](guia/instalacion.md)
- [Configuracion](guia/configuracion.md)
- [Contribuir](desarrollo/contribuir.md)

## Dashboard

```bash
streamlit run dashboard/app.py
```

Abre en `http://localhost:8501` con 6 paginas: Home, Logs, Comparacion, Benchmark, Parametros y Email Report.
