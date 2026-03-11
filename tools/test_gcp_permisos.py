"""
Diagnóstico de permisos GCP para el Service Account.

Prueba cada servicio GCP y reporta qué puede y qué no puede hacer el SA.
Útil para planificar features que dependan de GCP (GCS sync, notebooks, VMs, etc.)

Uso:
    python -m tools.test_gcp_permisos
    python tools/test_gcp_permisos.py
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Asegurar que el proyecto esté en el path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

# Credenciales
CRED_PATH = BASE_DIR / "credenciales" / "bfa-cl-trade-price-report-dev-9d137fc23b7f.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CRED_PATH)

# Scopes amplios para testear REST APIs
_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]
PROJECT_ID = "bfa-cl-trade-price-report-dev"
SA_EMAIL = "modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com"

# Resultados globales
_resultados = []


def _get_scoped_session():
    """Retorna AuthorizedSession con scopes correctos para llamadas REST."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_file(
        str(CRED_PATH), scopes=_SCOPES
    )
    session = AuthorizedSession(creds)
    # Proxy corporativo: requests/certifi no tiene el CA del proxy,
    # pero el store de certificados del sistema sí. Exportar y usar.
    session.verify = _get_system_ca_bundle()
    return session, creds


def _get_system_ca_bundle():
    """Exporta certificados del system store a un archivo PEM temporal."""
    import ssl
    import base64
    import tempfile
    ca_file = Path(tempfile.gettempdir()) / "system_ca_certs.pem"
    if ca_file.exists():
        return str(ca_file)
    ctx = ssl.create_default_context()
    certs = ctx.get_ca_certs(binary_form=True)
    with open(ca_file, "wb") as f:
        for cert in certs:
            f.write(b"-----BEGIN CERTIFICATE-----\n")
            f.write(base64.encodebytes(cert))
            f.write(b"-----END CERTIFICATE-----\n")
    return str(ca_file)


def _test(servicio: str, operacion: str, fn):
    """Ejecuta fn() y registra si fue OK o ERROR."""
    print(f"  [{servicio}] {operacion}...", end=" ", flush=True)
    try:
        detalle = fn()
        print(f"✓ OK — {detalle}")
        _resultados.append({
            "servicio": servicio,
            "operacion": operacion,
            "status": "OK",
            "detalle": str(detalle),
        })
    except Exception as e:
        err_short = str(e).split("\n")[0][:200]
        print(f"✗ ERROR — {err_short}")
        _resultados.append({
            "servicio": servicio,
            "operacion": operacion,
            "status": "ERROR",
            "detalle": err_short,
            "traceback": traceback.format_exc()[-500:],
        })


# ═══════════════════════════════════════════════════════════════
# 1. AUTENTICACIÓN BÁSICA
# ═══════════════════════════════════════════════════════════════

def test_autenticacion():
    print("\n═══ 1. AUTENTICACIÓN ═══")

    def _check_cred_file():
        with open(CRED_PATH) as f:
            data = json.load(f)
        return f"project={data['project_id']}, sa={data['client_email']}"
    _test("Auth", "Leer credencial JSON", _check_cred_file)

    def _check_default_creds():
        from google.auth import default
        creds, project = default()
        return f"project={project}, creds_type={type(creds).__name__}"
    _test("Auth", "google.auth.default()", _check_default_creds)

    def _check_token():
        from google.auth.transport.requests import Request as AuthRequest
        import requests as req_lib
        _, creds = _get_scoped_session()
        # Usar CA bundle del sistema para el token refresh
        http_session = req_lib.Session()
        http_session.verify = _get_system_ca_bundle()
        creds.refresh(AuthRequest(session=http_session))
        return f"token_expiry={creds.expiry}, valid={creds.valid}"
    _test("Auth", "Obtener access token (scoped)", _check_token)


# ═══════════════════════════════════════════════════════════════
# 2. RESOURCE MANAGER (proyectos)
# ═══════════════════════════════════════════════════════════════

def test_resource_manager():
    print("\n═══ 2. RESOURCE MANAGER ═══")

    def _get_project():
        session, _ = _get_scoped_session()
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return f"name={data.get('projectId')}, state={data.get('lifecycleState')}, number={data.get('projectNumber')}"
    _test("ResourceManager", "Get proyecto propio", _get_project)


# ═══════════════════════════════════════════════════════════════
# 3. SERVICE USAGE (APIs habilitadas)
# ═══════════════════════════════════════════════════════════════

def test_service_usage():
    print("\n═══ 3. SERVICE USAGE (APIs habilitadas) ═══")

    def _list_enabled_apis():
        session, _ = _get_scoped_session()
        url = f"https://serviceusage.googleapis.com/v1/projects/{PROJECT_ID}/services?filter=state:ENABLED&pageSize=200"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        services = [s["config"]["name"] for s in data.get("services", [])]
        return f"{len(services)} APIs habilitadas: {services}"
    _test("ServiceUsage", "Listar APIs habilitadas", _list_enabled_apis)


# ═══════════════════════════════════════════════════════════════
# 4. IAM (roles del SA)
# ═══════════════════════════════════════════════════════════════

def test_iam():
    print("\n═══ 4. IAM ═══")

    def _get_iam_policy():
        session, _ = _get_scoped_session()
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}:getIamPolicy"
        resp = session.post(url, json={})
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        policy = resp.json()
        my_roles = []
        for binding in policy.get("bindings", []):
            for member in binding.get("members", []):
                if SA_EMAIL in member:
                    my_roles.append(binding["role"])
        return f"Roles del SA: {my_roles}" if my_roles else "SA no aparece en policy (puede tener roles heredados)"
    _test("IAM", "getIamPolicy — roles del SA", _get_iam_policy)

    def _test_permissions():
        session, _ = _get_scoped_session()
        perms_to_test = [
            "bigquery.datasets.create",
            "bigquery.tables.create",
            "bigquery.tables.getData",
            "bigquery.jobs.create",
            "storage.buckets.create",
            "storage.buckets.list",
            "storage.objects.create",
            "storage.objects.get",
            "compute.instances.create",
            "compute.instances.list",
            "notebooks.instances.create",
            "notebooks.instances.list",
            "iam.serviceAccounts.list",
            "resourcemanager.projects.get",
        ]
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT_ID}:testIamPermissions"
        resp = session.post(url, json={"permissions": perms_to_test})
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        granted = resp.json().get("permissions", [])
        denied = [p for p in perms_to_test if p not in granted]
        lines = []
        for p in perms_to_test:
            mark = "✓" if p in granted else "✗"
            lines.append(f"  {mark} {p}")
        return f"\n{''.join(chr(10)+l for l in lines)}\n  ({len(granted)}/{len(perms_to_test)} granted)"
    _test("IAM", "testIamPermissions (14 permisos clave)", _test_permissions)


# ═══════════════════════════════════════════════════════════════
# 5. BIGQUERY
# ═══════════════════════════════════════════════════════════════

def test_bigquery():
    print("\n═══ 5. BIGQUERY ═══")

    def _list_datasets():
        from google.cloud import bigquery
        client = bigquery.Client()
        datasets = list(client.list_datasets(max_results=20))
        return f"{len(datasets)} datasets: {[d.dataset_id for d in datasets]}"
    _test("BigQuery", "Listar datasets", _list_datasets)

    def _query_simple():
        from google.cloud import bigquery
        client = bigquery.Client()
        q = "SELECT 1 AS test_col, CURRENT_TIMESTAMP() AS ts"
        result = list(client.query(q).result())
        return f"Query OK: {result[0]}"
    _test("BigQuery", "Query simple (SELECT 1)", _query_simple)

    def _list_tables():
        from google.cloud import bigquery
        client = bigquery.Client()
        datasets = list(client.list_datasets(max_results=1))
        if not datasets:
            return "No hay datasets"
        ds = datasets[0].dataset_id
        tables = list(client.list_tables(ds, max_results=10))
        return f"Dataset '{ds}': {len(tables)} tables — {[t.table_id for t in tables][:5]}"
    _test("BigQuery", "Listar tablas del primer dataset", _list_tables)

    def _create_temp_dataset():
        from google.cloud import bigquery
        client = bigquery.Client()
        ds_id = f"{client.project}._test_permisos_temp"
        ds = bigquery.Dataset(ds_id)
        ds.location = "US"
        ds.default_table_expiration_ms = 3600000  # 1h
        client.create_dataset(ds, exists_ok=True)
        client.delete_dataset(ds_id, delete_contents=True)
        return f"Create+Delete dataset '{ds_id}' OK"
    _test("BigQuery", "Crear y eliminar dataset temporal", _create_temp_dataset)


# ═══════════════════════════════════════════════════════════════
# 6. CLOUD STORAGE (GCS)
# ═══════════════════════════════════════════════════════════════

def test_gcs():
    print("\n═══ 6. CLOUD STORAGE (GCS) ═══")

    def _list_buckets():
        from google.cloud import storage
        client = storage.Client()
        buckets = list(client.list_buckets(max_results=20))
        return f"{len(buckets)} buckets: {[b.name for b in buckets]}"
    _test("GCS", "Listar buckets", _list_buckets)

    def _create_test_bucket():
        from google.cloud import storage
        client = storage.Client()
        bucket_name = f"{client.project}-test-permisos-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        bucket = client.create_bucket(bucket_name, location="us-central1")
        # Upload test object
        blob = bucket.blob("test.txt")
        blob.upload_from_string("test de permisos GCS")
        content = blob.download_as_text()
        # Cleanup
        blob.delete()
        bucket.delete()
        return f"Bucket '{bucket_name}': create+upload+download+delete OK"
    _test("GCS", "Crear bucket, upload, download, delete", _create_test_bucket)

    def _check_existing_bucket():
        from google.cloud import storage
        client = storage.Client()
        bucket_name = f"{client.project}-modelos-reportes"
        bucket = client.bucket(bucket_name)
        exists = bucket.exists()
        return f"Bucket '{bucket_name}' exists={exists}"
    _test("GCS", "Check bucket de reportes", _check_existing_bucket)

    def _upload_to_known_bucket():
        """Intenta subir a algún bucket existente (si lo hay)."""
        from google.cloud import storage
        client = storage.Client()
        # Usar la API REST con scoped creds para listar buckets
        session, _ = _get_scoped_session()
        url = f"https://storage.googleapis.com/storage/v1/b?project={PROJECT_ID}&projection=noAcl"
        resp = session.get(url)
        if resp.status_code != 200:
            return f"No se pudo listar buckets (HTTP {resp.status_code})"
        buckets = [b["name"] for b in resp.json().get("items", [])]
        if not buckets:
            return "No hay buckets en el proyecto"
        # Intentar upload a primer bucket
        bucket = client.bucket(buckets[0])
        blob = bucket.blob("_test_permisos/test.txt")
        blob.upload_from_string("test de permisos write")
        content = blob.download_as_text()
        blob.delete()
        return f"Upload+Download+Delete en '{buckets[0]}/_test_permisos/test.txt' OK"
    _test("GCS", "Upload/Download a bucket existente", _upload_to_known_bucket)


# ═══════════════════════════════════════════════════════════════
# 7. COMPUTE ENGINE
# ═══════════════════════════════════════════════════════════════

def test_compute():
    print("\n═══ 7. COMPUTE ENGINE ═══")

    def _list_instances():
        session, _ = _get_scoped_session()
        url = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT_ID}/aggregated/instances"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        items = resp.json().get("items", {})
        instances = []
        for zone_data in items.values():
            for inst in zone_data.get("instances", []):
                instances.append(f"{inst['name']} ({inst['status']})")
        return f"{len(instances)} instancias: {instances[:5]}"
    _test("Compute", "Listar instancias (aggregated)", _list_instances)

    def _list_zones():
        session, _ = _get_scoped_session()
        url = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT_ID}/zones"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        zones = [z["name"] for z in resp.json().get("items", [])]
        return f"{len(zones)} zonas disponibles"
    _test("Compute", "Listar zonas", _list_zones)


# ═══════════════════════════════════════════════════════════════
# 8. VERTEX AI / NOTEBOOKS
# ═══════════════════════════════════════════════════════════════

def test_vertex_notebooks():
    print("\n═══ 8. VERTEX AI / NOTEBOOKS ═══")

    def _list_notebook_runtimes():
        session, _ = _get_scoped_session()
        # Vertex AI Workbench managed notebooks
        url = f"https://notebooks.googleapis.com/v2/projects/{PROJECT_ID}/locations/us-central1/instances"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        instances = resp.json().get("instances", [])
        return f"{len(instances)} notebook instances en us-central1"
    _test("VertexAI", "Listar Workbench instances (us-central1)", _list_notebook_runtimes)

    def _list_vertex_locations():
        session, _ = _get_scoped_session()
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1"
        resp = session.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return f"Vertex AI location info: {resp.json().get('name', 'N/A')}"
    _test("VertexAI", "Get Vertex AI location", _list_vertex_locations)


# ═══════════════════════════════════════════════════════════════
# 9. CLOUD LOGGING
# ═══════════════════════════════════════════════════════════════

def test_cloud_logging():
    print("\n═══ 9. CLOUD LOGGING ═══")

    def _write_and_read_log():
        session, _ = _get_scoped_session()
        # Write log entry via REST
        url = f"https://logging.googleapis.com/v2/entries:write"
        body = {
            "logName": f"projects/{PROJECT_ID}/logs/test-permisos-modelos",
            "resource": {"type": "global"},
            "entries": [{"textPayload": "Test de permisos — se puede borrar", "severity": "INFO"}]
        }
        resp = session.post(url, json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"Write: HTTP {resp.status_code}: {resp.text[:300]}")
        # List log entries
        list_url = f"https://logging.googleapis.com/v2/entries:list"
        list_body = {
            "resourceNames": [f"projects/{PROJECT_ID}"],
            "filter": f'logName="projects/{PROJECT_ID}/logs/test-permisos-modelos"',
            "pageSize": 5
        }
        resp2 = session.post(list_url, json=list_body)
        if resp2.status_code != 200:
            raise RuntimeError(f"Read: HTTP {resp2.status_code}: {resp2.text[:300]}")
        entries = resp2.json().get("entries", [])
        return f"Write+Read OK ({len(entries)} entries leídas)"
    _test("CloudLogging", "Write + Read + Delete log entry", _write_and_read_log)


# ═══════════════════════════════════════════════════════════════
# REPORTE FINAL
# ═══════════════════════════════════════════════════════════════

def generar_reporte():
    print("\n" + "=" * 60)
    print("   RESUMEN DE PERMISOS GCP")
    print("=" * 60)

    ok = [r for r in _resultados if r["status"] == "OK"]
    err = [r for r in _resultados if r["status"] == "ERROR"]

    print(f"\n  ✓ {len(ok)} operaciones exitosas")
    print(f"  ✗ {len(err)} operaciones fallidas")

    if ok:
        print("\n  --- PUEDE HACER ---")
        for r in ok:
            print(f"  ✓ [{r['servicio']}] {r['operacion']}")

    if err:
        print("\n  --- NO PUEDE HACER ---")
        for r in err:
            print(f"  ✗ [{r['servicio']}] {r['operacion']}")
            print(f"      → {r['detalle'][:120]}")

    # Guardar reporte JSON
    report_path = BASE_DIR / "reports" / "gcp_permisos_test.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sa_email": "modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com",
        "project": "bfa-cl-trade-price-report-dev",
        "total_ok": len(ok),
        "total_error": len(err),
        "resultados": _resultados,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Reporte guardado en: {report_path}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  DIAGNÓSTICO DE PERMISOS GCP")
    print(f"  SA: modelosrf@bfa-cl-trade-price-report-dev.iam.gserviceaccount.com")
    print(f"  Proyecto: bfa-cl-trade-price-report-dev")
    print(f"  Timestamp: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)

    test_autenticacion()
    test_resource_manager()
    test_service_usage()
    test_iam()
    test_bigquery()
    test_gcs()
    test_compute()
    test_vertex_notebooks()
    test_cloud_logging()
    generar_reporte()

    print("\n✓ Diagnóstico completado.\n")
