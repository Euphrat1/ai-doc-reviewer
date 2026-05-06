from __future__ import annotations

import json
import time
from typing import Any, Iterable, Optional

import httpx

from .net import httpx_verify_config


CURSOR_API_BASE = "https://api.cursor.com/v1"


def _basic_auth_header(api_key: str) -> str:
    # Basic auth: username = api key, password empty
    import base64

    token = base64.b64encode(f"{api_key}:".encode("ascii")).decode("ascii")
    return f"Basic {token}"


def cursor_get_me(
    api_key: str,
    *,
    timeout_seconds: int = 15,
    ca_bundle_path: str | None = None,
    disable_ssl_verify: bool = False,
) -> dict[str, Any]:
    verify = httpx_verify_config(
        ca_bundle_path=ca_bundle_path, disable_ssl_verify=disable_ssl_verify
    )
    with httpx.Client(timeout=timeout_seconds, verify=verify) as c:
        r = c.get(
            f"{CURSOR_API_BASE}/me",
            headers={"Authorization": _basic_auth_header(api_key)},
        )
        r.raise_for_status()
        return r.json()


def create_agent(
    *,
    api_key: str,
    prompt_text: str,
    repo_url: str,
    starting_ref: str = "main",
    model_id: str | None = None,
    auto_create_pr: bool = False,
    ca_bundle_path: str | None = None,
    disable_ssl_verify: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": {"text": prompt_text},
        "repos": [{"url": repo_url, "startingRef": starting_ref}],
        "autoCreatePR": bool(auto_create_pr),
    }
    if model_id:
        payload["model"] = {"id": model_id}

    verify = httpx_verify_config(
        ca_bundle_path=ca_bundle_path, disable_ssl_verify=disable_ssl_verify
    )
    with httpx.Client(timeout=60, verify=verify) as c:
        r = c.post(
            f"{CURSOR_API_BASE}/agents",
            headers={
                "Authorization": _basic_auth_header(api_key),
                "Content-Type": "application/json",
            },
            content=json.dumps(payload).encode("utf-8"),
        )
        r.raise_for_status()
        return r.json()


def get_run(
    *,
    api_key: str,
    agent_id: str,
    run_id: str,
    timeout_seconds: int = 30,
    ca_bundle_path: str | None = None,
    disable_ssl_verify: bool = False,
) -> dict[str, Any]:
    verify = httpx_verify_config(
        ca_bundle_path=ca_bundle_path, disable_ssl_verify=disable_ssl_verify
    )
    with httpx.Client(timeout=timeout_seconds, verify=verify) as c:
        r = c.get(
            f"{CURSOR_API_BASE}/agents/{agent_id}/runs/{run_id}",
            headers={"Authorization": _basic_auth_header(api_key)},
        )
        r.raise_for_status()
        return r.json()


def stream_run_text(
    *,
    api_key: str,
    agent_id: str,
    run_id: str,
    timeout_seconds: int = 300,
    ca_bundle_path: str | None = None,
    disable_ssl_verify: bool = False,
) -> str:
    """
    Streams SSE and concatenates assistant text deltas into one string.
    """
    url = f"{CURSOR_API_BASE}/agents/{agent_id}/runs/{run_id}/stream"
    headers = {
        "Authorization": _basic_auth_header(api_key),
        "Accept": "text/event-stream",
    }

    text_parts: list[str] = []
    event_type: str | None = None

    verify = httpx_verify_config(
        ca_bundle_path=ca_bundle_path, disable_ssl_verify=disable_ssl_verify
    )
    with httpx.Client(timeout=timeout_seconds, verify=verify) as c:
        with c.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    event_type = None
                    continue
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    if event_type == "assistant":
                        try:
                            obj = json.loads(data_str)
                            delta = obj.get("text", "")
                            if delta:
                                text_parts.append(delta)
                        except Exception:
                            # best-effort; ignore malformed chunks
                            pass
                    continue

    return "".join(text_parts).strip()


def wait_run_terminal(
    *,
    api_key: str,
    agent_id: str,
    run_id: str,
    timeout_seconds: int = 600,
    poll_seconds: float = 2.0,
    ca_bundle_path: str | None = None,
    disable_ssl_verify: bool = False,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        last = get_run(
            api_key=api_key,
            agent_id=agent_id,
            run_id=run_id,
            ca_bundle_path=ca_bundle_path,
            disable_ssl_verify=disable_ssl_verify,
        )
        status = (last.get("status") or "").upper()
        if status in {"FINISHED", "CANCELLED", "ERROR", "FAILED"}:
            return last
        time.sleep(poll_seconds)
    raise TimeoutError("Cursor run did not reach terminal state in time")

