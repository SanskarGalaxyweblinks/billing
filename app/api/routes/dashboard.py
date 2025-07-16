from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, case, cast, String, Date, desc
import datetime

from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel
from app.models.user import User
from app.api.deps import get_db, get_user_info

router = APIRouter()

@router.get("/")
async def get_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_user_info(request)
    auth_id = user.get("sub")  # Supabase UID

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID in token")

    # Step 1: Find the User by auth_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    org_id = db_user.organization_id

    # Step 2: Compute today's date range
    today = datetime.date.today()
    start = datetime.datetime.combine(today, datetime.time.min)
    end = datetime.datetime.combine(today, datetime.time.max)

    # Step 3: Summary query
    summary_stmt = select(
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(case((APIUsageLog.status == 'success', 1), else_=0)) / func.count()
        ).label("success_rate")
    ).where(
        APIUsageLog.organization_id == org_id,
        APIUsageLog.created_at >= start,
        APIUsageLog.created_at <= end
    )

    # Step 4: Recent API calls
    recent_stmt = (
        select(APIUsageLog, AIModel)
        .join(AIModel, AIModel.id == APIUsageLog.model_id)
        .where(
            APIUsageLog.organization_id == org_id,
            APIUsageLog.created_at >= start,
            APIUsageLog.created_at <= end
        )
        .order_by(desc(APIUsageLog.created_at))
        .limit(5)
    )

    summary_result = await db.execute(summary_stmt)
    recent_result = await db.execute(recent_stmt)

    summary_data = summary_result.fetchone()
    recent_calls = recent_result.fetchall()

    return {
        "total_requests": summary_data.total_requests or 0,
        "total_cost": float(summary_data.total_cost or 0),
        "avg_response_time": round(summary_data.avg_response_time or 0),
        "success_rate": round(float(summary_data.success_rate or 0), 4),
        "recent_calls": [
            {
                "id": usage_log.id,
                "status": usage_log.status,
                "total_tokens": usage_log.total_tokens,
                "total_cost": float(usage_log.total_cost or 0),
                "response_time_ms": usage_log.response_time_ms,
                "created_at": usage_log.created_at.isoformat(),
                "ai_models": {
                    "name": ai_model.name,
                    "provider": ai_model.provider,
                }
            }
            for usage_log, ai_model in recent_calls
        ]
    }

@router.get("/usage-history")
async def get_usage_history(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user in DB using auth_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    org_id = db_user.organization_id

    # Fetch usage data
    start_date = datetime.date.today() - datetime.timedelta(days=days)

    stmt = (
        select(
            cast(APIUsageLog.created_at, Date).label("usage_date"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost")
        )
        .where(
            APIUsageLog.organization_id == org_id,
            APIUsageLog.created_at >= start_date
        )
        .group_by(cast(APIUsageLog.created_at, Date))
        .order_by(cast(APIUsageLog.created_at, Date))
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "usage_date": str(row.usage_date),
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0)
        }
        for row in rows
    ]