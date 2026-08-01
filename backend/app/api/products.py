from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Product, User, Version
from app.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services import storage
from app.services.storage import slugify

router = APIRouter(prefix="/products", tags=["products"])


def to_product_out(db: Session, p: Product) -> ProductOut:
    count = db.query(Version).filter(Version.product_id == p.id).count()
    return ProductOut(
        id=p.id,
        name=p.name,
        slug=p.slug,
        description=p.description or "",
        created_at=p.created_at,
        version_count=count,
    )


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Product)
    if q:
        like = f"%{q}%"
        query = query.filter(Product.name.ilike(like))
    products = query.order_by(Product.created_at.desc()).all()
    return [to_product_out(db, p) for p in products]


@router.post("", response_model=ProductOut)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="产品名称不能为空")
    if db.query(Product).filter(Product.name == name).first():
        raise HTTPException(status_code=400, detail="产品名称已存在")
    base_slug = slugify(name)
    slug = base_slug
    i = 1
    while db.query(Product).filter(Product.slug == slug).first():
        slug = f"{base_slug}-{i}"
        i += 1
    product = Product(name=name, slug=slug, description=body.description or "")
    db.add(product)
    db.commit()
    db.refresh(product)
    return to_product_out(db, product)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return to_product_out(db, product)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if body.name is not None:
        name = body.name.strip()
        exists = db.query(Product).filter(Product.name == name, Product.id != product_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="产品名称已存在")
        product.name = name
    if body.description is not None:
        product.description = body.description
    db.commit()
    db.refresh(product)
    return to_product_out(db, product)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "developer")),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    storage.delete_product_storage(product)
    db.delete(product)
    db.commit()
