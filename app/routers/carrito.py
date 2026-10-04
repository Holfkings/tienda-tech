from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CarritoItem, Producto
from app.schemas import CarritoAdd, CarritoUpdate, CarritoItemOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/carrito", tags=["carrito"])


@router.get("", response_model=list[CarritoItemOut])
def ver_carrito(db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    items = db.query(CarritoItem).filter(CarritoItem.usuario_id == usuario.id).all()
    return items


@router.post("", response_model=CarritoItemOut, status_code=201)
def agregar_al_carrito(
    data: CarritoAdd,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    producto = db.query(Producto).filter(Producto.id == data.producto_id, Producto.activo == True).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado o inactivo")
    if producto.stock < data.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    item = db.query(CarritoItem).filter(
        CarritoItem.usuario_id == usuario.id,
        CarritoItem.producto_id == data.producto_id,
    ).first()

    if item:
        item.cantidad += data.cantidad
    else:
        item = CarritoItem(usuario_id=usuario.id, producto_id=data.producto_id, cantidad=data.cantidad)
        db.add(item)

    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=CarritoItemOut)
def actualizar_cantidad(
    item_id: int,
    data: CarritoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    item = db.query(CarritoItem).filter(CarritoItem.id == item_id, CarritoItem.usuario_id == usuario.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado en tu carrito")

    producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
    if producto and producto.stock < data.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    item.cantidad = data.cantidad
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def quitar_del_carrito(
    item_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    item = db.query(CarritoItem).filter(CarritoItem.id == item_id, CarritoItem.usuario_id == usuario.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado en tu carrito")
    db.delete(item)
    db.commit()
