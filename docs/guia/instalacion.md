# Instalación

> **Autor:** vlandaetat  
> **Fecha de creación:** 2026-01-29  
> **Última edición por:** vlandaetat  
> **Fecha última edición:** 2026-03-11

---

!!! tip "Practicante / Primera vez?"
    Si recibiste un ZIP, ve directo a [Setup Practicante](SETUP.md) que tiene instrucciones paso a paso con scripts automáticos.

## Requisitos Previos

- Anaconda o Miniconda (Python 3.11+)
- Acceso VPN a red interna (para `\\vmdvorak`)
- Microsoft Access Database Engine 2016 (64-bit)
- Credenciales de Google Cloud Platform
- Git

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios.git
cd bfa-cl-modelos-diarios
```

### 2. Crear entorno conda

```bash
conda create -n bfa-cl-modelos-v2 python=3.11 -y
conda activate bfa-cl-modelos-v2
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install vendor/bfa_cl_utilidades-1.0.4-py3-none-any.whl
```

### 4. Configurar credenciales GCP

1. Obtener archivo JSON de credenciales de GCP
2. Colocarlo en `credenciales/`
3. Verificar que la ruta en `config/config_rutas.py` apunte al archivo correcto

### 5. Verificar instalación

```bash
python main.py --check-env
```

Debe mostrar **14/14 OK**.

## Problemas Comunes

Ver [Troubleshooting](TROUBLESHOOTING.md) para la guía completa de solución de problemas.

1. Verificar que el archivo JSON existe
2. Verificar que la variable de entorno `GOOGLE_APPLICATION_CREDENTIALS` apunta al archivo
3. O usar: `gcloud auth application-default login`
