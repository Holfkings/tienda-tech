import os
from sqlalchemy.orm import Session
from app.db import Base, engine, SessionLocal
from app.models import Usuario, Producto
from app.auth import get_password_hash


def _crear_admin(db: Session):
    admin = db.query(Usuario).filter(Usuario.es_admin == True).first()
    if admin:
        return

    email = os.getenv("ADMIN_EMAIL", "admin@tienda.com")
    pwd = os.getenv("ADMIN_PASSWORD")
    if not pwd:
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError("ADMIN_PASSWORD no configurada en producción")
        pwd = "admin123"

    db.add(Usuario(
        email=email,
        nombre="Administrador",
        password_hash=get_password_hash(pwd),
        es_admin=True,
    ))
    db.commit()


def _seed_productos(db: Session):
    existentes = db.query(Producto).count()
    if existentes > 0:
        return

    productos = [
        {"sku": "AUD-001", "nombre": "Audífonos Bluetooth Pro", "descripcion": "Audífonos inalámbricos con cancelación de ruido, 30h de batería.", "precio": 189900, "stock": 25, "categoria": "Audio", "imagen_url": "/static/assets/audifonos.svg"},
        {"sku": "AUD-002", "nombre": "Audífonos Deportivos", "descripcion": "Resistentes al agua IPX5, diseño ergonómico para ejercicio.", "precio": 89900, "stock": 40, "categoria": "Audio", "imagen_url": "/static/assets/audifonos-deportivos.svg"},
        {"sku": "CAR-001", "nombre": "Cargador Rápido 65W", "descripcion": "Carga rápida GaN, 2 puertos USB-C, compatible con laptops y celulares.", "precio": 79900, "stock": 60, "categoria": "Cargadores", "imagen_url": "/static/assets/cargador.svg"},
        {"sku": "CAR-002", "nombre": "Cargador Inalámbrico", "descripcion": "Base de carga Qi 15W, diseño delgado, LED indicador.", "precio": 49900, "stock": 35, "categoria": "Cargadores", "imagen_url": "/static/assets/cargador-inalambrico.svg"},
        {"sku": "FUN-001", "nombre": "Funda Antigolpes iPhone", "descripcion": "Protección militar MIL-STD-810G, bordes reforzados.", "precio": 39900, "stock": 80, "categoria": "Fundas", "imagen_url": "/static/assets/funda.svg"},
        {"sku": "FUN-002", "nombre": "Funda Silicona Samsung", "descripcion": "Silicona suave anti-rayones, diseño slim.", "precio": 29900, "stock": 100, "categoria": "Fundas", "imagen_url": "/static/assets/funda-silicona.svg"},
        {"sku": "CAB-001", "nombre": "Cable USB-C 2m", "descripcion": "Carga rápida 100W, datos 480Mbps, nylon trenzado.", "precio": 19900, "stock": 150, "categoria": "Cables", "imagen_url": "/static/assets/cable.svg"},
        {"sku": "CAB-002", "nombre": "Cable Lightning 1m", "descripcion": "Cable MFi certificado, carga rápida, resistente.", "precio": 24900, "stock": 120, "categoria": "Cables", "imagen_url": "/static/assets/cable-lightning.svg"},
        {"sku": "MOU-001", "nombre": "Mouse Inalámbrico", "descripcion": "Silencioso, 1600 DPI, batería 12 meses.", "precio": 34900, "stock": 50, "categoria": "Accesorios", "imagen_url": "/static/assets/mouse.svg"},
        {"sku": "TEC-001", "nombre": "Teclado Mecánico RGB", "descripcion": "Switches blue, retroiluminación RGB, layout compacto.", "precio": 149900, "stock": 20, "categoria": "Accesorios", "imagen_url": "/static/assets/teclado.svg"},
    ]

    for p in productos:
        db.add(Producto(**p))
    db.commit()


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _crear_admin(db)
        _seed_productos(db)
    finally:
        db.close()
