from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from services.groq_service import get_fertilizer_recommendation
from core.security import get_optional_user
from core.mongodb import db_insert, db_find
from loguru import logger

router = APIRouter(prefix="/api/fertilizer", tags=["Fertilizer Recommendation"])


class FertilizerRequest(BaseModel):
    crop_type: str
    soil_type: str
    state: str
    season: str
    irrigation: str
    disease: Optional[str] = "None"
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    language: str = "en"


@router.post("/recommend")
async def recommend_fertilizer(request: FertilizerRequest, current_user: dict = Depends(get_optional_user)):
    """Get AI-powered fertilizer recommendation and save to MongoDB."""
    try:
        data = request.model_dump()
        recommendation = await get_fertilizer_recommendation(data, request.language)

        # Save to MongoDB (always, even guests)
        report_data = {
            "user_id": current_user.get("user_id", "guest") if current_user else "guest",
            "crop_type": request.crop_type,
            "soil_type": request.soil_type,
            "state": request.state,
            "season": request.season,
            "irrigation": request.irrigation,
            "temperature": request.temperature,
            "humidity": request.humidity,
            "language": request.language,
            "primary_fertilizer": recommendation.get("primary_fertilizer", ""),
            "npk_ratio": recommendation.get("npk_ratio", ""),
            "quantity_per_acre": recommendation.get("quantity_per_acre", ""),
            "application_timing": recommendation.get("application_timing", ""),
            "application_method": recommendation.get("application_method", ""),
            "cost_estimate": recommendation.get("cost_estimate", ""),
            "organic_alternatives": recommendation.get("organic_alternatives", []),
            "weather_warnings": recommendation.get("weather_warnings", ""),
        }
        saved = await db_insert("fertilizer_reports", report_data)
        if saved:
            recommendation["report_id"] = saved.get("id")

        return {"success": True, "recommendation": recommendation}

    except Exception as e:
        logger.error(f"Fertilizer recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_fertilizer_history(limit: int = 20, current_user: dict = Depends(get_optional_user)):
    """Get user's fertilizer recommendation history from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    rows = await db_find("fertilizer_reports", {"user_id": user_id}, limit=limit)
    return {"history": rows}
