"""
AI Provider Call Center Agent — Professional, HIPAA-compliant AI interface
for Claims, Eligibility, Accumulators, and Pre-Cert queries.

Uses OpenAI GPT-5.2 via emergentintegrations.
"""
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from emergentintegrations.llm.chat import LlmChat, UserMessage
from core.database import db

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

SYSTEM_PROMPT = """You are FletchFlow Provider Services Agent, a professional, HIPAA-compliant AI assistant for healthcare provider inquiries. You work for a claims adjudication organization.

Your capabilities:
1. **Eligibility Verification**: Check if a member is active, their coverage status, hour bank balance, and effective/termination dates.
2. **Claim Status Inquiry**: Look up claim status, paid amounts, denial reasons, and adjudication notes.
3. **Accumulator Inquiry**: Report remaining deductible, out-of-pocket amounts, and annual maximums.
4. **Pre-Certification Check**: Determine if a CPT code requires prior authorization under the member's plan.

RULES:
- Always be professional, concise, and HIPAA-compliant.
- Never disclose Protected Health Information (PHI) without proper provider authentication.
- If you cannot find a record, inform the caller and offer to create an escalation ticket.
- When presenting financial data, always format as currency.
- If a question is outside your scope, say: "I'm unable to assist with that request. Let me create an escalation ticket for our examiner team."
- Always reference the data provided in [CONTEXT] blocks. Do not fabricate data.
- If no context data is provided for a query, state that the record was not found.
"""


async def lookup_member(member_id: str) -> dict:
    """Look up member details by member_id."""
    member = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    if not member:
        return None

    # Get hour bank
    bank = await db.hour_bank.find_one({"member_id": member_id}, {"_id": 0})
    # Get plan
    plan = None
    if member.get("plan_id"):
        plan = await db.plans.find_one({"id": member["plan_id"]}, {"_id": 0, "name": 1, "plan_type": 1, "network_type": 1})
    # Get group
    group = None
    if member.get("group_id"):
        group = await db.groups.find_one({"id": member["group_id"]}, {"_id": 0, "name": 1})
    # Get accumulators
    year = str(datetime.now(timezone.utc).year)
    accum = await db.accumulators.find_one(
        {"member_id": member_id, "plan_year": year}, {"_id": 0}
    )

    return {
        "member": member,
        "hour_bank": bank,
        "plan": plan,
        "group": group,
        "accumulators": accum,
    }


async def lookup_claim(claim_number: str) -> dict:
    """Look up claim by claim_number or id."""
    claim = await db.claims.find_one(
        {"$or": [{"claim_number": claim_number}, {"id": claim_number}]},
        {"_id": 0}
    )
    return claim


async def lookup_prior_auth_rules(cpt_code: str, plan_id: str = None) -> dict:
    """Check if a CPT code requires prior auth under a plan."""
    result = {"cpt_code": cpt_code, "requires_auth": False, "plan_rules": []}

    if plan_id:
        plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
        if plan:
            for benefit in plan.get("benefits", []):
                if benefit.get("prior_auth_required"):
                    result["plan_rules"].append(benefit.get("service_category", ""))
            for mod in plan.get("benefit_modules", []):
                if mod.get("prior_auth_required") and mod.get("enabled"):
                    result["plan_rules"].append(mod.get("module_id", ""))

    # Check prior_auth collection
    existing = await db.prior_authorizations.find_one(
        {"cpt_code": cpt_code, "status": "approved"}, {"_id": 0}
    )
    if existing:
        result["existing_auth"] = True

    return result


async def build_context_for_message(message: str, provider_context: dict = None) -> str:
    """Build context blocks from database for the AI to reference."""
    context_parts = []
    msg_lower = message.lower()

    member_id = provider_context.get("authenticated_member_id") if provider_context else None

    # Try to extract member ID from message
    if not member_id:
        import re
        mid_match = re.search(r'(?:member(?:\s+id)?[:\s#]+)([A-Za-z0-9-]+)', message, re.IGNORECASE)
        if mid_match:
            member_id = mid_match.group(1)

    # Eligibility / Member lookup
    if member_id and any(kw in msg_lower for kw in ["eligib", "active", "status", "member", "coverage", "hour", "bank", "deductible", "oop", "accumulator", "out-of-pocket"]):
        data = await lookup_member(member_id)
        if data and data["member"]:
            m = data["member"]
            context_parts.append(f"""[CONTEXT: MEMBER DATA]
Member ID: {m.get('member_id')}
Name: {m.get('first_name', '')} {m.get('last_name', '')}
Status: {m.get('status', 'unknown')}
Effective Date: {m.get('effective_date', 'N/A')}
Termination Date: {m.get('termination_date', 'N/A')}
Group: {data['group']['name'] if data.get('group') else 'N/A'}
Plan: {data['plan']['name'] if data.get('plan') else 'N/A'}
Plan Type: {data['plan']['plan_type'] if data.get('plan') else 'N/A'}""")
            if data.get("hour_bank"):
                hb = data["hour_bank"]
                context_parts.append(f"""[CONTEXT: HOUR BANK]
Current Balance: {hb.get('current_balance', 0)} hours
Reserve Balance: {hb.get('reserve_balance', 0)} hours
Eligibility Source: {hb.get('eligibility_source', 'standard_hours')}""")
            if data.get("accumulators"):
                acc = data["accumulators"]
                context_parts.append(f"""[CONTEXT: ACCUMULATORS - Year {acc.get('plan_year', 'current')}]
Deductible Met: ${acc.get('deductible_met', 0):,.2f}
Out-of-Pocket Met: ${acc.get('oop_met', 0):,.2f}
Annual Max Used: ${acc.get('annual_max_used', 0):,.2f}""")
        else:
            context_parts.append(f"[CONTEXT: NO MEMBER FOUND for ID: {member_id}]")

    # Claim lookup
    import re
    claim_match = re.search(r'(?:claim[:\s#]+)([A-Za-z0-9-]+)', message, re.IGNORECASE)
    if claim_match or any(kw in msg_lower for kw in ["claim status", "claim #", "claim number"]):
        claim_id = claim_match.group(1) if claim_match else None
        if claim_id:
            claim = await lookup_claim(claim_id)
            if claim:
                context_parts.append(f"""[CONTEXT: CLAIM DATA]
Claim ID: {claim.get('id', '')}
Claim Number: {claim.get('claim_number', '')}
Status: {claim.get('status', '')}
Service Date: {claim.get('service_date_from', '')}
Total Billed: ${claim.get('total_billed', 0):,.2f}
Total Allowed: ${claim.get('total_allowed', 0):,.2f}
Total Paid: ${claim.get('total_paid', 0):,.2f}
Member Responsibility: ${claim.get('member_responsibility', 0):,.2f}
Claim Type: {claim.get('claim_type', '')}
Notes: {'; '.join(claim.get('adjudication_notes', [])[:3])}""")
            else:
                context_parts.append(f"[CONTEXT: NO CLAIM FOUND for: {claim_id}]")

    # Pre-cert check
    cpt_match = re.search(r'(?:cpt[:\s#]+)(\d{5})', message, re.IGNORECASE)
    if cpt_match or "pre-cert" in msg_lower or "prior auth" in msg_lower or "authorization" in msg_lower:
        cpt_code = cpt_match.group(1) if cpt_match else None
        if cpt_code:
            plan_id = None
            if member_id:
                mdata = await lookup_member(member_id)
                if mdata and mdata["member"]:
                    plan_id = mdata["member"].get("plan_id")
            auth_data = await lookup_prior_auth_rules(cpt_code, plan_id)
            context_parts.append(f"""[CONTEXT: PRE-CERTIFICATION CHECK]
CPT Code: {cpt_code}
Requires Prior Auth: {'Yes' if auth_data.get('requires_auth') else 'Check plan benefits'}
Plan Rules Requiring Auth: {', '.join(auth_data.get('plan_rules', [])) or 'None found'}
Existing Approved Auth: {'Yes' if auth_data.get('existing_auth') else 'No'}""")

    return "\n\n".join(context_parts)


async def create_escalation_ticket(
    provider_tax_id: str,
    member_id: str,
    query_summary: str,
    session_id: str,
) -> dict:
    """Create a call log ticket in the examiner queue for human follow-up."""
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    ticket = {
        "id": ticket_id,
        "type": "ai_agent_escalation",
        "provider_tax_id": provider_tax_id,
        "member_id": member_id,
        "query_summary": query_summary,
        "session_id": session_id,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }

    await db.call_logs.insert_one(ticket)
    return {k: v for k, v in ticket.items() if k != "_id"}


async def chat_with_agent(
    message: str,
    session_id: str,
    provider_context: dict = None,
) -> dict:
    """Send a message to the AI agent and get a response."""
    if not EMERGENT_KEY:
        return {"response": "AI Agent is not configured. Please set EMERGENT_LLM_KEY.", "session_id": session_id}

    # Build context from database
    context = await build_context_for_message(message, provider_context)
    full_message = message
    if context:
        full_message = f"{message}\n\n{context}"

    # Load conversation history from DB
    history = await db.ai_agent_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("timestamp", 1).to_list(50)

    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    )
    chat.with_model("openai", "gpt-5.2")

    # Replay history into chat
    for msg in history:
        if msg["role"] == "user":
            user_msg = UserMessage(text=msg["content"])
            chat.messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            chat.messages.append({"role": "assistant", "content": msg["content"]})

    # Send new message
    user_msg = UserMessage(text=full_message)
    response = await chat.send_message(user_msg)

    now = datetime.now(timezone.utc).isoformat()

    # Store messages
    await db.ai_agent_messages.insert_one({
        "session_id": session_id,
        "role": "user",
        "content": message,
        "timestamp": now,
    })
    await db.ai_agent_messages.insert_one({
        "session_id": session_id,
        "role": "assistant",
        "content": response,
        "context_used": context[:500] if context else "",
        "timestamp": now,
    })

    return {
        "response": response,
        "session_id": session_id,
        "context_provided": bool(context),
    }
