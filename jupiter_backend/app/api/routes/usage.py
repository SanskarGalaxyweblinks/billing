from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, case, cast, String, extract

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("/")
async def get_monthly_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    month_year = func.concat(
        extract('year', APIUsageLog.created_at).cast(String),
        '-',
        func.lpad(extract('month', APIUsageLog.created_at).cast(String), 2, '0')
    ).label("month")

    # Get monthly summaries
    stmt = select(
        month_year,
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.sum(APIUsageLog.total_tokens).label("total_tokens"),
        (
            func.sum(
                case((APIUsageLog.status == 'success', 1), else_=0)
            ) / func.count()
        ).label("success_rate")
    ).where(
        APIUsageLog.user_id == current_user.id
    ).group_by(
        month_year
    ).order_by(
        month_year.desc()
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    # Get model-wise breakdown for each month
    response_data = []
    for row in rows:
        year, month = map(int, row.month.split('-'))
        
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
                extract('year', APIUsageLog.created_at) == year,
                extract('month', APIUsageLog.created_at) == month
            )
            .group_by(AIModel.name)
        )
        model_result = await db.execute(model_wise_stmt)
        model_rows = model_result.fetchall()

        response_data.append({
            "month": row.month,
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0),
            "total_tokens": row.total_tokens or 0,
            "success_rate": float(row.success_rate or 0),
            "model_wise_summary": [
                {
                    "model_name": model_row.model_name,
                    "total_requests": model_row.total_requests or 0,
                    "total_tokens": model_row.total_tokens or 0,
                    "total_cost": float(model_row.total_cost or 0)
                }
                for model_row in model_rows
            ]
        })
        
    return response_data