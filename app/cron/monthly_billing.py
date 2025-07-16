from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.organization import Organization
from app.models.api_usage_log import APIUsageLog
from app.models.billing_summary import MonthlyBillingSummary
from app.models.subscription_tier import SubscriptionTier

async def generate_monthly_bills(db: AsyncSession):
    today = datetime.utcnow()
    first_day_last_month = today.replace(day=1) - timedelta(days=1)
    year = first_day_last_month.year
    month = first_day_last_month.month

    orgs = (await db.execute(select(Organization))).scalars().all()

    for org in orgs:
        # Usage in that month
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, 28) + timedelta(days=4)
        end_date = end_date.replace(day=1)

        usage_stmt = select(APIUsageLog).where(
            APIUsageLog.organization_id == org.id,
            APIUsageLog.created_at >= start_date,
            APIUsageLog.created_at < end_date
        )
        usage_logs = (await db.execute(usage_stmt)).scalars().all()

        total_requests = sum(log.total_requests or 0 for log in usage_logs)
        total_tokens = sum(log.total_tokens or 0 for log in usage_logs)
        usage_cost = sum(float(log.total_cost or 0) for log in usage_logs)

        subscription_cost = float(org.subscription_tier.monthly_cost or 0)

        total_cost = usage_cost + subscription_cost

        billing = MonthlyBillingSummary(
            organization_id=org.id,
            year=year,
            month=month,
            total_requests=total_requests,
            total_tokens=total_tokens,
            usage_cost=usage_cost,
            subscription_cost=subscription_cost,
            total_cost=total_cost
        )
        db.add(billing)
    await db.commit()
