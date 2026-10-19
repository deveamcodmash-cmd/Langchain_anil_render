# Deploy Filantrophy AI v0.2.2 on Render

These files run your existing FastAPI + LangGraph backend as a **Render Web Service**.
The application talks to the existing Filantrophy frontend module over authenticated HTTPS. No Cloudflare Tunnel, `cloudflared`, local Python server, Docker, database, or browser CORS setup is needed for this connection.

## Recommended: Render Blueprint

1. **Extract the ZIP** and upload its **contents** to a new GitHub repository (at the repository root). GitHub should show `render.yaml` and the `fastapi_service/` folder; don't push the `.zip` as the only file.
2. Open https://dashboard.render.com/ -> **New** -> **Blueprint**, connect this GitHub repository and select the branch with these files.
3. Render will read `render.yaml` and create the `filantrophy-ai` Python web service. The default Blueprint uses the **Free** plan for testing. A paid always-on instance is recommended for a live donation chatbot so idle spin-down doesn't delay the first chat request.
4. Supply the **two secret values** during Blueprint setup (or immediately in your service's **Environment** section):

   | Key | Value |
   |---|---|
   | `OPENAI_API_KEY` | Your real private OpenAI API key |
   | `FILANTROPHY_SHARED_SECRET` | A newly generated random secret, **at least 32 characters**, exactly the same value as in your Filantrophy module |

   `OPENAI_MODEL` is already set to `gpt-4.1-mini` by default. The key must have access to that model and API billing must be enabled for your OpenAI project.
5. Generate a shared secret on your own computer, **not in GitHub or chat**:
   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```
   Copy it to both Render and the server-side settings in your Filantrophy AI module. **Do not copy `OPENAI_API_KEY` into the module or website frontend.**
6. Deploy and open the Render service URL shown in the dashboard, for example `https://YOUR-ACTUAL-SERVICE.onrender.com/health`. Use **the real URL Render assigned**, not this illustrative URL. Expected response:
   ```json
   {"status":"ok","service":"filantrophy-langgraph","version":"0.2.2"}
   ```
   This tests the web server only, not OpenAI or authenticated chat.
7. In **Filantrophy AI Assistant -> Python / LangGraph**, set:
   - AI Processing Engine: **Python FastAPI / LangGraph Multi-Agent**
   - **FastAPI Tunnel URL** (existing field name): `https://YOUR-ACTUAL-SERVICE.onrender.com` (**base URL only**; no `/health`, `/v1/chat`, or trailing path)
   - **Python Shared Secret**: same value as `FILANTROPHY_SHARED_SECRET` on Render
   - **Cloudflare Access Client ID/Secret**: leave empty (Render HTTPS does not require a Cloudflare service token)
   Save and run **Test AI Connection**, then send a real chat message.

## Alternative: Create a Web Service manually

Select **New -> Web Service**, connect the extracted GitHub repo and fill in these exact fields:

| Render setting | Value |
|---|---|
| Runtime | Python 3 |
| Root Directory | `fastapi_service` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/health` |
| Python version | `3.12` (provided by `fastapi_service/.python-version`) |
| Environment | The two required secrets above, plus `OPENAI_MODEL=gpt-4.1-mini` |

Render's default Python runtime may differ, so keep `.python-version` committed. Do not set a hard-coded port like 8000; Render provides `$PORT`.

## Verify authenticated connection without exposing secrets

From `fastapi_service/`, if you have a **local** `.env` with the same `FILANTROPHY_SHARED_SECRET`, run:

```bash
python tools/check_render.py https://YOUR-ACTUAL-SERVICE.onrender.com
```

It signs a POST to `/v1/health`; **HTTP 200** confirms your shared secret and HMAC request format are accepted. The result contains `openai_configured: true` when a non-placeholder key is present in Render's environment. This is not an actual model completion test. Confirm a real reply through the site chatbot.

### Troubleshooting

- **Build fails**: Verify `fastapi_service/requirements.txt` exists in GitHub and **Root Directory** is `fastapi_service`. Look at Render's **Events/Logs**. Python is deliberately set to 3.12 for LangGraph package compatibility.
- **404 on `/health`**: Verify the URL belongs to the **Web Service**, not a static site. A bare `/` path may return 404; that is normal.
- **401 on `/v1/health`**: It needs a signed POST with timestamp, nonce and HMAC; opening this private endpoint in a browser is not a valid test. Use the Filantrophy module's Test AI Connection or `tools/check_render.py`.
- **503 on `/v1/health`**: Shared secret missing, too short or placeholder in Render Environment. Update it, redeploy and ensure it matches the module.
- **503 or 502 during chat**: Confirm `OPENAI_API_KEY` and model name, OpenAI project access/billing, then inspect Render logs. `/health` returning OK alone does not prove the AI provider works.
- **First chat is very slow / timeout**: Free services spin down after inactivity. Paid always-on service is safer for a production chatbot, or re-try after the instance is awake. Network/request timeout settings in your hosting may also need adjustment.
- **The module displays `FastAPI Tunnel URL`**: That is only the existing field label; paste the **Render HTTPS base URL** in it. Do **not** start `cloudflared`.
- **Changes don't appear**: Push committed changes to the branch connected to Render; Render redeploys from that branch.

## Security and scope

`OPENAI_API_KEY` and `FILANTROPHY_SHARED_SECRET` **must remain server-side**, never in source code, frontend JavaScript, a screenshot, or chat. Every `/v1/chat` request is HMAC-authenticated; `/health` is public by design. Keep **one Uvicorn worker and one instance** because replay-nonce protection currently lives only in process memory. Multi-instance scaling requires shared nonce storage such as Redis first.

This FastAPI service **only** generates chatbot responses, discovers campaigns supplied by the Filantrophy frontend, and proposes giving plans. **Payment collection (Paystack/Stripe, card entry, receipts, and checkout UI) is implemented in the Filantrophy website module, not this Python backend**. Deploying this ZIP does not change the checkout design or payment integration.

## Local tests

```bash
cd fastapi_service
python -m pip install -r requirements.txt
python -m pip install pytest httpx
PYTHONPATH=. pytest -q
```
