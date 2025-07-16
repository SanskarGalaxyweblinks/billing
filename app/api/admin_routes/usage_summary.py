from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, Date, and_
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from app.models.api_usage_log import APIUsageLog
from app.models.organization import Organization
from app.api.deps import get_db

router = APIRouter()


@router.get("/usage-summary")
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    # ----------------- Date Range Default -----------------
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # ----------------- Global Summary -----------------
    global_stmt = select(
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_tokens).label("total_tokens"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(
                case((APIUsageLog.status == 'success', 1), else_=0)
            ) / func.count()
        ).label("success_rate")
    ).where(
        APIUsageLog.created_at >= start_dt,
        APIUsageLog.created_at <= end_dt
    )
    global_result = await db.execute(global_stmt)
    global_data = global_result.fetchone()

    # ----------------- Organization-wise Summary -----------------
    org_stmt = (
        select(
            Organization.name.label("organization_name"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            (
                func.sum(
                    case((APIUsageLog.status == 'success', 1), else_=0)
                ) / func.count()
            ).label("success_rate")
        )
        .join(Organization, Organization.id == APIUsageLog.organization_id)
        .where(
            APIUsageLog.created_at >= start_dt,
            APIUsageLog.created_at <= end_dt
        )
        .group_by(Organization.id)
    )
    org_result = await db.execute(org_stmt)
    org_rows = org_result.fetchall()

    organization_stats = [
        {
            "organization_name": row.organization_name,
            "total_requests": row.total_requests or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0),
            "avg_response_time": round(row.avg_response_time or 0, 2),
            "success_rate": round(float(row.success_rate or 0), 4)
        }
        for row in org_rows
    ]

    return {
        "global_summary": {
            "total_requests": global_data.total_requests or 0,
            "total_tokens": global_data.total_tokens or 0,
            "total_cost": float(global_data.total_cost or 0),
            "avg_response_time": round(global_data.avg_response_time or 0, 2),
            "success_rate": round(float(global_data.success_rate or 0), 4)
        },
        "organization_stats": organization_stats
    }
