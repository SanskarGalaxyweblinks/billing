from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.billing_summary import MonthlyBillingSummary
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("/")
async def get_all_bills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(MonthlyBillingSummary)
        .where(MonthlyBillingSummary.user_id == current_user.id)
        .order_by(MonthlyBillingSummary.year.desc(), MonthlyBillingSummary.month.desc())
    )

    result = await db.execute(stmt)
    bills = result.scalars().all()

    response_data = []
    for bill in bills:
        data = {
            "id": bill.id,
            "year": bill.year,
            "month": bill.month,
            "total_cost": float(bill.total_cost),
            "status": "paid" if bill.is_paid else "unpaid",
            "invoice_url": bill.stripe_invoice_url,
            "created_at": bill.created_at.isoformat() if bill.created_at else None,
            "payment_due_date": bill.payment_due_date.isoformat() if bill.payment_due_date else None,
        }
        if bill.is_paid:
            data["paid_at"] = bill.paid_at.isoformat() if bill.paid_at else None
        
        response_data.append(data)
        
    return response_data