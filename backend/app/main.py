from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, products, users, versions
from app.auth import hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(versions.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.default_admin_username).first()
        if not admin:
            db.add(
                User(
                    username=settings.default_admin_username,
                    password_hash=hash_password(settings.default_admin_password),
                    role="admin",
                    is_active=1,
                )
            )
            # seed demo roles for local preview
            if not db.query(User).filter(User.username == "dev").first():
                db.add(
                    User(
                        username="dev",
                        password_hash=hash_password("dev123"),
                        role="developer",
                        is_active=1,
                    )
                )
            if not db.query(User).filter(User.username == "tester").first():
                db.add(
                    User(
                        username="tester",
                        password_hash=hash_password("tester123"),
                        role="tester",
                        is_active=1,
                    )
                )
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
