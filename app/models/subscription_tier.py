from sqlalchemy import Column, Integer, String, Numeric, Boolean, JSON
from app.database import Base

class SubscriptionTier(Base):
    __tablename__ = "subscription_tiers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)  
    monthly_cost = Column(Numeric, nullable=False, default=0)
    plan_details = Column(JSON, nullable=False)  # all limits and extras as JSON
    is_active = Column(Boolean, default=True)
