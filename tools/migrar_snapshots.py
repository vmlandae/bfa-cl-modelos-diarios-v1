"""
Migración one-shot: convierte snapshots del formato legacy (copia por fecha)
al formato content-addressable (store/ + manifests/).

Uso:
    python -m tools.migrar_snapshots                  # dry-run
    python -m tools.migrar_snapshots --apply          # migrar
    python -m tools.migrar_snapshots --apply --clean   # migrar y borrar legacy

Estructura legacy:
    snapshots/{YYYYMMDD}/{modelo}/archivo.xlsx

Estructura nueva:
    snapshots/store/{modelo}/{sha256_12}.{ext}
    snapshots/manifests/{YYYYMMDD}.json
"""

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
STORE_DIR = SNAPSHOTS_DIR / "store"
MANIFESTS_DIR = SNAPSHOTS_DIR / "manifests"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _es_fecha_dir(name: str) -> bool:
    """Retorna True si el nombre parece YYYYMMDD (directorio legacy)."""
    if len(name) != 8 or not name.isdigit():
        return False
    try:
        datetime.strptime(name, "%Y%m%d")
        return True
    except ValueError:
        return False


def migrar(apply: bool = False, clean: bool = False) -> None:
    fecha_dirs = sorted(
        d for d in SNAPSHOTS_DIR.iterdir()
        if d.is_dir() and _es_fecha_dir(d.name)
    )

    if not fecha_dirs:
        print("No se encontraron directorios legacy para migrar.")
        return

    print(f"Encontrados {len(fecha_dirs)} directorios legacy: "
          f"{fecha_dirs[0].name} -> {fecha_dirs[-1].name}")

    total_files = 0
    dedup_skipped = 0
    # Track hashes vistas (para dry-run donde store/ no existe aún)
    seen_hashes: set = set()

    for fecha_dir in fecha_dirs:
        fecha_str = fecha_dir.name
        manifest = {"fecha": fecha_str, "modelos": {}}

        for modelo_dir in sorted(fecha_dir.iterdir()):
            if not modelo_dir.is_dir():
                continue
            modelo_key = modelo_dir.name
            archivos_entry = {}

            for archivo in sorted(modelo_dir.iterdir()):
                if not archivo.is_file():
                    continue
                total_files += 1

                file_hash = _sha256(archivo)
                hash_prefix = file_hash[:12]
                store_name = f"{hash_prefix}{archivo.suffix}"
                store_modelo_dir = STORE_DIR / modelo_key
                store_path = store_modelo_dir / store_name
                store_key = f"{modelo_key}/{store_name}"
                is_new = store_key not in seen_hashes and not store_path.exists()
                seen_hashes.add(store_key)

                if is_new:
                    if apply:
                        store_modelo_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(archivo), str(store_path))
                    print(f"  COPY {archivo.name} -> store/{modelo_key}/{store_name}")
                else:
                    dedup_skipped += 1
                    print(f"  SKIP {archivo.name} (ya existe {store_name})")

                archivos_entry[archivo.name] = {
                    "sha256": file_hash,
                    "store": f"store/{modelo_key}/{store_name}",
                    "size_bytes": archivo.stat().st_size,
                    "is_new": is_new,
                }

            if archivos_entry:
                manifest["modelos"][modelo_key] = {
                    "ts_snapshot": "migrated",
                    "archivos": archivos_entry,
                }

        manifest_path = MANIFESTS_DIR / f"{fecha_str}.json"
        if apply:
            MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"[{fecha_str}] {len(manifest['modelos'])} modelos -> manifest")

    print(f"\nResumen: {total_files} archivos, {dedup_skipped} deduplicados "
          f"({dedup_skipped/max(total_files,1)*100:.0f}% ahorro)")

    if apply and clean:
        print("\nLimpiando directorios legacy...")
        for fecha_dir in fecha_dirs:
            shutil.rmtree(fecha_dir)
            print(f"  Eliminado {fecha_dir.name}/")

    if not apply:
        print("\n⚠️  Dry-run — ningún cambio realizado. Usar --apply para migrar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrar snapshots a formato content-addressable")
    parser.add_argument("--apply", action="store_true", help="Ejecutar la migración")
    parser.add_argument("--clean", action="store_true", help="Eliminar dirs legacy después de migrar")
    args = parser.parse_args()
    migrar(apply=args.apply, clean=args.clean)
