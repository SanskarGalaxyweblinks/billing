from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)  # DB internal ID
    auth_id = Column(String, unique=True, nullable=False)       # Supabase UID
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    organization_id = Column(Integer, ForeignKey("organizations.id"))

    organization = relationship("Organization", backref="users")
