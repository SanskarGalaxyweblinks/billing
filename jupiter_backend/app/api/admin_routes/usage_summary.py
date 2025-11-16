from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, Date, and_, or_, desc
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.user_model_assignment import UserModelAssignment
from app.models.organization_model import OrganizationModel
from app.models.user_api_key import UserAPIKey
from app.api.deps import get_db, get_current_admin
from app.models.admin import Admin

router = APIRouter()

@router.get("/usage-summary")
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    organization_name: Optional[str] = Query(None, description="Filter by organization"),
    model_id: Optional[int] = Query(None, description="Filter by specific model"),
    include_unprocessed: bool = Query(False, description="Include unprocessed billing entries")
):
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Build base query with filters
    base_filter = and_(
        APIUsageLog.created_at >= start_dt,
        APIUsageLog.created_at <= end_dt
    )
    
    if organization_name:
        base_filter = and_(base_filter, User.organization_name.ilike(f"%{organization_name}%"))
    
    if model_id:
        base_filter = and_(base_filter, APIUsageLog.model_id == model_id)

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
        ).label("success_rate"),
        func.sum(case((APIUsageLog.billing_processed == True, 1), else_=0)).label("processed_entries"),
        func.sum(case((APIUsageLog.billing_processed == False, 1), else_=0)).label("unprocessed_entries")
    ).where(base_filter)
    
    if organization_name:
        global_stmt = global_stmt.join(User, User.id == APIUsageLog.user_id)
    
    global_result = await db.execute(global_stmt)
    global_data = global_result.fetchone()

    # Organization-wise Summary with enhanced metrics
    user_stmt = (
        select(
            User.organization_name.label("organization_name"),
            User.id.label("user_id"),
            User.email.label("user_email"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            (
                func.sum(
                    case((APIUsageLog.status == 'success', 1), else_=0)
                ) / func.count()
            ).label("success_rate"),
            func.sum(case((APIUsageLog.billing_processed == True, 1), else_=0)).label("processed_requests"),
            func.sum(case((APIUsageLog.billing_processed == False, 1), else_=0)).label("unprocessed_requests"),
            func.count(func.distinct(APIUsageLog.model_id)).label("unique_models_used")
        )
        .join(User, User.id == APIUsageLog.user_id)
        .where(base_filter)
        .group_by(User.id, User.organization_name, User.email)
        .order_by(desc(func.sum(APIUsageLog.total_cost)))
    )
    user_result = await db.execute(user_stmt)
    user_rows = user_result.fetchall()

    organization_stats = []
    for user_row in user_rows:
        # Get model-wise breakdown for this user
        model_wise_stmt = (
            select(
                AIModel.name.label("model_name"),
                AIModel.provider.label("model_provider"),
                func.count().label("total_requests"),
                func.sum(APIUsageLog.total_tokens).label("total_tokens"),
                func.sum(APIUsageLog.total_cost).label("total_cost"),
                func.avg(APIUsageLog.response_time_ms).label("avg_response_time")
            )
            .join(AIModel, AIModel.id == APIUsageLog.model_id)
            .where(
                APIUsageLog.user_id == user_row.user_id,
                APIUsageLog.created_at >= start_dt,
                APIUsageLog.created_at <= end_dt
            )
            .group_by(AIModel.id, AIModel.name, AIModel.provider)
            .order_by(desc(func.sum(APIUsageLog.total_cost)))
        )
        model_result = await db.execute(model_wise_stmt)
        model_rows = model_result.fetchall()
        
        # Get user's model assignments
        assignments_stmt = select(
            UserModelAssignment,
            AIModel.name.label("model_name")
        ).join(
            AIModel, UserModelAssignment.model_id == AIModel.id
        ).where(
            UserModelAssignment.user_id == user_row.user_id,
            UserModelAssignment.is_active == True
        )
        assignments_result = await db.execute(assignments_stmt)
        assignments_data = assignments_result.all()
        
        organization_stats.append({
            "organization_name": user_row.organization_name,
            "user_id": user_row.user_id,
            "user_email": user_row.user_email,
            "total_requests": user_row.total_requests or 0,
            "total_tokens": user_row.total_tokens or 0,
            "total_cost": float(user_row.total_cost or 0),
            "avg_response_time": round(user_row.avg_response_time or 0, 2),
            "success_rate": round(float(user_row.success_rate or 0), 4),
            "processed_requests": user_row.processed_requests or 0,
            "unprocessed_requests": user_row.unprocessed_requests or 0,
            "unique_models_used": user_row.unique_models_used or 0,
            "total_model_assignments": len(assignments_data),
            "model_wise_summary": [
                {
                    "model_name": row.model_name,
                    "model_provider": row.model_provider,
                    "total_requests": row.total_requests or 0,
                    "total_tokens": row.total_tokens or 0,
                    "total_cost": float(row.total_cost or 0),
                    "avg_response_time": round(row.avg_response_time or 0, 2)
                }
                for row in model_rows
            ]
        })

    # Global Model-wise Summary with enhanced metrics
    global_model_stmt = (
        select(
            AIModel.name.label("model_name"),
            AIModel.provider.label("model_provider"),
            AIModel.status.label("model_status"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            func.count(func.distinct(APIUsageLog.user_id)).label("unique_users"),
            (
                func.sum(
                    case((APIUsageLog.status == 'success', 1), else_=0)
                ) / func.count()
            ).label("success_rate")
        )
        .join(AIModel, AIModel.id == APIUsageLog.model_id)
        .where(base_filter)
        .group_by(AIModel.id, AIModel.name, AIModel.provider, AIModel.status)
        .order_by(desc(func.sum(APIUsageLog.total_cost)))
    )
    global_model_result = await db.execute(global_model_stmt)
    global_model_rows = global_model_result.fetchall()

    global_model_wise_summary = [
        {
            "model_name": row.model_name,
            "model_provider": row.model_provider,
            "model_status": row.model_status,
            "total_requests": row.total_requests or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0),
            "avg_response_time": round(row.avg_response_time or 0, 2),
            "unique_users": row.unique_users or 0,
            "success_rate": round(float(row.success_rate or 0), 4)
        }
        for row in global_model_rows
    ]

    # Company-based analytics (from raw model names)
    company_stmt = (
        select(
            APIUsageLog.company_name.label("company_name"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.count(func.distinct(APIUsageLog.raw_model_name)).label("unique_models"),
            func.sum(case((APIUsageLog.billing_processed == True, 1), else_=0)).label("processed_requests"),
            func.sum(case((APIUsageLog.billing_processed == False, 1), else_=0)).label("unprocessed_requests")
        )
        .where(
            and_(
                APIUsageLog.created_at >= start_dt,
                APIUsageLog.created_at <= end_dt,
                APIUsageLog.company_name.isnot(None)
            )
        )
        .group_by(APIUsageLog.company_name)
        .order_by(desc(func.sum(APIUsageLog.total_cost)))
    )
    company_result = await db.execute(company_stmt)
    company_rows = company_result.fetchall()

    company_analytics = [
        {
            "company_name": row.company_name,
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0),
            "unique_models": row.unique_models or 0,
            "processed_requests": row.processed_requests or 0,
            "unprocessed_requests": row.unprocessed_requests or 0,
            "processing_rate": round((row.processed_requests or 0) / (row.total_requests or 1) * 100, 2)
        }
        for row in company_rows
    ]

    response_data = {
        "date_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "global_summary": {
            "total_requests": global_data.total_requests or 0,
            "total_tokens": global_data.total_tokens or 0,
            "total_cost": float(global_data.total_cost or 0),
            "avg_response_time": round(global_data.avg_response_time or 0, 2),
            "success_rate": round(float(global_data.success_rate or 0), 4),
            "processed_entries": global_data.processed_entries or 0,
            "unprocessed_entries": global_data.unprocessed_entries or 0,
            "processing_rate": round((global_data.processed_entries or 0) / (global_data.total_requests or 1) * 100, 2)
        },
        "organization_stats": organization_stats,
        "global_model_wise_summary": global_model_wise_summary,
        "company_analytics": company_analytics
    }

    # Include unprocessed entries details if requested
    if include_unprocessed and global_data.unprocessed_entries > 0:
        unprocessed_stmt = (
            select(APIUsageLog)
            .where(
                and_(
                    APIUsageLog.billing_processed == False,
                    APIUsageLog.created_at >= start_dt,
                    APIUsageLog.created_at <= end_dt
                )
            )
            .order_by(APIUsageLog.created_at.desc())
            .limit(50)  # Limit to recent 50 unprocessed entries
        )
        unprocessed_result = await db.execute(unprocessed_stmt)
        unprocessed_entries = unprocessed_result.scalars().all()

        response_data["unprocessed_entries_sample"] = [
            {
                "id": entry.id,
                "raw_model_name": entry.raw_model_name,
                "company_name": entry.company_name,
                "status": entry.status,
                "error_message": entry.error_message,
                "retry_count": entry.retry_count,
                "created_at": entry.created_at.isoformat(),
                "user_mapped": entry.user_id is not None,
                "model_mapped": entry.model_id is not None
            }
            for entry in unprocessed_entries
        ]

    return response_data

@router.get("/usage-summary/trends")
async def get_usage_trends(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
    organization_name: Optional[str] = Query(None, description="Filter by organization"),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get usage trends over time for analytics dashboard"""
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily usage trends
    daily_stmt = (
        select(
            func.date(APIUsageLog.created_at).label("usage_date"),
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time")
        )
        .where(
            and_(
                APIUsageLog.created_at >= datetime.combine(start_date, datetime.min.time()),
                APIUsageLog.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        )
        .group_by(func.date(APIUsageLog.created_at))
        .order_by(func.date(APIUsageLog.created_at))
    )
    
    if organization_name:
        daily_stmt = daily_stmt.join(User, User.id == APIUsageLog.user_id).where(
            User.organization_name.ilike(f"%{organization_name}%")
        )
    
    daily_result = await db.execute(daily_stmt)
    daily_trends = daily_result.fetchall()

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days
        },
        "daily_trends": [
            {
                "date": trend.usage_date.isoformat(),
                "total_requests": trend.total_requests or 0,
                "total_cost": float(trend.total_cost or 0),
                "total_tokens": trend.total_tokens or 0,
                "avg_response_time": round(trend.avg_response_time or 0, 2)
            }
            for trend in daily_trends
        ]
    }

@router.get("/usage-summary/model-performance")
async def get_model_performance_metrics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze"),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get performance metrics for all models"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    performance_stmt = (
        select(
            AIModel.name.label("model_name"),
            AIModel.provider.label("provider"),
            func.count().label("total_requests"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            func.min(APIUsageLog.response_time_ms).label("min_response_time"),
            func.max(APIUsageLog.response_time_ms).label("max_response_time"),
            (
                func.sum(case((APIUsageLog.status == 'success', 1), else_=0)) / func.count() * 100
            ).label("success_rate"),
            func.sum(APIUsageLog.total_cost).label("total_revenue")
        )
        .join(AIModel, AIModel.id == APIUsageLog.model_id)
        .where(APIUsageLog.created_at >= start_date)
        .group_by(AIModel.id, AIModel.name, AIModel.provider)
        .order_by(desc(func.count()))
    )
    
    performance_result = await db.execute(performance_stmt)
    performance_data = performance_result.fetchall()

    return {
        "analysis_period_days": days,
        "model_performance": [
            {
                "model_name": row.model_name,
                "provider": row.provider,
                "total_requests": row.total_requests or 0,
                "avg_response_time": round(row.avg_response_time or 0, 2),
                "min_response_time": row.min_response_time or 0,
                "max_response_time": row.max_response_time or 0,
                "success_rate": round(float(row.success_rate or 0), 2),
                "total_revenue": float(row.total_revenue or 0)
            }
            for row in performance_data
        ]
    }

@router.get("/usage-summary/billing-health")
async def get_billing_system_health(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get billing system health metrics"""
    
    # Recent entries (last 24 hours)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    
    health_stmt = (
        select(
            func.count().label("total_recent_entries"),
            func.sum(case((APIUsageLog.billing_processed == True, 1), else_=0)).label("processed_entries"),
            func.sum(case((APIUsageLog.billing_processed == False, 1), else_=0)).label("unprocessed_entries"),
            func.sum(case((APIUsageLog.error_message.isnot(None), 1), else_=0)).label("failed_entries"),
            func.avg(
                func.extract('epoch', APIUsageLog.processed_at - APIUsageLog.created_at)
            ).label("avg_processing_time_seconds")
        )
        .where(APIUsageLog.created_at >= recent_cutoff)
    )
    
    health_result = await db.execute(health_stmt)
    health_data = health_result.fetchone()
    
    # Processing rate
    total_entries = health_data.total_recent_entries or 0
    processed_entries = health_data.processed_entries or 0
    processing_rate = (processed_entries / total_entries * 100) if total_entries > 0 else 100
    
    return {
        "last_24_hours": {
            "total_entries": total_entries,
            "processed_entries": processed_entries,
            "unprocessed_entries": health_data.unprocessed_entries or 0,
            "failed_entries": health_data.failed_entries or 0,
            "processing_rate": round(processing_rate, 2),
            "avg_processing_time_seconds": round(health_data.avg_processing_time_seconds or 0, 2)
        },
        "system_health": "healthy" if processing_rate >= 95 else "degraded" if processing_rate >= 80 else "unhealthy"
    }