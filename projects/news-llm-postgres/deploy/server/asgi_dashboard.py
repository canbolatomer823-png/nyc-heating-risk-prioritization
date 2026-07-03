from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = Path(os.environ.get("NEWS_DASHBOARD_HTML", BASE_DIR / "dashboard.html"))
SERVICE_NAME = os.environ.get("NEWS_SERVICE_NAME", "omer-news-dashboard")
DEPLOY_MODE = os.environ.get("NEWS_DEPLOY_MODE", "apache_reverse_proxy_uvicorn")
PUBLIC_BASE_URL = os.environ.get("NEWS_PUBLIC_BASE_URL", "")
PROXY_PATH = os.environ.get("NEWS_PROXY_PATH", "/omer-news-dashboard-live/")
LOCAL_BIND = os.environ.get("NEWS_LOCAL_BIND", "127.0.0.1:8011")
GIT_REV = os.environ.get("NEWS_GIT_REV", "unknown")
STARTED_AT = datetime.now(timezone.utc)


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    if path in {"/", "/dashboard", "/dashboard.html"}:
        await send_file(send, DASHBOARD_PATH, "text/html; charset=utf-8")
        return

    if path == "/health":
        await send_response(send, 200, b"ok\n", "text/plain; charset=utf-8")
        return

    if path == "/ready":
        status = dashboard_status()
        if status["exists"] and status["size_bytes"] > 0:
            await send_response(send, 200, b"ready\n", "text/plain; charset=utf-8")
        else:
            await send_response(send, 503, b"dashboard missing\n", "text/plain; charset=utf-8")
        return

    if path == "/metadata":
        payload = metadata_payload()
        await send_json(send, 200, payload)
        return

    if path == "/proof":
        payload = proof_payload()
        await send_response(
            send,
            200,
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            "application/json; charset=utf-8",
        )
        return

    await send_response(send, 404, b"not found\n", "text/plain; charset=utf-8")


def dashboard_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "exists": False,
        "path": str(DASHBOARD_PATH),
        "size_bytes": 0,
        "modified_at": None,
        "sha256": None,
        "error": None,
    }
    if not DASHBOARD_PATH.exists():
        return status

    try:
        stat = DASHBOARD_PATH.stat()
        content = DASHBOARD_PATH.read_bytes()
    except OSError as exc:
        status["error"] = str(exc)
        return status

    status["exists"] = True
    status["size_bytes"] = stat.st_size
    status["modified_at"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    status["sha256"] = hashlib.sha256(content).hexdigest()
    return status


def metadata_payload() -> dict[str, Any]:
    status = dashboard_status()
    return {
        "service": SERVICE_NAME,
        "dashboard_exists": status["exists"],
        "dashboard_path": status["path"],
        "dashboard_size": status["size_bytes"],
        "dashboard_modified_at": status["modified_at"],
        "started_at": STARTED_AT.isoformat(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def proof_payload() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    status = dashboard_status()
    ready = bool(status["exists"] and status["size_bytes"] > 0)
    return {
        "service": SERVICE_NAME,
        "status": "ready" if ready else "not_ready",
        "runtime": "asgi_uvicorn",
        "deploy_mode": DEPLOY_MODE,
        "public_base_url": PUBLIC_BASE_URL,
        "proxy_path": PROXY_PATH,
        "local_bind": LOCAL_BIND,
        "git_rev": GIT_REV,
        "dashboard": status,
        "endpoints": {
            "dashboard": public_url("/"),
            "health": public_url("/health"),
            "ready": public_url("/ready"),
            "metadata": public_url("/metadata"),
            "proof": public_url("/proof"),
        },
        "started_at": STARTED_AT.isoformat(),
        "checked_at": now.isoformat(),
        "uptime_seconds": int((now - STARTED_AT).total_seconds()),
    }


def public_url(path: str) -> str:
    if not PUBLIC_BASE_URL:
        return path
    return f"{PUBLIC_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


async def send_file(send: Any, path: Path, content_type: str) -> None:
    if not path.exists():
        await send_response(send, 503, b"dashboard not generated\n", "text/plain; charset=utf-8")
        return
    await send_response(send, 200, path.read_bytes(), content_type)


async def send_json(send: Any, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    await send_response(send, status, body, "application/json; charset=utf-8")


async def send_response(send: Any, status: int, body: bytes, content_type: str) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", content_type.encode("utf-8")),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
