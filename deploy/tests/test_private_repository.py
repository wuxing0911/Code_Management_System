import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError


spec = importlib.util.spec_from_file_location(
    "private_repository", Path(__file__).resolve().parents[1] / "check-private-repository.py"
)
private_repository = importlib.util.module_from_spec(spec)
spec.loader.exec_module(private_repository)


class PrivateRepositoryTests(unittest.TestCase):
    def opener(self, repository_info):
        self.requests = []

        def open_request(request, timeout):
            self.requests.append(request)
            self.assertEqual(timeout, 30)
            body = {"access_token": "test-access-token"} if len(self.requests) == 1 else repository_info
            return io.StringIO(json.dumps(body))

        return open_request

    def test_private_repository_is_allowed(self):
        private_repository.verify_private_repository(
            "testuser", "test-pat", opener=self.opener({"is_private": True})
        )
        self.assertEqual(self.requests[0].full_url, "https://hub.docker.com/v2/auth/token")
        self.assertEqual(json.loads(self.requests[0].data), {"identifier": "testuser", "secret": "test-pat"})
        self.assertEqual(self.requests[1].full_url, "https://hub.docker.com/v2/namespaces/testuser/repositories/vms")
        self.assertEqual(self.requests[1].get_header("Authorization"), "Bearer test-access-token")

    def test_public_or_unknown_visibility_is_blocked(self):
        for info in ({"is_private": False}, {}, {"is_private": "true"}):
            with self.subTest(info=info), self.assertRaisesRegex(ValueError, "must be Private"):
                private_repository.verify_private_repository("testuser", "test-pat", opener=self.opener(info))

    def test_missing_repository_is_not_created(self):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            if len(requests) == 1:
                return io.StringIO('{"access_token":"test-token"}')
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)

        with self.assertRaises(HTTPError) as raised:
            private_repository.verify_private_repository("testuser", "test-pat", opener=opener)
        raised.exception.close()
        self.assertEqual([request.get_method() for request in requests], ["POST", "GET"])

    def test_invalid_settings_fail_before_network(self):
        for username, secret, repository in (
            ("", "test-pat", "vms"),
            ("testuser", "", "vms"),
            ("testuser", "test-pat", "../public"),
        ):
            with self.subTest(username=username, repository=repository), self.assertRaises(ValueError):
                private_repository.verify_private_repository(username, secret, repository)


if __name__ == "__main__":
    unittest.main()
