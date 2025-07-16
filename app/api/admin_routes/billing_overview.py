from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.billing_summary import MonthlyBillingSummary
from app.models.organization import Organization
from app.api.deps import get_db

router = APIRouter()

@router.get("/billing/overview")
async def get_billing_overview(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MonthlyBillingSummary, Organization.name)
        .join(Organization, MonthlyBillingSummary.organization_id == Organization.id)
        .order_by(MonthlyBillingSummary.year.desc(), MonthlyBillingSummary.month.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": bill.id,
            "organization": org_name,
            "year": bill.year,
            "month": bill.month,
            "total_requests": bill.total_requests,
            "total_tokens": bill.total_tokens,
            "usage_cost": float(bill.usage_cost or 0),
            "subscription_cost": float(bill.subscription_cost or 0),
            "total_cost": float(bill.total_cost or 0),
            "status": "paid" if bill.is_paid else "unpaid",
            "bill_id": bill.stripe_invoice_id,
            "generated_date": bill.created_at.strftime("%Y-%m-%d")
        }
        for bill, org_name in rows
    ]
