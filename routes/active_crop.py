from fastapi import APIRouter, Depends
from datetime import datetime
from core.security import get_current_user
from core.mongodb import db_find_one

router = APIRouter(prefix="/api/active-crop", tags=["Active Crop"])


@router.get("/")
async def get_active_crop(
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["user_id"]

    profile = await db_find_one(
        "user_profiles",
        {"user_id": user_id}
    )

    if not profile:
        return {
            "crop": "Wheat",
            "growth_stage": "Unknown",
            "progress": 0
        }

    crop = profile.get("primary_crop", "Wheat")

    sowing_date = profile.get("sowing_date")

    progress = 0
    growth_stage = "Seedling"

    if sowing_date:

        sow_date = datetime.fromisoformat(sowing_date)

        days = (datetime.utcnow() - sow_date).days

        if days < 20:
            growth_stage = "Seedling"
            progress = 15

        elif days < 45:
            growth_stage = "Tillering"
            progress = 40

        elif days < 75:
            growth_stage = "Vegetative"
            progress = 65

        elif days < 100:
            growth_stage = "Flowering"
            progress = 85

        else:
            growth_stage = "Harvest Ready"
            progress = 100

    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "progress": progress,
        "sowing_date": sowing_date
    }