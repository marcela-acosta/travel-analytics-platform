"""
Run after Superset is up to register BigQuery + gold datasets automatically.
Usage: python setup_bigquery.py
"""
import os
import time
import requests

BASE = "http://localhost:8088"
_ADMIN_PASSWORD = os.environ["SUPERSET_ADMIN_PASSWORD"]
SA_PATH = "/app/gcp/sa.json"
PROJECT = "pipeline-health-mon-2026"
GOLD_TABLES = [
    "gld_dashboard_opportunities",
    "gld_pipeline_by_stage",
    "gld_conversion_by_agent",
    "gld_conversion_by_product",
    "gld_stale_opportunities",
]


def wait_for_superset(retries=30, delay=5):
    for i in range(retries):
        try:
            r = requests.get(f"{BASE}/health", timeout=5)
            if r.status_code == 200:
                print("Superset is up.")
                return
        except Exception:
            pass
        print(f"Waiting... ({i+1}/{retries})")
        time.sleep(delay)
    raise RuntimeError("Superset did not start in time.")


def get_session_and_headers():
    session = requests.Session()
    # Step 1: login
    login = session.post(f"{BASE}/api/v1/security/login", json={
        "username": "admin", "password": _ADMIN_PASSWORD,
        "provider": "db", "refresh": True,
    })
    login.raise_for_status()
    token = login.json()["access_token"]
    # Step 2: get CSRF token
    csrf_resp = session.get(f"{BASE}/api/v1/security/csrf_token/",
                            headers={"Authorization": f"Bearer {token}"})
    csrf_resp.raise_for_status()
    csrf_token = csrf_resp.json()["result"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token,
        "Referer": BASE,
    }
    return session, headers


def create_database(session, headers):
    payload = {
        "database_name": "BigQuery · Travel Analytics",
        "sqlalchemy_uri": f"bigquery://{PROJECT}?credentials_path={SA_PATH}",
        "expose_in_sqllab": True,
        "allow_run_async": False,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
    }
    r = session.post(f"{BASE}/api/v1/database/", json=payload, headers=headers)
    if r.status_code in (200, 201):
        db_id = r.json()["id"]
        print(f"Database registered (id={db_id}).")
        return db_id
    if r.status_code == 422 and "already exists" in r.text:
        print("Database already registered, fetching id...")
        existing = session.get(f"{BASE}/api/v1/database/", headers=headers)
        for db in existing.json().get("result", []):
            if "Travel Analytics" in db["database_name"]:
                return db["id"]
    r.raise_for_status()


def create_datasets(session, headers, db_id):
    for table in GOLD_TABLES:
        payload = {"database": db_id, "schema": "gold", "table_name": table}
        r = session.post(f"{BASE}/api/v1/dataset/", json=payload, headers=headers)
        if r.status_code in (200, 201):
            print(f"  ✓ gold.{table}")
        elif r.status_code == 422:
            print(f"  · gold.{table} (already exists)")
        else:
            print(f"  ! {table} ({r.status_code}): {r.text[:100]}")


if __name__ == "__main__":
    wait_for_superset()
    sess, hdrs = get_session_and_headers()
    db_id = create_database(sess, hdrs)
    create_datasets(sess, hdrs, db_id)
    print(f"\nDone. Open http://localhost:8088  →  admin / (see SUPERSET_ADMIN_PASSWORD in .env)")
