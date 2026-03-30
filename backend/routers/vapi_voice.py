"""
Vapi Voice Agent Router — Manages assistant creation, webhook handling, and call history.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os

from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from services.vapi_voice import (
    create_vapi_assistant, get_vapi_assistant,
    list_vapi_calls, process_vapi_webhook,
)

router = APIRouter(prefix="/vapi", tags=["vapi-voice"])

VAPI_API_KEY = os.environ.get("VAPI_API_KEY", "")


class AssistantCreateRequest(BaseModel):
    server_url: str


@router.post("/assistant")
async def setup_assistant(
    req: AssistantCreateRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """Create or update the Vapi voice assistant for FletchFlow."""
    result = await create_vapi_assistant(server_url=req.server_url)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/assistant")
async def get_assistant(user: dict = Depends(get_current_user)):
    """Get the current Vapi assistant configuration."""
    assistant = await get_vapi_assistant()
    return {
        "configured": bool(assistant.get("assistant_id")),
        "assistant_id": assistant.get("assistant_id"),
        "name": assistant.get("name"),
        "created_at": assistant.get("created_at"),
        "vapi_key_set": bool(VAPI_API_KEY),
    }


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """Handle incoming Vapi webhook events (tool-calls, status-update, end-of-call-report, etc.).
    
    This endpoint does NOT require auth — Vapi sends webhooks directly.
    """
    body = await request.json()
    result = await process_vapi_webhook(body)
    return result


@router.get("/calls")
async def get_call_history(
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """Get recent Vapi voice call history."""
    calls = await list_vapi_calls(limit)
    return calls


@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str, user: dict = Depends(get_current_user)):
    """Get details for a specific Vapi call."""
    call = await db.vapi_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(404, "Call not found")
    return call


@router.get("/config")
async def get_vapi_config(user: dict = Depends(get_current_user)):
    """Get Vapi integration status and public key for frontend."""
    assistant = await get_vapi_assistant()
    return {
        "enabled": bool(VAPI_API_KEY),
        "assistant_id": assistant.get("assistant_id"),
        "public_key": VAPI_API_KEY[:8] + "..." if VAPI_API_KEY else None,
    }
