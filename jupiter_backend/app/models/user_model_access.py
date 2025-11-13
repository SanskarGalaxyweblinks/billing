# jupiter_backend/app/models/user_model_access.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base

class UserModelAccess(Base):
    __tablename__ = "user_model_access"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=func.now())
    granted_by = Column(Integer, ForeignKey("admins.id"))
    
    # Relationships
    user = relationship("User", backref="model_access")
    model = relationship("AIModel", backref="user_access")