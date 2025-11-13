from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional

from app.models.discount_rule import DiscountRule
from app.api.deps import get_db

router = APIRouter()

class DiscountRuleCreate(BaseModel):
    name: str
    priority: int = 100
    user_id: Optional[int] = None
    model_id: Optional[int] = None
    min_requests: int = 0
    max_requests: Optional[int] = None
    discount_percentage: float
    is_active: bool = True

class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[int] = None
    user_id: Optional[int] = None
    model_id: Optional[int] = None
    min_requests: Optional[int] = None
    max_requests: Optional[int] = None
    discount_percentage: Optional[float] = None
    is_active: Optional[bool] = None

class DiscountRuleOut(DiscountRuleCreate):
    id: int

    class Config:
        from_attributes = True

@router.post("/discounts", response_model=DiscountRuleOut)
async def create_discount_rule(payload: DiscountRuleCreate, db: AsyncSession = Depends(get_db)):
    new_rule = DiscountRule(**payload.model_dump())
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule

@router.get("/discounts", response_model=List[DiscountRuleOut])
async def get_all_discount_rules(db: AsyncSession = Depends(get_db)):
    stmt = select(DiscountRule).order_by(DiscountRule.priority)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/discounts/{rule_id}", response_model=DiscountRuleOut)
async def get_discount_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    return rule

@router.put("/discounts/{rule_id}", response_model=DiscountRuleOut)
async def update_discount_rule(rule_id: int, payload: DiscountRuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/discounts/{rule_id}", status_code=204)
async def delete_discount_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    
    await db.delete(rule)
    await db.commit()
    return None