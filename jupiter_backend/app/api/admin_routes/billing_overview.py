from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.billing_summary import MonthlyBillingSummary
from app.models.user import User
from app.api.deps import get_db

router = APIRouter()

@router.get("/billing/overview")
async def get_billing_overview(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MonthlyBillingSummary, User.organization_name)
        .join(User, MonthlyBillingSummary.user_id == User.id)
        .order_by(MonthlyBillingSummary.year.desc(), MonthlyBillingSummary.month.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    response_data = []
    for bill, org_name in rows:
        data = {
            "id": bill.id,
            "organization": org_name,
            "year": bill.year,
            "month": bill.month,
            "total_cost": float(bill.total_cost or 0),
            "total_discount": float(bill.total_discount or 0),  # Add this line
            "status": "paid" if bill.is_paid else "unpaid",
            "invoice_url": bill.stripe_invoice_url,
            "paid_date": bill.paid_at.strftime("%Y-%m-%d") if bill.paid_at else None,
            "payment_due_date": bill.payment_due_date.strftime("%Y-%m-%d") if bill.payment_due_date else None,
            "generated_date": bill.created_at.strftime("%Y-%m-%d") if bill.created_at else None,
        }
        response_data.append(data)
    
    return response_data

@router.get("/billing/overview/unpaid")
async def get_billing_overview_unpaid(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MonthlyBillingSummary, User.organization_name)
        .join(User, MonthlyBillingSummary.user_id == User.id)
        .where(MonthlyBillingSummary.is_paid == False)
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
            "status": "unpaid",
            "bill_id": bill.stripe_invoice_id,
            "generated_date": bill.created_at.strftime("%Y-%m-%d") if bill.created_at else None,
            "payment_due_date": bill.payment_due_date.strftime("%Y-%m-%d") if bill.payment_due_date else None,
        }
        for bill, org_name in rows
    ]