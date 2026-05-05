from __future__ import annotations

import math


def estimate_tokens(text: str, k: float) -> int:
    if k <= 0:
        raise ValueError("k must be > 0")
    return int(math.ceil(len(text) / k))


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")

