from fastapi import Request, HTTPException, Depends
from app.database import async_session
import json

async def get_db():
    async with async_session() as session:
        yield session

def get_user_info(request: Request):
    user = getattr(request.state, "user_info", None)
    if not user:
        raise HTTPException(status_code=401, detail="User info missing")
    return user