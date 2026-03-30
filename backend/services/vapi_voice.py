"""
Vapi Voice Agent Integration — Connects existing AI Agent logic to Vapi's voice platform.
Creates a Vapi assistant configured for healthcare provider inquiries,
handles webhook events for function calling (eligibility, claims, pre-cert).
"""
import os
import json
import uuid
import httpx
from datetime import datetime, timezone
from core.database import db
from services.ai_agent import lookup_member, lookup_claim, lookup_prior_auth_rules

VAPI_API_KEY = os.environ.get("VAPI_API_KEY", "")
VAPI_BASE_URL = "https://api.vapi.ai"

VOICE_SYSTEM_PROMPT = """You are Morgan, the FletchFlow Provider Services Voice Agent. You are a professional, HIPAA-compliant AI assistant handling inbound voice calls from healthcare providers.

Your capabilities:
1. **Eligibility Verification**: Check if a member is active, coverage status, hour bank balance, effective/termination dates.
2. **Claim Status Inquiry**: Look up claim status, paid amounts, denial reasons, adjudication notes by claim number.
3. **Accumulator Inquiry**: Report remaining deductible, out-of-pocket amounts, annual maximums.
4. **Pre-Certification Check**: Determine if a CPT code requires prior authorization under the member's plan.

RULES:
- Always be professional, concise, and empathetic.
- Verify provider identity before releasing member information.
- If you cannot find a record, inform the caller and offer to create an escalation ticket.
- When presenting financial data, always state dollar amounts clearly.
- If a question is outside your scope, say: "I'm unable to assist with that. Let me transfer you to our examiner team."
- Keep responses brief and conversational — this is a phone call, not a text chat.
- Ask one question at a time and wait for a response.
- Spell out abbreviations when speaking (e.g., "C-P-T code" not "CPT code").
"""

HEALTHCARE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_member_eligibility",
            "description": "Check if a member is active and retrieve their coverage details, hour bank, and accumulators",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "The member ID to look up (e.g., MBR001)"
                    }
                },
                "required": ["member_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_claim_status",
            "description": "Look up the status of a submitted insurance claim by claim number",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_number": {
                        "type": "string",
                        "description": "The claim number or claim ID to look up"
                    }
                },
                "required": ["claim_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_prior_auth",
            "description": "Check if a CPT procedure code requires prior authorization under a member's plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "cpt_code": {
                        "type": "string",
                        "description": "The 5-digit CPT code to check"
                    },
                    "member_id": {
                        "type": "string",
                        "description": "Optional member ID to check against their specific plan"
                    }
                },
                "required": ["cpt_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_escalation",
            "description": "Create an escalation ticket for the examiner team when you cannot resolve an inquiry",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Summary of why the call is being escalated"
                    },
                    "member_id": {
                        "type": "string",
                        "description": "Member ID if available"
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


async def create_vapi_assistant(server_url: str) -> dict:
    """Create a Vapi assistant configured for FletchFlow healthcare provider calls."""
    if not VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not configured"}

    assistant_config = {
        "name": "FletchFlow Provider Services Agent",
        "firstMessage": "Thank you for calling FletchFlow Provider Services. My name is Morgan. Before I can assist you, may I have your provider Tax ID number for verification?",
        "firstMessageMode": "assistant-speaks-first",
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": VOICE_SYSTEM_PROMPT}
            ],
            "tools": HEALTHCARE_FUNCTIONS,
        },
        "voice": {
            "provider": "openai",
            "voiceId": "alloy",
        },
        "transcriber": {
            "provider": "deepgram",
            "language": "en",
            "model": "nova-2",
        },
        "serverUrl": server_url,
        "hipaaEnabled": True,
        "endCallFunctionEnabled": True,
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{VAPI_BASE_URL}/assistant",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=assistant_config,
        )
        if resp.status_code in (200, 201):
            result = resp.json()
            # Store assistant ID in settings
            await db.settings.update_one(
                {"key": "vapi_assistant"},
                {"$set": {"key": "vapi_assistant", "value": {
                    "assistant_id": result.get("id"),
                    "name": result.get("name"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }}},
                upsert=True,
            )
            return result
        else:
            return {"error": resp.text, "status_code": resp.status_code}


async def get_vapi_assistant() -> dict:
    """Get the stored Vapi assistant config."""
    doc = await db.settings.find_one({"key": "vapi_assistant"}, {"_id": 0})
    if doc:
        return doc.get("value", {})
    return {}


async def list_vapi_calls(limit: int = 20) -> list:
    """List recent Vapi voice calls from our DB log."""
    calls = await db.vapi_calls.find(
        {}, {"_id": 0}
    ).sort("started_at", -1).to_list(limit)
    return calls


async def handle_tool_call(function_name: str, parameters: dict) -> str:
    """Execute a tool call from Vapi and return the result as JSON string."""
    if function_name == "check_member_eligibility":
        member_id = parameters.get("member_id", "")
        data = await lookup_member(member_id)
        if not data or not data.get("member"):
            return json.dumps({"error": f"Member {member_id} not found in the system."})
        m = data["member"]
        result = {
            "member_id": m.get("member_id"),
            "name": f"{m.get('first_name', '')} {m.get('last_name', '')}",
            "status": m.get("status", "unknown"),
            "effective_date": m.get("effective_date", "N/A"),
            "termination_date": m.get("termination_date", "N/A"),
            "group": data["group"]["name"] if data.get("group") else "N/A",
            "plan": data["plan"]["name"] if data.get("plan") else "N/A",
        }
        if data.get("hour_bank"):
            hb = data["hour_bank"]
            result["hour_bank_current"] = hb.get("current_balance", 0)
            result["hour_bank_reserve"] = hb.get("reserve_balance", 0)
        if data.get("accumulators"):
            acc = data["accumulators"]
            result["deductible_met"] = acc.get("deductible_met", 0)
            result["oop_met"] = acc.get("oop_met", 0)
        return json.dumps(result)

    elif function_name == "check_claim_status":
        claim_number = parameters.get("claim_number", "")
        claim = await lookup_claim(claim_number)
        if not claim:
            return json.dumps({"error": f"Claim {claim_number} not found."})
        return json.dumps({
            "claim_number": claim.get("claim_number", ""),
            "status": claim.get("status", ""),
            "total_billed": claim.get("total_billed", 0),
            "total_allowed": claim.get("total_allowed", 0),
            "total_paid": claim.get("total_paid", 0),
            "member_responsibility": claim.get("member_responsibility", 0),
            "adjudication_notes": (claim.get("adjudication_notes", []) or [])[:3],
        })

    elif function_name == "check_prior_auth":
        cpt_code = parameters.get("cpt_code", "")
        member_id = parameters.get("member_id")
        plan_id = None
        if member_id:
            data = await lookup_member(member_id)
            if data and data.get("member"):
                plan_id = data["member"].get("plan_id")
        auth_data = await lookup_prior_auth_rules(cpt_code, plan_id)
        return json.dumps({
            "cpt_code": cpt_code,
            "requires_auth": bool(auth_data.get("plan_rules")),
            "plan_categories_requiring_auth": auth_data.get("plan_rules", []),
            "existing_approved_auth": auth_data.get("existing_auth", False),
        })

    elif function_name == "create_escalation":
        reason = parameters.get("reason", "Voice agent escalation")
        member_id = parameters.get("member_id", "")
        ticket_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        ticket = {
            "id": ticket_id,
            "type": "ai_agent_escalation",
            "source": "voice",
            "provider_tax_id": "",
            "member_id": member_id,
            "query_summary": reason,
            "session_id": "",
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        await db.call_logs.insert_one(ticket)
        return json.dumps({"ticket_id": ticket_id, "message": "Escalation ticket created. An examiner will follow up."})

    return json.dumps({"error": f"Unknown function: {function_name}"})


async def process_vapi_webhook(body: dict) -> dict:
    """Process incoming Vapi webhook events."""
    message = body.get("message", {})
    msg_type = message.get("type", "")

    if msg_type == "tool-calls":
        tool_call_list = message.get("toolCallList", [])
        results = []
        for tc in tool_call_list:
            fn_name = tc.get("function", {}).get("name", tc.get("name", ""))
            params = tc.get("function", {}).get("arguments", tc.get("parameters", {}))
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {}
            tc_id = tc.get("id", "")
            result_str = await handle_tool_call(fn_name, params)
            results.append({
                "toolCallId": tc_id,
                "result": result_str,
            })
        return {"results": results}

    elif msg_type == "status-update":
        call = message.get("call", {})
        status = message.get("status", call.get("status", ""))
        call_id = call.get("id", "")
        if call_id:
            now = datetime.now(timezone.utc).isoformat()
            await db.vapi_calls.update_one(
                {"call_id": call_id},
                {"$set": {
                    "call_id": call_id,
                    "status": status,
                    "assistant_id": call.get("assistantId", ""),
                    "updated_at": now,
                    **({"started_at": now} if status == "in-progress" else {}),
                    **({"ended_at": now} if status == "ended" else {}),
                }},
                upsert=True,
            )
        return {"received": True}

    elif msg_type == "end-of-call-report":
        call = message.get("call", {})
        call_id = call.get("id", "")
        artifact = message.get("artifact", {})
        ended_reason = message.get("endedReason", "")
        now = datetime.now(timezone.utc).isoformat()

        if call_id:
            transcript = artifact.get("transcript", "")
            messages_list = artifact.get("messages", [])
            await db.vapi_calls.update_one(
                {"call_id": call_id},
                {"$set": {
                    "status": "ended",
                    "ended_reason": ended_reason,
                    "transcript": transcript,
                    "message_count": len(messages_list),
                    "duration": call.get("duration"),
                    "ended_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            # Save transcript as call log
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()),
                "action": "vapi_call_ended",
                "entity_type": "vapi_call",
                "entity_id": call_id,
                "user_id": "system",
                "timestamp": now,
                "details": {"ended_reason": ended_reason, "duration": call.get("duration")},
            })
        return {"received": True}

    elif msg_type == "transcript":
        return {"received": True}

    elif msg_type == "assistant-request":
        assistant_doc = await get_vapi_assistant()
        if assistant_doc and assistant_doc.get("assistant_id"):
            return {"assistantId": assistant_doc["assistant_id"]}
        return {"error": "No assistant configured"}

    return {"received": True}
