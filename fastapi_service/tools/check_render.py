"""Probe a Render deployment using the same signed health request as Filantrophy.

Run from fastapi_service after setting FILANTROPHY_SHARED_SECRET locally:
    python tools/check_render.py https://YOUR-SERVICE.onrender.com

No secret is printed. Requires only Python's standard library (dotenv optional).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if len(sys.argv) != 2 or not sys.argv[1].startswith('https://'):
    raise SystemExit('Usage: python tools/check_render.py https://YOUR-SERVICE.onrender.com')

base = sys.argv[1].rstrip('/')
try:
    with urlopen(base + '/health', timeout=30) as res:
        print('Public health:', res.status, res.read().decode('utf-8')[:500])
except (HTTPError, URLError) as e:
    raise SystemExit(f'Could not reach public health endpoint: {e}') from e

secret = os.getenv('FILANTROPHY_SHARED_SECRET', '')
if len(secret) < 32 or secret.startswith('PASTE_'):
    raise SystemExit('Configure FILANTROPHY_SHARED_SECRET locally to test authenticated health')

body = b'{}'
stamp = str(int(time.time()))
nonce = secrets.token_hex(16)
signature = hmac.new(secret.encode(), stamp.encode() + b'.' + nonce.encode() + b'.' + body, hashlib.sha256).hexdigest()
headers = {
    'Content-Type': 'application/json',
    'X-Filantrophy-Timestamp': stamp,
    'X-Filantrophy-Nonce': nonce,
    'X-Filantrophy-Signature': 'sha256=' + signature,
}
try:
    with urlopen(Request(base + '/v1/health', data=body, headers=headers, method='POST'), timeout=40) as res:
        print('Signed health:', res.status, res.read().decode('utf-8')[:700])
except HTTPError as e:
    raise SystemExit(f'Signed health failed HTTP {e.code}; verify matching shared secret and service logs') from e
except URLError as e:
    raise SystemExit(f'Signed health could not reach the server: {e}') from e
