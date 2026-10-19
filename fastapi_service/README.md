> **Deploying to Render?** See [`../README_RENDER.md`](../README_RENDER.md). You do **not** need Cloudflare Tunnel when using Render.

# Filantrophy Python Multi-Agent Backend (FastAPI + LangChain + LangGraph)

This is a **Joomla-to-Python connection release**. Joomla/cPanel remains the system of record for published campaigns, giving plans, checkout, Paystack verification, receipts, and ledgers. Python runs a LangGraph workflow for chat/discovery/recommendation/giving-plan drafts. The AI **does not** charge donors, write donation rows, or approve payments.

## 1. Python setup (machine running cloudflared)

Python 3.11+ recommended; Python 3.10+ needed by LangChain.

```bash
cd fastapi_service
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Paste a **fresh private** OpenAI API key in `.env` as `OPENAI_API_KEY` and paste the generated random shared secret as `FILANTROPHY_SHARED_SECRET`. The shared secret is **not** the OpenAI key. Enter this same shared secret in the Joomla module configuration. `.env` never belongs in public hosting or source control.

Start Python:

```bash
uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000 --workers 1
```

Check from that machine:

```bash
curl http://127.0.0.1:8000/health
```

The public `/health` checks whether FastAPI is running; it **does not** test OpenAI. Use the signed `/v1/health` check from the Joomla Super User icon after configuring the module.

## 2. Cloudflare Tunnel

**Quick Tunnel for testing only:** In a SECOND terminal (keep Python running):

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflare prints a temporary `https://...trycloudflare.com` URL. Paste that **base URL** in the Joomla module. Do **not** append `/v1/chat` or `/health`. Quick Tunnel URLs change on restart and are not for production.

**Permanent Tunnel:** In Cloudflare Dashboard → Networking → Tunnels, create a named tunnel, install/run `cloudflared` on your Python machine, and create a **Published application** route, e.g. `ai.your-cloudflare-domain.com` → `http://127.0.0.1:8000`. Enter `https://ai.your-cloudflare-domain.com` in Joomla. Your domain for the tunnel must be in a Cloudflare account; it does not have to be your Joomla cPanel domain.

If you protect the hostname with **Cloudflare Access**, add a **Service Auth** policy and create a service token. Enter the `CF-Access-Client-Id` and `CF-Access-Client-Secret` values in the Joomla **Python / LangGraph** tab. Do not select an interactive email-login-only Access policy for Joomla's server-to-server requests.

## 3. Joomla module setup (on existing cPanel website)

1. Take a full backup; install `mod_filantrophy_ai-0.1.7.zip` over existing v0.1.6 **without uninstalling**. The current Paystack single-checkout code remains in the module, unchanged.
2. In **Extensions → Site Modules → Filantrophy AI Assistant → Python / LangGraph** choose **AI Processing Engine = Python FastAPI / LangGraph Multi-Agent**.
3. **FastAPI Tunnel URL** = `https://your-tunnel-hostname` (no trailing API endpoint).
4. **Python Shared Secret** = identical long random string in Python `.env`.
5. If using Cloudflare Access, enter the service token Client ID and Client Secret. Otherwise leave both blank.
6. Save the module. While signed into the frontend as a Joomla Super User, click **Test AI Connection** (plug icon). Successful response: **Backend Python FastAPI / LangGraph, Tunnel HTTP Status 200, Authenticated Yes**.
7. Chat normally. Try: **“Find 3 published campaigns for education, health and clean water and split ₦3,000 equally.”** When Python returns an allocation, choose **Apply AI Giving Plan**. Review amounts and click checkout only after an explicit user action.

Do not keep an OpenAI key in the Joomla frontend settings for the Python engine; the AI provider lives in Python `.env`. The older **AI Provider** tab is retained only for the original Direct OpenAI option.

### How requests travel

```
Browser → Joomla com_ajax (same origin) → [HMAC-SHA256 authenticated HTTPS]
Cloudflare public hostname → cloudflared → FastAPI → LangGraph / LangChain → OpenAI
                                ↓ response
Browser ← Joomla validates real campaign IDs and integer allocations ← Python
Browser → Joomla existing Paystack checkout → confirmed donation allocations (NO Python payments)
```

**Security:** The browser never receives `FILANTROPHY_SHARED_SECRET`, `OPENAI_API_KEY`, or Cloudflare Access service token. Every FastAPI private POST requires timestamp, nonce, HMAC signature and replay checks. Joomla validates returned campaign IDs and allocation totals against its current campaign catalogue. FastAPI only receives public campaign fields and recent chat text; nothing private from Joomla donor accounts. No direct MySQL connector to cPanel is used. Use one Uvicorn worker for in-memory replay protection; when scaling out, move the replay cache to Redis. TLS must remain enabled on the public tunnel and PHP cURL must be enabled on cPanel.

### Test from the Python machine

Once tunnel exists:

```bash
python tools/check_tunnel.py https://your-tunnel-hostname
```

This reads your private `.env` and signs the request. It never prints the shared secret.

## 4. Current multi-agent workflow

- Supervisor (LLM): routes intent and extracts budget/currency/causes/count.
- Discovery (deterministic tool): searches the eligible published campaign snapshot supplied by Joomla.
- Recommendation (LLM): explains grounded candidates without hallucinating verification.
- Giving Plan (deterministic tool): computes allocation integers; never charges or writes the plan.
- Knowledge (LLM): explains platform processes without pretending to know user payment status.

This release uses LangGraph `StateGraph` and LangChain's `ChatOpenAI` model integration. It does **not** claim durable cross-restart conversation memory, streaming, an unrestricted autonomous browser, or AI-controlled payment posting. The Joomla browser continues supplying recent conversation context. PostgreSQL checkpoint persistence and more specialist agents are later milestones.

## 5. Validation and known limits

- Backend request authentication and allocation unit tests: `PYTHONPATH=. pytest -q` after installing `pytest` and `httpx` in your development environment.
- PHP 8.1+ required by current Joomla module; cPanel outgoing HTTPS to Cloudflare must be allowed. Some hosts cap PHP request time below 68 seconds; ask hosting to raise the execution timeout if agent calls time out.
- Python machine must stay online for chat. If the tunnel closes, Joomla campaign discovery and existing checkout still work; Python chat fails with a clear message.
- This is **beta connection code**. Test with real OpenAI credentials and your Joomla beta server before production. No real Paystack payment or Joomla settlement is tested by these Python unit tests.

### Brand Voice (v0.2.1)
The generated, visitor-facing replies always use **Filantrophy** and do not mention underlying CMS/software names. The Knowledge, Recommendation and Supervisor agents receive a shared brand instruction, and generated replies get a final normalization guard. Campaign source data, database fields, and URLs are not changed. Restart FastAPI after upgrading.
