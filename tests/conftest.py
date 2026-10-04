"""Configuracion de pytest.

IMPORTANTE: las variables de entorno se fijan ANTES de importar la app, porque
`app.db` lee DATABASE_URL al importarse (el engine se crea en el import).
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Base de datos aislada para los tests (nunca toca la DB de desarrollo).
_tmp = Path(tempfile.mkdtemp(prefix="tienda-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["ENVIRONMENT"] = "production"  # exige ADMIN_PASSWORD explicito
os.environ["SECRET_KEY"] = "test-secret-key-no-usar-en-produccion"
os.environ["ADMIN_EMAIL"] = "admin@tienda.com"
os.environ["ADMIN_PASSWORD"] = "admin123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN = {"email": "admin@tienda.com", "password": "admin123"}


@pytest.fixture(scope="session")
def client():
    # `with` ejecuta el lifespan: crea tablas y corre el seed.
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/api/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def user_token(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "cliente@test.com", "nombre": "Cliente", "password": "secreto123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
