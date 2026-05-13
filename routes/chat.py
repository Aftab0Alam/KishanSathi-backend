from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import List, Optional
from services.groq_service import get_ai_response
from core.security import get_optional_user
from core.mongodb import db_insert, db_find, db_delete
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["AI Chatbot"])


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    language: str = "en"
    save_history: bool = True


class ChatResponse(BaseModel):
    response: str
    language: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_optional_user)):
    """Send message to KisanSathi AI chatbot."""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        response = await get_ai_response(messages, request.language)

        # Save to MongoDB
        if request.save_history and messages:
            user_id = current_user.get("user_id", "guest") if current_user else "guest"
            last_msg = messages[-1]
            await db_insert("chat_history", {
                "user_id": user_id, "role": "user",
                "content": last_msg["content"], "language": request.language
            })
            await db_insert("chat_history", {
                "user_id": user_id, "role": "assistant",
                "content": response, "language": request.language
            })

        return ChatResponse(response=response, language=request.language)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(limit: int = 50, current_user: dict = Depends(get_optional_user)):
    """Get user's chat history from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    rows = await db_find("chat_history", {"user_id": user_id}, limit=limit, sort_by="created_at")
    return {"messages": rows}


@router.delete("/history")
async def clear_chat_history(current_user: dict = Depends(get_optional_user)):
    """Clear user's chat history from MongoDB."""
    user_id = current_user.get("user_id", "guest") if current_user else "guest"
    await db_delete("chat_history", {"user_id": user_id})
    return {"message": "Chat history cleared successfully"}
