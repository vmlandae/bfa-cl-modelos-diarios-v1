# Troubleshooting

> **Autor:** vlandaetat
> **Fecha:** 2026-03-11
> **Contexto:** Guia de solucion de problemas comunes.

---

## Diagnostico Rapido

Antes de buscar problemas especificos, ejecutar:

```bash
check_env.bat
```

o desde terminal:

```bash
conda activate bfa-cl-modelos-v2
python main.py --check-env
```

Esto revisa 14 puntos y te dice exactamente que esta mal.

---

## Problemas de Instalacion

### "conda no encontrado en PATH"

**Causa:** Anaconda no esta instalado o no esta en PATH.

**Solucion:**

1. Buscar "Anaconda Prompt" en el menu de inicio
2. Ejecutar los comandos desde ahi (no desde cmd.exe ni PowerShell)
3. Si no existe, instalar Anaconda desde `Z:\RF_INSTALADORES\`

### "No se pudo activar el entorno bfa-cl-modelos-v2"

**Causa:** El entorno conda no existe.

**Solucion:**

```bash
conda create -n bfa-cl-modelos-v2 python=3.11 -y
conda activate bfa-cl-modelos-v2
pip install -r requirements.txt
pip install vendor\bfa_cl_utilidades-1.0.4-py3-none-any.whl --force-reinstall --no-deps
```

### "ModuleNotFoundError: bfa_cl_utilidades"

**Causa:** El paquete interno no esta instalado.

**Solucion:**

```bash
conda activate bfa-cl-modelos-v2
pip install vendor\bfa_cl_utilidades-1.0.4-py3-none-any.whl --force-reinstall --no-deps
```

### "No hay driver Access" / ODBC Error

**Causa:** Microsoft Access Database Engine no esta instalado.

**Solucion:**

1. Ir a `Z:\RF_INSTALADORES\` o pedir a TI
2. Instalar "AccessDatabaseEngine_X64.exe" (version 2016 64-bit)
3. **Importante:** instalar la version 64-bit (no 32-bit)

---

## Problemas de Red

### "No accesible: \\vmdvorak\..."

**Causa:** No hay conexion a la red interna del banco.

**Solucion:**

1. Verificar que VPN (FortiClient) esta conectada
2. Verificar en Explorador de Windows que puedes navegar a `\\vmdvorak\Riesgo Financiero Folder\`
3. Si ves carpetas pero los modelos fallan, puede ser un tema de permisos — contactar a TI

### "Z: no existe" / "Z:\RF_INSTALADORES no accesible"

**Causa:** Unidad de red no mapeada.

**Solucion:** No es critico para ejecucion diaria. La unidad Z: solo se necesita si hay que reinstalar `bfa_cl_utilidades` (ya esta en `vendor/`).

---

## Problemas de Ejecucion

### Modelo falla con ERROR pero sin mensaje claro

**Solucion:** Revisar el log detallado:

1. Abrir `logs/{YYYYMMDD}/modelos.jsonl` (donde YYYYMMDD es la fecha del dia)
2. Buscar la linea con `"level": "ERROR"` o `"exc_info"`
3. El campo `"message"` tiene el error detallado

### "Formato de fecha invalido"

**Causa:** La fecha no tiene formato YYYY-MM-DD.

**Solucion:** Usar formato `2026-03-11` (con guiones, 4 digitos de anio).

### Un modelo funciona pero otro no

**Solucion:** Ejecutar solo el modelo que fallo:

```bash
python main.py --fecha 2026-03-11 --modelos ml_mora_consumo --cargar-gcp
```

Modelos disponibles:

| Clave | Modelo |
|-------|--------|
| `mr_prepago_consumo` | Prepago Consumo |
| `mr_prepago_hipotecario` | Prepago Hipotecario |
| `mr_prepago_cmr` | Prepago CMR |
| `ml_mora_consumo` | Mora Consumo |
| `ml_mora_cae` | Mora CAE |
| `ml_mora_hipotecario` | Mora Hipotecario |
| `ml_mora_comercial` | Mora Comercial |
| `ml_nmd` | NMD |
| `ml_lc` | Linea de Credito |
| `ml_inversiones` | Inversiones |

### "UnicodeEncodeError" en consola

**Causa:** Terminal no soporta UTF-8.

**Solucion:** Ejecutar desde `run_diario.bat` (ya incluye `chcp 65001`). Si persiste, usar Anaconda Prompt en vez de cmd.exe.

---

## Problemas de GCP / BigQuery

### "DefaultCredentialsError" o "Could not automatically determine credentials"

**Causa:** Las credenciales GCP no se encuentran.

**Solucion:**

1. Verificar que existe `credenciales/bfa-cl-trade-price-report-dev-9d137fc23b7f.json`
2. El archivo no debe estar vacio ni corrupto (abrirlo con un editor de texto — debe ser JSON valido)

### "Forbidden 403" al cargar a BigQuery

**Causa:** La cuenta de servicio no tiene permisos suficientes.

**Solucion:** Contactar al equipo de datos/GCP. La cuenta de servicio (`modelosrf@...`) necesita permisos de BigQuery Data Editor en el proyecto.

### "Reporte no se sincronizo a BigQuery"

**Causa:** Error temporal de red o permisos.

**Solucion:** El reporte queda en `reports/_pendientes_sync/`. Se reintentara automaticamente en la proxima ejecucion. Tambien puedes forzar el reintento:

```bash
python -c "from core.sync_reportes import sync_pendientes; sync_pendientes()"
```

---

## Problemas de Datos

### "El modelo corrio pero los numeros parecen raros"

**Pasos:**

1. Revisar que la fecha es correcta (hay datos para esa fecha en `\\vmdvorak`)
2. Comparar con el dia anterior: abrir el Excel output del modelo y verificar ordenes de magnitud
3. Si los parametros cambiaron, revisar `RF_Modelo_*/parametros/`

### "Cache desactualizado"

Si los datos de Access se actualizaron pero el modelo sigue usando datos viejos:

```bash
python main.py --fecha 2026-03-11 --modelos todos --cargar-gcp --forzar-recarga
```

Esto ignora el cache parquet y lee directo de Access.

---

## Contacto

Si ningun paso de este documento resuelve el problema:

1. Tomar screenshot del error
2. Copiar el contenido de `reports/health_check.json`
3. Copiar las ultimas 20 lineas de `logs/{YYYYMMDD}/modelos.jsonl`
4. Enviar al equipo de Metodologias y Modelos
