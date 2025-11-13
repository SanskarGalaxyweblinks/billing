from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.subscription_tier import SubscriptionTier

router = APIRouter()

@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    subscription_tier_name = None
    if current_user.subscription_tier_id:
        stmt = select(SubscriptionTier.name).where(SubscriptionTier.id == current_user.subscription_tier_id)
        result = await db.execute(stmt)
        subscription_tier_name = result.scalar_one_or_none()

    return {
        "full_name": current_user.full_name,
        "email": current_user.email,
        "organization_name": current_user.organization_name,
        "subscription_tier_name": subscription_tier_name,
    }