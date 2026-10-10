from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth import hash_password, require_permission
from app.config import settings
from app.database import get_db
from app.models import User
from app.permissions import (
    MANAGE_USERS,
    default_permissions,
    ordered_permissions,
    replace_permission_overrides,
)
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
        is_active=bool(user.is_active),
        created_at=user.created_at,
        permissions=ordered_permissions(user),  # type: ignore[arg-type]
    )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_USERS)),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [to_user_out(user) for user in users]


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_USERS)),
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
    db.flush()
    replace_permission_overrides(db, user, body.permissions)
    db.commit()
    db.refresh(user)
    return to_user_out(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission(MANAGE_USERS)),
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
    if body.permissions is not None:
        if user.id == current.id and MANAGE_USERS not in body.permissions:
            raise HTTPException(status_code=400, detail="不能移除自己的用户管理权限")
        replace_permission_overrides(db, user, body.permissions)
    elif body.role is not None:
        if user.id == current.id and MANAGE_USERS not in default_permissions(user.role):
            raise HTTPException(status_code=400, detail="不能移除自己的用户管理权限")
        replace_permission_overrides(db, user, None)
    db.commit()
    db.refresh(user)
    return to_user_out(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission(MANAGE_USERS)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    # Startup seeds this account when absent. Do not allow deletion to recreate
    # a default-password administrator on the next service restart.
    if user.username == settings.default_admin_username:
        raise HTTPException(status_code=400, detail="不能删除系统初始管理员，可修改其密码或禁用账号")
    if user.role == "admin" and user.is_active:
        other_admin = db.query(User).filter(
            User.role == "admin", User.is_active == 1, User.id != user.id
        ).first()
        if not other_admin:
            raise HTTPException(status_code=400, detail="不能删除最后一个启用的管理员")
    # Keep products, versions and their files; only detach the nullable uploader
    # association. Per-user permission overrides are removed by the ORM cascade.
    for version in list(user.versions):
        version.uploader = None
    db.delete(user)
    db.commit()
    return Response(status_code=204)
