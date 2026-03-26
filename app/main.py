"""
GitHub App webhook: install the app on any repo, comment @coderev on a PR.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from coderev_lib import config
from coderev_lib.core import run_review_from_issue_comment_event
from coderev_lib.github_app_auth import get_installation_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coderev")

app = FastAPI(title="CodeRev", version="1.0.0")


def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    try:
        secret = config.webhook_secret()
    except RuntimeError:
        return False
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
        try:
            allowed = config.allowed_user()
            api_key = config.openrouter_key()
            model = config.model()
        except RuntimeError as e:
            logger.error("%s", e)
            return

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
