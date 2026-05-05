# fix/access-cache-vigencia -> main

Revalidacion de vigencia de la copia local de archivos Access contra la fuente de red, para evitar ejecuciones con datos stale dentro del mismo dia.

**URL para abrir el MR (disponible tras push a origin):**
https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/merge_requests/new?merge_request%5Bsource_branch%5D=fix%2Faccess-cache-vigencia

---

## Problema

`procesamiento_datos_input/cache_tablas.py` reutilizaba la copia local de `.accdb` si existia, sin comparar con la fuente UNC. Si la red actualizaba el archivo durante el dia (caso habitual con `RF_Base_Carteras_Completa.accdb`), las corridas subsiguientes leian datos desactualizados hasta que el usuario eliminara la copia manualmente.

## Fix

En `copiar_access_a_local()`:
- Comparar **mtime** (tolerancia 2s para jitter FS) y **tamano** del archivo local vs UNC.
- Si la red es mas nueva o el tamano difiere, recopiar.
- Si la UNC es inaccesible (VPN caida, share offline), loggear warning prominente y fallback a la copia local existente en vez de fallar.

## Scope

- Un unico archivo tocado: `procesamiento_datos_input/cache_tablas.py`.
- Dos commits:
  - `664525a fix(cache): revalidar vigencia de copia local de Access contra mtime/tamano en red`
  - `cd3b74e feat(cache): backup + metadata + autor en copia local de Access`
    - Antes de sobreescribir una copia desactualizada, la previa se preserva como `{stem}.pre_{YYYYMMDD_HHMMSS}.accdb` (con su metadata).
    - Cada copia escribe un sidecar `{archivo}.accdb.meta.json` con `timestamp_copia`, `usuario` (getpass), `host`, `ruta_origen`, `size_origen_bytes`, `mtime_origen_epoch`/`iso` y `duracion_copia_s`.
    - Log de copia ahora incluye `usuario@host`.
    - `limpiar_access_local()` barre tambien los `.meta.json`.
    - Simetria con el patron ya existente en `copiar_interfaz_a_local()` (PML).

## Contexto

- Detectado durante el desarrollo de `feat/modelo-ssv` (ese MR va en rama separada).
- Independiente y aplicable a todos los modelos del pipeline, no solo SSV.
- Sin cambios de interfaz publica, retrocompatible.

## Validacion

- Corrida diaria estandar: copia local actualizada correctamente cuando UNC cambio.
- Caso red caida: warning visible, pipeline continua con copia local, exit code 0.
- Smoke imports post-fix: OK.

## Dependencias

Ninguna. Se puede mergear antes o despues de `feat/modelo-ssv` sin conflictos (toca un archivo distinto).
