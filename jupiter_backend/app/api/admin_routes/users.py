from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal

from app.models.user import User
from app.api.deps import get_db

router = APIRouter()

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    subscription_tier_id: Optional[int] = None
    monthly_request_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    monthly_cost_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    auth_id: str
    email: str
    full_name: str
    is_active: bool
    created_at: Optional[str]
    organization_name: Optional[str]
    subscription_tier_id: Optional[int]
    monthly_request_limit: Optional[int]
    monthly_token_limit: Optional[int]
    monthly_cost_limit: Optional[Decimal]

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    """
    Fetches all users from the database.
    This is an admin-only endpoint.
    """
    stmt = select(User).order_by(User.id)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "auth_id": user.auth_id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "organization_name": user.organization_name,
            "subscription_tier_id": user.subscription_tier_id,
            "monthly_request_limit": user.monthly_request_limit,
            "monthly_token_limit": user.monthly_token_limit,
            "monthly_cost_limit": user.monthly_cost_limit,
        }
        for user in users
    ]

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates a user's details.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "auth_id": user.auth_id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "organization_name": user.organization_name,
        "subscription_tier_id": user.subscription_tier_id,
        "monthly_request_limit": user.monthly_request_limit,
        "monthly_token_limit": user.monthly_token_limit,
        "monthly_cost_limit": user.monthly_cost_limit,
    }