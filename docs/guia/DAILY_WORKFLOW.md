# Flujo de Trabajo Diario

> **Autor:** vlandaetat
> **Fecha:** 2026-03-11
> **Contexto:** Guia paso a paso para ejecutar los modelos cada dia habil.

---

## Resumen Rapido

Cada dia habil debes:

1. Conectar VPN
2. Doble-click en `run_diario.bat`
3. Ingresar la fecha del dia
4. Seleccionar opcion 1 (todos + GCP)
5. Esperar a que termine
6. Revisar el resumen final

---

## Paso a Paso Detallado

### 1. Antes de empezar

- [ ] VPN conectada (FortiClient)
- [ ] PC conectado a la red del banco (para `\\vmdvorak`)
- [ ] Fecha del dia habil a procesar (formato: `2026-03-11`)

### 2. Ejecutar los modelos

**Opcion A: Doble-click en `run_diario.bat`** (recomendado)

El script te pregunta:

```
Fecha de hoy: 2026-03-11
Ingrese fecha de ejecucion (YYYY-MM-DD) [2026-03-11]: 
```

Presiona Enter para usar la fecha del dia, o escribe otra fecha.

Luego muestra un menu:

```
Opciones de ejecucion:
  1. Ejecutar TODOS los modelos + cargar a GCP (recomendado)
  2. Ejecutar solo PRIMERA VUELTA + cargar a GCP
  3. Ejecutar solo SEGUNDA VUELTA + cargar a GCP
  4. Ejecutar TODOS sin cargar a GCP (solo local)
  5. Solo cargar a GCP (sin ejecutar modelos)
  6. Consolidar historico
  7. Cancelar
```

Para el flujo normal del dia, elige **opcion 1**.

**Opcion B: Desde terminal manualmente**

```bash
conda activate bfa-cl-modelos-v2
cd C:\Users\TU_USUARIO\code\bfa-cl-modelos-diarios
python main.py --fecha 2026-03-11 --modelos todos --cargar-gcp
```

### 3. Vueltas de ejecucion

Los modelos se ejecutan en dos vueltas:

| Vuelta | Modelos | Tiempo aprox. |
|--------|---------|---------------|
| **Primera** | Prepago Consumo, Prepago Hipotecario, Mora Consumo, Mora CAE, Mora Hipotecario, Mora Comercial | ~3-5 min |
| **Segunda** | Prepago CMR, NMD, Linea de Credito, Inversiones | ~5-10 min |

Si necesitas ejecutar por partes:

```bash
# Solo primera vuelta
python main.py --fecha 2026-03-11 --modelos primera_vuelta --cargar-gcp

# Solo segunda vuelta (despues)
python main.py --fecha 2026-03-11 --modelos segunda_vuelta --cargar-gcp
```

### 4. Interpretar el resumen

Al final veras una tabla como esta:

```
================================================================================
                         RESUMEN DE EJECUCION
================================================================================
MODELO                         |   EJECUCION   |   CARGA GCP   
-------------------------------+---------------+---------------
Modelo Prepago Consumo         |      OK       |      OK       
Modelo Prepago Hipotecario     |      OK       |      OK       
...
Modelo Inversiones             |      OK       |      OK       

Totales:
  Modelos ejecutados: 10/10
  Tablas cargadas a GCP: 11/11

Estado final: COMPLETADO EXITOSAMENTE
```

- **OK/OK** = Modelo ejecutado y cargado a BigQuery correctamente
- **ERROR** en ejecucion = El modelo fallo (ver logs)
- **ERROR** en carga = El modelo corrio pero la carga a GCP fallo

### 5. Si hay errores

1. **Revisar logs:** abrir `logs/{YYYYMMDD}/modelos.jsonl`
2. **Reejecutar modelo individual:**
   ```bash
   python main.py --fecha 2026-03-11 --modelos mr_prepago_consumo --cargar-gcp
   ```
3. **Si el error persiste**, ver [Troubleshooting](TROUBLESHOOTING.md)

---

## Casos Especiales

### Consolidar historico

Despues de ejecutar los modelos del dia, a veces se pide consolidar en tablas historicas:

```bash
python main.py --fecha 2026-03-11 --consolidar-historico todos
```

Si necesitas re-procesar una fecha que ya esta en historico:

```bash
python main.py --fecha 2026-03-11 --consolidar-historico todos --force-historico
```

> `--force-historico` hace backup CSV automatico antes de borrar y reinsertar.

### Solo cargar a GCP (sin ejecutar)

Si los modelos ya corrieron pero la carga fallo:

```bash
python main.py --fecha 2026-03-11 --solo-carga-gcp todos
```

### Forzar recarga de cache

Si los datos de Access cambiaron y necesitas que se vuelvan a leer:

```bash
python main.py --fecha 2026-03-11 --modelos todos --cargar-gcp --forzar-recarga
```

---

## Reportes y Monitoreo

Despues de cada ejecucion se genera automaticamente:

| Archivo | Ubicacion | Contenido |
|---------|-----------|-----------|
| Reporte JSON | `reports/{YYYYMMDD}/reporte_*.json` | Datos estructurados de la ejecucion |
| Reporte Markdown | `reports/{YYYYMMDD}/reporte_*.md` | Resumen legible |
| Health check | `reports/health_check.json` | Ultimo diagnostico del entorno |
| Log JSONL | `logs/{YYYYMMDD}/modelos.jsonl` | Log detallado de toda la ejecucion |

Los reportes se sincronizan automaticamente a BigQuery (tabla `reportes_ejecucion`) para que el equipo pueda monitorear remotamente.

Si la sincronizacion falla (sin internet, etc.), el reporte queda en `reports/_pendientes_sync/` y se reintenta en la proxima ejecucion.

---

## Checklist Diario

```
[ ] VPN conectada
[ ] Ejecutar run_diario.bat → opcion 1
[ ] Verificar: 10/10 modelos OK
[ ] Verificar: 11/11 tablas GCP OK
[ ] Si hay errores: revisar logs, reejecutar, o avisar al equipo
```
