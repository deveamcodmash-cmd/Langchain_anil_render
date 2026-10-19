"""Joomla-to-Python API. No checkout/payment endpoints by design."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .schemas import ChatRequest
from .security import authenticate

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('filantrophy-ai')
app=FastAPI(title='Filantrophy LangGraph API',version='0.2.2', docs_url=None, redoc_url=None, openapi_url=None)


@app.get('/health')
async def public_health():
    # Public uptime endpoint; never prints credentials, user data, or configuration.
    return {'status':'ok','service':'filantrophy-langgraph','version':'0.2.2'}


@app.post('/v1/health')
async def private_health(request: Request):
    body=await request.body()
    if len(body)>8192:
        raise HTTPException(status_code=413,detail='Request too large')
    authenticate(body,request)
    return {'status':'ok','service':'filantrophy-langgraph','openai_configured':bool(os.getenv('OPENAI_API_KEY')) and not os.getenv('OPENAI_API_KEY', '').startswith('PASTE_'), 'graph':'Supervisor → Discovery / Recommendation / Giving Plan / Knowledge'}


@app.post('/v1/chat')
async def chat(request: Request):
    body=await request.body()
    if len(body)>80000:
        raise HTTPException(status_code=413,detail='Request too large')
    authenticate(body,request)
    try:
        parsed=ChatRequest.model_validate_json(body)
    except ValidationError:
        raise HTTPException(status_code=422,detail='Invalid chat request')
    try:
        from .graph import run_workflow
        response=run_workflow(parsed)
        from .graph import normalize_public_reply
        result=response.model_dump()
        result["reply"]=normalize_public_reply(result.get("reply") or "")
        return result
    except (ImportError,ModuleNotFoundError):
        logger.exception('AI dependencies unavailable')
        raise HTTPException(status_code=503,detail='Python AI dependencies have not been installed')
    except RuntimeError as exc:
        logger.warning('AI configuration error')
        raise HTTPException(status_code=503,detail='Python AI model is not configured') from exc
    except Exception:
        # Provider exceptions may include request data, do not leak stack or model content.
        logger.exception('Agent workflow failed')
        raise HTTPException(status_code=502,detail='The agent workflow is temporarily unavailable')
