from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import uuid

from core.database import db
from core.auth import hash_password, verify_password, create_access_token, get_current_user, require_roles
from models.enums import UserRole
from models.schemas import UserCreate, UserLogin, UserResponse, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role.value,
        "created_at": now,
        "updated_at": now
    }

    await db.users.insert_one(user_doc)

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "user_registered",
        "user_id": user_id,
        "details": {"email": user_data.email, "role": user_data.role.value},
        "timestamp": now
    })

    token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role.value})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id, email=user_data.email, name=user_data.name,
            role=user_data.role.value, created_at=now
        )
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})

    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "user_login",
        "user_id": user["id"],
        "details": {"email": user["email"]},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"], email=user["email"], name=user["name"],
            role=user["role"], created_at=user["created_at"]
        )
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"], email=user["email"], name=user["name"],
        role=user["role"], created_at=user["created_at"]
    )


@router.get("/users")
async def list_users(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """List all system users (admin only)."""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return users


@router.post("/users")
async def create_user_admin(user_data: UserCreate, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Create a user (admin only)."""
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role.value,
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(user_doc)
    return {"id": user_id, "email": user_data.email, "name": user_data.name, "role": user_data.role.value, "created_at": now}
