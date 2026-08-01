from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["admin", "developer", "tester"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    role: Role = "tester"
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=4)


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=4)


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: str = ""


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    created_at: datetime
    version_count: int = 0

    class Config:
        from_attributes = True


class VersionCreate(BaseModel):
    name: str
    note: str = ""


class VersionUpdate(BaseModel):
    name: str | None = None
    note: str | None = None


class VersionOut(BaseModel):
    id: int
    product_id: int
    name: str
    note: str
    status: str
    uploader_id: int | None
    uploader_name: str | None = None
    created_at: datetime
    updated_at: datetime
    file_count: int = 0

    class Config:
        from_attributes = True


class FileNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int = 0
    md5: str = ""
    file_id: int | None = None
    category: str = "other"  # code | ui | other
    category_label: str = "其他"


class DownloadSelectedRequest(BaseModel):
    paths: list[str]


class DeleteSelectedRequest(BaseModel):
    paths: list[str]
