from __future__ import annotations

import ssl
from typing import Any


def httpx_verify_config(*, ca_bundle_path: str | None, disable_ssl_verify: bool) -> bool | str | Any:
    """
    Returns a value suitable for httpx.Client(verify=...).
    Preference order:
    - disable_ssl_verify -> False
    - explicit ca_bundle_path -> that path
    - Windows system trust store via truststore (if available) -> SSLContext
    - default -> True
    """
    if disable_ssl_verify:
        return False

    if ca_bundle_path and ca_bundle_path.strip():
        return ca_bundle_path.strip()

    try:
        import truststore

        # Use Windows system trust store (same idea as curl.exe on Windows).
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return True

