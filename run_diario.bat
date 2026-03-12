@echo off
chcp 65001 >nul
title Ejecución Diaria — Modelos BFA

:: ============================================================================
:: run_diario.bat — Ejecuta los modelos diarios
::
:: Uso: doble-click o ejecutar desde cmd/PowerShell
:: Pide la fecha y ejecuta todos los modelos + carga a GCP
:: ============================================================================

:: ── Configuración ──────────────────────────────────────────────────────────
set ENV_NAME=bfa-cl-modelos-v2
set BASE_DIR=%~dp0

:: ── Activar entorno ────────────────────────────────────────────────────────
echo.
echo =========================================================
echo   EJECUCION DIARIA — Modelos Banco Falabella
echo =========================================================
echo.

call conda activate %ENV_NAME% 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se pudo activar el entorno "%ENV_NAME%".
    echo Ejecute setup_env.bat primero.
    goto :fin_error
)

cd /d "%BASE_DIR%"

:: ── Health check rápido ────────────────────────────────────────────────────
echo Verificando entorno...
python tools\check_env.py --rapido --json-only 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ADVERTENCIA] El entorno tiene problemas criticos.
    echo Ejecute check_env.bat para ver los detalles.
    set /p CONTINUAR="Desea continuar de todas formas? (s/N): "
    if /I not "%CONTINUAR%"=="s" goto :fin
)
echo [OK] Entorno verificado.
echo.

:: ── Pedir fecha ────────────────────────────────────────────────────────────
:: Calcular fecha de hoy como default
for /f "tokens=1-3 delims=/" %%a in ('echo %date%') do (
    set TODAY=%%c-%%b-%%a 2>nul
)
:: Fallback: usar Python para obtener la fecha
for /f %%d in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y-%%m-%%d'))"') do set TODAY=%%d

echo Fecha de hoy: %TODAY%
set /p FECHA="Ingrese fecha de ejecucion (YYYY-MM-DD) [%TODAY%]: "
if "%FECHA%"=="" set FECHA=%TODAY%

:: Validar formato de fecha
python -c "from datetime import datetime; datetime.strptime('%FECHA%', '%%Y-%%m-%%d')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Formato de fecha invalido. Use YYYY-MM-DD
    goto :fin_error
)

:: ── Menú de ejecución ──────────────────────────────────────────────────────
echo.
echo Fecha seleccionada: %FECHA%
echo.
echo Opciones de ejecucion:
echo   1. Ejecutar TODOS los modelos + cargar a GCP (recomendado)
echo   2. Ejecutar solo PRIMERA VUELTA + cargar a GCP
echo   3. Ejecutar solo SEGUNDA VUELTA + cargar a GCP
echo   4. Ejecutar TODOS sin cargar a GCP (solo local)
echo   5. Solo cargar a GCP (sin ejecutar modelos)
echo   6. Consolidar historico
echo   7. Cancelar
echo.
set /p OPCION="Seleccione opcion [1]: "
if "%OPCION%"=="" set OPCION=1

if "%OPCION%"=="1" goto :todos_gcp
if "%OPCION%"=="2" goto :v1_gcp
if "%OPCION%"=="3" goto :v2_gcp
if "%OPCION%"=="4" goto :todos_local
if "%OPCION%"=="5" goto :solo_carga
if "%OPCION%"=="6" goto :consolidar
if "%OPCION%"=="7" goto :fin
echo [ERROR] Opcion invalida.
goto :fin_error

:todos_gcp
echo.
echo Ejecutando TODOS los modelos + carga GCP para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos todos --cargar-gcp
goto :post_ejecucion

:v1_gcp
echo.
echo Ejecutando PRIMERA VUELTA + carga GCP para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos primera_vuelta --cargar-gcp
goto :post_ejecucion

:v2_gcp
echo.
echo Ejecutando SEGUNDA VUELTA + carga GCP para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos segunda_vuelta --cargar-gcp
goto :post_ejecucion

:todos_local
echo.
echo Ejecutando TODOS los modelos (sin carga GCP) para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos todos
goto :post_ejecucion

:solo_carga
echo.
echo Cargando a GCP (sin ejecutar modelos) para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --solo-carga-gcp todos
goto :post_ejecucion

:consolidar
echo.
echo Consolidando historico para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --consolidar-historico todos
goto :post_ejecucion

:: ── Post ejecución ─────────────────────────────────────────────────────────
:post_ejecucion
set EXIT_CODE=%ERRORLEVEL%
echo.
echo =========================================================
if %EXIT_CODE% equ 0 (
    echo   EJECUCION COMPLETADA
) else (
    echo   EJECUCION COMPLETADA CON ERRORES
)
echo   Revise logs\ y reports\ para mas detalles
echo =========================================================
goto :fin

:fin_error
echo.
echo [EJECUCION CANCELADA]
:fin
echo.
pause
