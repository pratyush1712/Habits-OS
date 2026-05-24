"""WHOOP webhook signature helpers.

Webhook route wiring is intentionally deferred until pull-based sync is proven,
but the verification primitive is small and useful to test now.
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def calculate_signature(*, timestamp: str, raw_body: bytes, secret: str) -> str:
    signed = timestamp.encode("utf-8") + raw_body
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_signature(
    *,
    timestamp: str,
    raw_body: bytes,
    signature: str,
    secret: str,
) -> bool:
    expected = calculate_signature(timestamp=timestamp, raw_body=raw_body, secret=secret)
    return hmac.compare_digest(expected, signature)
