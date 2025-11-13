from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import select as select_new
from sqlalchemy.orm import selectinload
from typing import List
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.subscription_tier import SubscriptionTier
from app.models.ai_model import AIModel
from app.models.user_model_access import UserModelAccess

router = APIRouter()

class AssignedModel(BaseModel):
    id: int
    name: str
    provider: str
    status: str
    granted_at: str

@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    subscription_tier_name = None
    if current_user.subscription_tier_id:
        stmt = select_new(SubscriptionTier.name).where(SubscriptionTier.id == current_user.subscription_tier_id)
        result = await db.execute(stmt)
        subscription_tier_name = result.scalar_one_or_none()

    return {
        "full_name": current_user.full_name,
        "email": current_user.email,
        "organization_name": current_user.organization_name,
        "subscription_tier_name": subscription_tier_name,
    }

@router.get("/my-models", response_model=List[AssignedModel])
async def get_my_assigned_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all AI models assigned to the current user"""
    stmt = (
        select_new(AIModel, UserModelAccess)
        .join(UserModelAccess, AIModel.id == UserModelAccess.model_id)
        .where(UserModelAccess.user_id == current_user.id)
        .where(UserModelAccess.is_active == True)
        .where(AIModel.status == 'active')  # Only show active models
    )
    result = await db.execute(stmt)
    models_data = result.all()
    
    assigned_models = [
        AssignedModel(
            id=model.id,
            name=model.name,
            provider=model.provider,
            status=model.status,
            granted_at=access.granted_at.isoformat()
        )
        for model, access in models_data
    ]
    
    return assigned_models