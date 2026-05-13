from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.weather_service import get_weather_by_city, get_forecast, get_ai_weather_alerts
from core.security import get_optional_user
from core.database import supabase
from loguru import logger

router = APIRouter(prefix="/api/weather", tags=["Weather Intelligence"])


class WeatherRequest(BaseModel):
    city: str
    country: str = "IN"
    language: str = "en"


@router.post("/current")
async def get_current_weather(request: WeatherRequest, current_user: dict = Depends(get_optional_user)):
    """Get current weather with AI farming alerts."""
    try:
        weather = await get_weather_by_city(request.city, request.country)
        alerts = await get_ai_weather_alerts(weather, request.language)

        if supabase and current_user:
            try:
                await supabase.insert("weather_logs", {
                    "user_id": current_user["user_id"],
                    "location": f"{request.city},{request.country}",
                    "data_json": str(weather),
                })
            except Exception as db_err:
                logger.warning(f"Weather log save failed: {db_err}")

        return {"weather": weather, "ai_alerts": alerts}
    except Exception as e:
        logger.error(f"Weather error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_weather_forecast(city: str, country: str = "IN", current_user: dict = Depends(get_optional_user)):
    """Get 5-day weather forecast."""
    try:
        forecast = await get_forecast(city, country)
        return {"forecast": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
