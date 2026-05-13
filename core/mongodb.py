"""
KisanSathi AI - MongoDB Atlas Client (Motor async driver)
Primary database for all persistence: disease reports, fertilizer history,
chat history, crop recommendations, user data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import DESCENDING
from loguru import logger

from core.config import settings

# ── Module-level globals ────────────────────────────────────────────────────
_client: Optional[AsyncIOMotorClient] = None
_db:     Optional[AsyncIOMotorDatabase] = None


async def connect_mongodb() -> None:
    """Connect to MongoDB Atlas. Call once at app startup."""
    global _client, _db

    uri = settings.MONGODB_URI
    if not uri:
        logger.warning("MONGODB_URI not set — MongoDB will be unavailable.")
        return

    try:
        _client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5_000,
            connectTimeoutMS=5_000,
        )
        _db = _client[settings.MONGODB_DB_NAME]

        # Verify connection
        await _client.admin.command("ping")
        logger.info(f"✅ MongoDB Atlas connected → db: '{settings.MONGODB_DB_NAME}'")

        # Create indexes
        await _ensure_indexes()

    except Exception as exc:
        logger.error(f"❌ MongoDB connection failed: {exc}")
        _client = None
        _db = None


async def _ensure_indexes() -> None:
    """Create useful indexes on first connect."""
    if _db is None:
        return
    try:
        await _db["disease_reports"].create_index(
            [("user_id", DESCENDING), ("created_at", DESCENDING)]
        )
        await _db["fertilizer_reports"].create_index(
            [("user_id", DESCENDING), ("created_at", DESCENDING)]
        )
        await _db["chat_history"].create_index(
            [("user_id", DESCENDING), ("created_at", DESCENDING)]
        )
        await _db["crop_reports"].create_index(
            [("user_id", DESCENDING), ("created_at", DESCENDING)]
        )
        await _db["users"].create_index("email", unique=True)
        logger.info("MongoDB indexes ensured.")
    except Exception as exc:
        logger.warning(f"Index creation warning: {exc}")


async def close_mongodb() -> None:
    """Close MongoDB connection. Call at app shutdown."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    """Return the active database handle, or None if not connected."""
    return _db


# ── Convenience helpers ──────────────────────────────────────────────────────

def _new_doc(data: dict) -> dict:
    """Inject id + timestamps into a document before inserting."""
    now = datetime.now(timezone.utc)
    return {
        "_id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
        **data,
    }


async def db_insert(collection: str, data: dict) -> Optional[dict]:
    """Insert one document and return it."""
    if _db is None:
        logger.debug("MongoDB not available — skipping insert.")
        return None
    try:
        doc = _new_doc(data)
        await _db[collection].insert_one(doc)
        doc["id"] = doc.pop("_id")          # normalise id key for API responses
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        logger.debug(f"MongoDB insert [{collection}] id={doc['id']}")
        return doc
    except Exception as exc:
        logger.warning(f"MongoDB insert failed [{collection}]: {exc}")
        return None


async def db_find(
    collection: str,
    filters: dict,
    limit: int = 50,
    sort_by: str = "created_at",
) -> list[dict]:
    """Find documents matching filters, newest first."""
    if _db is None:
        return []
    try:
        cursor = (
            _db[collection]
            .find(filters)
            .sort(sort_by, DESCENDING)
            .limit(limit)
        )
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            if isinstance(doc.get("updated_at"), datetime):
                doc["updated_at"] = doc["updated_at"].isoformat()
            results.append(doc)
        return results
    except Exception as exc:
        logger.warning(f"MongoDB find failed [{collection}]: {exc}")
        return []


async def db_find_one(collection: str, filters: dict) -> Optional[dict]:
    """Find a single document."""
    if _db is None:
        return None
    try:
        doc = await _db[collection].find_one(filters)
        if doc:
            doc["id"] = str(doc.pop("_id"))
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
        return doc
    except Exception as exc:
        logger.warning(f"MongoDB find_one failed [{collection}]: {exc}")
        return None


async def db_update(collection: str, filters: dict, data: dict) -> bool:
    """Update first matching document."""
    if _db is None:
        return False
    try:
        data["updated_at"] = datetime.now(timezone.utc)
        result = await _db[collection].update_one(filters, {"$set": data})
        return result.modified_count > 0
    except Exception as exc:
        logger.warning(f"MongoDB update failed [{collection}]: {exc}")
        return False


async def db_delete(collection: str, filters: dict) -> bool:
    """Delete first matching document."""
    if _db is None:
        return False
    try:
        result = await _db[collection].delete_one(filters)
        return result.deleted_count > 0
    except Exception as exc:
        logger.warning(f"MongoDB delete failed [{collection}]: {exc}")
        return False


async def db_count(collection: str, filters: dict | None = None) -> int:
    """Count documents in a collection."""
    if _db is None:
        return 0
    try:
        return await _db[collection].count_documents(filters or {})
    except Exception as exc:
        logger.warning(f"MongoDB count failed [{collection}]: {exc}")
        return 0
