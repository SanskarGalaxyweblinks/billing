from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, func
from app.database import Base

class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    model_id = Column(Integer, ForeignKey("ai_models.id"))
    total_tokens = Column(Integer)
    original_cost = Column(Numeric, nullable=False, default=0)
    applied_discount = Column(Numeric(5, 2), default=0)
    total_cost = Column(Numeric)
    status = Column(String)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=func.now())