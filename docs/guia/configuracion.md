# Configuración

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-01-29

---

## Archivos de Configuración

El sistema utiliza varios archivos de configuración:

| Archivo | Propósito |
|---------|-----------|
| `config/config_rutas.py` | Rutas internas del proyecto |
| `config/config_rutas_ext_y_archivos.yaml` | Rutas de inputs/outputs externos |
| `config/config_modelos_old.yaml` | Configuración de modelos legacy |

## config_rutas_ext_y_archivos.yaml

Este archivo define las rutas de entrada y salida para cada modelo:

```yaml
modelos:
  mr_prepago_consumo:
    interfaz_datos_input: "ruta/a/inputs"
    excel_parametros_input: "RF_Modelo_Prepago_Consumo/parametros/parametros_mr_prepago_consumo.xlsx"
    excel_output: "RF_Modelo_Prepago_Consumo/mr_prepago_consumo.xlsm"
```

### Tipos de rutas

- **Rutas relativas**: Se resuelven desde la raíz del proyecto
- **Rutas de red**: Para carpetas compartidas (`\\servidor\carpeta`)
- **Rutas absolutas**: Evitar cuando sea posible

## Variables de Entorno

Puedes usar un archivo `.env` para configuraciones sensibles:

```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=credenciales/mi-credencial.json
BQ_PROJECT_ID=mi-proyecto-gcp
```

!!! warning "Importante"
    Nunca commits el archivo `.env` ni credenciales al repositorio.

## Parámetros de Modelos

Cada modelo tiene su archivo de parámetros en `RF_Modelo_*/parametros/`:

```
RF_Modelo_Prepago_Consumo/
└── parametros/
    └── parametros_mr_prepago_consumo.xlsx
```

Estos archivos contienen:

- Tasas SMM por producto
- Escenarios de stress
- Factores de ajuste
