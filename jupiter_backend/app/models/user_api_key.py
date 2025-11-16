from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
import secrets
import hashlib

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_name = Column(String(100), nullable=False)  # User-friendly name for the key
    api_key_hash = Column(String(256), nullable=False, unique=True)  # Hashed version for security
    api_key_prefix = Column(String(20), nullable=False)  # First few chars for display (e.g., "jb_1234...")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Rate limiting and permissions
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Allowed IP addresses (JSON array as string)
    allowed_ips = Column(Text, nullable=True)  # Store as JSON string: ["192.168.1.1", "10.0.0.1"]
    
    # Scopes/permissions (JSON array as string)
    scopes = Column(Text, default='["read", "write"]')  # ["read", "write", "admin"]

    # Relationships
    user = relationship("User", back_populates="api_keys")
    model_access = relationship("UserModelAssignment", back_populates="api_key")

    @classmethod
    def generate_api_key(cls) -> tuple[str, str, str]:
        """
        Generate a new API key with format: jb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        Returns: (full_key, hash, prefix)
        """
        # Generate random 32 character string
        key_suffix = secrets.token_urlsafe(32)[:32]
        full_key = f"jb_{key_suffix}"
        
        # Create hash for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        # Create prefix for display
        prefix = full_key[:12] + "..."  # Shows "jb_12345678..."
        
        return full_key, key_hash, prefix

    @classmethod
    def hash_api_key(cls, api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def update_last_used(self):
        """Update the last used timestamp"""
        self.last_used_at = datetime.utcnow()

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if the IP address is allowed"""
        if not self.allowed_ips:
            return True  # No restrictions
        
        import json
        try:
            allowed_list = json.loads(self.allowed_ips)
            return ip_address in allowed_list
        except (json.JSONDecodeError, TypeError):
            return True  # If parsing fails, allow access

    def has_scope(self, required_scope: str) -> bool:
        """Check if the API key has the required scope"""
        import json
        try:
            scopes_list = json.loads(self.scopes)
            return required_scope in scopes_list
        except (json.JSONDecodeError, TypeError):
            return False