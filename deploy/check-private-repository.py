"""Fail closed before publishing: never create a repository or change visibility."""

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(path, *, payload=None, token=None, opener=None):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://hub.docker.com{path}", data=data, headers=headers)
    with (opener or urlopen)(request, timeout=30) as response:
        return json.load(response)


def verify_private_repository(username, secret, repository="vms", *, opener=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", username):
        raise ValueError("Set DOCKERHUB_USERNAME to your lowercase Docker Hub username.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", repository):
        raise ValueError("DOCKERHUB_REPOSITORY must be a single repository name.")
    if not secret:
        raise ValueError("Configure the DOCKERHUB_TOKEN GitHub Actions secret.")
    login = request_json(
        "/v2/auth/token",
        payload={"identifier": username, "secret": secret},
        opener=opener,
    )
    token = login.get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Docker Hub did not return an access token.")
    info = request_json(
        f"/v2/namespaces/{username}/repositories/{repository}",
        token=token,
        opener=opener,
    )
    if info.get("is_private") is not True:
        raise ValueError("Publication blocked: the existing repository must be Private.")


def main():
    try:
        verify_private_repository(
            os.environ.get("DOCKERHUB_USERNAME", ""),
            os.environ.get("DOCKERHUB_TOKEN", ""),
            os.environ.get("DOCKERHUB_REPOSITORY", "vms"),
        )
    except HTTPError as exc:
        # Do not print response bodies, request headers, or credentials.
        print(
            f"Private-repository check failed (HTTP {exc.code}). Check the PAT and "
            "create the repository as Private before publishing.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, URLError, OSError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else "Cannot reach Docker Hub API."
        print(message, file=sys.stderr)
        return 1
    print("Private repository verified; publication is allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
