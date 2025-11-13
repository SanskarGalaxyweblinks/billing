from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Boolean, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.database import Base

class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)  # NEW: Description for users
    priority = Column(Integer, default=100)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)
    
    # Usage thresholds
    min_requests = Column(Integer, default=0)
    max_requests = Column(Integer, nullable=True)
    
    # Discount details
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    discount_type = Column(String, default="percentage")  # NEW: percentage, fixed_amount
    
    # Validity period
    valid_from = Column(DateTime, default=func.now())  # NEW: When discount becomes valid
    valid_until = Column(DateTime, nullable=True)  # NEW: When discount expires
    validity_days = Column(Integer, nullable=True)  # NEW: How many days valid after enrollment
    
    # Status and tracking
    is_active = Column(Boolean, default=True)
    auto_apply = Column(Boolean, default=False)  # NEW: Auto-apply or require enrollment
    max_uses_per_user = Column(Integer, nullable=True)  # NEW: Usage limits per user
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="discount_rules")
    model = relationship("AIModel", backref="discount_rules")


class UserDiscountEnrollment(Base):
    """Track which users have enrolled in which discounts"""
    __tablename__ = "user_discount_enrollments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    discount_rule_id = Column(Integer, ForeignKey("discount_rules.id"), nullable=False)
    
    # Enrollment details
    enrolled_at = Column(DateTime, default=func.now())
    valid_until = Column(DateTime, nullable=True)  # When this enrollment expires
    usage_count = Column(Integer, default=0)  # How many times used
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="discount_enrollments")
    discount_rule = relationship("DiscountRule", backref="enrollments")


class UserNotification(Base):
    """Track notifications for users"""
    __tablename__ = "user_notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification content
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, default="discount")  # discount, billing, system, etc.
    
    # Related data
    discount_rule_id = Column(Integer, ForeignKey("discount_rules.id"), nullable=True)
    extra_data = Column(Text, nullable=True)  # FIXED: Changed from 'metadata' to 'extra_data'
    
    # Status
    is_read = Column(Boolean, default=False)
    is_popup_shown = Column(Boolean, default=False)  # For one-time popups
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="notifications")
    discount_rule = relationship("DiscountRule", backref="notifications")