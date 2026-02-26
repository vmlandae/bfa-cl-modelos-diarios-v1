"""
Descarga mermaid.min.js para uso local en MkDocs.

Contexto: Detrás del proxy corporativo, los CDN (jsdelivr, unpkg) son bloqueados
o devuelven HTML del proxy. cdnjs.cloudflare.com sí responde con el JS real
cuando se usa `requests` con `verify=False` desde el conda env.

Uso:
    conda activate bfa-cl-modelos
    python docs/javascripts/descargar_mermaid.py

Más detalles: docs/guia/mermaid-local.md
"""
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")  # suppress InsecureRequestWarning

DESTINO = pathlib.Path(__file__).parent / "mermaid.min.js"
VERSION = "10.9.3"

# cdnjs.cloudflare.com es el único CDN que responde correctamente
# detrás del proxy corporativo Falabella. jsdelivr y unpkg devuelven
# HTML 403 del proxy (44KB de HTML, no JS).
URLS = [
    f"https://cdnjs.cloudflare.com/ajax/libs/mermaid/{VERSION}/mermaid.min.js",
    f"https://cdn.jsdelivr.net/npm/mermaid@{VERSION}/dist/mermaid.min.js",
    f"https://unpkg.com/mermaid@{VERSION}/dist/mermaid.min.js",
]


def es_js_valido(data: bytes) -> bool:
    """Verifica que sea JS real y no HTML de proxy."""
    return len(data) > 50_000 and not data[:50].strip().startswith(b"<")


def descargar() -> bytes | None:
    try:
        import requests

        session = requests.Session()
        session.verify = False

        for url in URLS:
            print(f"  Intentando {url[:70]}...")
            try:
                resp = session.get(url, timeout=30, allow_redirects=True)
                print(f"    HTTP {resp.status_code}, {len(resp.content):,} bytes")
                if resp.status_code == 200 and es_js_valido(resp.content):
                    return resp.content
                print(f"    (descartado: HTML de proxy o archivo incompleto)")
            except Exception as e:
                print(f"    Error: {e}")
    except ImportError:
        print("  Error: 'requests' no instalado. Ejecuta: pip install requests")
    return None


def main():
    print(f"=== Descarga mermaid.min.js v{VERSION} ===\n")

    if DESTINO.exists() and DESTINO.stat().st_size > 50_000:
        size = DESTINO.stat().st_size
        print(f"Ya existe: {DESTINO.name} ({size:,} bytes)")
        resp = input("¿Sobreescribir? [s/N]: ").strip().lower()
        if resp != "s":
            print("Cancelado.")
            return

    data = descargar()
    if data:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        DESTINO.write_bytes(data)
        print(f"\n✓ Guardado: {DESTINO}")
        print(f"  Tamaño: {len(data):,} bytes")
        print(f"  Versión: mermaid {VERSION}")
        print(f"\n  Reinicia mkdocs serve para aplicar.")
    else:
        print(f"\n✗ No se pudo descargar.")
        print(f"  Descarga manualmente desde un PC sin restricciones:")
        print(f"  https://cdnjs.cloudflare.com/ajax/libs/mermaid/{VERSION}/mermaid.min.js")
        print(f"  Y copia a: {DESTINO}")
        sys.exit(1)


if __name__ == "__main__":
    main()
