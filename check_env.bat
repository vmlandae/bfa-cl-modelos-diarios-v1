@echo off
chcp 65001 >nul
title Health Check — Modelos BFA

:: ============================================================================
:: check_env.bat — Verifica que el entorno esté correctamente configurado
::
:: Ejecuta el health check completo (Python, deps, red, GCP)
:: Resultado guardado en reports\health_check.json
:: ============================================================================

:: ── Configuración ──────────────────────────────────────────────────────────
set ENV_NAME=bfa-cl-modelos-v2
set BASE_DIR=%~dp0

echo.
echo =========================================================
echo   HEALTH CHECK — Modelos Diarios Banco Falabella
echo =========================================================
echo.

:: ── Activar entorno ────────────────────────────────────────────────────────
call conda activate %ENV_NAME% 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se pudo activar el entorno "%ENV_NAME%".
    echo.
    echo Posibles causas:
    echo   - conda no esta en PATH ^(abrir Anaconda Prompt^)
    echo   - El entorno no existe ^(ejecutar setup_env.bat^)
    echo.
    goto :fin
)

cd /d "%BASE_DIR%"

:: ── Ejecutar health check completo ─────────────────────────────────────────
python tools\check_env.py %*

echo.
pause
:fin
