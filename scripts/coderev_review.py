#!/usr/bin/env python3
"""
GitHub Actions entrypoint: PR comments containing @coderev.
Requires PYTHONPATH to include repo root (parent of coderev_lib).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/coderev_review.py` from repo root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from coderev_lib.core import run_review_from_issue_comment_event  # noqa: E402


def getenv_required(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing required env: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def main() -> None:
    event_path = getenv_required("GITHUB_EVENT_PATH")
    token = getenv_required("GITHUB_TOKEN")
    api_key = getenv_required("OPENROUTER_API_KEY")
    model = os.environ.get("MODEL", "minimax/minimax-m2.7").strip()
    allowed = getenv_required("CODEREV_ALLOWED_USER")

    with open(event_path, encoding="utf-8") as f:
        event: dict[str, Any] = json.load(f)

    repo = (os.environ.get("TARGET_REPOSITORY") or "").strip() or getenv_required(
        "GITHUB_REPOSITORY"
    )

    result = run_review_from_issue_comment_event(
        event,
        token=token,
        repo_full_name=repo,
        openrouter_api_key=api_key,
        allowed_user=allowed,
        model=model,
    )

    if result["status"] == "error":
        print(result.get("message", result), file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
