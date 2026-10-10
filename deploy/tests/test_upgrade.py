import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


DEPLOY = Path(__file__).resolve().parents[1]


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vms-upgrade-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.deploy = self.root / "deploy"
        self.deploy.mkdir()
        (self.root / "data" / "releases").mkdir(parents=True)
        (self.root / "data" / "app.db").write_text("database-before-upgrade")
        (self.root / "data" / "releases" / "firmware.bin").write_bytes(b"release-file")
        self.env_file = self.deploy / ".env.registry"
        self.env_file.write_text("DOCKERHUB_USERNAME=testuser\nVMS_VERSION=v1.0.0\nVMS_SECRET_KEY='test-only'\n")
        shutil.copy2(DEPLOY / "upgrade.sh", self.deploy)
        shutil.copy2(DEPLOY / "docker-compose.registry.yml", self.deploy)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        shutil.copy2(DEPLOY / "tests" / "fixtures" / "docker", self.bin)
        (self.bin / "flock").write_text('#!/bin/sh\nexit "${FAKE_LOCK_RESULT:-0}"\n')
        (self.bin / "tar").write_text(
            '#!/bin/sh\n[ "${FAKE_FAIL:-}" != backup ] || exit 1\nexec "$FAKE_REAL_TAR" "$@"\n'
        )
        for command in self.bin.iterdir():
            command.chmod(0o755)
        self.events_file = self.root / "events.jsonl"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_EVENTS": str(self.events_file),
            "FAKE_DATA_DIR": str(self.root / "data"),
            "FAKE_REAL_TAR": shutil.which("tar"),
        }
        # A user's shell must not influence the isolated mock test.
        self.env.pop("BASH_ENV", None)

    def run_upgrade(self, version="v1.1.0", **extra_env):
        return subprocess.run(
            ["bash", str(self.deploy / "upgrade.sh"), version],
            env={**self.env, **extra_env},
            capture_output=True,
            text=True,
        )

    def events(self):
        if not self.events_file.exists():
            return []
        return [json.loads(line) for line in self.events_file.read_text().splitlines()]

    def operations(self):
        return [
            next(arg for arg in event if arg in {"config", "ps", "pull", "stop", "up"})
            for event in self.events() if event[0] == "compose"
        ]

    def test_success_backs_up_data_and_records_version(self):
        result = self.run_upgrade()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(self.operations().index("pull"), self.operations().index("stop"))
        backup = next((self.root / "backups").iterdir())
        with tarfile.open(backup / "data.tar.gz") as archive:
            self.assertEqual(archive.extractfile("data/app.db").read(), b"database-before-upgrade")
            self.assertEqual(archive.extractfile("data/releases/firmware.bin").read(), b"release-file")
        self.assertIn("VMS_VERSION=v1.1.0", self.env_file.read_text())
        self.assertIn("VMS_VERSION=v1.0.0", (backup / ".env.registry").read_text())
        self.assertIn("vms-local-rollback/backend:", (backup / "rollback.compose.yml").read_text())
        self.assertEqual(self.env_file.stat().st_mode & 0o777, 0o600)
        up = next(event for event in self.events() if "up" in event)
        self.assertIn("--wait", up)
        self.assertIn("never", up)
        self.assertFalse(any("build" in event or "down" in event for event in self.events()))

    def test_pull_failure_does_not_stop_old_service(self):
        result = self.run_upgrade(FAKE_FAIL="pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("stop", self.operations())
        self.assertNotIn("up", self.operations())
        self.assertIn("VMS_VERSION=v1.0.0", self.env_file.read_text())

    def test_backup_failure_restarts_original_containers(self):
        result = self.run_upgrade(FAKE_FAIL="backup")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(["start", "old-backend", "old-frontend"], self.events())
        self.assertNotIn("up", self.operations())

    def test_failed_health_check_stops_new_service_without_restoring_data(self):
        result = self.run_upgrade(FAKE_FAIL="up")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.operations().count("stop"), 2)
        self.assertNotIn(["start", "old-backend", "old-frontend"], self.events())
        self.assertIn("VMS_VERSION=v1.0.0", self.env_file.read_text())
        self.assertEqual((self.root / "data" / "app.db").read_text(), "database-before-upgrade")

    def test_wrong_mount_is_rejected_before_pulling(self):
        self.assertNotEqual(self.run_upgrade(FAKE_FAIL="mount").returncode, 0)
        self.assertNotIn("pull", self.operations())
        self.assertNotIn("stop", self.operations())

    def test_lock_prevents_parallel_upgrade(self):
        self.assertNotEqual(self.run_upgrade(FAKE_LOCK_RESULT="1").returncode, 0)
        self.assertNotIn("pull", self.operations())

    def test_invalid_version_does_not_access_docker(self):
        for version in ("latest", "v1.0.0;touch-file", "../v1.0.0", "v1.0"):
            with self.subTest(version=version):
                self.assertNotEqual(self.run_upgrade(version).returncode, 0)
        self.assertEqual(self.events(), [])


if __name__ == "__main__":
    unittest.main()
