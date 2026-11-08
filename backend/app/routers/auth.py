from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut, status_code=201)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = models.User(name=data.name.strip(), email=email,
                       password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    return schemas.TokenOut(access_token=create_token(user), user=user)


@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return schemas.TokenOut(access_token=create_token(user), user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user
