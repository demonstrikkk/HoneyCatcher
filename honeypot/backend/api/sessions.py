from fastapi import APIRouter, Depends, HTTPException
from db.mongo import get_collection
from db.models import SessionCreate, SessionInDB
from core.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(body: SessionCreate, user=Depends(get_current_user)):
    session = SessionInDB(
        user_id=user["sub"],
        scammer_phone=body.scammer_phone,
        operator_name=body.operator_name,
        metadata={"call_type": body.call_type},
    )
    await get_collection("sessions").insert_one(session.model_dump())
    return {"session_id": session.session_id}


@router.get("")
async def list_sessions(user=Depends(get_current_user)):
    col = get_collection("sessions")
    docs = await col.find(
        {"user_id": user["sub"]},
        {"_id": 0},
        sort=[("created_at", -1)],
        limit=50
    ).to_list(50)
    return docs


@router.get("/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user)):
    doc = await get_collection("sessions").find_one(
        {"session_id": session_id, "user_id": user["sub"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Session not found")
    return doc


@router.delete("/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    await get_collection("sessions").delete_one(
        {"session_id": session_id, "user_id": user["sub"]}
    )
    return {"deleted": session_id}
