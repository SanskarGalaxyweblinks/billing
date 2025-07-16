from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.organization import Organization
from app.models.user import User
from app.api.deps import get_db, get_user_info

router = APIRouter()

@router.get("/")
async def get_org_limits(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user by auth_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    org_id = db_user.organization_id

    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "organization_id": org.id,
        "name": org.name,
        "subscription_tier": org.subscription_tier,
        "monthly_request_limit": org.monthly_request_limit,
        "monthly_token_limit": round((org.monthly_token_limit or 0), 2),
        "monthly_cost_limit": float(org.monthly_cost_limit or 0)
    }
