from groq import Groq
from core.config import settings
from loguru import logger
from typing import Optional

client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

LANGUAGE_PROMPTS = {
    "hi": "Please respond in Hindi (Devanagari script). You are KisanSathi AI, a helpful AI farming assistant.",
    "pa": "Please respond in Punjabi (Gurmukhi script). You are KisanSathi AI, a helpful AI farming assistant.",
    "en": "You are KisanSathi AI, a helpful AI farming assistant for Indian farmers.",
    # Legacy fallbacks
    "hindi": "Please respond in Hindi (Devanagari script). You are KisanSathi AI, a helpful AI farming assistant.",
    "punjabi": "Please respond in Punjabi (Gurmukhi script). You are KisanSathi AI, a helpful AI farming assistant.",
    "english": "You are KisanSathi AI, a helpful AI farming assistant for Indian farmers.",
}

SYSTEM_PROMPT = """You are KisanSathi AI — an advanced AI-powered smart farming assistant built for Indian farmers.
You have expertise in:
- Crop diseases, prevention, and treatment
- Fertilizer recommendations (NPK, Urea, DAP, organic alternatives)
- Crop recommendation based on soil, season, climate
- Yield and production prediction
- Weather-based farming decisions
- Irrigation and soil management
- Government agricultural schemes (PM-Kisan, MSP, etc.)
- Organic and sustainable farming practices

Always provide practical, actionable advice. Be empathetic and farmer-friendly.
When unsure, recommend consulting a local agricultural extension officer."""


async def get_ai_response(
    messages: list,
    language: str = "en",
    model: str = "llama-3.1-8b-instant"
) -> str:
    if not client:
        return "AI service is not configured. Please set your GROQ_API_KEY."

    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])
    system_msg = f"{SYSTEM_PROMPT}\n\nLanguage instruction: {lang_instruction}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_msg}] + messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise Exception(f"AI service error: {str(e)}")


async def analyze_plant_disease(image_base64: str, language: str = "english") -> dict:
    """Analyze plant disease from base64 image using Groq vision."""
    if not client:
        return {"error": "AI service not configured"}

    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this plant/crop image and provide:
1. Disease name (if any)
2. Severity level (Low/Medium/High/Critical)
3. Confidence percentage (0-100)
4. Disease description
5. Symptoms observed
6. Treatment recommendations
7. Fertilizer adjustments needed
8. Preventive measures
9. Recommended medicines/pesticides

{lang_instruction}

Respond in JSON format with these exact keys:
{{
  "disease_name": "",
  "severity": "",
  "confidence": 0,
  "description": "",
  "symptoms": [],
  "treatment": "",
  "fertilizer_adjustment": "",
  "prevention_tips": [],
  "recommended_medicines": []
}}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        import json
        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"disease_name": "Analysis complete", "raw_response": content}
    except Exception as e:
        logger.error(f"Disease analysis error: {e}")
        raise Exception(f"Disease analysis failed: {str(e)}")


async def get_fertilizer_recommendation(data: dict, language: str = "english") -> dict:
    """Get AI fertilizer recommendation."""
    if not client:
        return {"error": "AI service not configured"}

    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])
    prompt = f"""Based on this farming data, provide detailed fertilizer recommendations:

Crop: {data.get('crop_type', 'Unknown')}
Soil Type: {data.get('soil_type', 'Unknown')}
State/Location: {data.get('state', 'Unknown')}
Season: {data.get('season', 'Unknown')}
Irrigation Status: {data.get('irrigation', 'Unknown')}
Current Disease (if any): {data.get('disease', 'None')}
Temperature: {data.get('temperature', 'Unknown')}°C
Humidity: {data.get('humidity', 'Unknown')}%

{lang_instruction}

Respond in JSON format:
{{
  "primary_fertilizer": "",
  "quantity_per_acre": "",
  "application_timing": "",
  "npk_ratio": "",
  "organic_alternatives": [],
  "nutrient_schedule": [],
  "weather_warnings": "",
  "application_method": "",
  "expected_improvement": "",
  "cost_estimate": "",
  "ai_tips": []
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        import json
        content = response.choices[0].message.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"raw_response": content}
    except Exception as e:
        logger.error(f"Fertilizer recommendation error: {e}")
        raise Exception(str(e))


async def get_crop_recommendation(data: dict, language: str = "english") -> dict:
    """Get AI crop recommendation."""
    if not client:
        return {"error": "AI service not configured"}

    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])
    prompt = f"""Based on this data, recommend the best crops to grow:

Soil Type: {data.get('soil_type')}
State: {data.get('state')}
District: {data.get('district', 'Unknown')}
Season: {data.get('season')}
Rainfall (mm): {data.get('rainfall')}
Temperature (°C): {data.get('temperature')}
Humidity (%): {data.get('humidity')}
Farm Size (acres): {data.get('farm_size')}

{lang_instruction}

Respond in JSON:
{{
  "recommended_crops": [
    {{
      "crop": "",
      "suitability_score": 0,
      "water_requirement": "",
      "farming_difficulty": "",
      "expected_yield": "",
      "market_price": "",
      "seasonal_fit": "",
      "reason": ""
    }}
  ],
  "companion_crops": [],
  "avoid_crops": [],
  "soil_preparation": "",
  "irrigation_advice": ""
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        import json
        content = response.choices[0].message.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"raw_response": content}
    except Exception as e:
        logger.error(f"Crop recommendation error: {e}")
        raise Exception(str(e))


async def get_yield_prediction(data: dict, language: str = "english") -> dict:
    """Predict crop yield and profit."""
    if not client:
        return {"error": "AI service not configured"}

    lang_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])
    prompt = f"""Predict crop yield, production, and profit based on this data:

Crop: {data.get('crop_type')}
Land Area (acres): {data.get('land_area')}
Soil Type: {data.get('soil_type')}
Rainfall (mm): {data.get('rainfall')}
Temperature (°C): {data.get('temperature')}
Fertilizer Usage: {data.get('fertilizer_usage')}
Irrigation Level: {data.get('irrigation_level')}
State: {data.get('state')}

{lang_instruction}

Respond in JSON:
{{
  "expected_yield_kg_per_acre": 0,
  "total_production_kg": 0,
  "estimated_profit_inr": 0,
  "farming_cost_inr": 0,
  "net_profit_inr": 0,
  "break_even_yield": 0,
  "risk_level": "",
  "risk_factors": [],
  "improvement_tips": [],
  "market_price_per_kg": 0,
  "harvest_timeline": ""
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        import json
        content = response.choices[0].message.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"raw_response": content}
    except Exception as e:
        logger.error(f"Yield prediction error: {e}")
        raise Exception(str(e))
