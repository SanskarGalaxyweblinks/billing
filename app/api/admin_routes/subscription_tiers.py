from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.subscription_tier import SubscriptionTier
from app.api.deps import get_db

router = APIRouter()

@router.get("/subscription-tiers")
async def get_subscription_tiers(db: AsyncSession = Depends(get_db)):
    stmt = select(SubscriptionTier).where(SubscriptionTier.is_active == True)
    result = await db.execute(stmt)
    tiers = result.scalars().all()

    return [
        {
            "id": tier.id,
            "name": tier.name,
            "monthly_cost": float(tier.monthly_cost),
            "plan_details": tier.plan_details
        }
        for tier in tiers
    ]
