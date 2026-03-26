"""PR review: fetch diff, OpenRouter, post GitHub review."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_DIFF_CHARS = 120_000


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
    req = urllib.request.Request(OPENROUTER_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "https://github.com")
    req.add_header("X-Title", "coderev")
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = json.loads(resp.read().decode())
    choices = raw.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter: empty choices: {json.dumps(raw)[:2000]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not content:
        raise RuntimeError("OpenRouter: no message content")
    return content.strip()


def run_review_from_issue_comment_event(
    event: dict[str, Any],
    *,
    token: str,
    repo_full_name: str,
    openrouter_api_key: str,
    allowed_user: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Process a GitHub issue_comment webhook payload (action=created).
    Returns { "status": "skipped"|"posted"|"error", ... }.
    """
    model = (model or os.environ.get("MODEL") or "minimax/minimax-m2.7").strip()
    allowed = allowed_user.strip().lower()

    comment = event.get("comment") or {}
    if comment.get("user", {}).get("type") == "Bot":
        return {"status": "skipped", "reason": "comment from bot"}

    actor = (comment.get("user") or {}).get("login") or ""
    if actor.lower() != allowed:
        return {"status": "skipped", "reason": f"actor {actor!r} != allowed {allowed!r}"}

    body = comment.get("body") or ""
    if "@coderev" not in body:
        return {"status": "skipped", "reason": "no @coderev mention"}

    issue = event.get("issue") or {}
    if not issue.get("pull_request"):
        return {"status": "skipped", "reason": "not a pull request"}

    owner, repo_name = repo_full_name.split("/", 1)
    pr_number = int(issue["number"])

    status, diff_body = github_api(
        "GET",
        f"/repos/{owner}/{repo_name}/pulls/{pr_number}",
        token,
        accept="application/vnd.github.diff",
    )
    if status != 200:
        return {
            "status": "error",
            "message": f"fetch diff HTTP {status}: {diff_body[:500]!r}",
        }

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

    review_body = openrouter_chat(openrouter_api_key, model, system, user_prompt)

    payload = {"body": review_body, "event": "COMMENT"}
    st, out = github_api(
        "POST",
        f"/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
        token,
        data=payload,
    )
    if st not in (200, 201):
        return {
            "status": "error",
            "message": f"post review HTTP {st}: {out.decode(errors='replace')[:2000]}",
        }

    return {"status": "posted", "repo": repo_full_name, "pr": pr_number}

