"""Tests de catalogo, validacion de datos y carrito."""
from tests.conftest import auth


# ---------- catalogo publico ----------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_listar_productos_seed(client):
    r = client.get("/api/productos?limit=500")
    assert r.status_code == 200
    skus = {p["sku"] for p in r.json()}
    # Los 10 SKU del seed deben estar; no se fija el total exacto porque otros
    # tests crean productos sobre la misma base de datos.
    assert {"AUD-001", "AUD-002", "CAR-001", "CAR-002", "FUN-001", "FUN-002", "CAB-001", "CAB-002", "MOU-001", "TEC-001"} <= skus


def test_categorias(client):
    r = client.get("/api/productos/categorias")
    assert r.status_code == 200
    assert {"Accesorios", "Audio", "Cables", "Cargadores", "Fundas"} <= set(r.json())


def test_filtro_por_categoria(client):
    r = client.get("/api/productos", params={"categoria": "Audio"})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all(p["categoria"] == "Audio" for p in r.json())


def test_busqueda_por_nombre(client):
    r = client.get("/api/productos", params={"buscar": "cable"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert all("cable" in p["nombre"].lower() for p in r.json())


def test_filtro_por_precio(client):
    r = client.get("/api/productos", params={"precio_min": 100000, "precio_max": 200000})
    assert r.status_code == 200
    assert all(100000 <= p["precio"] <= 200000 for p in r.json())


def test_paginacion(client):
    r = client.get("/api/productos", params={"skip": 0, "limit": 3})
    assert len(r.json()) == 3


def test_producto_inexistente_404(client):
    assert client.get("/api/productos/99999").status_code == 404


def test_frontend_servido(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


# ---------- validacion de datos (Pydantic) ----------

def test_precio_negativo_rechazado(client, admin_token):
    r = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "NEG-1", "nombre": "Malo", "precio": -5, "stock": 1, "categoria": "Test"},
    )
    assert r.status_code == 422


def test_precio_cero_rechazado(client, admin_token):
    r = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "CERO-1", "nombre": "Malo", "precio": 0, "stock": 1, "categoria": "Test"},
    )
    assert r.status_code == 422


def test_stock_negativo_rechazado(client, admin_token):
    r = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "STK-1", "nombre": "Malo", "precio": 10, "stock": -1, "categoria": "Test"},
    )
    assert r.status_code == 422


def test_campos_obligatorios_faltantes(client, admin_token):
    r = client.post("/api/productos", headers=auth(admin_token), json={"nombre": "Sin SKU"})
    assert r.status_code == 422


def test_sku_duplicado_409(client, admin_token):
    payload = {"sku": "DUP-1", "nombre": "A", "precio": 10, "stock": 1, "categoria": "Test"}
    assert client.post("/api/productos", headers=auth(admin_token), json=payload).status_code == 201
    assert client.post("/api/productos", headers=auth(admin_token), json=payload).status_code == 409


def test_update_a_sku_existente_da_409_no_500(client, admin_token):
    """Regresion: antes el commit reventaba con IntegrityError y devolvia 500."""
    a = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "SKU-A", "nombre": "A", "precio": 10, "stock": 1, "categoria": "Test"},
    ).json()
    b = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "SKU-B", "nombre": "B", "precio": 10, "stock": 1, "categoria": "Test"},
    ).json()

    r = client.put(f"/api/productos/{b['id']}", headers=auth(admin_token), json={"sku": "SKU-A"})
    assert r.status_code == 409, r.text

    # El producto no debe haber quedado modificado ni la sesion rota.
    assert client.get(f"/api/productos/{b['id']}").json()["sku"] == "SKU-B"


def test_update_al_mismo_sku_no_da_409(client, admin_token):
    p = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "MISMO-1", "nombre": "M", "precio": 10, "stock": 1, "categoria": "Test"},
    ).json()
    r = client.put(f"/api/productos/{p['id']}", headers=auth(admin_token), json={"sku": "MISMO-1", "precio": 20})
    assert r.status_code == 200


def test_limit_fuera_de_rango_rechazado(client):
    """Regresion: `limit` sin validar permitia pedir 1.000.000.000 filas."""
    assert client.get("/api/productos", params={"limit": -1}).status_code == 422
    assert client.get("/api/productos", params={"limit": 0}).status_code == 422
    assert client.get("/api/productos", params={"limit": 1000000000}).status_code == 422
    assert client.get("/api/productos", params={"skip": -5}).status_code == 422


def test_limit_dentro_de_rango_ok(client):
    assert client.get("/api/productos", params={"limit": 500}).status_code == 200


# ---------- CRUD admin ----------

def test_ciclo_completo_producto(client, admin_token):
    creado = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "CICLO-1", "nombre": "Ciclo", "precio": 5000, "stock": 3, "categoria": "Test"},
    )
    assert creado.status_code == 201
    pid = creado.json()["id"]

    upd = client.put(f"/api/productos/{pid}", headers=auth(admin_token), json={"precio": 7500})
    assert upd.status_code == 200
    assert upd.json()["precio"] == 7500

    assert client.delete(f"/api/productos/{pid}", headers=auth(admin_token)).status_code == 204
    assert client.get(f"/api/productos/{pid}").status_code == 404


def test_update_parcial_no_borra_otros_campos(client, admin_token):
    creado = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "PAR-1", "nombre": "Parcial", "precio": 100, "stock": 9, "categoria": "Test"},
    ).json()

    upd = client.put(f"/api/productos/{creado['id']}", headers=auth(admin_token), json={"stock": 42})
    assert upd.status_code == 200
    assert upd.json()["stock"] == 42
    assert upd.json()["nombre"] == "Parcial"
    assert upd.json()["precio"] == 100


def test_producto_inactivo_no_sale_en_catalogo(client, admin_token):
    creado = client.post(
        "/api/productos",
        headers=auth(admin_token),
        json={"sku": "INA-1", "nombre": "Inactivo", "precio": 100, "stock": 1, "categoria": "Test"},
    ).json()

    client.put(f"/api/productos/{creado['id']}", headers=auth(admin_token), json={"activo": False})

    activos = client.get("/api/productos", params={"limit": 500}).json()
    assert creado["id"] not in [p["id"] for p in activos]

    # `solo_activos=false` (lo que usa el panel de admin) SI lo muestra.
    todos = client.get("/api/productos", params={"limit": 500, "solo_activos": False}).json()
    assert creado["id"] in [p["id"] for p in todos]


# Aislamiento: cada test corre con datos que el mismo crea, pero la DB es
# compartida por sesion. Los tests de carrito dependen del producto 1 del seed.

def test_carrito_requiere_sesion(client):
    assert client.get("/api/carrito").status_code in (401, 403)


def test_agregar_y_ver_carrito(client, user_token):
    r = client.post("/api/carrito", headers=auth(user_token), json={"producto_id": 1, "cantidad": 2})
    assert r.status_code == 201

    items = client.get("/api/carrito", headers=auth(user_token)).json()
    assert any(i["producto_id"] == 1 for i in items)


def test_agregar_cantidad_cero_rechazado(client, user_token):
    r = client.post("/api/carrito", headers=auth(user_token), json={"producto_id": 1, "cantidad": 0})
    assert r.status_code == 422


def test_agregar_sin_stock_suficiente(client, user_token):
    r = client.post("/api/carrito", headers=auth(user_token), json={"producto_id": 1, "cantidad": 99999})
    assert r.status_code == 400


def test_agregar_producto_inexistente(client, user_token):
    r = client.post("/api/carrito", headers=auth(user_token), json={"producto_id": 99999, "cantidad": 1})
    assert r.status_code == 404


def test_carrito_es_privado_por_usuario(client, admin_token, user_token):
    """El carrito de otro usuario no se puede modificar."""
    item = client.post("/api/carrito", headers=auth(user_token), json={"producto_id": 2, "cantidad": 1}).json()
    r = client.delete(f"/api/carrito/{item['id']}", headers=auth(admin_token))
    assert r.status_code == 404, "un usuario no debe poder tocar el carrito de otro"
