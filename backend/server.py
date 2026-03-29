from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from core.config import logger
from core.database import client

from routers import (
    auth, plans, members, groups, claims, examiner,
    duplicates, dashboard, reports, edi, codes,
    network, prior_auth, preventive, settings, audit,
    hour_bank,
)

app = FastAPI(title="FletchFlow Claims Adjudication System", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main API router - all sub-routers included under /api
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(plans.router)
api_router.include_router(members.router)
api_router.include_router(groups.router)
api_router.include_router(claims.router)
api_router.include_router(examiner.router)
api_router.include_router(duplicates.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(edi.router)
api_router.include_router(codes.router)
api_router.include_router(network.router)
api_router.include_router(prior_auth.router)
api_router.include_router(preventive.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)
api_router.include_router(hour_bank.router)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": "FletchFlow Claims Adjudication System",
        "version": "2.0.0",
        "status": "operational",
        "architecture": "modular",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
