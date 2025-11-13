from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.models.discount_rule import DiscountRule, UserDiscountEnrollment, UserNotification
from app.models.user import User
from app.models.ai_model import AIModel
from app.api.deps import get_db

router = APIRouter()

class DiscountRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: int = 100
    user_id: Optional[int] = None
    model_id: Optional[int] = None
    min_requests: int = 0
    max_requests: Optional[int] = None
    discount_percentage: float
    discount_type: str = "percentage"
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    validity_days: Optional[int] = None  # Days valid after enrollment
    auto_apply: bool = False
    max_uses_per_user: Optional[int] = None
    is_active: bool = True

class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    user_id: Optional[int] = None
    model_id: Optional[int] = None
    min_requests: Optional[int] = None
    max_requests: Optional[int] = None
    discount_percentage: Optional[float] = None
    discount_type: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    validity_days: Optional[int] = None
    auto_apply: Optional[bool] = None
    max_uses_per_user: Optional[int] = None
    is_active: Optional[bool] = None

class DiscountRuleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    priority: int
    user_id: Optional[int]
    model_id: Optional[int]
    min_requests: int
    max_requests: Optional[int]
    discount_percentage: float
    discount_type: str
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    validity_days: Optional[int]
    auto_apply: bool
    max_uses_per_user: Optional[int]
    is_active: bool
    created_at: Optional[datetime]
    
    # Additional computed fields
    user_name: Optional[str] = None
    model_name: Optional[str] = None
    enrollment_count: int = 0
    
    class Config:
        from_attributes = True

class EnrollmentStats(BaseModel):
    total_enrollments: int
    active_enrollments: int
    total_usage: int
    users_enrolled: List[dict]

@router.post("/discounts", response_model=DiscountRuleOut)
async def create_discount_rule(payload: DiscountRuleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new discount rule with enhanced features"""
    
    # Validate model and user if specified
    if payload.model_id:
        model = await db.get(AIModel, payload.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    
    if payload.user_id:
        user = await db.get(User, payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Set valid_from to now if not specified
    if not payload.valid_from:
        payload.valid_from = datetime.utcnow()
    
    new_rule = DiscountRule(**payload.model_dump())
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    # Get additional info for response
    result = await _get_discount_rule_with_info(db, new_rule.id)
    return result

@router.get("/discounts", response_model=List[DiscountRuleOut])
async def get_all_discount_rules(
    active_only: bool = Query(False),
    model_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all discount rules with additional information"""
    
    stmt = select(DiscountRule)
    
    if active_only:
        stmt = stmt.where(DiscountRule.is_active == True)
    
    if model_id:
        stmt = stmt.where(DiscountRule.model_id == model_id)
    
    stmt = stmt.order_by(DiscountRule.priority, DiscountRule.created_at.desc())
    
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    # Get additional info for each rule
    enriched_rules = []
    for rule in rules:
        enriched_rule = await _get_discount_rule_with_info(db, rule.id)
        enriched_rules.append(enriched_rule)
    
    return enriched_rules

@router.get("/discounts/{rule_id}", response_model=DiscountRuleOut)
async def get_discount_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific discount rule with additional information"""
    
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    
    return await _get_discount_rule_with_info(db, rule_id)

@router.put("/discounts/{rule_id}", response_model=DiscountRuleOut)
async def update_discount_rule(rule_id: int, payload: DiscountRuleUpdate, db: AsyncSession = Depends(get_db)):
    """Update a discount rule"""
    
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    
    # Validate references if being updated
    if "model_id" in update_data and update_data["model_id"]:
        model = await db.get(AIModel, update_data["model_id"])
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
    
    if "user_id" in update_data and update_data["user_id"]:
        user = await db.get(User, update_data["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(rule)
    
    return await _get_discount_rule_with_info(db, rule_id)

@router.delete("/discounts/{rule_id}", status_code=204)
async def delete_discount_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a discount rule and related enrollments"""
    
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    
    # Delete related enrollments and notifications
    await db.execute(delete(UserDiscountEnrollment).where(UserDiscountEnrollment.discount_rule_id == rule_id))
    await db.execute(delete(UserNotification).where(UserNotification.discount_rule_id == rule_id))
    
    await db.delete(rule)
    await db.commit()
    return None

@router.get("/discounts/{rule_id}/enrollments", response_model=EnrollmentStats)
async def get_discount_enrollments(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Get enrollment statistics for a discount rule"""
    
    # Check if rule exists
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    
    # Get enrollment stats
    enrollments_stmt = select(
        UserDiscountEnrollment,
        User.full_name,
        User.email,
        User.organization_name
    ).join(User).where(UserDiscountEnrollment.discount_rule_id == rule_id)
    
    result = await db.execute(enrollments_stmt)
    enrollments = result.all()
    
    total_enrollments = len(enrollments)
    active_enrollments = len([e for e in enrollments if e.UserDiscountEnrollment.is_active])
    total_usage = sum([e.UserDiscountEnrollment.usage_count for e in enrollments])
    
    users_enrolled = [
        {
            "user_id": e.UserDiscountEnrollment.user_id,
            "full_name": e.full_name,
            "email": e.email,
            "organization_name": e.organization_name,
            "enrolled_at": e.UserDiscountEnrollment.enrolled_at.isoformat(),
            "usage_count": e.UserDiscountEnrollment.usage_count,
            "is_active": e.UserDiscountEnrollment.is_active,
            "valid_until": e.UserDiscountEnrollment.valid_until.isoformat() if e.UserDiscountEnrollment.valid_until else None
        }
        for e in enrollments
    ]
    
    return EnrollmentStats(
        total_enrollments=total_enrollments,
        active_enrollments=active_enrollments,
        total_usage=total_usage,
        users_enrolled=users_enrolled
    )

@router.post("/discounts/{rule_id}/trigger-notifications")
async def trigger_discount_notifications(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger notifications for users who meet the discount criteria"""
    
    rule = await db.get(DiscountRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    
    # This would typically be called by a background job
    # For now, it's a manual trigger for testing
    notifications_created = await _check_and_create_discount_notifications(db, rule)
    
    return {"message": f"Created {notifications_created} notifications"}

# Helper function to get discount rule with additional info
async def _get_discount_rule_with_info(db: AsyncSession, rule_id: int) -> DiscountRuleOut:
    """Get discount rule with additional computed information"""
    
    # Get the rule
    rule = await db.get(DiscountRule, rule_id)
    
    # Get user and model names
    user_name = None
    if rule.user_id:
        user = await db.get(User, rule.user_id)
        user_name = user.full_name if user else None
    
    model_name = None
    if rule.model_id:
        model = await db.get(AIModel, rule.model_id)
        model_name = model.name if model else None
    
    # Get enrollment count
    enrollment_stmt = select(func.count(UserDiscountEnrollment.id)).where(
        UserDiscountEnrollment.discount_rule_id == rule_id
    )
    enrollment_result = await db.execute(enrollment_stmt)
    enrollment_count = enrollment_result.scalar() or 0
    
    # Convert to response model
    rule_data = DiscountRuleOut.model_validate(rule)
    rule_data.user_name = user_name
    rule_data.model_name = model_name
    rule_data.enrollment_count = enrollment_count
    
    return rule_data

# Helper function to check and create notifications
async def _check_and_create_discount_notifications(db: AsyncSession, rule: DiscountRule) -> int:
    """Check users who meet criteria and create notifications"""
    
    # This is a simplified version - you'd implement the actual logic
    # to check user usage against the rule criteria
    
    notifications_created = 0
    
    # For now, just return 0 - implement the actual logic based on your needs
    return notifications_created