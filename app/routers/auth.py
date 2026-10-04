from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario
from app.schemas import UsuarioRegister, UsuarioLogin, Token
from app.auth import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
def register(data: UsuarioRegister, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")

    usuario = Usuario(
        email=data.email,
        nombre=data.nombre,
        password_hash=get_password_hash(data.password),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = create_access_token({"sub": usuario.id, "es_admin": usuario.es_admin})
    return Token(access_token=token, es_admin=usuario.es_admin)


@router.post("/login", response_model=Token)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token({"sub": usuario.id, "es_admin": usuario.es_admin})
    return Token(access_token=token, es_admin=usuario.es_admin)
