"""Authenticate signed Joomla -> FastAPI requests over a Cloudflare Tunnel.

Only Joomla servers with the shared secret can use /v1 endpoints. No raw
session cookies, API keys, or checkout credentials are transferred to Python.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import OrderedDict
from threading import Lock

from fastapi import HTTPException, Request

_REPLAY: OrderedDict[str, float] = OrderedDict()
_LOCK = Lock()
_WINDOW_SECONDS = 120


def authenticate(raw: bytes, request: Request) -> None:
    secret = os.getenv("FILANTROPHY_SHARED_SECRET", "")
    if len(secret) < 32 or secret.startswith("PASTE_"):
        raise HTTPException(status_code=503, detail="Service authentication is not configured")
    stamp = request.headers.get("x-filantrophy-timestamp", "")
    nonce = request.headers.get("x-filantrophy-nonce", "")
    supplied = request.headers.get("x-filantrophy-signature", "")
    if not stamp.isascii() or not stamp.isdigit() or len(stamp) > 12 or len(nonce) < 16 or len(nonce) > 96:
        raise HTTPException(status_code=401, detail="Missing or invalid request authentication")
    now = int(time.time())
    if abs(now - int(stamp)) > _WINDOW_SECONDS:
        raise HTTPException(status_code=401, detail="Request has expired")
    expected = 'sha256=' + hmac.new(secret.encode(), stamp.encode() + b'.' + nonce.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid request signature")
    # Single-process replay protection; use Redis when scaling to >1 worker.
    with _LOCK:
        for key, seen in list(_REPLAY.items()):
            if now - seen > _WINDOW_SECONDS:
                _REPLAY.pop(key, None)
        if nonce in _REPLAY:
            raise HTTPException(status_code=401, detail="Request has already been used")
        _REPLAY[nonce] = now
        if len(_REPLAY) > 5000:
            _REPLAY.popitem(last=False)
