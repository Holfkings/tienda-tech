from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class ProductoBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: str = ""
    precio: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    categoria: str = Field(..., min_length=1, max_length=100)
    imagen_url: str = ""
    activo: bool = True


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = None
    precio: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    categoria: Optional[str] = Field(None, min_length=1, max_length=100)
    imagen_url: Optional[str] = None
    activo: Optional[bool] = None


class ProductoOut(ProductoBase):
    id: int

    class Config:
        from_attributes = True


class UsuarioRegister(BaseModel):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=255)
    # Largo en CARACTERES. Se permite amplio porque bcrypt ya no es el limite:
    # el password se pre-hashea con SHA-256 antes de bcrypt.
    password: str = Field(..., min_length=8, max_length=128)


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    es_admin: bool = False


class CarritoAdd(BaseModel):
    producto_id: int
    cantidad: int = Field(1, ge=1)


class CarritoUpdate(BaseModel):
    cantidad: int = Field(..., ge=1)


class CarritoItemOut(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    producto: ProductoOut

    class Config:
        from_attributes = True
