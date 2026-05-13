"""
KisanSathi AI — User Profile Routes
Stores farmer profile data in MongoDB `user_profiles` collection.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from core.security import get_current_user, get_optional_user
from core.mongodb import db_find_one, db_insert, db_update, get_db

router = APIRouter(prefix="/api/profile", tags=["User Profile"])


# ── Schema ──────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name:         Optional[str] = Field(None, max_length=100)
    phone:        Optional[str] = Field(None, max_length=20)
    location:     Optional[str] = Field(None, max_length=200)
    farm_size:    Optional[str] = Field(None, max_length=50)
    primary_crop: Optional[str] = Field(None, max_length=100)
    avatar_url:   Optional[str] = Field(None, max_length=500)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_profile(user_id: str) -> Optional[dict]:
    doc = await db_find_one("user_profiles", {"user_id": user_id})
    if doc:
        doc.pop("_id", None)
    return doc


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Return the logged-in user's profile from MongoDB."""
    user_id = current_user["user_id"]
    profile = await _get_profile(user_id)
    if not profile:
        # Return a minimal default so frontend never gets 404
        return {
            "user_id":     user_id,
            "email":       current_user.get("email", ""),
            "name":        current_user.get("email", "").split("@")[0] if current_user.get("email") else "Kisan",
            "phone":       "",
            "location":    "",
            "farm_size":   "",
            "primary_crop": "",
            "avatar_url":  "",
        }
    return profile


@router.put("/me")
async def update_my_profile(
    data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update the logged-in user's profile in MongoDB."""
    user_id = current_user["user_id"]
    db = get_db()

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    existing = await _get_profile(user_id)
    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if existing:
        # Update existing document
        updated = await db_update(
            "user_profiles",
            {"user_id": user_id},
            update_data,
        )
        if not updated:
            # Document exists but nothing changed — still return success
            logger.debug(f"Profile unchanged for user {user_id}")
        profile = await _get_profile(user_id)
    else:
        # Insert new document
        profile = await db_insert("user_profiles", {
            "user_id": user_id,
            "email":   current_user.get("email", ""),
            **update_data,
        })

    logger.info(f"Profile saved for user_id={user_id}")
    return {"message": "Profile saved successfully", "profile": profile}
