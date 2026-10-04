from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    es_admin = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    carrito_items = relationship("CarritoItem", back_populates="usuario", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="usuario")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, default="")
    precio = Column(Float, nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    categoria = Column(String(100), nullable=False, index=True)
    imagen_url = Column(String(500), default="")
    activo = Column(Boolean, default=True, nullable=False, index=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    carrito_items = relationship("CarritoItem", back_populates="producto", cascade="all, delete-orphan")
    pedido_items = relationship("PedidoItem", back_populates="producto")


class CarritoItem(Base):
    __tablename__ = "carrito"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    cantidad = Column(Integer, default=1, nullable=False)
    agregado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="carrito_items")
    producto = relationship("Producto", back_populates="carrito_items")


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    estado = Column(String(50), default="pendiente", nullable=False)
    total = Column(Float, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    nombre_producto = Column(String(255), nullable=False)
    precio_unitario = Column(Float, nullable=False)
    cantidad = Column(Integer, nullable=False)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="pedido_items")
