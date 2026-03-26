"""GitHub App JWT and installation access token."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import jwt


def _load_private_key() -> str:
    raw = os.environ.get("GITHUB_APP_PRIVATE_KEY", "").strip()
    if not raw:
        raise RuntimeError("GITHUB_APP_PRIVATE_KEY is not set")
    if "BEGIN" not in raw:
        raw = raw.replace("\\n", "\n")
    return raw


def create_app_jwt(app_id: str) -> str:
    now = int(time.time())
    private_key = _load_private_key()
    payload = {"iat": now - 60, "exp": now + 600, "iss": int(app_id, 10)}
    encoded = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded if isinstance(encoded, str) else encoded.decode("ascii")


def get_installation_access_token(installation_id: int) -> str:
    app_id = os.environ.get("GITHUB_APP_ID", "").strip()
    if not app_id:
        raise RuntimeError("GITHUB_APP_ID is not set")
    jwt_token = create_app_jwt(app_id)
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/')}/app/installations/{installation_id}/access_tokens"
    body = b"{}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {jwt_token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"installation token HTTP {e.code}: {err[:2000]}") from e
    token = data.get("token")
    if not token:
        raise RuntimeError(f"no token in response: {data!r}")
    return token
