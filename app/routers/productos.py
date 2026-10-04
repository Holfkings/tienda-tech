from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.models import Producto
from app.schemas import ProductoCreate, ProductoUpdate, ProductoOut
from app.auth import get_current_admin

router = APIRouter(prefix="/api/productos", tags=["productos"])

# Techo duro: evita que un `limit` gigante tumbe la respuesta (y la memoria) del
# proceso. El panel de admin pide limit=100, asi que 500 sobra.
LIMITE_MAX = 500


def _conflicto_sku(db: Session, sku: str, excluir_id: Optional[int] = None) -> None:
    """Valida unicidad de SKU ANTES del commit.

    Sin esto, un SKU repetido revienta en el commit como IntegrityError y el
    cliente recibe un HTTP 500 en lugar del 409 que corresponde.
    """
    q = db.query(Producto).filter(Producto.sku == sku)
    if excluir_id is not None:
        q = q.filter(Producto.id != excluir_id)
    if db.query(q.exists()).scalar():
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU")


@router.get("", response_model=list[ProductoOut])
def listar_productos(
    categoria: Optional[str] = None,
    buscar: Optional[str] = None,
    precio_min: Optional[float] = None,
    precio_max: Optional[float] = None,
    solo_activos: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=LIMITE_MAX),
    db: Session = Depends(get_db),
):
    query = db.query(Producto)
    if solo_activos:
        query = query.filter(Producto.activo == True)
    if categoria:
        query = query.filter(Producto.categoria == categoria)
    if buscar:
        query = query.filter(Producto.nombre.ilike(f"%{buscar}%"))
    if precio_min is not None:
        query = query.filter(Producto.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(Producto.precio <= precio_max)
    return query.offset(skip).limit(limit).all()


@router.get("/categorias", response_model=list[str])
def listar_categorias(db: Session = Depends(get_db)):
    rows = db.query(Producto.categoria).distinct().all()
    return [r[0] for r in rows]


@router.get("/{producto_id}", response_model=ProductoOut)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(Producto).filter(Producto.id == producto_id, Producto.activo == True).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("", response_model=ProductoOut, status_code=201)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    _conflicto_sku(db, data.sku)
    producto = Producto(**data.model_dump())
    db.add(producto)
    try:
        db.commit()
    except IntegrityError:
        # Carrera entre la validacion y el commit: otra peticion gano.
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU")
    db.refresh(producto)
    return producto


@router.put("/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    if "sku" in cambios:
        _conflicto_sku(db, cambios["sku"], excluir_id=producto_id)

    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU")
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=204)
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Soft-delete: marca el producto como inactivo en vez de borrarlo.

    Borrado físico rompería carritos de usuarios (cascade delete-orphan)
    y perdería el historial de pedidos. Con `activo=False` el producto
    desaparece de las listas públicas pero los pedidos históricos
    conservan nombre y precio unitario en pedido_items.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.activo = False
    db.commit()
