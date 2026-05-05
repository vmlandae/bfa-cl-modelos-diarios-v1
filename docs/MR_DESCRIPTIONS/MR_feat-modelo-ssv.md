# feat/modelo-ssv -> main

Port del modelo MR SSV (Margen Relativo - Saldos Sin Vencimiento) desde el workbook legado `MT_SSV.XLSM` hacia una implementacion Python integrada al pipeline diario, con carga a BigQuery en la misma infraestructura de los demas modelos de segunda vuelta.

**URL para abrir el MR:**
https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/merge_requests/new?merge_request%5Bsource_branch%5D=feat%2Fmodelo-ssv

---

## Resumen ejecutivo

- Nuevo modelo `mr_ssv` (vuelta 2, cadencia EOM) ejecutable desde el orquestador estandar.
- Genera `report_mr_ssv_dly` y `report_mr_ssv_hist` y los carga a BigQuery.
- Fix critico al problema historico del literal `'nan'` en columnas STRING (astype(object) + where + map), con validacion empirica 0/1037 nan-strings en dly e hist.
- Documentacion completa: README actualizado, CHANGELOG 1.13.0-dev y nueva feature F27 destacada en el roadmap para automatizar saldos CORE.
- Limpieza extensa: legacy `MR_SSV/` y scratchpads movidos a `backups_historicos/20260424/ssv_port/`; `.gitignore` refinado.

## Commits (12 desde `main`)

```
f038ac6 feat(dashboard): registrar mr_ssv en MODELOS_CANONICOS (vuelta 2)
e96823c docs(ssv): README, CHANGELOG 1.13.0-dev y roadmap F27 (automatizar CORE)
e6d24d3 chore(gitignore): ignorar scratchpads efimeros en la raiz del proyecto
758dce5 chore(ssv): archivar MR_SSV/ y MR_SSV.zip legacy en backups_historicos
36c312b chore(orquestador): deshabilitar limpieza post-ejecucion de Access local durante dev SSV
6db56b1 refactor(config): ajustar tablas Access de input para mr_ssv
1ccb99e feat(ssv): parametros definitivos y utilitario de carga CORE manual
276f0cd fix(gcp-dly): preservar None al castear columnas STRING a str
f623331 refactor(ssv): iteracion definitiva del modelo
... (commits previos al ultimo reset de la rama)
```

## Cambios por area

### Modelo SSV (`RF_Modelo_MR_SSV/`)
- Nuevo `mr_ssv.py` con logica portada del workbook Excel legado.
- Parametros centralizados en `parametros_mr_ssv.xlsx` / `parametros_mr_ssv.json`.
- Utilitario `agregar_core_hardcode.py` para carga manual mensual de saldos CORE (hoy es hardcode; automatizacion queda como F27 en el roadmap).
- README del modelo con contexto, inputs, outputs y caveats.

### Carga BigQuery (`carga_modelos_gcp/`)
- `cargar_output_modelos_bigquery_dly.py`: **fix critico** — al castear columnas STRING a `str` ahora preservamos `None` aplicando `astype(object)` antes del `where(notna, None)`. Antes, el `.astype(str)` convertia `NaN` al literal `'nan'` que terminaba persistido en BQ.
- `cargar_output_modelos_bigquery_hist.py`: mismo fix, ajustes de headers para el modelo SSV.

### Configuracion / orquestacion
- `config/config_rutas_ext_y_archivos.yaml`: agregadas entradas de tablas Access `MOD_Saldos_para_Modelos`, remocion de `saldos_core.xlsx` ya no usado.
- `core/orquestador.py`: deshabilitada la limpieza automatica post-ejecucion del Access local durante desarrollo de SSV (reversible tras estabilizar F27).

### Dashboard y reportes
- `dashboard/utils/theme.py`: `mr_ssv` agregado a `MODELOS_CANONICOS` como modelo de segunda vuelta ("SSV (EOM)").
- `core/email_report.py`: `report_mr_ssv_hist` ya estaba en `TABLAS_SEGUNDA_VUELTA`, verificado.

### Documentacion
- `README.md`: seccion "Modelos de Margen Relativo (MR)" y arbol `RF_Modelo_MR_SSV/`.
- `docs/CHANGELOG.md`: entrada completa `[1.13.0-dev] - 2026-04-24 - Modelo MR SSV (port + carga BQ)`.
- `docs/roadmap/PLAN.md`: seccion **DESTACADO — F27** al inicio del archivo.
- `docs/roadmap/roadmap.yaml`: F27 como feature backlog (prioridad alta, tamano M).

### Limpieza
- `backups_historicos/20260424/ssv_port/MR_SSV_legacy/`: dir `MR_SSV/` completo + `MR_SSV.zip`.
- `backups_historicos/20260424/ssv_port/sandbox_ssv/`: scratchpads, `mt_ssv_heredado/`, `mt_ssv_prod/`, `ssv_saldos_core/`, plus 40+ archivos `zz_*.py`, `tmp_*.py`, `out_*.txt`.
- `.gitignore`: patrones nuevos para `/check_nan.py`, `/output.txt`, `/script.py`, `/temp_*.py`, `/tmp_*.py`, `/zz_*.txt`, `/zz_*.py`.

## Validacion

- **Fix literal 'nan'**: query BQ sobre `report_mr_ssv_dly` y `report_mr_ssv_hist` para `fecha_proceso = '2026-02-28'` (EOM de febrero) — **0 literales 'nan' / 1037 NULL reales** en columnas STRING.
- **Smoke imports**: `mr_ssv`, los dos loaders GCP, `orquestador`, `email_report`, `dashboard.utils.theme`, `config.config_rutas` importan sin errores.
- **Orquestador end-to-end**: corrida completa EOM 20260228 exitosa (Access copy, carga parametros, ejecucion, output Excel, carga BQ).

## Dependencias / orden de merge

- **Independiente**, no bloquea ni es bloqueado por otros MRs abiertos.
- Existe MR complementario **`fix/access-cache-vigencia` -> main** con un bugfix independiente detectado durante este trabajo. Puede mergearse antes o despues sin conflictos.

## TODO post-merge

- **F27 (roadmap, destacado)**: automatizar la carga mensual de saldos CORE hoy hardcodeada via `agregar_core_hardcode.py`. Prioridad alta.
- Re-habilitar limpieza post-ejecucion de Access local una vez estabilizado el pipeline SSV.
