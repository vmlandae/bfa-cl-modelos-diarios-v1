# Instalación

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-01-29

---

## Requisitos Previos

- Python 3.10 o superior
- Acceso a carpetas compartidas de red (para inputs)
- Credenciales de Google Cloud Platform
- Git

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios.git
cd bfa-cl-modelos-diarios
```

### 2. Crear entorno virtual (recomendado)

=== "Windows"

    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

=== "Linux/Mac"

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales GCP

1. Obtener archivo JSON de credenciales de GCP
2. Colocarlo en `credenciales/`
3. Verificar que la ruta en `config/config_rutas.py` apunte al archivo correcto

### 5. Verificar instalación

```bash
python -c "import pandas; import openpyxl; import google.cloud.bigquery; print('✅ Todo OK')"
```

## Problemas Comunes

### Error de conexión a carpetas compartidas

Si ves errores de acceso a `\\vmdvorak\...`:

1. Verificar que tienes acceso VPN activo
2. Verificar permisos de usuario en las carpetas
3. Probar acceder manualmente desde Explorador de Windows

### Error de credenciales GCP

Si ves `DefaultCredentialsError`:

1. Verificar que el archivo JSON existe
2. Verificar que la variable de entorno `GOOGLE_APPLICATION_CREDENTIALS` apunta al archivo
3. O usar: `gcloud auth application-default login`
