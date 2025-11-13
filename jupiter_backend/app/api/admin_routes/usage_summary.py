from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, Date, and_
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.api.deps import get_db

router = APIRouter()


@router.get("/usage-summary")
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Global Summary
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

    # Organization-wise Summary
    user_stmt = (
        select(
            User.organization_name.label("organization_name"),
            User.id.label("user_id"),
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
        .join(User, User.id == APIUsageLog.user_id)
        .where(
            APIUsageLog.created_at >= start_dt,
            APIUsageLog.created_at <= end_dt
        )
        .group_by(User.id)
    )
    user_result = await db.execute(user_stmt)
    user_rows = user_result.fetchall()

    organization_stats = []
    for user_row in user_rows:
        model_wise_stmt = (
            select(
                AIModel.name.label("model_name"),
                func.count().label("total_requests"),
                func.sum(APIUsageLog.total_tokens).label("total_tokens"),
                func.sum(APIUsageLog.total_cost).label("total_cost")
            )
            .join(AIModel, AIModel.id == APIUsageLog.model_id)
            .where(
                APIUsageLog.user_id == user_row.user_id,
                APIUsageLog.created_at >= start_dt,
                APIUsageLog.created_at <= end_dt
            )
            .group_by(AIModel.name)
        )
        model_result = await db.execute(model_wise_stmt)
        model_rows = model_result.fetchall()
        
        organization_stats.append({
            "organization_name": user_row.organization_name,
            "total_requests": user_row.total_requests or 0,
            "total_tokens": user_row.total_tokens or 0,
            "total_cost": float(user_row.total_cost or 0),
            "avg_response_time": round(user_row.avg_response_time or 0, 2),
            "success_rate": round(float(user_row.success_rate or 0), 4),
            "model_wise_summary": [
                {
                    "model_name": row.model_name,
                    "total_requests": row.total_requests or 0,
                    "total_tokens": row.total_tokens or 0,
                    "total_cost": float(row.total_cost or 0)
                }
                for row in model_rows
            ]
        })

    # Global Model-wise Summary
    global_model_stmt = (
        select(
            AIModel.name.label("model_name"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.sum(APIUsageLog.total_cost).label("total_cost")
        )
        .join(AIModel, AIModel.id == APIUsageLog.model_id)
        .where(
            APIUsageLog.created_at >= start_dt,
            APIUsageLog.created_at <= end_dt
        )
        .group_by(AIModel.name)
        .order_by(AIModel.name)
    )
    global_model_result = await db.execute(global_model_stmt)
    global_model_rows = global_model_result.fetchall()

    global_model_wise_summary = [
        {
            "model_name": row.model_name,
            "total_requests": row.total_requests or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0)
        }
        for row in global_model_rows
    ]

    return {
        "global_summary": {
            "total_requests": global_data.total_requests or 0,
            "total_tokens": global_data.total_tokens or 0,
            "total_cost": float(global_data.total_cost or 0),
            "avg_response_time": round(global_data.avg_response_time or 0, 2),
            "success_rate": round(float(global_data.success_rate or 0), 4)
        },
        "organization_stats": organization_stats,
        "global_model_wise_summary": global_model_wise_summary
    }