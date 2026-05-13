from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from services.groq_service import get_crop_recommendation, get_yield_prediction
from core.security import get_optional_user
from core.mongodb import db_insert, db_find
from loguru import logger

router = APIRouter(prefix="/api/crop", tags=["Crop Intelligence"])


class CropRecommendationRequest(BaseModel):
    soil_type: str
    state: str
    district: Optional[str] = ""
    season: str
    rainfall: float
    temperature: float
    humidity: float
    farm_size: float
    language: str = "en"


class YieldPredictionRequest(BaseModel):
    crop_type: str
    land_area: float
    soil_type: str
    rainfall: float
    temperature: float
    fertilizer_usage: str
    irrigation_level: str
    state: str
    language: str = "en"


@router.post("/recommend")
async def recommend_crops(request: CropRecommendationRequest, current_user: dict = Depends(get_optional_user)):
    """Get AI crop recommendations based on soil and climate data."""
    try:
        data = request.model_dump()
        recommendations = await get_crop_recommendation(data, request.language)

        # Save to MongoDB
        user_id = current_user.get("user_id", "guest") if current_user else "guest"
        await db_insert("crop_reports", {
            "user_id": user_id,
            "type": "recommendation",
            "state": request.state,
            "soil_type": request.soil_type,
            "season": request.season,
            "language": request.language,
            "result": recommendations,
        })

        return {"success": True, "recommendations": recommendations}
    except Exception as e:
        logger.error(f"Crop recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yield-predict")
async def predict_yield(request: YieldPredictionRequest, current_user: dict = Depends(get_optional_user)):
    """Predict crop yield and profitability."""
    try:
        data = request.model_dump()
        prediction = await get_yield_prediction(data, request.language)

        # Save to MongoDB
        user_id = current_user.get("user_id", "guest") if current_user else "guest"
        await db_insert("crop_reports", {
            "user_id": user_id,
            "type": "yield_prediction",
            "crop_type": request.crop_type,
            "land_area": request.land_area,
            "state": request.state,
            "language": request.language,
            "predicted_yield": prediction.get("expected_yield_kg_per_acre", 0),
            "profit_estimate": prediction.get("estimated_profit_inr", 0),
            "risk_level": prediction.get("risk_level", "Unknown"),
            "result": prediction,
        })

        return {"success": True, "prediction": prediction}
    except Exception as e:
        logger.error(f"Yield prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_crop_history(limit: int = 20, current_user: dict = Depends(get_optional_user)):
    """Get user's crop history from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    rows = await db_find("crop_reports", {"user_id": user_id}, limit=limit)
    return {"history": rows}
