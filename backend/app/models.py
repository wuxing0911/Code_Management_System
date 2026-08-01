from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="tester")  # admin/developer/tester
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    versions = relationship("Version", back_populates="uploader")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    versions = relationship("Version", back_populates="product", cascade="all, delete-orphan")


class Version(Base):
    __tablename__ = "versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="available")
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="versions")
    uploader = relationship("User", back_populates="versions")
    files = relationship("FileEntry", back_populates="version", cascade="all, delete-orphan")


class FileEntry(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id"), index=True)
    relative_path: Mapped[str] = mapped_column(String(1024), index=True)
    is_dir: Mapped[int] = mapped_column(Integer, default=0)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    md5: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    version = relationship("Version", back_populates="files")
