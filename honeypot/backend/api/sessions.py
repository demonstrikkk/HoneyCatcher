from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from db.mongo import db
from db.models import Session
from core.auth import verify_api_key

router = APIRouter()

@router.get("/sessions", response_model=List[dict])
async def list_sessions(
    voiceEnabled: Optional[bool] = None,
    language: Optional[str] = None,
    minScamScore: Optional[float] = None,
    voiceMode: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    query = {}
    if voiceEnabled is not None:
        query["voice_enabled"] = voiceEnabled
    if language:
        query["detected_language"] = language
    if minScamScore is not None:
        query["scam_score"] = {"$gte": minScamScore}
    if voiceMode:
        query["voice_mode"] = voiceMode

    cursor = db.sessions.find(query).sort("last_updated", -1).limit(50)
    sessions = await cursor.to_list(length=50)
    # Fix serialization: convert _id to string or remove it
    for s in sessions:
        if "_id" in s:
            s["id"] = str(s["_id"])
            del s["_id"]
    return sessions

@router.get("/sessions/{session_id}")
async def get_session(session_id: str, api_key: str = Depends(verify_api_key)):
    session = await db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Also fetch messages
    messages = await db.messages.find({"session_id": session_id}).sort("timestamp", 1).to_list(length=100)
    
    # Fix serialization for session
    if "_id" in session:
        session["id"] = str(session["_id"])
        del session["_id"]
        
    # Fix serialization for messages
    for msg in messages:
        if "_id" in msg:
            msg["id"] = str(msg["_id"])
            del msg["_id"]

    session["history"] = messages
    return session
