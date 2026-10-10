"""User API regression tests against isolated in-memory SQLite, without a server."""

import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Set these before importing application settings; never open the real app DB.
os.environ["VMS_DATABASE_URL"] = "sqlite://"
os.environ["VMS_STORAGE_ROOT"] = tempfile.gettempdir()
os.environ["VMS_SECRET_KEY"] = "isolated-user-api-test-secret"

from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth, users
from app.auth import create_access_token, hash_password
from app.config import settings
from app.database import Base, get_db
from app.models import FileEntry, Product, User, UserPermission, Version


class UserApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password("test-password")

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.app = FastAPI()
        self.app.include_router(auth.router, prefix="/api")
        self.app.include_router(users.router, prefix="/api")

        def test_db():
            yield self.db

        self.app.dependency_overrides[get_db] = test_db
        self.admin = self.add_user(settings.default_admin_username, "admin")
        self.tester = self.add_user("tester-account", "tester")

    def add_user(self, username, role="tester", *, manage_users=False):
        user = User(username=username, password_hash=self.password_hash, role=role, is_active=1)
        self.db.add(user)
        self.db.flush()
        if manage_users:
            self.db.add(UserPermission(user_id=user.id, permission="manage_users", allowed=True))
        self.db.commit()
        return user

    def request(self, method, path, *, user=None, token=None, body=None, form=None):
        if user is not None:
            token = create_access_token(user)
        headers = []
        if token is not None:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        payload = b""
        if body is not None:
            headers.append((b"content-type", b"application/json"))
            payload = json.dumps(body).encode()
        if form is not None:
            from urllib.parse import urlencode

            headers.append((b"content-type", b"application/x-www-form-urlencoded"))
            payload = urlencode(form).encode()
        messages = []

        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(
            self.app(
                {
                    "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                    "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                    "root_path": "", "query_string": b"", "headers": headers,
                    "client": ("127.0.0.1", 1234), "server": ("test", 80),
                },
                receive,
                send,
            )
        )
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return status, json.loads(content) if content else None

    def test_delete_user_cleans_permissions_but_preserves_versions_and_files(self):
        target = self.add_user("removable", "developer", manage_users=True)
        target_id = target.id
        product = Product(name="Test product", slug="test-product")
        version = Version(name="v1", product=product, uploader=target)
        file = FileEntry(version=version, relative_path="firmware.bin", size=4)
        self.db.add_all([product, version, file])
        self.db.commit()
        version_id, file_id = version.id, file.id
        with tempfile.TemporaryDirectory(prefix="vms-user-delete-test-") as directory:
            disk_file = Path(directory) / "firmware.bin"
            disk_file.write_bytes(b"test")
            status, body = self.request("DELETE", f"/api/users/{target_id}", user=self.admin)
            self.assertEqual((status, body), (204, None))
            self.assertEqual(disk_file.read_bytes(), b"test")
        self.db.expire_all()
        self.assertIsNone(self.db.get(User, target_id))
        self.assertEqual(self.db.query(UserPermission).filter_by(user_id=target_id).count(), 0)
        self.assertIsNone(self.db.get(Version, version_id).uploader_id)
        self.assertIsNotNone(self.db.get(FileEntry, file_id))
        self.assertIsNotNone(self.db.get(Product, product.id))

    def test_cannot_delete_self(self):
        status, body = self.request("DELETE", f"/api/users/{self.admin.id}", user=self.admin)
        self.assertEqual(status, 400)
        self.assertIn("当前登录账号", body["detail"])
        self.assertIsNotNone(self.db.get(User, self.admin.id))

    def test_requires_permission(self):
        target = self.add_user("other-account")
        self.assertEqual(self.request("DELETE", f"/api/users/{target.id}", user=self.tester)[0], 403)
        self.assertEqual(self.request("DELETE", f"/api/users/{target.id}")[0], 401)
        self.assertIsNotNone(self.db.get(User, target.id))

    def test_explicit_user_management_permission_allows_deletion(self):
        manager = self.add_user("delegated-manager", "developer", manage_users=True)
        self.assertEqual(self.request("DELETE", f"/api/users/{self.tester.id}", user=manager)[0], 204)

    def test_initial_administrator_is_protected(self):
        manager = self.add_user("delegated-manager", "developer", manage_users=True)
        status, body = self.request("DELETE", f"/api/users/{self.admin.id}", user=manager)
        self.assertEqual(status, 400)
        self.assertIn("系统初始管理员", body["detail"])

    def test_last_active_administrator_is_protected(self):
        self.admin.is_active = 0
        target = self.add_user("last-admin", "admin")
        manager = self.add_user("delegated-manager", "developer", manage_users=True)
        status, body = self.request("DELETE", f"/api/users/{target.id}", user=manager)
        self.assertEqual(status, 400)
        self.assertIn("最后一个", body["detail"])

    def test_missing_user_returns_not_found(self):
        self.assertEqual(self.request("DELETE", "/api/users/99999", user=self.admin)[0], 404)

    def test_deleted_token_stays_invalid_after_username_and_id_reuse(self):
        target = self.add_user("reused-account")
        old_id = target.id
        old_token = create_access_token(target)
        self.assertEqual(self.request("DELETE", f"/api/users/{old_id}", user=self.admin)[0], 204)
        self.assertEqual(self.request("GET", "/api/auth/me", token=old_token)[0], 401)
        status, replacement = self.request(
            "POST", "/api/users", user=self.admin,
            body={"username": "reused-account", "password": "test-password", "role": "admin"},
        )
        self.assertEqual(status, 200)
        # SQLite may recycle the highest deleted primary key: even that must not
        # revive the previous account's token, including with the same password.
        self.assertEqual(replacement["id"], old_id)
        self.assertEqual(self.request("GET", "/api/auth/me", token=old_token)[0], 401)

    def test_reset_password_invalidates_previous_token(self):
        token = create_access_token(self.tester)
        status, _ = self.request(
            "PATCH", f"/api/users/{self.tester.id}", user=self.admin, body={"password": "new-password"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.request("GET", "/api/auth/me", token=token)[0], 401)

    def test_legacy_token_requires_fresh_login(self):
        token = jwt.encode(
            {"sub": self.admin.username, "exp": datetime.utcnow() + timedelta(hours=1)},
            settings.secret_key, algorithm=settings.algorithm,
        )
        self.assertEqual(self.request("GET", "/api/auth/me", token=token)[0], 401)

    def test_invalid_credential_claim_is_rejected_without_server_error(self):
        for credential in (None, [], "不是有效凭据"):
            with self.subTest(credential=credential):
                token = jwt.encode(
                    {
                        "sub": self.admin.username, "uid": self.admin.id, "credential": credential,
                        "exp": datetime.utcnow() + timedelta(hours=1),
                    },
                    settings.secret_key, algorithm=settings.algorithm,
                )
                self.assertEqual(self.request("GET", "/api/auth/me", token=token)[0], 401)

    def test_json_and_form_login_issue_working_tokens(self):
        for keyword in ("body", "form"):
            with self.subTest(keyword=keyword):
                path = "/api/auth/login-json" if keyword == "body" else "/api/auth/login"
                status, body = self.request(
                    "POST", path, **{keyword: {"username": self.admin.username, "password": "test-password"}}
                )
                self.assertEqual(status, 200)
                status, account = self.request("GET", "/api/auth/me", token=body["access_token"])
                self.assertEqual(status, 200)
                self.assertEqual(account["id"], self.admin.id)


if __name__ == "__main__":
    unittest.main()
