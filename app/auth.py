import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# bcrypt 5.x RECHAZA entradas de mas de 72 bytes (ya no trunca en silencio) y
# cuenta BYTES, no caracteres: 25 caracteres con acentos o emojis ya pasan de 72.
# Pre-hasheamos con SHA-256 en base64 (44 bytes ASCII) para aceptar cualquier
# longitud sin recortar el password. Mismo patron que passlib y Django.
security = HTTPBearer()


def _prehash(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # RFC 7519: el claim `sub` DEBE ser string. python-jose >= 3.4 lo valida al
    # decodificar y lanza JWTClaimsError ("Subject must be a string") si es int,
    # lo que rompe TODOS los endpoints autenticados.
    if to_encode.get("sub") is not None:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def get_current_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.es_admin:
        raise HTTPException(status_code=403, detail="Se requiere permisos de administrador")
    return current_user
