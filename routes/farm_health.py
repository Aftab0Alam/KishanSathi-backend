"""
KisanSathi — Farm Health Score Route
Computes a real, dynamic farm health score from:
  • Live weather data (temperature, humidity, wind)
  • Most recent soil analysis stored in MongoDB
  • Recent disease detection results from MongoDB
  • Overall activity metrics

Score is 0-100 with four sub-metrics:
  soil_health, crop_health, water_level, disease_risk
"""

from fastapi import APIRouter, Depends, Query
from loguru import logger
import time

from core.security import get_optional_user
from core.mongodb import db_find
from services.weather_service import get_weather_by_city

router = APIRouter(prefix="/api/farm-health", tags=["Farm Health"])

# Simple in-memory cache: {user_id: (timestamp, result)}
_cache: dict = {}
CACHE_TTL = 900  # 15 minutes


def _get_cache(user_id: str):
    if user_id in _cache:
        ts, data = _cache[user_id]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _set_cache(user_id: str, data: dict):
    _cache[user_id] = (time.time(), data)


# ── Scoring helpers ──────────────────────────────────────────────────────────

def _weather_water_score(weather: dict) -> tuple[int, str]:
    """Score irrigation/water adequacy from humidity + rain data."""
    humidity = weather.get("humidity", 50)
    rain_1h = weather.get("rain_1h", 0) or 0

    if rain_1h > 5:
        return 90, "High"
    if humidity >= 70:
        return 80, "Good"
    if humidity >= 50:
        return 60, "Medium"
    return 40, "Low"


def _weather_crop_score(weather: dict) -> tuple[int, str]:
    """Score crop growing conditions from temp + wind + clouds."""
    temp = weather.get("temperature", 25)
    wind = weather.get("wind_speed", 5) or 5
    clouds = weather.get("clouds", 40) or 40

    score = 100
    # Temperature stress
    if temp < 10 or temp > 40:
        score -= 35
    elif temp < 15 or temp > 35:
        score -= 15

    # High wind stress
    if wind > 15:
        score -= 20
    elif wind > 10:
        score -= 8

    # Too cloudy = less sunlight
    if clouds > 85:
        score -= 10

    score = max(20, min(100, score))
    if score >= 80:
        status = "Excellent"
    elif score >= 65:
        status = "Good"
    elif score >= 45:
        status = "Fair"
    else:
        status = "Poor"
    return score, status


def _soil_score(soil_reports: list) -> tuple[int, str]:
    """Extract soil health score from the most recent soil analysis."""
    if not soil_reports:
        return 65, "Unknown"  # neutral fallback

    latest = soil_reports[0]
    raw = latest.get("soil_health_score")
    if raw is not None:
        try:
            score = int(float(raw))
            score = max(0, min(100, score))
        except (TypeError, ValueError):
            score = 65
    else:
        score = 65

    if score >= 80:
        status = "Excellent"
    elif score >= 65:
        status = "Good"
    elif score >= 45:
        status = "Fair"
    else:
        status = "Poor"
    return score, status


def _disease_risk_score(disease_reports: list) -> tuple[int, str]:
    """
    Compute disease risk from recent disease detection results.
    Lower severity = higher score (lower risk is better).
    """
    if not disease_reports:
        return 85, "Low"  # no detections = low risk

    # Count recent high-severity detections (last 5)
    recent = disease_reports[:5]
    high_risk_count = 0
    medium_risk_count = 0

    for r in recent:
        result = r.get("result", {}) or {}
        severity = str(result.get("severity", "")).lower()
        confidence = float(result.get("confidence", 0) or 0)

        if severity in ("high", "severe", "critical") and confidence > 0.5:
            high_risk_count += 1
        elif severity in ("medium", "moderate") and confidence > 0.5:
            medium_risk_count += 1

    if high_risk_count >= 2:
        return 25, "High"
    if high_risk_count == 1:
        return 45, "Medium"
    if medium_risk_count >= 2:
        return 60, "Medium"
    if medium_risk_count == 1:
        return 72, "Low"
    return 88, "Low"


def _overall_score(soil: int, crop: int, water: int, disease_risk: int) -> int:
    """Weighted average — disease risk inverted (high score = low risk)."""
    return round(
        soil * 0.30
        + crop * 0.25
        + water * 0.20
        + disease_risk * 0.25
    )


# ── Route ────────────────────────────────────────────────────────────────────

@router.get("/score")
async def get_farm_health_score(
    city: str = Query(default="Jalandhar", description="City for weather lookup"),
    current_user: dict = Depends(get_optional_user),
):
    """
    Return a real-time farm health score (0-100) for the authenticated user.
    Combines weather, soil history, and disease detection history.
    """
    user_id = (current_user or {}).get("user_id", "guest")

    cached = _get_cache(user_id)
    if cached:
        logger.info(f"Farm health cache hit for user={user_id}")
        return {**cached, "cached": True}

    # ── Fetch data in parallel (sequential here but fast enough) ─────────────
    weather: dict = {}
    try:
        weather = await get_weather_by_city(city)
    except Exception as e:
        logger.warning(f"Weather fetch failed for farm health: {e}")

    soil_reports: list = []
    disease_reports: list = []
    try:
        soil_reports = await db_find("soil_reports", {"user_id": user_id}, limit=3)
        disease_reports = await db_find("disease_reports", {"user_id": user_id}, limit=10)
    except Exception as e:
        logger.warning(f"MongoDB fetch failed for farm health: {e}")

    # ── Compute sub-scores ────────────────────────────────────────────────────
    soil_score, soil_status = _soil_score(soil_reports)
    crop_score, crop_status = _weather_crop_score(weather)
    water_score, water_status = _weather_water_score(weather)
    disease_score, disease_status = _disease_risk_score(disease_reports)
    overall = _overall_score(soil_score, crop_score, water_score, disease_score)

    # ── Build tip message ─────────────────────────────────────────────────────
    if overall >= 80:
        tip = "Your farm is in excellent condition. Keep it up!"
    elif overall >= 65:
        tip = "Farm is doing well. Monitor water levels regularly."
    elif overall >= 50:
        tip = "Moderate farm health. Consider soil enrichment soon."
    else:
        tip = "Farm needs attention. Check soil and disease risk."

    result = {
        "overall_score": overall,
        "tip": tip,
        "metrics": {
            "soil_health":  {"score": soil_score,   "status": soil_status,    "has_data": len(soil_reports) > 0},
            "crop_health":  {"score": crop_score,   "status": crop_status,    "has_data": bool(weather)},
            "water_level":  {"score": water_score,  "status": water_status,   "has_data": bool(weather)},
            "disease_risk": {"score": disease_score,"status": disease_status, "has_data": len(disease_reports) > 0},
        },
        "data_sources": {
            "weather": bool(weather),
            "soil_reports": len(soil_reports),
            "disease_reports": len(disease_reports),
        },
        "cached": False,
    }

    _set_cache(user_id, result)
    return result
