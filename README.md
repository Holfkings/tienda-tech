# Tienda Tech — Infraestructura y Despliegue

Tienda online de accesorios tecnológicos. **FastAPI + SQLite, un solo servicio en Railway.**
El backend sirve el frontend estático (`static/`), así que hay **un despliegue, un dominio y cero CORS en producción**.

## Estructura esperada del repo

```
tienda-tech/
├── app/
│   ├── main.py          # FastAPI: monta /api/* y StaticFiles(static/)
│   ├── db.py            # engine + DATABASE_URL desde env
│   ├── models.py        # SQLAlchemy
│   ├── seed.py          # run_seed() idempotente
│   └── routers/         # productos, auth, carrito
├── static/              # frontend (index.html, admin.html, css, js)
├── scripts/
│   ├── backup_db.py     # backup diario (stdlib, no requiere binario sqlite3)
│   ├── backup_db.sh     # variante con el CLI sqlite3
│   └── smoke_test.sh    # verifica un despliegue, solo lectura
├── railway.json
├── nixpacks.toml
├── requirements.txt
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

## Puesta en marcha local

```bash
cp .env.example .env                 # ajustar SECRET_KEY y ADMIN_PASSWORD
python -m venv .venv && source .venv/Scripts/activate   # Windows git-bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
bash scripts/smoke_test.sh http://127.0.0.1:8000
```

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
`python scripts/backup_db.py /data/tienda.db /data/backups`.

> Un backup que vive en el mismo disco que la DB original no protege contra perder el
> volumen. Una vez por semana hay que **bajarlo fuera de Railway**.

## Comandos que modifican o eliminan información

| Comando | Efecto |
|---|---|
| `pip install -r requirements.txt` | instala paquetes (modifica el entorno) |
| `uvicorn app.main:app` | arranca el servidor; `run_seed()` **inserta** admin y productos si faltan |
| `python scripts/backup_db.py` | **crea** un backup y **elimina** los de más de 7 días |
| `git push` a `main` | dispara deploy en prod (recrea el contenedor) |
| `rm /data/tienda.db` | **borra toda la tienda** — solo con backup verificado a mano |
