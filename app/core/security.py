"""Hash password dan JWT.

Passlib bcrypt dipakai untuk password (otomatis menangani salt), PyJWT
untuk token. Token menyimpan id_user dan role — role selalu dibaca dari
token, bukan dari body request, supaya tidak bisa dipalsukan klien.
"""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(id_user: int, role: str) -> str:
    settings = get_settings()
    payload = {
        "sub": str(id_user),
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
