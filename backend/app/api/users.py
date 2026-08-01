from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, require_roles
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        UserOut(
            id=u.id,
            username=u.username,
            role=u.role,  # type: ignore[arg-type]
            is_active=bool(u.is_active),
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=1 if body.is_active else 0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
        is_active=bool(user.is_active),
        created_at=user.created_at,
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        if user.id == current.id and not body.is_active:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        user.is_active = 1 if body.is_active else 0
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
        is_active=bool(user.is_active),
        created_at=user.created_at,
    )
