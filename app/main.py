import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
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

# ===== Static files =====
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
