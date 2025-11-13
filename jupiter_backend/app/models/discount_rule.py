from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Boolean
from app.database import Base

class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    priority = Column(Integer, default=100)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)
    min_requests = Column(Integer, default=0)
    max_requests = Column(Integer, nullable=True)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, default=True)