# Guia de Instalacion — Practicante

> **Autor:** vlandaetat
> **Fecha:** 2026-03-11
> **Contexto:** Manual para configurar el entorno desde cero usando el ZIP entregado.

---

## Prerequisitos

Antes de comenzar, necesitas tener instalado:

| Software | Version | Donde obtenerlo |
|----------|---------|----------------|
| Anaconda | 2024.10+ | Incluido en ZIP o `Z:\RF_INSTALADORES\` |
| Git | 2.52+ | Incluido en ZIP o `Z:\RF_INSTALADORES\` |
| Microsoft Access Database Engine | 2016 (64-bit) | Solicitar a TI si no esta instalado |
| VPN | FortiClient | Debe estar conectado para acceder a `\\vmdvorak` |

## Opcion A: Instalacion Automatica (Recomendada)

### 1. Descomprimir el ZIP

Extraer el ZIP en una carpeta local, por ejemplo:

```
C:\Users\TU_USUARIO\code\bfa-cl-modelos-diarios\
```

> **Importante:** NO descomprimir en una ruta de red ni en el Escritorio. Usar una ruta local corta.

### 2. Ejecutar `setup_env.bat`

Doble-click en `setup_env.bat`. Este script:

1. Verifica que conda esta instalado
2. Crea el entorno `bfa-cl-modelos-v2` con Python 3.11
3. Instala todas las dependencias desde `requirements.txt`
4. Instala `bfa_cl_utilidades` desde el `.whl` incluido en `vendor/`
5. Ejecuta un health check rapido para verificar que todo quedo bien

Si el script dice `SETUP COMPLETADO`, estas listo.

### 3. Verificar con `check_env.bat`

Doble-click en `check_env.bat` para una verificacion completa que incluye:

- Python y entorno conda
- Todas las dependencias Python
- Driver ODBC de Microsoft Access
- Credenciales GCP
- Acceso a carpetas de red (`\\vmdvorak`)
- Conexion a BigQuery

Debe salir **14/14 OK**. Si alguno falla, ver [Troubleshooting](TROUBLESHOOTING.md).

---

## Opcion B: Instalacion Manual

Si `setup_env.bat` falla o prefieres hacerlo manualmente:

### 1. Instalar Anaconda

Ejecutar `Anaconda3-2024.10-1-Windows-x86_64.exe` (incluido en ZIP o en `Z:\RF_INSTALADORES\`).

Opciones de instalacion por defecto. **Marcar "Add to PATH"** si lo da como opcion.

### 2. Abrir Anaconda Prompt

Buscar "Anaconda Prompt" en el menu de inicio.

### 3. Crear entorno conda

```bash
conda create -n bfa-cl-modelos-v2 python=3.11 -y
conda activate bfa-cl-modelos-v2
```

### 4. Navegar al proyecto

```bash
cd C:\Users\TU_USUARIO\code\bfa-cl-modelos-diarios
```

### 5. Instalar dependencias

```bash
pip install -r requirements.txt
pip install vendor\bfa_cl_utilidades-1.0.4-py3-none-any.whl --force-reinstall --no-deps
```

### 6. Verificar

```bash
python tools\check_env.py
```

---

## Estructura de Carpetas Importantes

```
bfa-cl-modelos-diarios/
├── main.py              # Punto de entrada (NO modificar)
├── setup_env.bat        # Instalacion automatica
├── run_diario.bat       # Ejecucion diaria (doble-click)
├── check_env.bat        # Verificacion de entorno
├── config/              # Configuracion (NO modificar)
├── core/                # Motor del sistema (NO modificar)
├── credenciales/        # Credenciales GCP (NO compartir)
├── vendor/              # Wheel de bfa_cl_utilidades
├── logs/                # Logs de ejecucion (por fecha)
├── reports/             # Reportes generados
├── RF_Modelo_*/         # Carpetas de cada modelo
│   └── parametros/      # Parametros JSON + Excel
├── data/                # Cache de datos (se genera solo)
└── tools/               # Scripts de utilidad
```

### Que NO tocar

- `core/`, `config/`, `procesamiento_datos_input/`, `carga_modelos_gcp/` — son el motor
- `credenciales/` — no compartir ni subir a ningun lado
- `main.py` — punto de entrada, no modificar

### Que SI revisar

- `logs/{YYYYMMDD}/` — logs del dia en formato JSONL
- `reports/` — reportes de ejecucion (JSON + Markdown)
- `RF_Modelo_*/parametros/` — parametros de los modelos (si hay que actualizar algo)

---

## Verificacion Post-Instalacion

Ejecutar esta prueba completa para confirmar que todo funciona:

```bash
conda activate bfa-cl-modelos-v2
python main.py --check-env
```

Debe mostrar **14/14 OK**. Si hay errores, ver [Troubleshooting](TROUBLESHOOTING.md).

---

## Siguiente Paso

Una vez instalado, leer [Flujo de Trabajo Diario](DAILY_WORKFLOW.md) para aprender a ejecutar los modelos.
