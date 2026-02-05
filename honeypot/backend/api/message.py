from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import logging

from core.auth import verify_api_key
from db.mongo import db
from db.models import Session, Message
from services.scam_detector import scam_detector
from services.intelligence_extractor import extraction_service
from core.lifecycle import lifecycle_manager
from agents.graph import agent_system

router = APIRouter()
logger = logging.getLogger("api.message")

class InnerMessage(BaseModel):
    sender: str
    text: str
    timestamp: int

class MessageInput(BaseModel):
    sessionId: str
    message: InnerMessage
    conversationHistory: Optional[List[dict]] = []
    metadata: Optional[dict] = {}

class MessageResponse(BaseModel):
    status: str
    action: str
    reply: Optional[str] = None
    sessionId: str

async def process_background_tasks(session_id: str, message_content: str):
    """
    Background task: Intelligence Extraction & Lifecycle Management.
    """
    # 1. Extract Intelligence
    await extraction_service.extract(session_id, message_content)
    
    # 2. Check Lifecycle (Termination)
    await lifecycle_manager.check_termination(session_id)

@router.post("/message", response_model=MessageResponse)
async def receive_message(
    payload: MessageInput, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Ingests a message, detects scam intent, and returns agent response if active.
    """
    try:
        session_id = payload.sessionId
        incoming_text = payload.message.text
        
        logger.info(f"Received message for session {session_id}: {incoming_text[:50]}...")
        
        # 1. Session Management
        session = None
        session_data = await db.sessions.find_one({"session_id": session_id})
        if not session_data:
            session = Session(session_id=session_id)
            await db.sessions.insert_one(session.model_dump())
            logger.info(f"Created new session: {session_id}")
        else:
            try:
                session = Session(**session_data)
            except Exception as e:
                logger.error(f"Failed to parse session: {e}")
                # Fallback: create fresh session
                session = Session(session_id=session_id)

        if session.status == "terminated":
            return {
                "status": "terminated",
                "action": "none",
                "reply": None,
                "sessionId": session_id
            }

        # Fetch History
        current_history = await db.messages.find({"session_id": session_id}).sort("timestamp", 1).to_list(length=20)
        formatted_history = [{"role": m["sender"], "content": m["content"]} for m in current_history]

        # 2. Persist User Message
        user_msg = Message(
            session_id=session_id,
            sender="scammer",
            content=incoming_text,
            metadata=payload.metadata
        )
        await db.messages.insert_one(user_msg.model_dump())
        
        # 3. Detect Scam
        is_confirmed_scam = session.is_confirmed_scam
        
        if not is_confirmed_scam:
            detection_result = await scam_detector.analyze(incoming_text, formatted_history)
            
            # Update Session
            updates = {
                "scam_score": detection_result["confidence"],
                "last_updated": datetime.utcnow(),
                "message_count": session.message_count + 1
            }
            
            if detection_result["is_scam"]:
                updates["is_confirmed_scam"] = True
                is_confirmed_scam = True
                logger.info(f"🚨 Session {session_id} CONFIRMED SCAM.")
            
            await db.sessions.update_one({"session_id": session_id}, {"$set": updates})
        else:
            await db.sessions.update_one(
                {"session_id": session_id}, 
                {"$inc": {"message_count": 1}, "$set": {"last_updated": datetime.utcnow()}}
            )

        # 4. Agent Engagement
        agent_reply = None
        action_taken = "monitoring"

        if is_confirmed_scam:
            action_taken = "engaged"
            
            # Add current message to history for the agent
            full_history = formatted_history + [{"role": "scammer", "content": incoming_text}]
            
            # Run Agent Graph
            agent_reply = await agent_system.run(full_history)
            
            # Persist Agent Reply
            agent_msg = Message(
                session_id=session_id,
                sender="agent",
                content=agent_reply
            )
            await db.messages.insert_one(agent_msg.model_dump())

        # 5. Background Tasks
        background_tasks.add_task(process_background_tasks, session_id, incoming_text)

        return {
            "status": "success",
            "action": action_taken,
            "reply": agent_reply,
            "sessionId": session_id
        }
    except Exception as e:
        logger.error(f"❌ Message endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
