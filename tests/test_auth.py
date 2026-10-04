"""Tests de autenticacion y autorizacion.

Cubren dos bugs reales encontrados al verificar la migracion a FastAPI:

1. `sub` del JWT se emitia como int. python-jose >= 3.4 valida el claim y lanza
   JWTClaimsError("Subject must be a string") al decodificar, asi que TODOS los
   endpoints con token devolvian 401.
2. bcrypt 5.x rechaza passwords de mas de 72 BYTES (no caracteres). Con el
   schema viejo (max_length=100) un password de 100 caracteres daba HTTP 500.
"""
from tests.conftest import auth

PASSWORD_100 = "a" * 100
PASSWORD_EMOJIS = "\U0001F600" * 30  # 30 caracteres = 120 bytes en UTF-8


# ---------- login / registro ----------

def test_login_admin_ok(client):
    r = client.post("/api/auth/login", json={"email": "admin@tienda.com", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["es_admin"] is True


def test_login_password_incorrecta(client):
    r = client.post("/api/auth/login", json={"email": "admin@tienda.com", "password": "mala"})
    assert r.status_code == 401


def test_registro_ok(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "nuevo@test.com", "nombre": "Nuevo", "password": "secreto123"},
    )
    assert r.status_code == 201
    assert r.json()["es_admin"] is False


def test_registro_email_duplicado(client):
    payload = {"email": "dup@test.com", "nombre": "Dup", "password": "secreto123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_registro_password_corta_rechazada(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "corta@test.com", "nombre": "C", "password": "123"},
    )
    assert r.status_code == 422


def test_registro_email_invalido(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "no-es-un-email", "nombre": "X", "password": "secreto123"},
    )
    assert r.status_code == 422


# ---------- bug #2: bcrypt > 72 bytes ----------

def test_password_de_100_caracteres_no_da_500(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "largo@test.com", "nombre": "L", "password": PASSWORD_100},
    )
    assert r.status_code == 201, r.text

    r = client.post("/api/auth/login", json={"email": "largo@test.com", "password": PASSWORD_100})
    assert r.status_code == 200, "no puede loguear con el password con el que se registro"


def test_password_con_emojis_multibyte(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "emoji@test.com", "nombre": "E", "password": PASSWORD_EMOJIS},
    )
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": "emoji@test.com", "password": PASSWORD_EMOJIS})
    assert r.status_code == 200


def test_password_no_se_trunca_a_72_bytes(client):
    """Regresion: si se truncara a 72 bytes, estas dos claves serian la misma."""
    base = "a" * 72
    client.post(
        "/api/auth/register",
        json={"email": "trunc@test.com", "nombre": "T", "password": base + "UNO"},
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "trunc@test.com", "password": base + "DOS"},
    )
    assert r.status_code == 401, "el password se esta truncando: claves distintas entran igual"


# ---------- bug #1: JWT con sub string ----------

def test_token_permite_endpoint_autenticado(client, admin_token):
    """Regresion del bug de `sub`: antes esto devolvia 401 con token valido."""
    r = client.get("/api/carrito", headers=auth(admin_token))
    assert r.status_code == 200, r.text


def test_token_contiene_sub_string(admin_token):
    from jose import jwt

    payload = jwt.decode(admin_token, "test-secret-key-no-usar-en-produccion", algorithms=["HS256"])
    assert isinstance(payload["sub"], str), "RFC 7519 exige que `sub` sea string"
    assert payload["es_admin"] is True


def test_token_falso_rechazado(client):
    r = client.get("/api/carrito", headers=auth("eyJhbGciOiJIUzI1NiJ9.falso.firma"))
    assert r.status_code == 401


def test_token_ausente_rechazado(client):
    assert client.get("/api/carrito").status_code in (401, 403)


def test_usuario_normal_no_puede_crear_producto(client, user_token):
    r = client.post(
        "/api/productos",
        headers=auth(user_token),
        json={"sku": "USR-1", "nombre": "X", "precio": 10, "stock": 1, "categoria": "Test"},
    )
    assert r.status_code == 403


def test_admin_puede_crear_producto(client, admin_token):
    r = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "ADM-1", "nombre": "Admin", "precio": 10, "stock": 1, "categoria": "Test"},
    )
    assert r.status_code == 201
