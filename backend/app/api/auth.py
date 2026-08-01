from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    return Token(access_token=create_access_token(user.username))


@router.post("/login-json", response_model=Token)
def login_json(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    return Token(access_token=create_access_token(user.username))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
        is_active=bool(user.is_active),
        created_at=user.created_at,
    )
