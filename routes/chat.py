from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from services.groq_service import get_ai_response
from core.security import get_current_user
from core.mongodb import db_insert, db_find, db_delete
from loguru import logger

router = APIRouter(
    prefix="/api/chat",
    tags=["AI Chatbot"]
)


# ─────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    language: str = "en"
    save_history: bool = True


class ChatResponse(BaseModel):
    response: str
    language: str


# ─────────────────────────────────────────────────────────────
# Chat API
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send message to KisanSathi AI chatbot."""

    try:

        user_id = current_user["user_id"]

        messages = [
            {
                "role": m.role,
                "content": m.content
            }
            for m in request.messages
        ]

        response = await get_ai_response(
            messages,
            request.language
        )

        # Save chat history
        if request.save_history and messages:

            last_msg = messages[-1]

            # Save user message
            await db_insert(
                "chat_history",
                {
                    "user_id": user_id,
                    "role": "user",
                    "content": last_msg["content"],
                    "language": request.language,
                }
            )

            # Save assistant response
            await db_insert(
                "chat_history",
                {
                    "user_id": user_id,
                    "role": "assistant",
                    "content": response,
                    "language": request.language,
                }
            )

        return ChatResponse(
            response=response,
            language=request.language
        )

    except Exception as e:

        logger.error(f"Chat error: {e}")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ─────────────────────────────────────────────────────────────
# Get Chat History
# ─────────────────────────────────────────────────────────────

@router.get("/history")
async def get_chat_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get logged-in user's chat history."""

    try:

        user_id = current_user["user_id"]

        rows = await db_find(
            "chat_history",
            {"user_id": user_id},
            limit=limit,
            sort_by="created_at"
        )

        return {
            "messages": rows
        }

    except Exception as e:

        logger.error(f"History fetch error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch chat history"
        )


# ─────────────────────────────────────────────────────────────
# Clear Chat History
# ─────────────────────────────────────────────────────────────

@router.delete("/history")
async def clear_chat_history(
    current_user: dict = Depends(get_current_user)
):
    """Clear logged-in user's chat history."""

    try:

        user_id = current_user["user_id"]

        await db_delete(
            "chat_history",
            {"user_id": user_id}
        )

        return {
            "message": "Chat history cleared successfully"
        }

    except Exception as e:

        logger.error(f"History delete error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to clear chat history"
        )