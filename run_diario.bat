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
:: Calcular t-1 habil (lun-vie): si hoy es lunes, t-1 = viernes anterior
for /f %%d in ('python -c "from datetime import datetime,timedelta; t=datetime.now(); d={0:3,5:1,6:2}.get(t.weekday(),1); print((t-timedelta(days=d)).strftime('%%Y-%%m-%%d'))"') do set DEFAULT_FECHA=%%d

:: Mostrar dia de la semana de la fecha default
for /f %%w in ('python -c "from datetime import datetime; dias=['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']; print(dias[datetime.strptime('%DEFAULT_FECHA%','%%Y-%%m-%%d').weekday()])"') do set DIA_DEFAULT=%%w
echo Fecha default (t-1 habil): %DEFAULT_FECHA% (%DIA_DEFAULT%)
set /p FECHA="Ingrese fecha de ejecucion (YYYY-MM-DD) [%DEFAULT_FECHA%]: "
if "%FECHA%"=="" set FECHA=%DEFAULT_FECHA%

:: Validar formato de fecha y obtener dia de la semana
for /f %%w in ('python -c "from datetime import datetime; dias=['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']; print(dias[datetime.strptime('%FECHA%','%%Y-%%m-%%d').weekday()])" 2^>nul') do set DIA_SEMANA=%%w
if "%DIA_SEMANA%"=="" (
    echo [ERROR] Formato de fecha invalido. Use YYYY-MM-DD
    goto :fin_error
)

:: ── Menú de ejecución ──────────────────────────────────────────────────────
:menu_principal
echo.
echo Fecha seleccionada: %FECHA% (%DIA_SEMANA%)
echo.
echo Opciones de ejecucion:
echo.
echo   --- Con carga a GCP ---
echo   1. Ejecutar TODOS los modelos + cargar a GCP (recomendado)
echo   2. Ejecutar solo PRIMERA VUELTA + cargar a GCP
echo   3. Ejecutar solo SEGUNDA VUELTA + cargar a GCP
echo.
echo   --- Solo local (sin GCP) ---
echo   4. Ejecutar TODOS sin cargar a GCP
echo   5. Ejecutar solo PRIMERA VUELTA sin GCP
echo   6. Ejecutar solo SEGUNDA VUELTA sin GCP
echo   7. Ejecutar modelo individual...
echo.
echo   --- Otras ---
echo   8. Solo cargar a GCP (sin ejecutar modelos)
echo   9. Consolidar historico
echo   0. Cancelar
echo.
set /p OPCION="Seleccione opcion [1]: "
if "%OPCION%"=="" set OPCION=1

if "%OPCION%"=="1" goto :todos_gcp
if "%OPCION%"=="2" goto :v1_gcp
if "%OPCION%"=="3" goto :v2_gcp
if "%OPCION%"=="4" goto :todos_local
if "%OPCION%"=="5" goto :v1_local
if "%OPCION%"=="6" goto :v2_local
if "%OPCION%"=="7" goto :modelo_individual
if "%OPCION%"=="8" goto :solo_carga
if "%OPCION%"=="9" goto :consolidar
if "%OPCION%"=="0" goto :fin
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

:v1_local
echo.
echo Ejecutando PRIMERA VUELTA (sin carga GCP) para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos primera_vuelta
goto :post_ejecucion

:v2_local
echo.
echo Ejecutando SEGUNDA VUELTA (sin carga GCP) para %FECHA%...
echo ─────────────────────────────────────────────────────────
python main.py --fecha %FECHA% --modelos segunda_vuelta
goto :post_ejecucion

:modelo_individual
echo.
echo ─────────────────────────────────────────────────────────
echo   Seleccione un modelo para ejecutar:
echo ─────────────────────────────────────────────────────────
echo.
echo   --- Primera Vuelta ---
echo    1. Prepago Consumo          (mr_prepago_consumo)
echo    2. Prepago Hipotecario      (mr_prepago_hipotecario)
echo    3. Mora Consumo             (ml_mora_consumo)
echo    4. Mora CAE                 (ml_mora_cae)
echo    5. Mora Hipotecario         (ml_mora_hipotecario)
echo    6. Mora Comercial           (ml_mora_comercial)
echo.
echo   --- Segunda Vuelta ---
echo    7. Prepago CMR              (mr_prepago_cmr)
echo    8. NMD                      (ml_nmd)
echo    9. Linea de Credito         (ml_lc)
echo   10. Inversiones              (ml_inversiones)
echo.
echo    0. Volver al menu principal
echo.
set /p MOD_SEL="Seleccione modelo: "

if "%MOD_SEL%"=="1" set MODELO_KEY=mr_prepago_consumo
if "%MOD_SEL%"=="2" set MODELO_KEY=mr_prepago_hipotecario
if "%MOD_SEL%"=="3" set MODELO_KEY=ml_mora_consumo
if "%MOD_SEL%"=="4" set MODELO_KEY=ml_mora_cae
if "%MOD_SEL%"=="5" set MODELO_KEY=ml_mora_hipotecario
if "%MOD_SEL%"=="6" set MODELO_KEY=ml_mora_comercial
if "%MOD_SEL%"=="7" set MODELO_KEY=mr_prepago_cmr
if "%MOD_SEL%"=="8" set MODELO_KEY=ml_nmd
if "%MOD_SEL%"=="9" set MODELO_KEY=ml_lc
if "%MOD_SEL%"=="10" set MODELO_KEY=ml_inversiones
if "%MOD_SEL%"=="0" goto :menu_principal

if not defined MODELO_KEY (
    echo [ERROR] Opcion invalida.
    set MODELO_KEY=
    goto :modelo_individual
)

set /p CON_GCP="Cargar a GCP? (s/N): "
if /I "%CON_GCP%"=="s" (
    echo.
    echo Ejecutando %MODELO_KEY% + carga GCP para %FECHA%...
    echo ─────────────────────────────────────────────────────────
    python main.py --fecha %FECHA% --modelos %MODELO_KEY% --cargar-gcp
) else (
    echo.
    echo Ejecutando %MODELO_KEY% (sin carga GCP) para %FECHA%...
    echo ─────────────────────────────────────────────────────────
    python main.py --fecha %FECHA% --modelos %MODELO_KEY%
)
set MODELO_KEY=
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

:: ── Email report (solo si incluye primera vuelta) ──────────────────────────
:: Lee auto_post_ejecucion del YAML. Si es true, envía sin preguntar.
:: Si es false (default), pregunta al usuario.
if "%OPCION%"=="3" goto :skip_email
if "%OPCION%"=="6" goto :skip_email

:: Verificar si auto_post_ejecucion está habilitado
for /f %%a in ('python -c "import yaml; cfg=yaml.safe_load(open('config/config_rutas_ext_y_archivos.yaml',encoding='utf-8')); print(cfg.get('email_report',{}).get('auto_post_ejecucion',False))" 2^>nul') do set AUTO_EMAIL=%%a

if /I "%AUTO_EMAIL%"=="True" (
    echo.
    echo Enviando reporte de amortizacion por email (automatico)...
    python -m core.email_report --fecha %FECHA%
    goto :skip_email
)

echo.
echo Enviar reporte de amortizacion por email?
echo   [1] Si, enviar ahora
echo   [2] Si, pero abrir en Outlook para revisar (display)
echo   [3] No, saltar
set /p EMAIL_CHOICE="Opcion [3]: "
if "%EMAIL_CHOICE%"=="" set EMAIL_CHOICE=3

if "%EMAIL_CHOICE%"=="1" (
    python -m core.email_report --fecha %FECHA% --modo send
)
if "%EMAIL_CHOICE%"=="2" (
    python -m core.email_report --fecha %FECHA% --modo display
)

:skip_email
goto :fin

:fin_error
echo.
echo [EJECUCION CANCELADA]
:fin
echo.
pause
