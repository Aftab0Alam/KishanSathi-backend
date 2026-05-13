"""
KisanSathi AI — Soil Intelligence Routes
Provides AI-powered soil analysis from uploaded images with crop recommendations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
import base64
from services.soil_service import analyze_soil_image
from services.cloudinary_service import upload_image
from core.security import get_optional_user
from core.mongodb import db_insert, db_find
from loguru import logger

router = APIRouter(prefix="/api/soil", tags=["Soil Intelligence"])


@router.post("/analyze")
async def analyze_soil(
    file: UploadFile = File(...),
    lat:  str = Form(default=""),
    lng:  str = Form(default=""),
    city: str = Form(default=""),
    language: str = Form(default="en"),
    current_user: dict = Depends(get_optional_user),
):
    """Analyze soil image and return soil type, nutrients, and crop recommendations."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

    # Build location context string
    if city:
        location = city
    elif lat and lng:
        location = f"{float(lat):.3f}°N, {float(lng):.3f}°E"
    else:
        location = "India"

    try:
        # Upload to Cloudinary for storage
        image_url = ""
        try:
            upload_result = await upload_image(file_bytes, folder="kisansathi/soil")
            image_url = upload_result.get("url", "")
        except Exception as e:
            logger.warning(f"Cloudinary upload failed (continuing): {e}")

        # Encode for vision model
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

        # Run AI analysis
        analysis = await analyze_soil_image(image_base64, location, language)
        analysis["image_url"] = image_url
        analysis["location"] = location

        # Save to MongoDB
        user_id = current_user.get("user_id", "guest") if current_user else "guest"
        record = {
            "user_id":          user_id,
            "image_url":        image_url,
            "soil_type":        analysis.get("soil_type", "Unknown"),
            "confidence":       analysis.get("confidence", 0),
            "ph":               analysis.get("ph"),
            "organic_matter":   analysis.get("organic_matter"),
            "water_retention":  analysis.get("water_retention"),
            "soil_health_score":analysis.get("soil_health_score"),
            "location":         location,
            "language":         language,
        }
        saved = await db_insert("soil_reports", record)
        if saved:
            analysis["report_id"] = saved.get("id")
            analysis["created_at"] = saved.get("created_at")

        return {"success": True, "analysis": analysis}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Soil analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_soil_history(
    limit: int = 20,
    current_user: dict = Depends(get_optional_user),
):
    """Return the user's past soil analysis reports from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    rows = await db_find("soil_reports", {"user_id": user_id}, limit=limit)
    return {"history": rows, "total": len(rows)}
