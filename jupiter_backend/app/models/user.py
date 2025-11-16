from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func, Numeric
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # Fields from old Organization model
    organization_name = Column(String)
    subscription_tier_id = Column(Integer, ForeignKey("subscription_tiers.id"))
    monthly_request_limit = Column(Integer)
    monthly_token_limit = Column(Integer)
    monthly_cost_limit = Column(Numeric)
    subscription_tier = relationship("SubscriptionTier", lazy="joined")

    # Fields for email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_token_expires = Column(DateTime, nullable=True)

    # New fields for password reset
    password_reset_token = Column(String, nullable=True)
    password_reset_token_expires = Column(DateTime, nullable=True)

    # Relationships for Epic 1: Model-User Association & Billing Foundation
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")
    model_assignments = relationship("UserModelAssignment", back_populates="user", cascade="all, delete-orphan")
    api_usage_logs = relationship("APIUsageLog", back_populates="user")