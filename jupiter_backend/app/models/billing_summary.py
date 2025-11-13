from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, func, Boolean, Date
from app.database import Base

class MonthlyBillingSummary(Base):
    __tablename__ = "monthly_billing_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    total_requests = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    usage_cost = Column(Numeric, nullable=False, default=0)
    subscription_cost = Column(Numeric, nullable=False, default=0)
    total_discount = Column(Numeric, nullable=False, default=0)
    total_cost = Column(Numeric, nullable=False, default=0)

    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    stripe_invoice_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=func.now())
    payment_due_date = Column(Date, nullable=True)
    stripe_invoice_url = Column(String, nullable=True)