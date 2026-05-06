from __future__ import annotations

import json
import os
from typing import Any

import httpx
from openai import OpenAI

from .net import httpx_verify_config


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def make_client(
    api_key: str, *, ca_bundle_path: str | None = None, disable_ssl_verify: bool = False
) -> OpenAI:
    verify = httpx_verify_config(
        ca_bundle_path=ca_bundle_path, disable_ssl_verify=disable_ssl_verify
    )
    http_client = httpx.Client(verify=verify, timeout=90.0)
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        http_client=http_client,
    )


def chat_json(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    timeout_seconds: int = 90,
) -> tuple[dict[str, Any], str]:
    """
    Returns (parsed_json, raw_text). Raises on parse error or API error.
    """
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_output_tokens,
        timeout=timeout_seconds,
    )
    raw = (resp.choices[0].message.content or "").strip()
    return json.loads(raw), raw


def reformat_to_json(
    *,
    client: OpenAI,
    model: str,
    raw_text: str,
    max_output_tokens: int,
    timeout_seconds: int = 90,
) -> tuple[dict[str, Any], str]:
    messages = [
        {
            "role": "system",
            "content": "Return ONLY valid JSON object. No Markdown. No extra text.",
        },
        {
            "role": "user",
            "content": "Fix the following into a single valid JSON object only:\n\n"
            + raw_text,
        },
    ]
    return chat_json(
        client=client,
        model=model,
        messages=messages,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
    )

