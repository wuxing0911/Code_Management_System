from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_name: str = "项目代码版本管理系统"
    secret_key: str = "dev-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
    storage_root: str = str(DATA_DIR / "releases")
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2GB
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    class Config:
        env_prefix = "VMS_"


settings = Settings()

STORAGE_ROOT = Path(settings.storage_root).resolve()
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
