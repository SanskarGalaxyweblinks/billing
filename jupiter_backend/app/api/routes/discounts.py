from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, update
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.models.discount_rule import DiscountRule, UserDiscountEnrollment, UserNotification
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.api_usage_log import APIUsageLog
from app.api.deps import get_db, get_current_user

router = APIRouter()

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    discount_rule_id: Optional[int]
    extra_data: Optional[str]  # FIXED: Changed from 'metadata' to 'extra_data'
    is_read: bool
    is_popup_shown: bool
    created_at: datetime
    
    # Additional discount info if applicable
    discount_name: Optional[str] = None
    discount_percentage: Optional[float] = None
    
    class Config:
        from_attributes = True

class AvailableDiscountOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    discount_percentage: float
    model_name: Optional[str]
    min_requests: int
    max_requests: Optional[int]
    valid_until: Optional[datetime]
    validity_days: Optional[int]
    can_enroll: bool
    usage_progress: int  # How many requests user has made
    
    class Config:
        from_attributes = True

class EnrolledDiscountOut(BaseModel):
    id: int
    discount_rule_id: int
    discount_name: str
    discount_percentage: float
    enrolled_at: datetime
    valid_until: Optional[datetime]
    usage_count: int
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/notifications", response_model=List[NotificationOut])
async def get_user_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current user"""
    
    stmt = select(UserNotification).where(UserNotification.user_id == current_user.id)
    
    if unread_only:
        stmt = stmt.where(UserNotification.is_read == False)
    
    stmt = stmt.order_by(UserNotification.created_at.desc())
    
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    # Enrich notifications with discount info
    enriched_notifications = []
    for notification in notifications:
        notification_data = NotificationOut.model_validate(notification)
        
        if notification.discount_rule_id:
            discount_rule = await db.get(DiscountRule, notification.discount_rule_id)
            if discount_rule:
                notification_data.discount_name = discount_rule.name
                notification_data.discount_percentage = float(discount_rule.discount_percentage)
        
        enriched_notifications.append(notification_data)
    
    return enriched_notifications

@router.get("/notifications/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications"""
    
    stmt = select(func.count(UserNotification.id)).where(
        and_(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read == False
        )
    )
    
    result = await db.execute(stmt)
    count = result.scalar() or 0
    
    return {"unread_count": count}

@router.put("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    
    notification = await db.get(UserNotification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Notification marked as read"}

@router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for current user"""
    
    stmt = update(UserNotification).where(
        and_(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read == False
        )
    ).values(
        is_read=True,
        read_at=datetime.utcnow()
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return {"message": f"Marked {result.rowcount} notifications as read"}

@router.get("/available-discounts", response_model=List[AvailableDiscountOut])
async def get_available_discounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get discounts available for the current user to enroll in"""
    
    # Get active discount rules that apply to this user
    stmt = select(DiscountRule).where(
        and_(
            DiscountRule.is_active == True,
            or_(
                DiscountRule.user_id == current_user.id,
                DiscountRule.user_id.is_(None)  # Global rules
            ),
            or_(
                DiscountRule.valid_until.is_(None),
                DiscountRule.valid_until > datetime.utcnow()
            )
        )
    )
    
    result = await db.execute(stmt)
    discount_rules = result.scalars().all()
    
    available_discounts = []
    
    for rule in discount_rules:
        # Check if user is already enrolled
        enrollment_stmt = select(UserDiscountEnrollment).where(
            and_(
                UserDiscountEnrollment.user_id == current_user.id,
                UserDiscountEnrollment.discount_rule_id == rule.id,
                UserDiscountEnrollment.is_active == True
            )
        )
        enrollment_result = await db.execute(enrollment_stmt)
        existing_enrollment = enrollment_result.scalar_one_or_none()
        
        can_enroll = existing_enrollment is None
        
        # Get user's current usage for this model (if model-specific)
        usage_count = 0
        if rule.model_id:
            # Get current month's usage for this model
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage_stmt = select(func.count(APIUsageLog.id)).where(
                and_(
                    APIUsageLog.user_id == current_user.id,
                    APIUsageLog.model_id == rule.model_id,
                    APIUsageLog.created_at >= start_of_month
                )
            )
            usage_result = await db.execute(usage_stmt)
            usage_count = usage_result.scalar() or 0
        
        # Get model name if applicable
        model_name = None
        if rule.model_id:
            model = await db.get(AIModel, rule.model_id)
            model_name = model.name if model else None
        
        discount_data = AvailableDiscountOut(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            discount_percentage=float(rule.discount_percentage),
            model_name=model_name,
            min_requests=rule.min_requests,
            max_requests=rule.max_requests,
            valid_until=rule.valid_until,
            validity_days=rule.validity_days,
            can_enroll=can_enroll,
            usage_progress=usage_count
        )
        
        available_discounts.append(discount_data)
    
    return available_discounts

@router.get("/my-discounts", response_model=List[EnrolledDiscountOut])
async def get_my_enrolled_discounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get discounts the current user is enrolled in"""
    
    stmt = select(
        UserDiscountEnrollment,
        DiscountRule.name,
        DiscountRule.discount_percentage
    ).join(DiscountRule).where(
        UserDiscountEnrollment.user_id == current_user.id
    ).order_by(UserDiscountEnrollment.enrolled_at.desc())
    
    result = await db.execute(stmt)
    enrollments = result.all()
    
    enrolled_discounts = [
        EnrolledDiscountOut(
            id=enrollment.UserDiscountEnrollment.id,
            discount_rule_id=enrollment.UserDiscountEnrollment.discount_rule_id,
            discount_name=enrollment.name,
            discount_percentage=float(enrollment.discount_percentage),
            enrolled_at=enrollment.UserDiscountEnrollment.enrolled_at,
            valid_until=enrollment.UserDiscountEnrollment.valid_until,
            usage_count=enrollment.UserDiscountEnrollment.usage_count,
            is_active=enrollment.UserDiscountEnrollment.is_active
        )
        for enrollment in enrollments
    ]
    
    return enrolled_discounts

@router.post("/discounts/{discount_id}/enroll")
async def enroll_in_discount(
    discount_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll current user in a discount"""
    
    # Get the discount rule
    discount_rule = await db.get(DiscountRule, discount_id)
    if not discount_rule or not discount_rule.is_active:
        raise HTTPException(status_code=404, detail="Discount not found or inactive")
    
    # Check if discount is still valid
    if discount_rule.valid_until and discount_rule.valid_until < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Discount has expired")
    
    # Check if user is eligible (global or user-specific)
    if discount_rule.user_id and discount_rule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not eligible for this discount")
    
    # Check if already enrolled
    existing_stmt = select(UserDiscountEnrollment).where(
        and_(
            UserDiscountEnrollment.user_id == current_user.id,
            UserDiscountEnrollment.discount_rule_id == discount_id,
            UserDiscountEnrollment.is_active == True
        )
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already enrolled in this discount")
    
    # Calculate validity period for enrollment
    valid_until = None
    if discount_rule.validity_days:
        valid_until = datetime.utcnow() + timedelta(days=discount_rule.validity_days)
    elif discount_rule.valid_until:
        valid_until = discount_rule.valid_until
    
    # Create enrollment
    enrollment = UserDiscountEnrollment(
        user_id=current_user.id,
        discount_rule_id=discount_id,
        valid_until=valid_until,
        is_active=True
    )
    
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    
    # Create success notification
    notification = UserNotification(
        user_id=current_user.id,
        title="Discount Enrolled!",
        message=f"You've successfully enrolled in {discount_rule.name}. Enjoy {discount_rule.discount_percentage}% off!",
        notification_type="discount",
        discount_rule_id=discount_id,
        is_popup_shown=True  # This will trigger a popup
    )
    
    db.add(notification)
    await db.commit()
    
    return {
        "message": "Successfully enrolled in discount",
        "enrollment_id": enrollment.id,
        "valid_until": valid_until.isoformat() if valid_until else None
    }

@router.get("/popup-notifications", response_model=List[NotificationOut])
async def get_popup_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications that should be shown as popups (one-time)"""
    
    stmt = select(UserNotification).where(
        and_(
            UserNotification.user_id == current_user.id,
            UserNotification.is_popup_shown == False,
            UserNotification.notification_type == "discount"
        )
    ).order_by(UserNotification.created_at.desc())
    
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    # Mark as popup shown
    if notifications:
        notification_ids = [n.id for n in notifications]
        update_stmt = update(UserNotification).where(
            UserNotification.id.in_(notification_ids)
        ).values(is_popup_shown=True)
        
        await db.execute(update_stmt)
        await db.commit()
    
    # Enrich with discount info
    enriched_notifications = []
    for notification in notifications:
        notification_data = NotificationOut.model_validate(notification)
        
        if notification.discount_rule_id:
            discount_rule = await db.get(DiscountRule, notification.discount_rule_id)
            if discount_rule:
                notification_data.discount_name = discount_rule.name
                notification_data.discount_percentage = float(discount_rule.discount_percentage)
        
        enriched_notifications.append(notification_data)
    
    return enriched_notifications