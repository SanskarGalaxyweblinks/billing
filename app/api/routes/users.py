from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.api.deps import get_db, get_user_info
from pydantic import BaseModel
from app.models.user import User as DBUser  # Adjust import based on your model file structure
from app.models.organization import Organization
router = APIRouter()
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional


class UserCreate(BaseModel):
    id: str  # Supabase user ID
    email: str
    full_name: str
    # email_verified: bool

class UserDetailsResponse(BaseModel):
    id: int
    auth_id: str
    email: str
    full_name: str
    organization_id: int
    organization_name: str | None
    subscription_tier_name: Optional[str] 

@router.post("/")
async def create_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = get_user_info(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    try:
        stmt = pg_insert(DBUser).values(
            auth_id=user_data.id,
            email=user_data.email,
            full_name=user_data.full_name,
        ).on_conflict_do_nothing(index_elements=['auth_id'])

        await db.execute(stmt)
        await db.commit()
        return {"success": True}

    except Exception as e:
        print("DB Insert Error:", e)
        raise HTTPException(status_code=500, detail="DB insert failed")


@router.get("/me", response_model=UserDetailsResponse)
async def get_user_details(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_info = get_user_info(request)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # Load user -> organization -> subscription_tier using joinedload
    stmt = (
        select(DBUser)
        .options(
            joinedload(DBUser.organization).joinedload(Organization.subscription_tier)
        )
        .where(DBUser.auth_id == user_info["sub"])
    )

    result = await db.execute(stmt)
    user: DBUser = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org_name = None
    tier_name = None

    if user.organization:
        org_name = user.organization.name
        if user.organization.subscription_tier:
            tier_name = user.organization.subscription_tier.name

    return UserDetailsResponse(
        id=user.id,
        auth_id=user.auth_id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
        organization_name=org_name,
        subscription_tier_name=tier_name 
    )