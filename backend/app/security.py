"""Password hashing (PBKDF2, stdlib) and JWT auth dependencies."""
import hashlib
import hmac
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

_DEV_SECRET = "dev-secret-change-me-use-a-long-random-key-in-production"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
if os.getenv("ENVIRONMENT") == "production" and SECRET_KEY == _DEV_SECRET:
    raise RuntimeError("SECRET_KEY must be set to a long random value when ENVIRONMENT=production")
ALGORITHM = "HS256"
TOKEN_HOURS = 12
ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "200000"))
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        iterations, salt, digest = stored.split("$")
        new = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(new.hex(), digest)
    except Exception:
        return False


def create_token(user: models.User) -> str:
    payload = {"sub": str(user.id), "role": user.role, "exp": int(time.time()) + TOKEN_HOURS * 3600}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> models.User:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        data = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(models.User, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if not user:
        raise HTTPException(401, "User no longer exists")
    return user


def require_role(role: str):
    def dep(user: models.User = Depends(current_user)) -> models.User:
        if user.role != role:
            raise HTTPException(403, f"{role.capitalize()} access only")
        return user
    return dep
