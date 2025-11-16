from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func, Text, Numeric, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

class OrganizationModel(Base):
    __tablename__ = "organization_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Links to User as organization
    base_model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)  # Optional link to base AI model
    
    # Model identification
    model_name = Column(String(200), nullable=False)  # e.g., "cadex_email_classifier"
    display_name = Column(String(200), nullable=False)  # e.g., "Cadex Email Classifier"
    model_type = Column(String(100), nullable=False)  # e.g., "email_classifier", "sentiment_analyzer"
    version = Column(String(50), default="1.0")
    description = Column(Text, nullable=True)
    
    # Model configuration
    endpoint_url = Column(String(500), nullable=True)  # Custom model endpoint
    api_endpoint_type = Column(String(50), default="rest")  # rest, graphql, grpc
    authentication_method = Column(String(50), default="api_key")  # api_key, oauth, basic_auth
    model_config = Column(JSON, nullable=True)  # Model-specific configuration
    
    # Status and availability
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)  # Whether other orgs can use this model
    deployment_status = Column(String(50), default="deployed")  # deployed, pending, failed, maintenance
    health_check_url = Column(String(500), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50), default="unknown")  # healthy, unhealthy, unknown
    
    # Pricing and billing
    pricing_model = Column(String(50), default="per_request")  # per_request, per_token, per_minute, custom
    cost_per_request = Column(Numeric(10, 4), default=0.01)
    cost_per_1k_tokens = Column(Numeric(10, 6), default=0)
    cost_per_minute = Column(Numeric(10, 4), default=0)
    custom_pricing_config = Column(JSON, nullable=True)  # For complex pricing models
    
    # Usage limits and quotas
    max_requests_per_minute = Column(Integer, default=100)
    max_requests_per_hour = Column(Integer, default=1000)
    max_requests_per_day = Column(Integer, default=10000)
    max_concurrent_requests = Column(Integer, default=10)
    
    # Model capabilities and metadata
    input_types = Column(JSON, default=lambda: ["text"])  # ["text", "image", "audio"]
    output_types = Column(JSON, default=lambda: ["text"])  # ["text", "json", "classification"]
    max_input_size = Column(Integer, default=4096)  # In tokens or characters
    max_output_size = Column(Integer, default=1024)
    supported_languages = Column(JSON, default=lambda: ["en"])
    
    # Performance metrics
    average_response_time = Column(Numeric(8, 2), default=0)  # In milliseconds
    success_rate = Column(Numeric(5, 4), default=1.0)  # 0.0 to 1.0
    total_requests_processed = Column(Integer, default=0)
    total_tokens_processed = Column(Integer, default=0)
    total_revenue_generated = Column(Numeric(12, 4), default=0)
    
    # Access control
    access_level = Column(String(50), default="organization")  # organization, public, private
    allowed_user_roles = Column(JSON, default=lambda: ["admin", "user"])
    ip_whitelist = Column(JSON, nullable=True)  # Allowed IP addresses for this model
    rate_limiting_rules = Column(JSON, nullable=True)  # Custom rate limiting
    
    # Model lifecycle
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deployed_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    deprecated_at = Column(DateTime, nullable=True)
    
    # Maintenance and monitoring
    maintenance_window = Column(JSON, nullable=True)  # Scheduled maintenance times
    monitoring_enabled = Column(Boolean, default=True)
    alert_thresholds = Column(JSON, nullable=True)  # Performance alert settings
    backup_endpoint_url = Column(String(500), nullable=True)  # Fallback endpoint
    
    # Documentation and support
    documentation_url = Column(String(500), nullable=True)
    support_contact = Column(String(200), nullable=True)
    changelog = Column(JSON, default=lambda: [])  # Version history
    tags = Column(JSON, default=lambda: [])  # For categorization and search

    # Relationships
    organization = relationship("User", foreign_keys=[organization_id], back_populates="organization_models")
    base_model = relationship("AIModel", foreign_keys=[base_model_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<OrganizationModel(name={self.model_name}, org={self.organization_id}, active={self.is_active})>"

    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration as dictionary"""
        if not self.model_config:
            return {}
        if isinstance(self.model_config, str):
            try:
                return json.loads(self.model_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.model_config or {}

    def set_model_config(self, config: Dict[str, Any]):
        """Set model configuration from dictionary"""
        self.model_config = config

    def get_custom_pricing_config(self) -> Dict[str, Any]:
        """Get custom pricing configuration"""
        if not self.custom_pricing_config:
            return {}
        if isinstance(self.custom_pricing_config, str):
            try:
                return json.loads(self.custom_pricing_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.custom_pricing_config or {}

    def set_custom_pricing_config(self, config: Dict[str, Any]):
        """Set custom pricing configuration"""
        self.custom_pricing_config = config

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        if isinstance(self.supported_languages, str):
            try:
                return json.loads(self.supported_languages)
            except (json.JSONDecodeError, TypeError):
                return ["en"]
        return self.supported_languages or ["en"]

    def get_input_types(self) -> List[str]:
        """Get list of supported input types"""
        if isinstance(self.input_types, str):
            try:
                return json.loads(self.input_types)
            except (json.JSONDecodeError, TypeError):
                return ["text"]
        return self.input_types or ["text"]

    def get_output_types(self) -> List[str]:
        """Get list of supported output types"""
        if isinstance(self.output_types, str):
            try:
                return json.loads(self.output_types)
            except (json.JSONDecodeError, TypeError):
                return ["text"]
        return self.output_types or ["text"]

    def get_ip_whitelist(self) -> List[str]:
        """Get IP whitelist"""
        if not self.ip_whitelist:
            return []
        if isinstance(self.ip_whitelist, str):
            try:
                return json.loads(self.ip_whitelist)
            except (json.JSONDecodeError, TypeError):
                return []
        return self.ip_whitelist or []

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        whitelist = self.get_ip_whitelist()
        if not whitelist:
            return True  # No restrictions
        return ip_address in whitelist

    def calculate_cost(self, request_data: Dict[str, Any]) -> float:
        """
        Calculate cost for a request based on pricing model
        """
        if self.pricing_model == "per_request":
            return float(self.cost_per_request)
        
        elif self.pricing_model == "per_token":
            token_count = request_data.get("token_count", 0)
            if token_count and self.cost_per_1k_tokens:
                return float(self.cost_per_1k_tokens * token_count / 1000)
            return float(self.cost_per_request)  # Fallback
        
        elif self.pricing_model == "per_minute":
            processing_time = request_data.get("processing_time_ms", 0)
            minutes = processing_time / (1000 * 60)  # Convert ms to minutes
            return float(self.cost_per_minute * minutes)
        
        elif self.pricing_model == "custom":
            # Implement custom pricing logic based on custom_pricing_config
            pricing_config = self.get_custom_pricing_config()
            # This would need custom implementation based on requirements
            return float(self.cost_per_request)  # Fallback
        
        return float(self.cost_per_request)

    def update_usage_stats(self, requests: int = 1, tokens: int = 0, revenue: float = 0, response_time: float = 0):
        """Update usage statistics"""
        self.total_requests_processed += requests
        self.total_tokens_processed += tokens
        self.total_revenue_generated += revenue
        self.last_used_at = datetime.utcnow()
        
        # Update average response time (simple moving average)
        if response_time > 0:
            if self.average_response_time == 0:
                self.average_response_time = response_time
            else:
                # Weighted average (giving more weight to recent measurements)
                self.average_response_time = (self.average_response_time * 0.9) + (response_time * 0.1)

    def update_health_status(self, is_healthy: bool, error_message: str = None):
        """Update health check status"""
        self.last_health_check = datetime.utcnow()
        self.health_status = "healthy" if is_healthy else "unhealthy"
        
        if not is_healthy and error_message:
            # Log health check failure (could be stored in a separate health_logs table)
            pass

    def is_available(self) -> bool:
        """Check if model is available for use"""
        return (
            self.is_active and 
            self.deployment_status == "deployed" and
            self.health_status in ["healthy", "unknown"]
        )

    def get_rate_limit_for_user(self, user_role: str = "user") -> Dict[str, int]:
        """Get rate limits based on user role"""
        base_limits = {
            "per_minute": self.max_requests_per_minute,
            "per_hour": self.max_requests_per_hour,
            "per_day": self.max_requests_per_day,
            "concurrent": self.max_concurrent_requests
        }
        
        # Could be enhanced to have role-specific limits
        rate_rules = self.rate_limiting_rules
        if rate_rules and isinstance(rate_rules, dict):
            role_limits = rate_rules.get(user_role, {})
            base_limits.update(role_limits)
        
        return base_limits

    def add_changelog_entry(self, version: str, changes: str, author_id: int = None):
        """Add an entry to the changelog"""
        if not self.changelog:
            self.changelog = []
        
        entry = {
            "version": version,
            "changes": changes,
            "timestamp": datetime.utcnow().isoformat(),
            "author_id": author_id
        }
        
        changelog = self.changelog.copy() if isinstance(self.changelog, list) else []
        changelog.append(entry)
        self.changelog = changelog

    def deprecate_model(self, reason: str = None, replacement_model_id: int = None):
        """Mark model as deprecated"""
        self.deprecated_at = datetime.utcnow()
        self.is_active = False
        
        # Add to changelog
        changelog_msg = f"Model deprecated. Reason: {reason or 'Not specified'}"
        if replacement_model_id:
            changelog_msg += f" Replacement model ID: {replacement_model_id}"
        
        self.add_changelog_entry(self.version, changelog_msg)

    def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for the specified number of days"""
        # This would typically query the APIUsageLog table
        # For now, return current totals
        return {
            "total_requests": self.total_requests_processed,
            "total_tokens": self.total_tokens_processed,
            "total_revenue": float(self.total_revenue_generated),
            "average_response_time": float(self.average_response_time),
            "success_rate": float(self.success_rate),
            "last_used": self.last_used_at.isoformat() if self.last_used_at else None
        }

    @classmethod
    def create_organization_model(
        cls,
        organization_id: int,
        model_name: str,
        display_name: str,
        model_type: str,
        created_by_id: int,
        endpoint_url: str = None,
        cost_per_request: float = 0.01,
        description: str = None,
        base_model_id: int = None
    ):
        """Factory method to create a new organization model"""
        return cls(
            organization_id=organization_id,
            model_name=model_name,
            display_name=display_name,
            model_type=model_type,
            created_by=created_by_id,
            endpoint_url=endpoint_url,
            cost_per_request=cost_per_request,
            description=description,
            base_model_id=base_model_id,
            deployed_at=datetime.utcnow()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "model_type": self.model_type,
            "version": self.version,
            "description": self.description,
            "endpoint_url": self.endpoint_url,
            "is_active": self.is_active,
            "deployment_status": self.deployment_status,
            "health_status": self.health_status,
            "pricing_model": self.pricing_model,
            "cost_per_request": float(self.cost_per_request),
            "total_requests_processed": self.total_requests_processed,
            "total_revenue_generated": float(self.total_revenue_generated),
            "average_response_time": float(self.average_response_time),
            "success_rate": float(self.success_rate),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }