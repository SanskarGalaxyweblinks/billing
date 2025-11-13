from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.models.billing_summary import MonthlyBillingSummary

async def generate_monthly_bills(db: AsyncSession):
    today = datetime.utcnow()
    first_day_last_month = today.replace(day=1) - timedelta(days=1)
    year = first_day_last_month.year
    month = first_day_last_month.month

    users = (await db.execute(select(User))).scalars().all()

    for user in users:
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, 28) + timedelta(days=4)
        end_date = end_date.replace(day=1)

        usage_stmt = select(
            func.count(),
            func.sum(APIUsageLog.total_tokens),
            func.sum(APIUsageLog.original_cost),
            func.sum(APIUsageLog.total_cost)
        ).where(
            APIUsageLog.user_id == user.id,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.created_at < end_date
        )
        
        usage_result = (await db.execute(usage_stmt)).first()
        total_requests, total_tokens, original_usage_cost, usage_cost = usage_result

        total_requests = total_requests or 0
        total_tokens = total_tokens or 0
        original_usage_cost = original_usage_cost or 0
        usage_cost = usage_cost or 0
        
        total_discount = original_usage_cost - usage_cost

        subscription_cost = 0
        if user.subscription_tier:
            subscription_cost = float(user.subscription_tier.monthly_cost or 0)

        total_cost = usage_cost + subscription_cost
        
        payment_due_date = today.date() + timedelta(days=7)

        billing = MonthlyBillingSummary(
            user_id=user.id,
            year=year,
            month=month,
            total_requests=total_requests,
            total_tokens=total_tokens,
            usage_cost=usage_cost,
            subscription_cost=subscription_cost,
            total_discount=total_discount,
            total_cost=total_cost,
            payment_due_date=payment_due_date
        )
        db.add(billing)
    await db.commit()