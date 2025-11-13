from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, cast, Date, case
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel

router = APIRouter()

@router.get("/")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    start_of_month = today_start.replace(day=1)

    # Corrected CASE statement syntax
    success_rate_query = func.coalesce(
        func.sum(case((APIUsageLog.status == 'success', 1), else_=0)) / func.count(), 
        0.0
    )

    stmt = (
        select(
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            success_rate_query.label("success_rate")
        )
        .where(APIUsageLog.user_id == current_user.id)
        .where(APIUsageLog.created_at >= today_start)
    )

    result = await db.execute(stmt)
    daily_stats = result.first()

    # Model-wise summary for the current month
    model_wise_stmt = (
        select(
            AIModel.name.label("model_name"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.sum(APIUsageLog.total_cost).label("total_cost")
        )
        .join(AIModel, AIModel.id == APIUsageLog.model_id)
        .where(
            APIUsageLog.user_id == current_user.id,
            APIUsageLog.created_at >= start_of_month
        )
        .group_by(AIModel.name)
        .order_by(AIModel.name)
    )
    model_wise_result = await db.execute(model_wise_stmt)
    model_wise_summary = model_wise_result.fetchall()

    return {
        "total_requests": daily_stats.total_requests or 0,
        "total_cost": float(daily_stats.total_cost or 0),
        "avg_response_time": float(daily_stats.avg_response_time or 0),
        "success_rate": float(daily_stats.success_rate or 0),
        "model_wise_summary": [
            {
                "model_name": row.model_name,
                "total_requests": row.total_requests or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0)
            } for row in model_wise_summary
        ]
    }

@router.get("/usage-history")
async def get_usage_history(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)

    stmt = (
        select(
            cast(APIUsageLog.created_at, Date).label("usage_date"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost")
        )
        .where(APIUsageLog.user_id == current_user.id)
        .where(cast(APIUsageLog.created_at, Date).between(start_date, end_date))
        .group_by(cast(APIUsageLog.created_at, Date))
        .order_by(cast(APIUsageLog.created_at, Date))
    )

    result = await db.execute(stmt)
    rows = result.all()

    usage_map = { (start_date + timedelta(days=i)).isoformat(): {"total_requests": 0, "total_cost": 0.0} for i in range(days) }

    for row in rows:
        usage_map[row.usage_date.isoformat()] = {
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0)
        }

    return [{"usage_date": date, **data} for date, data in usage_map.items()]