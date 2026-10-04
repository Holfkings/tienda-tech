# Tienda Tech — API FastAPI + SQLite, un solo servicio en Railway

Tienda online de accesorios tecnológicos. **FastAPI + SQLite, un solo servicio.**
El backend sirve el frontend estático (`static/`), así que hay **un despliegue, un dominio y cero CORS en producción**.

## Arranque rápido

```bash
cp .env.example .env        # ajustar SECRET_KEY y ADMIN_PASSWORD
python -m venv .venv && source .venv/Scripts/activate   # Windows git-bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
bash scripts/smoke_test.sh http://127.0.0.1:8000
```

Tests: `pip install -r requirements-dev.txt && python -m pytest`

## API

Todas las rutas de datos viven bajo `/api`. El frontend está montado en `/`.

| Método | Ruta | Auth | Éxito | Errores |
|---|---|---|---|---|
| GET | `/api/health` | — | 200 | — |
| POST | `/api/auth/register` | — | 201 | 409 email repetido, 422 datos inválidos |
| POST | `/api/auth/login` | — | 200 | 401 credenciales |
| GET | `/api/productos` | — | 200 | 422 `limit`/`skip` fuera de rango |
| GET | `/api/productos/categorias` | — | 200 | — |
| GET | `/api/productos/{id}` | — | 200 | 404 |
| POST | `/api/productos` | admin | 201 | 401 sin token, 403 no admin, 409 SKU repetido, 422 datos inválidos |
| PUT | `/api/productos/{id}` | admin | 200 | 401/403, 404, 409 SKU repetido, 422 |
| DELETE | `/api/productos/{id}` | admin | 204 | 401/403, 404 |
| GET | `/api/carrito` | usuario | 200 | 401 |
| POST | `/api/carrito` | usuario | 201 | 400 stock insuficiente, 404 producto, 422 cantidad |
| PUT | `/api/carrito/{item_id}` | usuario | 200 | 400 stock, 404 item |
| DELETE | `/api/carrito/{item_id}` | usuario | 204 | 404 item |

`GET /api/productos` acepta `categoria`, `buscar`, `precio_min`, `precio_max`,
`solo_activos` (default `true`), `skip` y `limit` (**1–500**; el panel de admin usa `solo_activos=false&limit=500`).

### Ejemplos con curl

```bash
# Login admin -> guarda el token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@tienda.com","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Crear producto
curl -s -X POST http://localhost:8000/api/productos \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sku":"NEW-1","nombre":"Producto","precio":25000,"stock":10,"categoria":"Accesorios"}'

# Verificar que el token sirve (antes daba 401 por el bug de `sub`)
curl -s http://localhost:8000/api/carrito -H "Authorization: Bearer $TOKEN"

# SKU repetido -> 409, no 500
curl -s -o /dev/null -w '%{http_code}\n' -X PUT http://localhost:8000/api/productos/2 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"sku":"NEW-1"}'
```

## Estructura

```
tienda-tech/
├── app/
│   ├── main.py          # FastAPI: monta /api/*, sirve / y /static/*
│   ├── db.py            # engine + DATABASE_URL desde env
│   ├── models.py        # SQLAlchemy: Usuario, Producto, CarritoItem, Pedido, PedidoItem
│   ├── schemas.py       # Pydantic: validación de entrada
│   ├── auth.py          # bcrypt + JWT
│   ├── seed.py          # run_seed() idempotente
│   └── routers/         # productos, auth, carrito
├── static/              # frontend (index.html, css, js, assets/*.svg)
├── tests/               # pytest: auth, validación, catálogo, carrito
├── scripts/
│   ├── backup_db.py     # backup diario (stdlib, no requiere binario sqlite3)
│   ├── backup_db.sh     # variante con el CLI sqlite3
│   └── smoke_test.sh    # verifica un despliegue, solo lectura
├── requirements.txt     # producción
├── requirements-dev.txt # pytest + httpx (no entra al contenedor)
├── pytest.ini
├── railway.json
├── nixpacks.toml
├── Procfile
├── .python-version      # 3.12
├── .env.example
└── .gitignore
```

## Regla de oro: la base de datos NO vive en la imagen

Railway recrea el contenedor en cada deploy. Si `tienda.db` queda dentro del repo/imagen,
**cada push borra el catálogo**. La DB va en un **volumen persistente montado en `/data`**.

| Entorno | DATABASE_URL | Volumen |
|---|---|---|
| Dev local | `sqlite:///./tienda_dev.db` | no aplica |
| Producción | `sqlite:////data/tienda.db` | `/data` en Railway |

> Las **4 barras** en `sqlite:////data/tienda.db` son la ruta absoluta. Con 3 barras
> (`sqlite:///data/...`) SQLite busca la carpeta `data/` dentro del proyecto y falla o
> escribe en el lugar equivocado.

## Despliegue en Railway

1. **Nuevo proyecto → Deploy from GitHub repo.** Nixpacks detecta Python.
2. **Service → Settings → Volumes → New Volume**, mount path: **`/data`**.
3. **Service → Variables** (nunca en el repo):

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | `sqlite:////data/tienda.db` |
   | `SECRET_KEY` | `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
   | `ADMIN_EMAIL` | tu correo real |
   | `ADMIN_PASSWORD` | **distinta de `admin123`** |
   | `ENVIRONMENT` | `production` |

4. **Settings → Networking → Generate Domain.** El healthcheck (`/api/health`) ya está
   declarado en `railway.json`; sin él Railway no distingue "arrancó" de "crash silencioso".

## Verificación del despliegue

```bash
bash scripts/smoke_test.sh https://<app>.up.railway.app
```

**Prueba real del volumen** (la única que importa antes de cargar el catálogo):

1. Crear un producto desde el panel admin.
2. Redeploy (`git push` o `railway up`).
3. `GET /api/productos` → el producto **sigue ahí**. Si desapareció, el volumen no está montado.

## Backups

```bash
python scripts/backup_db.py /data/tienda.db /data/backups   # retención 7 días
```

El script valida el backup (`PRAGMA integrity_check` + cuenta de tablas) y **descarta** la
copia si salió corrupta o vacía. La retención **elimina** archivos de más de `RETENTION_DAYS` días.

En Railway se ejecuta como **Cron Job** diario con
`python scripts/backup_db.py /data/tienda.db /data/backups`. El Cron Job debe ser un servicio
**con el mismo volumen montado en `/data`** — si no, no ve la base de datos.

> Un backup que vive en el mismo disco que la DB original no protege contra perder el
> volumen. Una vez por semana hay que **bajarlo fuera de Railway**.

### Por qué el backup usa `sqlite3.Connection.backup` y no un `cp`

La app corre en modo **WAL** (`PRAGMA journal_mode=WAL` en `app/db.py`). Con WAL, las
escrituras recientes viven en `tienda.db-wal` hasta que SQLite hace *checkpoint*; el archivo
`tienda.db` por sí solo está **desactualizado**.

| Copia | Qué incluye | Resultado |
|---|---|---|
| `cp tienda.db` (o un snapshot del disco) | solo el `.db`, sin el `-wal` | **pierde datos en silencio**, con `integrity_check = ok` |
| `python scripts/backup_db.py` | `.db` + `-wal` (API de backup en línea) | consistente, incluso con la app escribiendo |

Medido en este proyecto: con ~9.000 productos insertados y el WAL sin checkpoint,
`cp tienda.db` devolvió **8.919** filas donde había **8.950** — 31 productos perdidos y un
backup que *parece* sano. El script oficial devolvió las 8.950. Por eso el script también
compara el conteo de `productos` de la DB contra el del backup y **falla con código 1** si
no coincide.

**Consecuencia práctica:** no hagas backup con `cp`, `tar` del volumen ni snapshots del
disco mientras la app corre. Y no valides un backup solo con `PRAGMA integrity_check`:
SQLite puede decir `ok` sobre una copia a la que le falta el WAL. El criterio real es
**conteo de filas + integrity**.

## Comandos que modifican o eliminan información

| Comando | Efecto |
|---|---|
| `pip install -r requirements.txt` | instala paquetes (modifica el entorno) |
| `uvicorn app.main:app` | arranca el servidor; `run_seed()` **inserta** admin y productos si faltan |
| `python -m pytest` | usa una DB temporal en `$TMPDIR`; **no** toca `tienda_dev.db` |
| `python scripts/backup_db.py` | **crea** un backup y **elimina** los de más de 7 días |
| `git push` a `main` | dispara deploy en prod (recrea el contenedor) |
| `rm /data/tienda.db` | **borra toda la tienda** — solo con backup verificado a mano |

## Notas de implementación (cosas que rompen en producción)

- **`sub` del JWT debe ser string.** RFC 7519 lo exige y `python-jose` lo valida al
  decodificar (`JWTClaimsError: Subject must be a string`). Si se emite como `int`, **todos**
  los endpoints autenticados devuelven 401 aunque el token sea válido.
- **bcrypt 5.x rechaza >72 bytes** (cuenta bytes, no caracteres: 25 con acentos ya pasan).
  El password se pre-hashea con SHA-256 en base64 antes de bcrypt, así cualquier longitud
  funciona sin truncar.
- **Unicidad de SKU se valida antes del `commit`.** Si no, un SKU repetido en un `PUT`
  revienta como `IntegrityError` y el cliente recibe 500 en lugar de 409.
