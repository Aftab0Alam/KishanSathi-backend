
import httpx
from datetime import datetime, timedelta
from core.config import settings
from loguru import logger
from services.groq_service import get_ai_response


OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


# ─────────────────────────────────────────────────────────────
# CURRENT WEATHER
# ─────────────────────────────────────────────────────────────

async def get_weather_by_city(
    city: str,
    country: str = "IN"
) -> dict:
    """Fetch current weather for a city."""

    if not settings.OPENWEATHER_API_KEY:
        return {
            "error": "OpenWeather API key not configured"
        }

    async with httpx.AsyncClient() as client:

        try:

            response = await client.get(
                f"{OPENWEATHER_BASE}/weather",
                params={
                    "q": f"{city},{country}",
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": "en"
                },
                timeout=10.0
            )

            response.raise_for_status()

            data = response.json()

            return parse_weather(data)

        except Exception as e:

            logger.error(f"Weather API error: {e}")

            raise Exception(
                f"Weather fetch failed: {str(e)}"
            )


# ─────────────────────────────────────────────────────────────
# 5 DAY FORECAST
# ─────────────────────────────────────────────────────────────

async def get_forecast(
    city: str,
    country: str = "IN"
) -> dict:
    """Fetch 5-day forecast."""

    if not settings.OPENWEATHER_API_KEY:
        return {
            "error": "OpenWeather API key not configured"
        }

    async with httpx.AsyncClient() as client:

        try:

            response = await client.get(
                f"{OPENWEATHER_BASE}/forecast",
                params={
                    "q": f"{city},{country}",
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                    "cnt": 40
                },
                timeout=10.0
            )

            response.raise_for_status()

            return response.json()

        except Exception as e:

            logger.error(f"Forecast API error: {e}")

            raise Exception(
                f"Forecast fetch failed: {str(e)}"
            )


# ─────────────────────────────────────────────────────────────
# AI WEATHER ALERTS
# ─────────────────────────────────────────────────────────────

async def get_ai_weather_alerts(
    weather_data: dict,
    language: str = "english"
) -> str:
    """Generate AI-powered farming alerts."""

    messages = [
        {
            "role": "user",
            "content": f"""
Based on this weather data for an Indian farmer, generate specific farming alerts and recommendations.

Temperature: {weather_data.get('temperature')}°C
Humidity: {weather_data.get('humidity')}%
Weather: {weather_data.get('description')}
Wind Speed: {weather_data.get('wind_speed')} m/s
Rain probability: {weather_data.get('rain_probability', 0)}%
UV Index: {weather_data.get('uv_index', 'Unknown')}

Generate:
1. Farming alerts
2. Disease risk assessment
3. Recommended farming activities
4. Fertilizer advice

Keep it concise and actionable.
"""
        }
    ]

    return await get_ai_response(
        messages,
        language
    )


# ─────────────────────────────────────────────────────────────
# WEATHER PARSER
# ─────────────────────────────────────────────────────────────

def parse_weather(data: dict) -> dict:
    """Parse OpenWeather response."""

    return {
        "city":
            data.get("name"),

        "country":
            data.get("sys", {}).get("country"),

        "temperature":
            round(data.get("main", {}).get("temp", 0), 1),

        "feels_like":
            round(data.get("main", {}).get("feels_like", 0), 1),

        "humidity":
            data.get("main", {}).get("humidity"),

        "pressure":
            data.get("main", {}).get("pressure"),

        "description":
            data.get("weather", [{}])[0].get(
                "description",
                ""
            ),

        "icon":
            data.get("weather", [{}])[0].get(
                "icon",
                ""
            ),

        "wind_speed":
            data.get("wind", {}).get("speed"),

        "visibility":
            data.get("visibility", 0) // 1000,

        "clouds":
            data.get("clouds", {}).get("all"),

        "rain_1h":
            data.get("rain", {}).get("1h", 0),

        "latitude":
            data.get("coord", {}).get("lat"),

        "longitude":
            data.get("coord", {}).get("lon"),
    }


# ─────────────────────────────────────────────────────────────
# SMART WEATHER ALERT SYSTEM
# ─────────────────────────────────────────────────────────────

async def generate_weather_alert(
    temp,
    humidity,
    rain,
    crop="Wheat",
    growth_stage="Tillering"
):
    """Generate smart farming weather alerts."""

    alerts = []

    disease_risk = "Low"

    water_level = "Normal"

    # Heavy rain
    if rain > 70:

        alerts.append(
            "Heavy rain expected. Avoid pesticide spray."
        )

        water_level = "High"

    # High temperature
    if temp > 38:

        alerts.append(
            "High temperature detected. Increase irrigation."
        )

    # High humidity
    if humidity > 85:

        alerts.append(
            "High humidity may increase fungal disease risk."
        )

        disease_risk = "Medium"

    # Extreme disease conditions
    if humidity > 90 and rain > 60:

        disease_risk = "High"

    # Low water conditions
    if rain < 20 and temp > 35:

        water_level = "Low"

    # ─────────────────────────────────────
    # Crop-specific intelligence
    # ─────────────────────────────────────

    crop = crop.lower()

    # Wheat
    if crop == "wheat":

        if growth_stage == "Tillering":

            alerts.append(
                "Apply nitrogen fertilizer during tillering stage."
            )

        if temp > 32:

            alerts.append(
                "Heat stress risk increasing for wheat crop."
            )

    # Rice
    elif crop == "rice":

        if rain < 20:

            alerts.append(
                "Low rainfall detected. Maintain standing water in paddy field."
            )

        if humidity > 90:

            alerts.append(
                "Rice blast disease risk is increasing."
            )

    # Maize
    elif crop == "maize":

        if temp > 36:

            alerts.append(
                "Maize crop may face heat stress."
            )

        if humidity > 88:

            alerts.append(
                "Monitor leaf blight symptoms in maize."
            )

    return {
        "alerts": alerts,
        "disease_risk": disease_risk,
        "water_level": water_level,
    }


# ─────────────────────────────────────────────────────────────
# GROWTH STAGE CALCULATOR
# ─────────────────────────────────────────────────────────────

def calculate_growth_stage(
    sowing_date: str
):
    """Calculate crop growth stage."""

    sow_date = datetime.fromisoformat(
        sowing_date
    )

    days = (
        datetime.utcnow() - sow_date
    ).days

    if days < 20:

        return {
            "stage": "Seedling",
            "progress": 15
        }

    elif days < 45:

        return {
            "stage": "Tillering",
            "progress": 40
        }

    elif days < 75:

        return {
            "stage": "Vegetative",
            "progress": 65
        }

    elif days < 100:

        return {
            "stage": "Flowering",
            "progress": 85
        }

    return {
        "stage": "Harvest Ready",
        "progress": 100
    }


# ─────────────────────────────────────────────────────────────
# HARVEST PREDICTION
# ─────────────────────────────────────────────────────────────

def predict_harvest_date(
    crop: str,
    sowing_date: str
):
    """Predict expected harvest date."""

    crop_days = {
        "wheat": 120,
        "rice": 140,
        "maize": 100,
        "cotton": 180,
        "sugarcane": 300,
    }

    crop_lower = crop.lower()

    total_days = crop_days.get(
        crop_lower,
        120
    )

    sow_date = datetime.fromisoformat(
        sowing_date
    )

    harvest_date = sow_date + timedelta(
        days=total_days
    )

    return harvest_date.strftime(
        "%d %B %Y"
    )