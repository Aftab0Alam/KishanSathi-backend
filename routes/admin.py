from fastapi import APIRouter, HTTPException, Depends
from core.security import get_optional_user
from core.database import supabase
from loguru import logger

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


def require_admin(current_user: dict = Depends(get_optional_user)) -> dict:
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    """Get platform-wide statistics for admin dashboard."""
    if not supabase:
        return {"stats": {"total_users": 0, "total_disease_reports": 0, "total_chat_history": 0}}
    try:
        stats = {}
        for table in ["users", "disease_reports", "fertilizer_reports", "yield_predictions", "chat_history"]:
            try:
                rows = await supabase.select(table)
                stats[f"total_{table}"] = len(rows)
            except Exception:
                stats[f"total_{table}"] = 0
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users(limit: int = 50, offset: int = 0, admin: dict = Depends(require_admin)):
    """Get all registered users."""
    if not supabase:
        return {"users": [], "total": 0}
    try:
        rows = await supabase.select("farmer_profiles")
        page = rows[offset: offset + limit]
        return {"users": page, "total": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disease-analytics")
async def get_disease_analytics(admin: dict = Depends(require_admin)):
    """Get disease detection analytics."""
    if not supabase:
        return {"analytics": []}
    try:
        rows = await supabase.select("disease_reports")
        disease_counts: dict = {}
        for row in rows:
            disease = row.get("disease", "Unknown")
            disease_counts[disease] = disease_counts.get(disease, 0) + 1
        analytics = [{"disease": k, "count": v} for k, v in sorted(disease_counts.items(), key=lambda x: -x[1])]
        return {"analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity")
async def get_recent_activity(limit: int = 20, admin: dict = Depends(require_admin)):
    """Get recent platform activity."""
    if not supabase:
        return {"recent_diseases": [], "recent_chats": [], "recent_fertilizer": []}
    try:
        disease = await supabase.select("disease_reports")
        chat = await supabase.select("chat_history")
        fertilizer = await supabase.select("fertilizer_reports")
        return {
            "recent_diseases": disease[:5],
            "recent_chats": chat[:5],
            "recent_fertilizer": fertilizer[:5],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
