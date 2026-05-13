from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
import base64
from services.groq_service import analyze_plant_disease
from services.cloudinary_service import upload_image
from core.security import get_optional_user
from core.mongodb import db_insert, db_find, db_find_one
from loguru import logger

router = APIRouter(prefix="/api/disease", tags=["Disease Detection"])


@router.post("/analyze")
async def analyze_disease(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    current_user: dict = Depends(get_optional_user)
):
    """Upload and analyze plant/leaf image for disease detection."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

    try:
        # Upload to Cloudinary
        upload_result = await upload_image(file_bytes, folder="kisansathi/disease")
        image_url = upload_result.get("url", "")

        # Encode image for AI analysis
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

        # Analyze with Groq AI
        analysis = await analyze_plant_disease(image_base64, language)
        analysis["image_url"] = image_url

        # Save to MongoDB
        report_data = {
            "user_id": current_user.get("user_id", "guest") if current_user else "guest",
            "image_url": image_url,
            "disease_name": analysis.get("disease_name", "Unknown"),
            "severity": analysis.get("severity", "Unknown"),
            "confidence": analysis.get("confidence", 0),
            "treatment": analysis.get("treatment", ""),
            "description": analysis.get("description", ""),
            "prevention_tips": analysis.get("prevention_tips", []),
            "crop_type": analysis.get("crop_type", ""),
            "language": language,
        }
        saved = await db_insert("disease_reports", report_data)
        if saved:
            analysis["report_id"] = saved.get("id")
            analysis["created_at"] = saved.get("created_at")

        return {"success": True, "analysis": analysis, "image_url": image_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disease analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def get_disease_reports(limit: int = 20, current_user: dict = Depends(get_optional_user)):
    """Get user's disease detection history from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    rows = await db_find("disease_reports", {"user_id": user_id}, limit=limit)
    return {"reports": rows}


@router.get("/reports/{report_id}")
async def get_disease_report(report_id: str, current_user: dict = Depends(get_optional_user)):
    """Get a specific disease report by ID."""
    doc = await db_find_one("disease_reports", {"_id": report_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    return doc
