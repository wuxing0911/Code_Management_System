import hashlib
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import STORAGE_ROOT
from app.models import FileEntry, Product, Version


SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")
CODE_DIR = "程序代码"
UI_DIR = "界面工程"
CODE_EXTS = {".bin", ".hex", ".lop100"}
UI_EXTS = {".pkg"}
UI_FOLDER_NAME = "private"


def detect_category(relative_path: str, is_dir: bool = False) -> tuple[str, str]:
    path = (relative_path or "").replace("\\", "/").strip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "other", "其他"

    first = parts[0]
    if first in (CODE_DIR, "code"):
        return "code", "程序代码"
    if first in (UI_DIR, "ui"):
        return "ui", "界面工程"

    # 界面工程文件夹：路径中任一目录名为 private
    if any(part.lower() == UI_FOLDER_NAME for part in parts):
        return "ui", "界面工程"

    name = parts[-1]
    suffix = Path(name).suffix.lower()
    if not is_dir:
        if suffix in CODE_EXTS:
            return "code", "程序代码"
        if suffix in UI_EXTS:
            return "ui", "界面工程"
    elif name.lower() == UI_FOLDER_NAME:
        return "ui", "界面工程"

    return "other", "其他"


def slugify(name: str) -> str:
    s = name.strip().lower().replace(" ", "-")
    s = SLUG_RE.sub("-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or len(s) < 2:
        from datetime import datetime

        s = f"p{int(datetime.utcnow().timestamp())}"
    return s


def version_dir(product: Product, version: Version) -> Path:
    path = STORAGE_ROOT / product.slug / version.name
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_join(base: Path, relative: str) -> Path:
    relative = relative.replace("\\", "/").lstrip("/")
    if ".." in Path(relative).parts:
        raise HTTPException(status_code=400, detail="非法路径")
    target = (base / relative).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="非法路径")
    return target


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def upsert_file_entry(
    db: Session,
    version_id: int,
    relative_path: str,
    is_dir: bool,
    size: int = 0,
    md5: str = "",
) -> FileEntry:
    relative_path = relative_path.replace("\\", "/").strip("/")
    entry = (
        db.query(FileEntry)
        .filter(FileEntry.version_id == version_id, FileEntry.relative_path == relative_path)
        .first()
    )
    if entry:
        entry.is_dir = 1 if is_dir else 0
        entry.size = size
        entry.md5 = md5
    else:
        entry = FileEntry(
            version_id=version_id,
            relative_path=relative_path,
            is_dir=1 if is_dir else 0,
            size=size,
            md5=md5,
        )
        db.add(entry)
    return entry


def ensure_parent_dirs(db: Session, version_id: int, relative_path: str) -> None:
    parts = Path(relative_path.replace("\\", "/")).parts
    acc = []
    for part in parts[:-1]:
        acc.append(part)
        upsert_file_entry(db, version_id, "/".join(acc), is_dir=True)


def rescan_version_files(db: Session, product: Product, version: Version) -> None:
    root = version_dir(product, version)
    db.query(FileEntry).filter(FileEntry.version_id == version.id).delete()
    if not root.exists():
        db.commit()
        return
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            upsert_file_entry(db, version.id, rel, is_dir=True)
        else:
            upsert_file_entry(
                db,
                version.id,
                rel,
                is_dir=False,
                size=path.stat().st_size,
                md5=md5_file(path),
            )
    db.commit()


def list_directory(product: Product, version: Version, sub_path: str = "") -> list[dict]:
    root = version_dir(product, version)
    current = safe_join(root, sub_path) if sub_path else root
    if not current.exists():
        return []
    if not current.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    items: list[dict] = []
    for child in sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = child.relative_to(root).as_posix()
        items.append(
            {
                "name": child.name,
                "path": rel,
                "is_dir": child.is_dir(),
                "size": 0 if child.is_dir() else child.stat().st_size,
                "md5": "",
            }
        )
    return items


async def save_upload_files(
    db: Session,
    product: Product,
    version: Version,
    files: list[UploadFile],
    relative_paths: list[str] | None = None,
) -> int:
    root = version_dir(product, version)
    count = 0
    for idx, upload in enumerate(files):
        rel = (
            relative_paths[idx]
            if relative_paths and idx < len(relative_paths) and relative_paths[idx]
            else upload.filename or f"file_{idx}"
        )
        rel = rel.replace("\\", "/").lstrip("/")
        if not rel or ".." in Path(rel).parts:
            raise HTTPException(status_code=400, detail=f"非法文件路径: {rel}")
        target = safe_join(root, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        ensure_parent_dirs(db, version.id, rel)
        upsert_file_entry(
            db,
            version.id,
            rel,
            is_dir=False,
            size=target.stat().st_size,
            md5=md5_file(target),
        )
        count += 1
    db.commit()
    return count


async def save_zip_upload(db: Session, product: Product, version: Version, upload: UploadFile) -> int:
    root = version_dir(product, version)
    data = await upload.read()
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if name.endswith("/") or info.is_dir():
                    dest = safe_join(root, name)
                    dest.mkdir(parents=True, exist_ok=True)
                    upsert_file_entry(db, version.id, name.strip("/"), is_dir=True)
                    continue
                if ".." in Path(name).parts:
                    raise HTTPException(status_code=400, detail=f"压缩包含非法路径: {name}")
                dest = safe_join(root, name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, dest.open("wb") as out:
                    shutil.copyfileobj(src, out)
                ensure_parent_dirs(db, version.id, name)
                upsert_file_entry(
                    db,
                    version.id,
                    name,
                    is_dir=False,
                    size=dest.stat().st_size,
                    md5=md5_file(dest),
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="无效的 zip 文件") from exc
    db.commit()
    return 1


def build_selected_zip(product: Product, version: Version, paths: list[str]) -> BytesIO:
    root = version_dir(product, version)
    if not paths:
        raise HTTPException(status_code=400, detail="请先勾选文件或文件夹")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw in paths:
            rel = raw.replace("\\", "/").strip("/")
            target = safe_join(root, rel)
            if not target.exists():
                raise HTTPException(status_code=404, detail=f"不存在: {rel}")
            if target.is_file():
                zf.write(target, arcname=rel)
            else:
                for file_path in target.rglob("*"):
                    if file_path.is_file():
                        arc = file_path.relative_to(root).as_posix()
                        zf.write(file_path, arcname=arc)
    buf.seek(0)
    return buf


def build_version_zip(product: Product, version: Version) -> BytesIO:
    root = version_dir(product, version)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if root.exists():
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, arcname=file_path.relative_to(root).as_posix())
    buf.seek(0)
    return buf


def count_files(db: Session, version_id: int) -> int:
    return (
        db.query(FileEntry)
        .filter(FileEntry.version_id == version_id, FileEntry.is_dir == 0)
        .count()
    )


def delete_version_storage(product: Product, version: Version) -> None:
    root = STORAGE_ROOT / product.slug / version.name
    if root.exists():
        shutil.rmtree(root)


def rename_version_storage(product: Product, old_name: str, new_name: str) -> None:
    old_root = STORAGE_ROOT / product.slug / old_name
    new_root = STORAGE_ROOT / product.slug / new_name
    if old_root.exists():
        if new_root.exists():
            raise HTTPException(status_code=400, detail="目标版本目录已存在")
        old_root.rename(new_root)


def delete_product_storage(product: Product) -> None:
    root = STORAGE_ROOT / product.slug
    if root.exists():
        shutil.rmtree(root)


def delete_paths(db: Session, product: Product, version: Version, paths: list[str]) -> int:
    root = version_dir(product, version)
    deleted = 0
    for raw in paths:
        rel = raw.replace("\\", "/").strip("/")
        if not rel:
            raise HTTPException(status_code=400, detail="不能删除版本根目录")
        target = safe_join(root, rel)
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"不存在: {rel}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        db.query(FileEntry).filter(
            FileEntry.version_id == version.id,
            (
                (FileEntry.relative_path == rel)
                | (FileEntry.relative_path.like(f"{rel}/%"))
            ),
        ).delete(synchronize_session=False)
        deleted += 1
    db.commit()
    return deleted

