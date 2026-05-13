import httpx
from core.config import settings
from loguru import logger
from services.groq_service import get_ai_response


OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


async def get_weather_by_city(city: str, country: str = "IN") -> dict:
    """Fetch current weather for a city."""
    if not settings.OPENWEATHER_API_KEY:
        return {"error": "OpenWeather API key not configured"}
    
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
            raise Exception(f"Weather fetch failed: {str(e)}")


async def get_forecast(city: str, country: str = "IN") -> dict:
    """Fetch 5-day forecast."""
    if not settings.OPENWEATHER_API_KEY:
        return {"error": "OpenWeather API key not configured"}
    
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
            raise Exception(f"Forecast fetch failed: {str(e)}")


async def get_ai_weather_alerts(weather_data: dict, language: str = "english") -> str:
    """Generate AI-powered farming alerts based on weather."""
    messages = [
        {
            "role": "user",
            "content": f"""Based on this weather data for an Indian farmer, generate specific farming alerts and recommendations:

Temperature: {weather_data.get('temperature')}°C
Humidity: {weather_data.get('humidity')}%
Weather: {weather_data.get('description')}
Wind Speed: {weather_data.get('wind_speed')} m/s
Rain probability: {weather_data.get('rain_probability', 0)}%
UV Index: {weather_data.get('uv_index', 'Unknown')}

Generate:
1. Farming alerts (irrigation, spraying, harvesting warnings)
2. Disease risk assessment
3. Recommended farming activities for today
4. Weather-based fertilizer advice
Keep it concise and actionable."""
        }
    ]
    return await get_ai_response(messages, language)


def parse_weather(data: dict) -> dict:
    """Parse OpenWeather API response into clean format."""
    return {
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "temperature": round(data.get("main", {}).get("temp", 0), 1),
        "feels_like": round(data.get("main", {}).get("feels_like", 0), 1),
        "humidity": data.get("main", {}).get("humidity"),
        "pressure": data.get("main", {}).get("pressure"),
        "description": data.get("weather", [{}])[0].get("description", ""),
        "icon": data.get("weather", [{}])[0].get("icon", ""),
        "wind_speed": data.get("wind", {}).get("speed"),
        "visibility": data.get("visibility", 0) // 1000,  # Convert to km
        "clouds": data.get("clouds", {}).get("all"),
        "rain_1h": data.get("rain", {}).get("1h", 0),
        "latitude": data.get("coord", {}).get("lat"),
        "longitude": data.get("coord", {}).get("lon"),
    }
