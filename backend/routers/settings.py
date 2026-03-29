from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import AdjudicationGatewayConfig

router = APIRouter(prefix="/settings", tags=["settings"])


BRIDGE_DEFAULTS = {"enabled": False, "rate_per_hour": 20.0}


@router.get("/adjudication-gateway")
async def get_gateway_settings(user: dict = Depends(get_current_user)):
    doc = await db.settings.find_one({"key": "adjudication_gateway"}, {"_id": 0})
    if not doc:
        return AdjudicationGatewayConfig().model_dump()
    return doc.get("value", AdjudicationGatewayConfig().model_dump())


@router.put("/adjudication-gateway")
async def update_gateway_settings(config: AdjudicationGatewayConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    await db.settings.update_one(
        {"key": "adjudication_gateway"},
        {"$set": {"key": "adjudication_gateway", "value": config.model_dump()}},
        upsert=True
    )
    return config.model_dump()


# ── Bridge Payment Settings ──

class BridgePaymentConfig(BaseModel):
    enabled: bool = False
    rate_per_hour: float = 20.0


@router.get("/bridge-payment")
async def get_bridge_settings(user: dict = Depends(get_current_user)):
    doc = await db.settings.find_one({"key": "bridge_payment"}, {"_id": 0})
    if not doc:
        return BRIDGE_DEFAULTS
    return doc.get("value", BRIDGE_DEFAULTS)


@router.put("/bridge-payment")
async def update_bridge_settings(config: BridgePaymentConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    await db.settings.update_one(
        {"key": "bridge_payment"},
        {"$set": {"key": "bridge_payment", "value": config.model_dump()}},
        upsert=True
    )
    return config.model_dump()
