from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, case, cast, String
import datetime

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.api.deps import get_db, get_user_info

router = APIRouter()


@router.get("/")
async def get_monthly_summary(request: Request, db: AsyncSession = Depends(get_db)):
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user by auth_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    org_id = db_user.organization_id

    truncated_date = func.date_trunc('month', APIUsageLog.created_at).label("month")

    stmt = select(
        truncated_date,
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.sum(APIUsageLog.total_tokens).label("total_tokens"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(
                case((APIUsageLog.status == 'success', 1), else_=0)
            ) / func.count()
        ).label("success_rate")
    ).where(
        APIUsageLog.organization_id == org_id
    ).group_by(
        truncated_date
    ).order_by(
        truncated_date.desc()
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "month": row.month.strftime("%Y-%m"),
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0),
            "total_tokens": float(row.total_tokens or 0),
            "avg_response_time": round(row.avg_response_time or 0),
            "success_rate": round(float(row.success_rate or 0), 4)
        }
        for row in rows
    ]
