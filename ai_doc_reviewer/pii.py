from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def get_json(url: str, timeout_seconds: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        data = resp.read().decode("utf-8", errors="ignore")
        return json.loads(data)


def post_json(url: str, payload: dict[str, Any], timeout_seconds: int = 90) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        data = resp.read().decode("utf-8", errors="ignore")
        return json.loads(data)


def mask_pii_sync(
    *,
    service_url: str,
    trace_id: str,
    method_id: str,
    text: str,
    options: dict[str, Any] | None = None,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    payload = {
        "api_version": 1,
        "trace_id": trace_id,
        "method_id": method_id,
        "text": text,
        "options": options or {},
    }
    return post_json(service_url.rstrip("/") + "/mask", payload, timeout_seconds=timeout_seconds)

