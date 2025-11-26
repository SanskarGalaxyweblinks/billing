from sqlalchemy import Column, String, Integer, Boolean, DateTime, Numeric, Text, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base

class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Can be null initially
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)  # Can be null initially
    
    # Original billing data from external models
    raw_model_name = Column(String(200), nullable=False)  # "company_name_email_classifier"
    company_name = Column(String(100), nullable=True)  # Extracted "company_name"
    predicted_label = Column(String(500), nullable=True)  # Model prediction result
    
    # Usage metrics
    total_tokens = Column(Integer, default=0)
    original_cost = Column(Numeric, nullable=False, default=0)
    applied_discount = Column(Numeric(5, 2), default=0)
    total_cost = Column(Numeric, default=0)
    response_time_ms = Column(Integer, default=0)
    
    # Status and metadata
    status = Column(String(50), default="success")
    request_timestamp = Column(String(100), nullable=True)  # Original timestamp from billing client
    billing_processed = Column(Boolean, default=False)  # Whether this has been processed for billing
    
    # Additional metadata
    client_ip = Column(String(45), nullable=True)  # For tracking IP addresses
    user_agent = Column(Text, nullable=True)  # For tracking client information
    api_key_id = Column(Integer, ForeignKey("user_api_keys.id"), nullable=True)  # Which API key was used
    
    # Error handling
    error_message = Column(Text, nullable=True)  # Store any processing errors
    retry_count = Column(Integer, default=0)  # For failed processing retries
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime, nullable=True)  # When user/model mapping was completed

    # FIXED: Relationships - removed back_populates since User doesn't have api_usage_logs anymore
    user = relationship("User")
    model = relationship("AIModel")
    api_key = relationship("UserAPIKey")

    def extract_company_name(self):
        """
        Extract company name from raw_model_name.
        Expected format: "company_name_model_type" -> "company_name"
        """
        if not self.raw_model_name:
            return None
            
        # Split by underscore and take the first part as company name
        parts = self.raw_model_name.split('_')
        if len(parts) >= 2:
            self.company_name = parts[0].lower().strip()
            return self.company_name
        return None

    def calculate_cost(self, model_pricing=None):
        """
        Calculate cost based on tokens or processing time.
        This will be enhanced when we have proper model pricing.
        """
        if model_pricing:
            # Use actual model pricing when available
            if self.total_tokens and model_pricing.get('cost_per_token'):
                self.original_cost = float(self.total_tokens * model_pricing['cost_per_token'])
            elif self.response_time_ms and model_pricing.get('cost_per_request'):
                self.original_cost = float(model_pricing['cost_per_request'])
        else:
            # Default fallback pricing (you can adjust these rates)
            if self.total_tokens:
                self.original_cost = float(self.total_tokens * 0.0001)  # $0.0001 per token
            else:
                self.original_cost = 0.01  # $0.01 per request if no tokens
        
        # Apply discount and calculate final cost
        discount_amount = float(self.original_cost * (self.applied_discount / 100))
        self.total_cost = float(self.original_cost - discount_amount)
        
        return self.total_cost

    def mark_as_processed(self, user_id=None, model_id=None):
        """Mark the log entry as processed with user and model mapping"""
        from datetime import datetime
        
        if user_id:
            self.user_id = user_id
        if model_id:
            self.model_id = model_id
            
        self.billing_processed = True
        self.processed_at = datetime.utcnow()

    def is_valid_for_billing(self) -> bool:
        """Check if this log entry has all required data for billing"""
        return (
            self.user_id is not None and 
            self.total_cost is not None and 
            self.status == "success"
        )

    @classmethod
    def create_from_billing_data(cls, billing_data: dict):
        """
        Create APIUsageLog from incoming billing data.
        Expected billing_data format:
        {
            "model_name": "company_email_classifier",
            "predicted_label": "spam",
            "processing_time_ms": 150,
            "timestamp": "2024-01-01T12:00:00Z",
            "status": "success"
        }
        """
        log_entry = cls(
            raw_model_name=billing_data.get("model_name", ""),
            predicted_label=billing_data.get("predicted_label", ""),
            response_time_ms=billing_data.get("processing_time_ms", 0),
            status=billing_data.get("status", "success"),
            request_timestamp=billing_data.get("timestamp", ""),
            total_tokens=billing_data.get("total_tokens", 0)  # If provided
        )
        
        # Extract company name
        log_entry.extract_company_name()
        
        # Calculate initial cost
        log_entry.calculate_cost()
        
        return log_entry