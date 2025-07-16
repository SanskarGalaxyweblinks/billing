from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, desc, extract
from datetime import datetime, timedelta, date
from app.api.deps import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel, AIModelStatus

router = APIRouter()

@router.get("/dashboard-summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Total Stats ---
    total_users_stmt = select(func.count()).select_from(User)
    total_orgs_stmt = select(func.count()).select_from(Organization)
    active_models_stmt = select(func.count()).select_from(AIModel).where(AIModel.status == AIModelStatus.active)
    requests_stmt = select(func.count()).where(APIUsageLog.created_at >= start_of_month)
    revenue_stmt = select(func.sum(APIUsageLog.total_cost)).where(APIUsageLog.created_at >= start_of_month)
    tokens_stmt = select(func.sum(APIUsageLog.total_tokens)).where(APIUsageLog.created_at >= start_of_month)

    total_users = (await db.execute(total_users_stmt)).scalar() or 0
    total_orgs = (await db.execute(total_orgs_stmt)).scalar() or 0
    active_models = (await db.execute(active_models_stmt)).scalar() or 0
    requests_month = (await db.execute(requests_stmt)).scalar() or 0
    revenue_month = float((await db.execute(revenue_stmt)).scalar() or 0)
    tokens_month = (await db.execute(tokens_stmt)).scalar() or 0

    # --- Recent Activity (last 5 API logs) ---
    recent_stmt = (
        select(APIUsageLog)
        .order_by(desc(APIUsageLog.created_at))
        .limit(5)
    )
    recent_logs = (await db.execute(recent_stmt)).scalars().all()
    recent_activity = [
        {
            "status": log.status,
            "model_id": log.model_id,
            "created_at": log.created_at.isoformat(),
            "minutes_ago": int((today - log.created_at).total_seconds() // 60)
        }
        for log in recent_logs
    ]

    # --- Top organizations by usage ---
    top_org_stmt = (
        select(
            Organization.name.label("organization_name"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.count().label("total_requests")
        )
        .join(Organization, Organization.id == APIUsageLog.organization_id)
        .where(APIUsageLog.created_at >= start_of_month)
        .group_by(Organization.id)
        .order_by(desc(func.sum(APIUsageLog.total_cost)))
        .limit(5)
    )
    top_orgs = (await db.execute(top_org_stmt)).fetchall()

    top_organizations = [
        {
            "organization_name": row.organization_name,
            "total_cost": float(row.total_cost or 0),
            "total_requests": row.total_requests
        }
        for row in top_orgs
    ]

    # --- Return ---
    return {
        "stats": {
            "total_users": total_users,
            "total_organizations": total_orgs,
            "active_models": active_models,
            "requests_this_month": requests_month,
            "revenue_this_month": revenue_month,
            "tokens_this_month": tokens_month,
        },
        "recent_activity": recent_activity,
        "top_organizations": top_organizations
    }
