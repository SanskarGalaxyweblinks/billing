from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.billing_summary import MonthlyBillingSummary
from app.api.deps import get_db, get_user_info

router = APIRouter()

@router.get("/unpaid")
async def get_unpaid_bills(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user by Supabase auth ID
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    # Fetch unpaid bills for the user's organization
    stmt = (
        select(MonthlyBillingSummary)
        .where(
            MonthlyBillingSummary.organization_id == db_user.organization_id,
            MonthlyBillingSummary.is_paid == False
        )
        .order_by(MonthlyBillingSummary.year.desc(), MonthlyBillingSummary.month.desc())
    )

    result = await db.execute(stmt)
    unpaid_bills = result.scalars().all()

    return [
        {
            "id": bill.id,
            "year": bill.year,
            "month": bill.month,
            "total_requests": bill.total_requests,
            "total_tokens": bill.total_tokens,
            "usage_cost": bill.usage_cost,
            "subscription_cost": bill.subscription_cost,
            "total_cost": float(bill.total_cost or 0),
            "created_at": bill.created_at,
            "status": "unpaid"
        }
        for bill in unpaid_bills
    ]
