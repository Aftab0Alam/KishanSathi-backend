"""
KisanSathi AI — Soil Analysis Service
Uses Groq vision to detect soil type, nutrients, pH, and recommend crops.
"""
import json
from loguru import logger
from groq import Groq
from core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

SYSTEM_PROMPT = """You are KisanSathi Soil Expert — an advanced AI soil scientist for Indian farmers.
You analyze soil photos and provide actionable farming recommendations."""


async def analyze_soil_image(image_base64: str, location: str = "", language: str = "en") -> dict:
    """Analyze soil image using Groq vision AI and return detailed soil report."""
    if not client:
        raise Exception("AI service not configured. Please set GROQ_API_KEY.")

    location_context = f"\nLocation context: {location}" if location else ""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this soil photo from an Indian farm and provide a complete soil intelligence report.{location_context}

Respond ONLY with a valid JSON object using these exact keys:
{{
  "soil_type": "one of: Clay, Sandy, Loamy, Black Cotton, Red, Alluvial, Laterite, Saline",
  "confidence": <integer 60-98>,
  "ph": <float between 4.0 and 9.0>,
  "organic_matter": "<Low/Medium/High> (<percentage>%)",
  "water_retention": "Poor/Moderate/Good/Excellent",
  "drainage": "Poor/Moderate/Well-drained/Excessive",
  "nitrogen": "<Low/Medium/High>",
  "phosphorus": "<Low/Medium/High>",
  "potassium": "<Low/Medium/High>",
  "texture": "<description>",
  "color_analysis": "<what the color indicates>",
  "soil_health_score": <integer 40-95>,
  "location": "{location}",
  "crop_recommendations": [
    {{
      "crop": "<crop name in English and Hindi>",
      "season": "<Kharif/Rabi/Year Round> (<months>)",
      "water": "Low/Medium/High",
      "fertilizer": "NPK <N>-<P>-<K>",
      "yield": "<range> q/acre",
      "profit_per_acre": "<estimate in INR>",
      "suitability": <integer 70-99>
    }}
  ],
  "soil_improvement_tips": ["<tip1>", "<tip2>", "<tip3>"],
  "warnings": "<any soil health warnings, or null>"
}}

Provide exactly 4 crop recommendations best suited for this soil type in India."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            temperature=0.2,
            max_tokens=1500,
        )

        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
            # Ensure crop_recommendations is always a list
            if "crop_recommendations" not in result:
                result["crop_recommendations"] = []
            return result
        raise Exception("Could not parse AI response as JSON")

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in soil analysis: {e}")
        raise Exception("AI returned invalid response format. Please try again.")
    except Exception as e:
        logger.error(f"Soil analysis error: {e}")
        raise Exception(f"Soil analysis failed: {str(e)}")
