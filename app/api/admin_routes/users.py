from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.models.user import User
from app.models.organization import Organization
from app.api.deps import get_db
from pydantic import BaseModel

class AssignOrganizationRequest(BaseModel):
    user_id: int
    organization_id: Optional[int] = None 

router = APIRouter()

@router.get("/users")
async def get_all_users(request: Request, db: AsyncSession = Depends(get_db)):
    # For now: no auth check – open to all
    # In future: Add admin token validation here

    # Query all users
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Format and return users
    return [
        {
            "id": user.id,
            "auth_id": user.auth_id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "organization_id": user.organization_id,
        }
        for user in users
    ]


@router.post("/users/assign-organization")
async def assign_user_to_organization(
    payload: AssignOrganizationRequest,
    db: AsyncSession = Depends(get_db)
):
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If organization_id is provided (not None), validate it exists
    if payload.organization_id is not None:
        org_result = await db.execute(
            select(Organization).where(Organization.id == payload.organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

    # Assign or unassign organization
    user.organization_id = payload.organization_id
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Organization updated successfully",
        "user_id": user.id,
        "organization_id": user.organization_id
    }
