from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func, Text, Numeric
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

class UserModelAssignment(Base):
    __tablename__ = "user_model_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("user_api_keys.id"), nullable=True)
    
    # Assignment status and permissions
    is_active = Column(Boolean, default=True)
    access_level = Column(String(50), default="read_write")  # read_only, read_write, admin
    
    # Usage limits per user-model combination
    daily_request_limit = Column(Integer, nullable=True)  # Requests per day for this model
    monthly_request_limit = Column(Integer, nullable=True)  # Requests per month for this model
    daily_token_limit = Column(Integer, nullable=True)  # Tokens per day for this model
    monthly_token_limit = Column(Integer, nullable=True)  # Tokens per month for this model
    daily_cost_limit = Column(Numeric(10, 4), nullable=True)  # Cost per day for this model
    monthly_cost_limit = Column(Numeric(10, 4), nullable=True)  # Cost per month for this model
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=10)
    requests_per_hour = Column(Integer, default=100)
    
    # Billing and pricing overrides
    custom_pricing_enabled = Column(Boolean, default=False)
    custom_cost_per_token = Column(Numeric(10, 8), nullable=True)  # Custom pricing per token
    custom_cost_per_request = Column(Numeric(10, 4), nullable=True)  # Custom pricing per request
    discount_percentage = Column(Numeric(5, 2), default=0)  # Percentage discount (0-100)
    
    # Model-specific configuration
    model_config = Column(Text, nullable=True)  # JSON string for model-specific settings
    endpoint_url = Column(String(500), nullable=True)  # Custom endpoint URL for this user-model
    
    # Access restrictions
    ip_whitelist = Column(Text, nullable=True)  # JSON array of allowed IP addresses
    time_restrictions = Column(Text, nullable=True)  # JSON object for time-based access
    
    # Usage tracking
    total_requests_made = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_cost_incurred = Column(Numeric(10, 4), default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Assignment metadata
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who assigned
    assignment_reason = Column(Text, nullable=True)  # Reason for assignment
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Timestamps
    assigned_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deactivated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="model_assignments")
    model = relationship("AIModel")
    api_key = relationship("UserAPIKey", back_populates="model_access")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    def is_expired(self) -> bool:
        """Check if this assignment has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_accessible(self) -> bool:
        """Check if this model is currently accessible by the user"""
        return (
            self.is_active and 
            not self.is_expired() and 
            self.user.is_active if self.user else False
        )

    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration as dictionary"""
        if not self.model_config:
            return {}
        try:
            return json.loads(self.model_config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_model_config(self, config: Dict[str, Any]):
        """Set model configuration from dictionary"""
        try:
            self.model_config = json.dumps(config)
        except (TypeError, ValueError):
            self.model_config = "{}"

    def get_ip_whitelist(self) -> list:
        """Get IP whitelist as list"""
        if not self.ip_whitelist:
            return []
        try:
            return json.loads(self.ip_whitelist)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_ip_whitelist(self, ip_list: list):
        """Set IP whitelist from list"""
        try:
            self.ip_whitelist = json.dumps(ip_list)
        except (TypeError, ValueError):
            self.ip_whitelist = "[]"

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        whitelist = self.get_ip_whitelist()
        if not whitelist:
            return True  # No restrictions
        return ip_address in whitelist

    def get_time_restrictions(self) -> Dict[str, Any]:
        """Get time restrictions as dictionary"""
        if not self.time_restrictions:
            return {}
        try:
            return json.loads(self.time_restrictions)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_time_restrictions(self, restrictions: Dict[str, Any]):
        """Set time restrictions from dictionary"""
        try:
            self.time_restrictions = json.dumps(restrictions)
        except (TypeError, ValueError):
            self.time_restrictions = "{}"

    def is_time_allowed(self, check_time: datetime = None) -> bool:
        """Check if current time is within allowed time restrictions"""
        restrictions = self.get_time_restrictions()
        if not restrictions:
            return True  # No restrictions
        
        if check_time is None:
            check_time = datetime.utcnow()
        
        # Check day of week restrictions
        if "allowed_days" in restrictions:
            weekday = check_time.weekday()  # 0=Monday, 6=Sunday
            if weekday not in restrictions["allowed_days"]:
                return False
        
        # Check time of day restrictions
        if "allowed_hours" in restrictions:
            current_hour = check_time.hour
            allowed_hours = restrictions["allowed_hours"]
            if isinstance(allowed_hours, dict):
                start_hour = allowed_hours.get("start", 0)
                end_hour = allowed_hours.get("end", 23)
                if not (start_hour <= current_hour <= end_hour):
                    return False
        
        return True

    def check_usage_limits(self, request_count: int = 0, token_count: int = 0, cost: float = 0) -> Dict[str, bool]:
        """
        Check if the user can make a request based on current usage limits.
        Returns dict with limit check results.
        """
        from sqlalchemy import func, and_
        from app.models.api_usage_log import APIUsageLog
        
        # This would need to be called with a database session
        # For now, return a simple check
        results = {
            "daily_requests_ok": True,
            "monthly_requests_ok": True,
            "daily_tokens_ok": True,
            "monthly_tokens_ok": True,
            "daily_cost_ok": True,
            "monthly_cost_ok": True,
            "can_proceed": True
        }
        
        # Simple checks against total usage (this would be enhanced with actual DB queries)
        if self.daily_request_limit and self.total_requests_made >= self.daily_request_limit:
            results["daily_requests_ok"] = False
            results["can_proceed"] = False
        
        if self.monthly_request_limit and self.total_requests_made >= self.monthly_request_limit:
            results["monthly_requests_ok"] = False
            results["can_proceed"] = False
        
        if self.daily_token_limit and self.total_tokens_used >= self.daily_token_limit:
            results["daily_tokens_ok"] = False
            results["can_proceed"] = False
        
        if self.monthly_token_limit and self.total_tokens_used >= self.monthly_token_limit:
            results["monthly_tokens_ok"] = False
            results["can_proceed"] = False
        
        return results

    def update_usage_stats(self, requests: int = 0, tokens: int = 0, cost: float = 0):
        """Update usage statistics"""
        self.total_requests_made += requests
        self.total_tokens_used += tokens
        self.total_cost_incurred += cost
        self.last_used_at = datetime.utcnow()

    def calculate_effective_cost(self, base_cost: float) -> float:
        """Calculate the effective cost after applying custom pricing and discounts"""
        if self.custom_pricing_enabled:
            if self.custom_cost_per_request is not None:
                effective_cost = float(self.custom_cost_per_request)
            else:
                effective_cost = base_cost
        else:
            effective_cost = base_cost
        
        # Apply discount
        discount_amount = effective_cost * (float(self.discount_percentage) / 100)
        return max(0, effective_cost - discount_amount)

    def deactivate(self, reason: str = None):
        """Deactivate this assignment"""
        self.is_active = False
        self.deactivated_at = datetime.utcnow()
        if reason:
            self.notes = f"{self.notes or ''}\nDeactivated: {reason}".strip()

    def extend_expiry(self, days: int):
        """Extend the expiry date by specified number of days"""
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)

    @classmethod
    def create_assignment(
        cls,
        user_id: int,
        model_id: int,
        assigned_by_id: int,
        access_level: str = "read_write",
        daily_request_limit: int = None,
        monthly_request_limit: int = None,
        expires_in_days: int = None,
        assignment_reason: str = None
    ):
        """Factory method to create a new user-model assignment"""
        assignment = cls(
            user_id=user_id,
            model_id=model_id,
            assigned_by=assigned_by_id,
            access_level=access_level,
            daily_request_limit=daily_request_limit,
            monthly_request_limit=monthly_request_limit,
            assignment_reason=assignment_reason
        )
        
        if expires_in_days:
            assignment.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        return assignment

    def __repr__(self):
        return f"<UserModelAssignment(user_id={self.user_id}, model_id={self.model_id}, active={self.is_active})>"