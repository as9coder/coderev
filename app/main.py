"""
GitHub App webhook: install the app on any repo, comment @coderev on a PR.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from coderev_lib.core import run_review_from_issue_comment_event
from coderev_lib.github_app_auth import get_installation_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coderev")

app = FastAPI(title="CodeRev", version="1.0.0")


def _webhook_secret() -> str:
    s = os.environ.get("GITHUB_WEBHOOK_SECRET", "").strip()
    if not s:
        raise RuntimeError("GITHUB_WEBHOOK_SECRET is not set")
    return s


def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    secret = _webhook_secret()
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _process_issue_comment(payload: dict[str, Any]) -> None:
    try:
        installation = payload.get("installation") or {}
        iid = installation.get("id")
        if not iid:
            logger.warning("issue_comment: no installation id")
            return

        repo = (payload.get("repository") or {}).get("full_name")
        if not repo:
            logger.warning("issue_comment: no repository.full_name")
            return

        token = get_installation_access_token(int(iid))
        allowed = os.environ.get("CODEREV_ALLOWED_USER", "").strip()
        if not allowed:
            logger.error("CODEREV_ALLOWED_USER is not set")
            return

        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            logger.error("OPENROUTER_API_KEY is not set")
            return

        model = os.environ.get("MODEL", "minimax/minimax-m2.7").strip()

        result = run_review_from_issue_comment_event(
            payload,
            token=token,
            repo_full_name=repo,
            openrouter_api_key=api_key,
            allowed_user=allowed,
            model=model,
        )

        if result["status"] == "skipped":
            logger.info("skipped: %s", result.get("reason"))
        elif result["status"] == "posted":
            logger.info("posted review on %s PR #%s", result.get("repo"), result.get("pr"))
        else:
            logger.error("error: %s", result.get("message"))
    except Exception:
        logger.exception("process issue_comment failed")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    delivery = request.headers.get("X-GitHub-Delivery", "")

    if event == "ping":
        logger.info("ping delivery=%s", delivery)
        return PlainTextResponse("pong", status_code=200)

    if event != "issue_comment":
        return Response(status_code=204)

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="bad json")

    if payload.get("action") != "created":
        return Response(status_code=204)

    background_tasks.add_task(_process_issue_comment, payload)
    return Response(status_code=202)
