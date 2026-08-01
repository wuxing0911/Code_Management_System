from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import FileEntry, Product, User, Version
from app.schemas import (
    DeleteSelectedRequest,
    DownloadSelectedRequest,
    FileNode,
    VersionCreate,
    VersionOut,
    VersionUpdate,
)
from app.services import storage

router = APIRouter(tags=["versions"])


def to_version_out(db: Session, v: Version) -> VersionOut:
    uploader_name = v.uploader.username if v.uploader else None
    return VersionOut(
        id=v.id,
        product_id=v.product_id,
        name=v.name,
        note=v.note or "",
        status=v.status,
        uploader_id=v.uploader_id,
        uploader_name=uploader_name,
        created_at=v.created_at,
        updated_at=v.updated_at,
        file_count=storage.count_files(db, v.id),
    )


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


def get_version_or_404(db: Session, version_id: int) -> Version:
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    return version


@router.get("/products/{product_id}/versions", response_model=list[VersionOut])
def list_versions(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    get_product_or_404(db, product_id)
    versions = (
        db.query(Version)
        .filter(Version.product_id == product_id)
        .order_by(Version.created_at.desc())
        .all()
    )
    return [to_version_out(db, v) for v in versions]


@router.post("/products/{product_id}/versions", response_model=VersionOut)
def create_version(
    product_id: int,
    body: VersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "developer")),
):
    product = get_product_or_404(db, product_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="版本号不能为空")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="版本号含非法字符")
    exists = (
        db.query(Version)
        .filter(Version.product_id == product_id, Version.name == name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该产品下版本已存在")
    version = Version(
        product_id=product.id,
        name=name,
        note=body.note or "",
        uploader_id=user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    storage.version_dir(product, version)
    return to_version_out(db, version)


@router.get("/versions/{version_id}", response_model=VersionOut)
def get_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    version = get_version_or_404(db, version_id)
    return to_version_out(db, version)


@router.patch("/versions/{version_id}", response_model=VersionOut)
def update_version(
    version_id: int,
    body: VersionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="版本号不能为空")
        if ".." in name or "/" in name or "\\" in name:
            raise HTTPException(status_code=400, detail="版本号含非法字符")
        exists = (
            db.query(Version)
            .filter(
                Version.product_id == version.product_id,
                Version.name == name,
                Version.id != version_id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="该产品下版本已存在")
        if name != version.name:
            storage.rename_version_storage(product, version.name, name)
            version.name = name
    if body.note is not None:
        version.note = body.note
    version.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(version)
    return to_version_out(db, version)


@router.delete("/versions/{version_id}", status_code=204)
def delete_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    storage.delete_version_storage(product, version)
    db.delete(version)
    db.commit()


@router.get("/versions/{version_id}/files", response_model=list[FileNode])
def list_files(
    version_id: int,
    path: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    items = storage.list_directory(product, version, path)
    result: list[FileNode] = []
    for item in items:
        entry = (
            db.query(FileEntry)
            .filter(FileEntry.version_id == version.id, FileEntry.relative_path == item["path"])
            .first()
        )
        category, category_label = storage.detect_category(item["path"], is_dir=item["is_dir"])
        result.append(
            FileNode(
                name=item["name"],
                path=item["path"],
                is_dir=item["is_dir"],
                size=item["size"],
                md5=item.get("md5") or (entry.md5 if entry else ""),
                file_id=entry.id if entry and not item["is_dir"] else None,
                category=category,
                category_label=category_label,
            )
        )
    return result


@router.post("/versions/{version_id}/upload/files")
async def upload_files(
    version_id: int,
    files: list[UploadFile] = File(...),
    paths: list[str] | None = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    # FastAPI may pass a single string when one path; normalize
    rel_paths = paths
    if isinstance(paths, str):
        rel_paths = [paths]
    count = await storage.save_upload_files(db, product, version, files, rel_paths)
    version.updated_at = datetime.utcnow()
    db.commit()
    return {"uploaded": count}


@router.post("/versions/{version_id}/upload/folder")
async def upload_folder(
    version_id: int,
    files: list[UploadFile] = File(...),
    paths: list[str] = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    if isinstance(paths, str):
        paths = [paths]
    count = await storage.save_upload_files(db, product, version, files, paths)
    version.updated_at = datetime.utcnow()
    db.commit()
    return {"uploaded": count}


@router.post("/versions/{version_id}/upload/zip")
async def upload_zip(
    version_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    count = await storage.save_zip_upload(db, product, version, file)
    version.updated_at = datetime.utcnow()
    db.commit()
    return {"uploaded": count}


@router.post("/versions/{version_id}/download-selected")
def download_selected(
    version_id: int,
    body: DownloadSelectedRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)

    # Single file shortcut: return original file
    if len(body.paths) == 1:
        root = storage.version_dir(product, version)
        target = storage.safe_join(root, body.paths[0])
        if target.is_file():
            return FileResponse(
                path=target,
                filename=target.name,
                media_type="application/octet-stream",
            )

    buf = storage.build_selected_zip(product, version, body.paths)
    filename = f"{product.slug}_{version.name}_selected.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/versions/{version_id}/download")
def download_version(
    version_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    buf = storage.build_version_zip(product, version)
    filename = f"{product.slug}_{version.name}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/versions/{version_id}/delete-selected")
def delete_selected(
    version_id: int,
    body: DeleteSelectedRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    version = get_version_or_404(db, version_id)
    product = get_product_or_404(db, version.product_id)
    if not body.paths:
        raise HTTPException(status_code=400, detail="请先勾选要删除的文件或文件夹")
    count = storage.delete_paths(db, product, version, body.paths)
    version.updated_at = datetime.utcnow()
    db.commit()
    return {"deleted": count}


@router.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entry = db.query(FileEntry).filter(FileEntry.id == file_id).first()
    if not entry or entry.is_dir:
        raise HTTPException(status_code=404, detail="文件不存在")
    version = get_version_or_404(db, entry.version_id)
    product = get_product_or_404(db, version.product_id)
    root = storage.version_dir(product, version)
    target = storage.safe_join(root, entry.relative_path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="磁盘文件缺失")
    return FileResponse(
        path=target,
        filename=target.name,
        media_type="application/octet-stream",
    )
