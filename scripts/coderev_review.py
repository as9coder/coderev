#!/usr/bin/env python3
"""
Triggered from GitHub Actions on PR comments containing @coderev.
Fetches the PR diff, calls OpenRouter, posts a pull request review.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_DIFF_CHARS = 120_000


def getenv_required(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        print(f"Missing required env: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def github_api(
    method: str,
    path: str,
    token: str,
    *,
    accept: str = "application/vnd.github+json",
    data: dict[str, Any] | None = None,
) -> tuple[int, bytes]:
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    url = f"{base}{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def openrouter_chat(api_key: str, model: str, system: str, user: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    # OpenRouter recommends optional headers for rankings; harmless if ignored
    req.add_header("HTTP-Referer", "https://github.com")
    req.add_header("X-Title", "coderev")
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = json.loads(resp.read().decode())
    choices = raw.get("choices") or []
    if not choices:
        print(json.dumps(raw, indent=2)[:4000], file=sys.stderr)
        sys.exit("OpenRouter: empty choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not content:
        sys.exit("OpenRouter: no message content")
    return content.strip()


def main() -> None:
    event_path = getenv_required("GITHUB_EVENT_PATH")
    token = getenv_required("GITHUB_TOKEN")
    api_key = getenv_required("OPENROUTER_API_KEY")
    model = os.environ.get("MODEL", "minimax/minimax-m2.7").strip()
    allowed = getenv_required("CODEREV_ALLOWED_USER").lower()

    with open(event_path, encoding="utf-8") as f:
        event: dict[str, Any] = json.load(f)

    actor = (event.get("comment") or {}).get("user") or {}
    login = (actor.get("login") or "").lower()
    if login != allowed:
        print(f"Skip: actor {login!r} is not allowed user {allowed!r}", file=sys.stderr)
        sys.exit(0)

    issue = event.get("issue") or {}
    if not issue.get("pull_request"):
        print("Skip: comment is not on a pull request", file=sys.stderr)
        sys.exit(0)

    # Reusable workflows set TARGET_REPOSITORY to the repo that has the PR;
    # GITHUB_REPOSITORY would otherwise point at the workflow definition repo.
    repo = (os.environ.get("TARGET_REPOSITORY") or "").strip() or getenv_required(
        "GITHUB_REPOSITORY"
    )
    owner, repo_name = repo.split("/", 1)
    pr_number = int(issue["number"])

    status, diff_body = github_api(
        "GET",
        f"/repos/{owner}/{repo_name}/pulls/{pr_number}",
        token,
        accept="application/vnd.github.diff",
    )
    if status != 200:
        print(f"Failed to fetch diff: HTTP {status} {diff_body[:500]!r}", file=sys.stderr)
        sys.exit(1)

    truncated = False
    diff_text = diff_body.decode("utf-8", errors="replace")
    if len(diff_text) > MAX_DIFF_CHARS:
        truncated = True
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n\n[… diff truncated for size …]\n"

    pr_title = issue.get("title") or "(no title)"

    system = """You are a senior security and code reviewer. Analyze the unified diff only.
Report: correctness bugs, security (injection, authz, secrets, crypto), race conditions, error handling,
performance pitfalls, and test gaps. Ignore pure formatting unless it hides a bug.
Be concise: use markdown with ### sections and bullet lists. Cite file paths from the diff.
If the diff is insufficient for a claim, say so. Do not claim certainty without evidence."""

    user_prompt = f"""Pull request: {pr_title}

Unified diff:
```diff
{diff_text}
```
"""

    if truncated:
        user_prompt += "\n(Note: diff was truncated; mention if coverage may be incomplete.)\n"

    review_body = openrouter_chat(api_key, model, system, user_prompt)

    # Post as a PR review (shows in the review UI)
    payload = {
        "body": review_body,
        "event": "COMMENT",
    }
    st, out = github_api(
        "POST",
        f"/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
        token,
        data=payload,
    )
    if st not in (200, 201):
        print(f"Failed to post review: HTTP {st} {out.decode(errors='replace')[:2000]}", file=sys.stderr)
        sys.exit(1)

    print("Posted pull request review.")


if __name__ == "__main__":
    main()
