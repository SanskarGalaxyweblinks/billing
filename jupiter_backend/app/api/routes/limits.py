from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("/")
async def get_limits(
    current_user: User = Depends(get_current_user)
):
    return {
        "user_id": current_user.id,
        "organization_name": current_user.organization_name,
        "subscription_tier": current_user.subscription_tier.name if current_user.subscription_tier else None,
        "monthly_request_limit": current_user.monthly_request_limit,
        "monthly_token_limit": round((current_user.monthly_token_limit or 0), 2),
        "monthly_cost_limit": float(current_user.monthly_cost_limit or 0)
    }