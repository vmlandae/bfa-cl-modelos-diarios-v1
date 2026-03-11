@echo off
chcp 65001 >nul
title Instalación de Entorno — Modelos Diarios BFA

:: ============================================================================
:: setup_env.bat — Configura el entorno conda e instala dependencias
::
:: Uso: doble-click o ejecutar desde cmd/PowerShell
:: Prerequisitos: Anaconda/Miniconda instalado
:: ============================================================================

:: ── Configuración ──────────────────────────────────────────────────────────
set ENV_NAME=bfa-cl-modelos-v2
set PYTHON_VERSION=3.11
set BASE_DIR=%~dp0

:: ── Detectar conda ─────────────────────────────────────────────────────────
echo.
echo =========================================================
echo   SETUP DE ENTORNO — Modelos Diarios Banco Falabella
echo =========================================================
echo.

where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] conda no encontrado en PATH.
    echo.
    echo Opciones:
    echo   1. Instalar Anaconda desde el ZIP ^(Anaconda3-*-Windows-x86_64.exe^)
    echo   2. Si ya esta instalado, abrir "Anaconda Prompt" y ejecutar este .bat desde ahi
    echo.
    goto :fin_error
)

echo [OK] conda encontrado: 
conda --version

:: ── Verificar si el env ya existe ──────────────────────────────────────────
conda env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo.
    echo [INFO] El entorno "%ENV_NAME%" ya existe.
    set /p RECREAR="Desea recrearlo desde cero? (s/N): "
    if /I not "%RECREAR%"=="s" (
        echo Saltando creacion. Instalando dependencias en env existente...
        goto :instalar_deps
    )
    echo Eliminando entorno existente...
    conda deactivate 2>nul
    conda env remove -n %ENV_NAME% -y
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] No se pudo eliminar el entorno.
        goto :fin_error
    )
)

:: ── Crear entorno conda ───────────────────────────────────────────────────
echo.
echo Creando entorno conda "%ENV_NAME%" con Python %PYTHON_VERSION%...
conda create -n %ENV_NAME% python=%PYTHON_VERSION% -y
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al crear el entorno conda.
    goto :fin_error
)
echo [OK] Entorno creado.

:: ── Instalar dependencias ──────────────────────────────────────────────────
:instalar_deps
echo.
echo Activando entorno %ENV_NAME%...
call conda activate %ENV_NAME%
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se pudo activar el entorno.
    goto :fin_error
)

echo Instalando dependencias desde requirements.txt...
pip install -r "%BASE_DIR%requirements.txt"
if %ERRORLEVEL% neq 0 (
    echo [ADVERTENCIA] Algunos paquetes fallaron. Revise los errores arriba.
)

:: ── Instalar bfa_cl_utilidades desde wheel ─────────────────────────────────
echo.
echo Instalando bfa_cl_utilidades desde vendor/...
if exist "%BASE_DIR%vendor\bfa_cl_utilidades-*.whl" (
    for %%f in ("%BASE_DIR%vendor\bfa_cl_utilidades-*.whl") do (
        pip install "%%f" --force-reinstall --no-deps
    )
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fallo al instalar bfa_cl_utilidades.
        goto :fin_error
    )
    echo [OK] bfa_cl_utilidades instalado.
) else (
    echo [ADVERTENCIA] No se encontro .whl en vendor/
    echo Intentando instalar desde Z:\RF_INSTALADORES\...
    if exist "Z:\RF_INSTALADORES\bfa-cl-utilidades" (
        pip install "Z:\RF_INSTALADORES\bfa-cl-utilidades"
    ) else (
        echo [ERROR] No se encontro bfa_cl_utilidades en ningun lugar.
        goto :fin_error
    )
)

:: ── Verificación rápida ────────────────────────────────────────────────────
echo.
echo Ejecutando verificacion rapida del entorno...
python "%BASE_DIR%tools\check_env.py" --rapido
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ADVERTENCIA] El health check reporto errores criticos. Revise arriba.
) else (
    echo.
    echo [OK] Entorno configurado correctamente.
)

echo.
echo =========================================================
echo   SETUP COMPLETADO
echo   Para ejecutar modelos use: run_diario.bat
echo   Para verificar entorno use: check_env.bat
echo =========================================================
goto :fin

:fin_error
echo.
echo [SETUP FALLIDO] Revise los errores y reintente.
:fin
echo.
pause
