from fastapi import APIRouter, Depends
from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import AdjudicationGatewayConfig

router = APIRouter(prefix="/settings", tags=["settings"])


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
