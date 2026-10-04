import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.seed import run_seed
from app.routers import productos, carrito, auth

# ===== Config =====
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

# ===== Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_seed()
    yield

# ===== App =====
app = FastAPI(
    title="Tienda Tech API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS solo en desarrollo
if ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ===== Routers =====
app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(carrito.router)

# ===== Health =====
@app.get("/api/health")
def health():
    return {"status": "ok", "env": ENVIRONMENT}

# ===== Frontend estatico =====
# Se monta en /static, NO en "/": el HTML y el seed referencian rutas con ese
# prefijo (/static/css/styles.css, /static/js/main.js, /static/assets/*.svg).
# Montar en "/" hacia que todos esos assets respondieran 404 y el frontend
# quedara sin estilos ni JS (el 200 de "/" lo ocultaba).
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(_static_dir, "index.html"))


app.mount("/static", StaticFiles(directory=_static_dir), name="static")
