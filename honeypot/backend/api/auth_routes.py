from fastapi import APIRouter, HTTPException, status, Depends
from db.mongo import get_collection
from db.models import UserCreate, UserInDB, UserOut
from core.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(body: UserCreate):
    col = get_collection("users")
    if await col.find_one({"username": body.username}):
        raise HTTPException(400, "Username already taken")

    user = UserInDB(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    await col.insert_one(user.model_dump())
    return {"message": "registered", "user_id": user.user_id}


@router.post("/login")
async def login(body: UserCreate):
    col = get_collection("users")
    doc = await col.find_one({"username": body.username})
    if not doc or not verify_password(body.password, doc["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    await col.update_one(
        {"username": body.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    payload = {"sub": doc["user_id"], "username": doc["username"]}
    return {
        "access_token":  create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type":    "bearer",
    }


@router.post("/refresh")
async def refresh(body: dict):
    token = body.get("refresh_token", "")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")
    new_token = create_access_token({"sub": payload["sub"], "username": payload["username"]})
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    col = get_collection("users")
    doc = await col.find_one({"user_id": user["sub"]})
    if not doc:
        raise HTTPException(404, "User not found")
    return UserOut(**doc)
