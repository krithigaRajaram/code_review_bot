import hmac
import hashlib
import os
from fastapi import APIRouter, Request, HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def verify_signature(payload_bytes: bytes, signature: str) -> bool:
    """HMAC-SHA256 verification — ensures request is from GitHub."""
    if not signature or not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    payload_bytes = await request.body()

    # Step 1: Verify it's from GitHub
    if not verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Step 2: Only care about PR events
    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    payload = await request.json()
    action = payload.get("action")

    # Step 3: Only on PR open or new commits pushed
    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "action": action}

    pr_number = payload["pull_request"]["number"]
    repo_full_name = payload["repository"]["full_name"]  # e.g. "user/repo"

    print(f"[PR #{pr_number}] New PR event on {repo_full_name}")

    # Phase 4 will enqueue a Celery task here
    return {"status": "received", "pr": pr_number, "repo": repo_full_name}