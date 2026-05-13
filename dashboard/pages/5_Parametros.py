"""
Página: Diff de Parámetros entre Fechas.

Compara snapshots de parámetros entre dos fechas.
Nivel 1: SHA comparison (rápido). Nivel 2: deepdiff para JSON.
ml_inversiones solo muestra cambió/no cambió (no tiene JSON).
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
# F32: DeepDiff es pesado en boot. Se importa lazy en _deepdiff_json/_diff_a_tabla.

from dashboard.utils.local_data import (
    listar_fechas_con_snapshot,
    cargar_manifest_snapshot,
)
from dashboard.utils.theme import MODELOS_CANONICOS

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_STORE_DIR = _BASE_DIR / "snapshots" / "store"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cargar_json_store(store_path: str) -> dict | None:
    """Lee un archivo JSON del store de snapshots."""
    path = _BASE_DIR / "snapshots" / store_path
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _comparar_manifests(manifest_a: dict, manifest_b: dict) -> list[dict]:
    """Compara dos manifests a nivel SHA, retorna resumen por modelo."""
    modelos_a = manifest_a.get("modelos", {})
    modelos_b = manifest_b.get("modelos", {})
    todos = sorted(set(modelos_a) | set(modelos_b))

    resultados = []
    for modelo in todos:
        info_a = modelos_a.get(modelo, {})
        info_b = modelos_b.get(modelo, {})
        archivos_a = info_a.get("archivos", {})
        archivos_b = info_b.get("archivos", {})

        if not info_a:
            resultados.append({
                "modelo": modelo,
                "estado": "🆕 Solo en Fecha B",
                "archivos_total": len(archivos_b),
                "archivos_cambiados": len(archivos_b),
                "detalle": archivos_b,
            })
            continue
        if not info_b:
            resultados.append({
                "modelo": modelo,
                "estado": "🗑️ Solo en Fecha A",
                "archivos_total": len(archivos_a),
                "archivos_cambiados": len(archivos_a),
                "detalle": archivos_a,
            })
            continue

        todos_arch = sorted(set(archivos_a) | set(archivos_b))
        cambiados = []
        for arch in todos_arch:
            meta_a = archivos_a.get(arch)
            meta_b = archivos_b.get(arch)
            if meta_a is None:
                cambiados.append({"archivo": arch, "tipo": "nuevo"})
            elif meta_b is None:
                cambiados.append({"archivo": arch, "tipo": "eliminado"})
            elif meta_a.get("sha256") != meta_b.get("sha256"):
                cambiados.append({
                    "archivo": arch,
                    "tipo": "modificado",
                    "store_a": meta_a.get("store"),
                    "store_b": meta_b.get("store"),
                })

        if cambiados:
            estado = f"🔄 {len(cambiados)} archivo(s) cambió"
        else:
            estado = "✅ Sin cambios"

        resultados.append({
            "modelo": modelo,
            "estado": estado,
            "archivos_total": len(todos_arch),
            "archivos_cambiados": len(cambiados),
            "cambiados": cambiados,
        })

    return resultados


def _deepdiff_json(store_a: str, store_b: str) -> "dict | None":
    """Ejecuta DeepDiff entre dos archivos JSON del store."""
    from deepdiff import DeepDiff  # lazy F32
    json_a = _cargar_json_store(store_a)
    json_b = _cargar_json_store(store_b)
    if json_a is None or json_b is None:
        return None
    diff = DeepDiff(json_a, json_b, ignore_order=True, significant_digits=6)
    return diff


def _diff_a_tabla(diff) -> pd.DataFrame:
    """Convierte un DeepDiff a tabla legible."""
    rows = []

    for change_type, changes in diff.items():
        if change_type == "values_changed":
            for path, detail in changes.items():
                rows.append({
                    "Tipo": "Modificado",
                    "Ruta": path,
                    "Valor A": str(detail.get("old_value", ""))[:80],
                    "Valor B": str(detail.get("new_value", ""))[:80],
                })
        elif change_type == "dictionary_item_added":
            for path in changes:
                rows.append({
                    "Tipo": "Agregado en B",
                    "Ruta": str(path),
                    "Valor A": "—",
                    "Valor B": str(changes[path])[:80] if isinstance(changes, dict) else "—",
                })
        elif change_type == "dictionary_item_removed":
            for path in changes:
                rows.append({
                    "Tipo": "Eliminado en B",
                    "Ruta": str(path),
                    "Valor A": str(changes[path])[:80] if isinstance(changes, dict) else "—",
                    "Valor B": "—",
                })
        elif change_type == "type_changes":
            for path, detail in changes.items():
                rows.append({
                    "Tipo": "Tipo cambió",
                    "Ruta": path,
                    "Valor A": f"{detail.get('old_type', '?')}: {detail.get('old_value', '')}",
                    "Valor B": f"{detail.get('new_type', '?')}: {detail.get('new_value', '')}",
                })
        elif change_type in ("iterable_item_added", "iterable_item_removed"):
            for path, val in changes.items():
                rows.append({
                    "Tipo": "Elemento " + ("agregado" if "added" in change_type else "eliminado"),
                    "Ruta": str(path),
                    "Valor A": "—" if "added" in change_type else str(val)[:80],
                    "Valor B": str(val)[:80] if "added" in change_type else "—",
                })

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Tipo", "Ruta", "Valor A", "Valor B"])


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("⚙️ Comparación de Parámetros")

fechas = listar_fechas_con_snapshot()
if len(fechas) < 2:
    st.warning("Se necesitan al menos 2 fechas con snapshots para comparar.")
    if fechas:
        st.info(f"Solo hay snapshot del {fechas[0]}")
    st.stop()

# Selectores
col_a, col_b = st.columns(2)
fmt = lambda f: f"{f[:4]}-{f[4:6]}-{f[6:]}"

with col_a:
    fecha_a = st.selectbox("Fecha A (anterior)", fechas[1:], format_func=fmt)
with col_b:
    # Fechas B: solo las posteriores a A
    idx_a = fechas.index(fecha_a)
    fechas_b = [f for f in fechas if f > fecha_a]
    if not fechas_b:
        fechas_b = [fechas[0]]
    fecha_b = st.selectbox("Fecha B (posterior)", fechas_b, format_func=fmt)

# Cargar manifests
manifest_a = cargar_manifest_snapshot(fecha_a)
manifest_b = cargar_manifest_snapshot(fecha_b)

if manifest_a is None or manifest_b is None:
    st.error("No se pudo cargar uno de los manifests.")
    st.stop()

# --- Resumen ---
resultados = _comparar_manifests(manifest_a, manifest_b)

st.subheader("Resumen de cambios")

nombre_map = {k: v["nombre"] for k, v in MODELOS_CANONICOS.items()}

df_resumen = pd.DataFrame([
    {
        "Modelo": nombre_map.get(r["modelo"], r["modelo"]),
        "Archivos": r["archivos_total"],
        "Estado": r["estado"],
    }
    for r in resultados
])

st.dataframe(df_resumen, use_container_width=True, hide_index=True)

# Métricas
n_sin_cambio = sum(1 for r in resultados if r["archivos_cambiados"] == 0)
n_con_cambio = sum(1 for r in resultados if r["archivos_cambiados"] > 0)
mc1, mc2 = st.columns(2)
with mc1:
    st.metric("Sin cambios", n_sin_cambio)
with mc2:
    st.metric("Con cambios", n_con_cambio)

# --- Detalle por modelo ---
modelos_con_cambios = [r for r in resultados if r.get("cambiados")]

if modelos_con_cambios:
    st.subheader("Detalle de cambios")

    for res in modelos_con_cambios:
        modelo_id = res["modelo"]
        modelo_nombre = nombre_map.get(modelo_id, modelo_id)

        with st.expander(f"🔄 {modelo_nombre} — {len(res['cambiados'])} archivo(s)"):
            for cambio in res["cambiados"]:
                archivo = cambio["archivo"]
                tipo = cambio["tipo"]

                st.markdown(f"**{archivo}** — _{tipo}_")

                # Solo deepdiff para archivos JSON modificados
                if tipo == "modificado" and archivo.endswith(".json"):
                    store_a = cambio.get("store_a")
                    store_b = cambio.get("store_b")
                    if store_a and store_b:
                        diff = _deepdiff_json(store_a, store_b)
                        if diff:
                            df_diff = _diff_a_tabla(diff)
                            if df_diff.empty:
                                st.success("Sin diferencias de contenido (solo metadata)")
                            else:
                                st.dataframe(df_diff, use_container_width=True, hide_index=True)
                        else:
                            st.info("No se pudo generar diff (archivo no encontrado en store)")

                elif tipo == "modificado" and (archivo.endswith(".xlsx") or archivo.endswith(".xlsm")):
                    # Para Excel/xlsm: solo indicar cambió/no cambió
                    st.info(f"📊 Excel cambió (SHA diferente). Diff detallado no disponible para `.{archivo.split('.')[-1]}`.")

                elif tipo == "nuevo":
                    st.success(f"🆕 Archivo nuevo en Fecha B")

                elif tipo == "eliminado":
                    st.error(f"🗑️ Archivo eliminado en Fecha B")

                st.divider()
else:
    if resultados:
        st.success("🎉 Sin cambios en parámetros entre las dos fechas.")
