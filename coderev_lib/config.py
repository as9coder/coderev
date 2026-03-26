"""Resolve env with short aliases. GitHub + OpenRouter need a handful of values — this keeps names short."""
from __future__ import annotations

import os
from pathlib import Path

# Repo root (…/coderev)
REPO_ROOT = Path(__file__).resolve().parent.parent


def _first(*names: str) -> str:
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return ""


def app_id() -> str:
    v = _first("APP_ID", "GITHUB_APP_ID")
    if not v:
        raise RuntimeError("Set APP_ID (GitHub App → About → App ID)")
    return v


def private_key_pem() -> str:
    path = _first("PRIVATE_KEY_FILE", "GITHUB_APP_PRIVATE_KEY_FILE")
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.is_file():
            raise RuntimeError(f"Private key file not found: {p}")
        raw = p.read_text(encoding="utf-8").strip()
    else:
        raw = _first("PRIVATE_KEY", "GITHUB_APP_PRIVATE_KEY")
    if not raw:
        raise RuntimeError(
            "Set PRIVATE_KEY_FILE=./github-app.pem (recommended) or PRIVATE_KEY with PEM text"
        )
    if "BEGIN" not in raw:
        raw = raw.replace("\\n", "\n")
    return raw


def webhook_secret() -> str:
    v = _first("WEBHOOK_SECRET", "GITHUB_WEBHOOK_SECRET")
    if not v:
        raise RuntimeError("Set WEBHOOK_SECRET (same as GitHub App webhook secret)")
    return v


def openrouter_key() -> str:
    v = _first("OPENROUTER_KEY", "OPENROUTER_API_KEY")
    if not v:
        raise RuntimeError("Set OPENROUTER_KEY")
    return v


def allowed_user() -> str:
    v = _first("ALLOWED_USER", "CODEREV_ALLOWED_USER")
    if not v:
        raise RuntimeError("Set ALLOWED_USER (your GitHub username)")
    return v


def model() -> str:
    return _first("MODEL") or "minimax/minimax-m2.7"
