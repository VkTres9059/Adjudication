from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from urllib.parse import unquote

from core.auth import get_current_user
from cpt_codes import (
    CPT_CODES_DATABASE, GPCI_LOCALITIES, CONVERSION_FACTOR_2024,
    get_cpt_code, get_codes_by_category, calculate_medicare_rate,
    get_all_localities, search_cpt_codes,
)
from dental_codes import CDT_CODES_DATABASE, get_dental_code, search_dental_codes
from vision_codes import VISION_CODES_DATABASE, get_vision_code, search_vision_codes
from hearing_codes import HEARING_CODES_DATABASE, get_hearing_code, search_hearing_codes

router = APIRouter(tags=["codes"])


@router.get("/cpt-codes/search")
async def search_cpt(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, le=100),
    user: dict = Depends(get_current_user)
):
    results = search_cpt_codes(q, limit)
    return {"results": results, "count": len(results)}


@router.get("/cpt-codes/{code}")
async def get_cpt_code_details(code: str, user: dict = Depends(get_current_user)):
    cpt_data = get_cpt_code(code)
    if not cpt_data:
        raise HTTPException(status_code=404, detail="CPT code not found")
    return {"code": code, **cpt_data}


@router.get("/cpt-codes/category/{category:path}")
async def get_codes_by_cat(category: str, user: dict = Depends(get_current_user)):
    category = unquote(category)
    valid_categories = ["E/M", "Anesthesia", "Surgery", "Radiology", "Pathology/Lab", "Medicine", "HCPCS"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {valid_categories}")
    codes = get_codes_by_category(category)
    return {"category": category, "codes": codes, "count": len(codes)}


@router.get("/fee-schedule/rate")
async def calculate_rate(
    cpt_code: str,
    locality: str = Query(default="00000"),
    facility: bool = Query(default=True),
    user: dict = Depends(get_current_user)
):
    cpt_data = get_cpt_code(cpt_code)
    if not cpt_data:
        raise HTTPException(status_code=404, detail="CPT code not found")

    locality_data = GPCI_LOCALITIES.get(locality)
    if not locality_data:
        raise HTTPException(status_code=400, detail="Invalid locality code")

    rate = calculate_medicare_rate(cpt_code, locality, use_facility=facility)

    return {
        "cpt_code": cpt_code,
        "description": cpt_data.get("description"),
        "category": cpt_data.get("category"),
        "locality_code": locality,
        "locality_name": locality_data.get("name"),
        "facility_setting": facility,
        "work_rvu": cpt_data.get("work_rvu"),
        "pe_rvu": cpt_data.get("pe_rvu"),
        "mp_rvu": cpt_data.get("mp_rvu"),
        "total_rvu": cpt_data.get("total_rvu"),
        "gpci_work": locality_data.get("work"),
        "gpci_pe": locality_data.get("pe"),
        "gpci_mp": locality_data.get("mp"),
        "conversion_factor": CONVERSION_FACTOR_2024,
        "medicare_rate": rate,
        "national_facility_rate": cpt_data.get("facility_rate"),
        "national_non_facility_rate": cpt_data.get("non_facility_rate")
    }


@router.get("/fee-schedule/localities")
async def list_localities(user: dict = Depends(get_current_user)):
    localities = get_all_localities()
    return {
        "localities": [
            {"code": code, "name": data["name"], "work_gpci": data["work"], "pe_gpci": data["pe"], "mp_gpci": data["mp"]}
            for code, data in localities.items()
        ],
        "count": len(localities)
    }


@router.get("/fee-schedule/stats")
async def fee_schedule_stats(user: dict = Depends(get_current_user)):
    categories = {}
    for code, data in CPT_CODES_DATABASE.items():
        cat = data.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    return {
        "total_cpt_codes": len(CPT_CODES_DATABASE),
        "total_localities": len(GPCI_LOCALITIES),
        "conversion_factor_2024": CONVERSION_FACTOR_2024,
        "categories": categories,
        "category_counts": [
            {"category": cat, "count": count}
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])
        ]
    }


@router.get("/dental-codes/search")
async def search_dental(q: str = Query(..., min_length=1), limit: int = Query(default=50, le=100), user: dict = Depends(get_current_user)):
    results = search_dental_codes(q, limit)
    return {"results": results, "count": len(results)}


@router.get("/dental-codes/{code}")
async def get_dental(code: str, user: dict = Depends(get_current_user)):
    data = get_dental_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="CDT code not found")
    return {"code": code, **data}


@router.get("/vision-codes/search")
async def search_vision(q: str = Query(..., min_length=1), limit: int = Query(default=50, le=100), user: dict = Depends(get_current_user)):
    results = search_vision_codes(q, limit)
    return {"results": results, "count": len(results)}


@router.get("/vision-codes/{code}")
async def get_vision(code: str, user: dict = Depends(get_current_user)):
    data = get_vision_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Vision code not found")
    return {"code": code, **data}


@router.get("/hearing-codes/search")
async def search_hearing(q: str = Query(..., min_length=1), limit: int = Query(default=50, le=100), user: dict = Depends(get_current_user)):
    results = search_hearing_codes(q, limit)
    return {"results": results, "count": len(results)}


@router.get("/hearing-codes/{code}")
async def get_hearing(code: str, user: dict = Depends(get_current_user)):
    data = get_hearing_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Hearing code not found")
    return {"code": code, **data}


@router.get("/code-database/stats")
async def code_database_stats(user: dict = Depends(get_current_user)):
    dental_cats = {}
    for code, data in CDT_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        dental_cats[cat] = dental_cats.get(cat, 0) + 1

    vision_cats = {}
    for code, data in VISION_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        vision_cats[cat] = vision_cats.get(cat, 0) + 1

    hearing_cats = {}
    for code, data in HEARING_CODES_DATABASE.items():
        cat = data.get("category", "Other")
        hearing_cats[cat] = hearing_cats.get(cat, 0) + 1

    return {
        "medical": {"total": len(CPT_CODES_DATABASE), "localities": len(GPCI_LOCALITIES)},
        "dental": {"total": len(CDT_CODES_DATABASE), "categories": dental_cats},
        "vision": {"total": len(VISION_CODES_DATABASE), "categories": vision_cats},
        "hearing": {"total": len(HEARING_CODES_DATABASE), "categories": hearing_cats},
        "grand_total": len(CPT_CODES_DATABASE) + len(CDT_CODES_DATABASE) + len(VISION_CODES_DATABASE) + len(HEARING_CODES_DATABASE),
    }
