from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = Path(os.environ.get("NEWS_DASHBOARD_HTML", BASE_DIR / "dashboard.html"))


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

    if path == "/metadata":
        payload = {
            "dashboard_exists": DASHBOARD_PATH.exists(),
            "dashboard_path": str(DASHBOARD_PATH),
            "dashboard_size": DASHBOARD_PATH.stat().st_size if DASHBOARD_PATH.exists() else 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        await send_response(
            send,
            200,
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json; charset=utf-8",
        )
        return

    await send_response(send, 404, b"not found\n", "text/plain; charset=utf-8")


async def send_file(send: Any, path: Path, content_type: str) -> None:
    if not path.exists():
        await send_response(send, 503, b"dashboard not generated\n", "text/plain; charset=utf-8")
        return
    await send_response(send, 200, path.read_bytes(), content_type)


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
