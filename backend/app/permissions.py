from sqlalchemy.orm import Session

from app.models import User, UserPermission


MANAGE_USERS = "manage_users"
MANAGE_PRODUCTS = "manage_products"
MANAGE_VERSIONS = "manage_versions"
UPLOAD_FILES = "upload_files"
DOWNLOAD_FILES = "download_files"
DELETE_FILES = "delete_files"

ALL_PERMISSIONS = (
    MANAGE_USERS,
    MANAGE_PRODUCTS,
    MANAGE_VERSIONS,
    UPLOAD_FILES,
    DOWNLOAD_FILES,
    DELETE_FILES,
)

ROLE_DEFAULT_PERMISSIONS = {
    "admin": set(ALL_PERMISSIONS),
    "developer": {
        MANAGE_PRODUCTS,
        MANAGE_VERSIONS,
        UPLOAD_FILES,
        DOWNLOAD_FILES,
        DELETE_FILES,
    },
    "tester": {DOWNLOAD_FILES},
}


def default_permissions(role: str) -> set[str]:
    return set(ROLE_DEFAULT_PERMISSIONS.get(role, set()))


def effective_permissions(user: User) -> set[str]:
    permissions = default_permissions(user.role)
    for override in user.permission_overrides:
        if override.permission not in ALL_PERMISSIONS:
            continue
        if override.allowed:
            permissions.add(override.permission)
        else:
            permissions.discard(override.permission)
    return permissions


def ordered_permissions(user: User) -> list[str]:
    effective = effective_permissions(user)
    return [permission for permission in ALL_PERMISSIONS if permission in effective]


def replace_permission_overrides(
    db: Session,
    user: User,
    permissions: list[str] | None,
) -> None:
    db.query(UserPermission).filter(UserPermission.user_id == user.id).delete()
    if permissions is None:
        return

    selected = set(permissions)
    defaults = default_permissions(user.role)
    for permission in ALL_PERMISSIONS:
        allowed = permission in selected
        if allowed != (permission in defaults):
            db.add(
                UserPermission(
                    user_id=user.id,
                    permission=permission,
                    allowed=allowed,
                )
            )
