from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from core.database import db
from core.auth import get_current_user, require_roles
from models.enums import UserRole
from models.schemas import AdjudicationGatewayConfig

router = APIRouter(prefix="/settings", tags=["settings"])


BRIDGE_DEFAULTS = {"enabled": False, "rate_per_hour": 20.0}
VENDOR_DEFAULTS = []


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


# ── Vendor Feed Configuration ──

class VendorConfig(BaseModel):
    id: Optional[str] = None
    name: str
    vendor_type: str = "medical_tpa"
    feed_types: List[str] = ["834"]
    format: str = "hipaa_5010"
    sftp_host: str = ""
    sftp_path: str = ""
    enabled: bool = True


@router.get("/vendors")
async def get_vendors(user: dict = Depends(get_current_user)):
    """List all configured feed vendors."""
    vendors = await db.feed_vendors.find({}, {"_id": 0}).sort("name", 1).to_list(100)
    return vendors


@router.post("/vendors")
async def create_vendor(config: VendorConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a new feed vendor."""
    import uuid
    doc = config.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    await db.feed_vendors.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.put("/vendors/{vendor_id}")
async def update_vendor(vendor_id: str, config: VendorConfig, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Update a feed vendor configuration."""
    doc = config.model_dump()
    doc["id"] = vendor_id
    await db.feed_vendors.update_one({"id": vendor_id}, {"$set": doc})
    return doc


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    await db.feed_vendors.delete_one({"id": vendor_id})
    return {"status": "deleted"}
