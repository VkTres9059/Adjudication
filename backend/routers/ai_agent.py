from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import get_current_user
from services.ai_agent import chat_with_agent, create_escalation_ticket

router = APIRouter(prefix="/ai-agent", tags=["ai-agent"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider_tax_id: Optional[str] = None
    member_id: Optional[str] = None


class EscalationRequest(BaseModel):
    provider_tax_id: str = ""
    member_id: str = ""
    query_summary: str
    session_id: str = ""


@router.post("/chat")
async def agent_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Send a message to the AI Provider Call Center Agent."""
    session_id = req.session_id or str(uuid.uuid4())

    provider_context = {}
    if req.provider_tax_id:
        provider_context["provider_tax_id"] = req.provider_tax_id
    if req.member_id:
        provider_context["authenticated_member_id"] = req.member_id

    result = await chat_with_agent(
        message=req.message,
        session_id=session_id,
        provider_context=provider_context,
    )
    return result


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
):
    """List recent AI agent chat sessions."""
    pipeline = [
        {"$group": {
            "_id": "$session_id",
            "last_message": {"$last": "$content"},
            "last_timestamp": {"$max": "$timestamp"},
            "message_count": {"$sum": 1},
        }},
        {"$sort": {"last_timestamp": -1}},
        {"$limit": limit},
    ]
    sessions = await db.ai_agent_messages.aggregate(pipeline).to_list(limit)
    return [{
        "session_id": s["_id"],
        "last_message": s["last_message"][:100],
        "last_timestamp": s["last_timestamp"],
        "message_count": s["message_count"],
    } for s in sessions]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user: dict = Depends(get_current_user)):
    """Get all messages for a specific session."""
    messages = await db.ai_agent_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("timestamp", 1).to_list(200)
    return messages


@router.post("/escalate")
async def escalate_to_examiner(req: EscalationRequest, user: dict = Depends(get_current_user)):
    """Create an escalation ticket (Call Log) for the Examiner Queue."""
    ticket = await create_escalation_ticket(
        provider_tax_id=req.provider_tax_id,
        member_id=req.member_id,
        query_summary=req.query_summary,
        session_id=req.session_id,
    )
    return ticket


@router.get("/call-logs")
async def get_call_logs(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(get_current_user),
):
    """Get AI agent escalation call logs."""
    query = {"type": "ai_agent_escalation"}
    if status:
        query["status"] = status
    logs = await db.call_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return logs


@router.put("/call-logs/{log_id}/resolve")
async def resolve_call_log(
    log_id: str,
    notes: str = Query(default=""),
    user: dict = Depends(get_current_user),
):
    """Resolve an escalation call log."""
    result = await db.call_logs.update_one(
        {"id": log_id},
        {"$set": {
            "status": "resolved",
            "resolved_by": user["id"],
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_notes": notes,
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Call log not found")
    return {"status": "resolved", "id": log_id}
