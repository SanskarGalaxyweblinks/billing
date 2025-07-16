from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from app.database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin") 
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())