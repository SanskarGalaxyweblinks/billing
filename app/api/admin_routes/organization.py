from fastapi import APIRouter, Request, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.organization import Organization
from app.api.deps import get_db
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import joinedload
from app.models.subscription_tier import SubscriptionTier

router = APIRouter()

# ------------------- Pydantic Schemas -------------------

class OrganizationStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    subscription_tier_id: Optional[int] = None
    monthly_request_limit: Optional[int] = 0
    monthly_token_limit: Optional[int] = 0
    monthly_cost_limit: Optional[Decimal] = 0.0
    status: Optional[OrganizationStatus] = OrganizationStatus.active


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    subscription_tier_id: Optional[int] = None
    monthly_request_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    monthly_cost_limit: Optional[Decimal] = None
    status: Optional[OrganizationStatus] = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    subscription_tier_id: Optional[int]
    subscription_tier_name: Optional[str] = None  # ✅ for convenience in frontend
    monthly_request_limit: Optional[int]
    monthly_token_limit: Optional[int]
    monthly_cost_limit: Optional[Decimal]
    status: OrganizationStatus

    class Config:
        orm_mode = True


# ------------------- CRUD Endpoints -------------------

@router.get("/organizations", response_model=List[OrganizationOut])
async def get_all_organizations(db: AsyncSession = Depends(get_db)):
    stmt = select(Organization).options(joinedload(Organization.subscription_tier))
    result = await db.execute(stmt)
    orgs = result.scalars().all()

    # Attach tier name manually
    return [
        OrganizationOut(
            **org.__dict__,
            subscription_tier_name=org.subscription_tier.name if org.subscription_tier else None
        )
        for org in orgs
    ]


@router.get("/organizations/{org_id}", response_model=OrganizationOut)
async def get_organization_by_id(org_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Organization).options(joinedload(Organization.subscription_tier)).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationOut(
        **org.__dict__,
        subscription_tier_name=org.subscription_tier.name if org.subscription_tier else None
    )


@router.post("/organizations", response_model=OrganizationOut)
async def create_organization(payload: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    org = Organization(**payload.dict(exclude_unset=True))
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.put("/organizations/{org_id}", response_model=OrganizationOut)
async def update_organization(org_id: int, payload: OrganizationUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(org)
    await db.commit()
    return {"detail": "Organization deleted successfully"}
