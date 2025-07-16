from sqlalchemy import Column, String, Integer, Numeric, Enum, ForeignKey
from app.database import Base
import enum
from sqlalchemy.orm import relationship

class OrganizationStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    slug = Column(String, unique=True)
    subscription_tier_id = Column(Integer, ForeignKey("subscription_tiers.id"))
    monthly_request_limit = Column(Integer)
    monthly_token_limit = Column(Integer)
    monthly_cost_limit = Column(Numeric)
    status = Column(Enum(OrganizationStatus, name="organizationstatus"), default=OrganizationStatus.active)

    subscription_tier = relationship("SubscriptionTier", lazy="joined")
