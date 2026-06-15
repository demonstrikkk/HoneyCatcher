from fastapi import APIRouter, Depends
from db.mongo import get_collection
from db.models import MessageCreate, MessageInDB
from core.auth import get_current_user
from agents.graph import run_agent

router = APIRouter(prefix="/api/message", tags=["message"])


@router.post("/send")
async def send_message(body: MessageCreate, user=Depends(get_current_user)):
    col_msg = get_collection("messages")

    scammer_msg = MessageInDB(
        session_id=body.session_id,
        sender="scammer",
        content=body.content,
    )
    await col_msg.insert_one(scammer_msg.model_dump())

    history = await col_msg.find(
        {"session_id": body.session_id},
        {"_id": 0, "sender": 1, "content": 1},
        sort=[("timestamp", -1)],
        limit=10,
    ).to_list(10)
    history = [{"speaker": h["sender"], "text": h["content"]} for h in reversed(history)]

    result = await run_agent(
        scammer_text=body.content,
        history=history,
        mode="ai_takeover",
    )

    agent_reply = result.get("ai_response", "I'm sorry, could you repeat that?")

    agent_msg = MessageInDB(
        session_id=body.session_id,
        sender="agent",
        content=agent_reply,
    )
    await col_msg.insert_one(agent_msg.model_dump())

    return {"reply": agent_reply, "intent": result.get("intent"), "strategy": result.get("strategy")}


@router.get("/session/{session_id}")
async def get_messages(session_id: str, user=Depends(get_current_user)):
    docs = await get_collection("messages").find(
        {"session_id": session_id},
        {"_id": 0},
        sort=[("timestamp", 1)],
    ).to_list(500)
    return docs
