"""Test cPanel-compatible signed /v1/health from any machine, no secrets printed.

Example: python tools/check_tunnel.py https://ai.yourdomain.com
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if len(sys.argv) != 2 or not sys.argv[1].startswith('https://'):
    raise SystemExit('Usage: python tools/check_tunnel.py https://your-tunnel-hostname')
base = sys.argv[1].rstrip('/')
secret = os.getenv('FILANTROPHY_SHARED_SECRET','')
if len(secret) < 32 or secret.startswith('PASTE_'):
    raise SystemExit('Set the real FILANTROPHY_SHARED_SECRET in your local .env first')
body=b'{}'
stamp=str(int(time.time()))
nonce=secrets.token_hex(16)
signature=hmac.new(secret.encode(),stamp.encode()+b'.'+nonce.encode()+b'.'+body,hashlib.sha256).hexdigest()
headers={
 'Content-Type':'application/json',
 'X-Filantrophy-Timestamp':stamp,
 'X-Filantrophy-Nonce':nonce,
 'X-Filantrophy-Signature':'sha256='+signature,
}
try:
    with urlopen(Request(base+'/v1/health',data=body,headers=headers,method='POST'),timeout=20) as response:
        print('HTTP:',response.status)
        print('Response:',response.read().decode('utf-8')[:700])
except HTTPError as exc:
    print('HTTP:',exc.code,'— Review the shared secret or Cloudflare Access policy')
except URLError:
    print('Network error — is FastAPI running and is your Cloudflare Tunnel connected?')
