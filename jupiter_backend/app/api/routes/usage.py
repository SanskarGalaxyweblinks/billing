from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, case, cast, String, extract, and_, desc, or_
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.user_model_assignment import UserModelAssignment
from app.models.user_api_key import UserAPIKey
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("/monthly-summary")
async def get_monthly_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    month_year = func.concat(
        extract('year', APIUsageLog.created_at).cast(String),
        '-',
        func.lpad(extract('month', APIUsageLog.created_at).cast(String), 2, '0')
    ).label("month")

    # Get monthly summaries with enhanced metrics
    stmt = select(
        month_year,
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.sum(APIUsageLog.total_tokens).label("total_tokens"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(
                case((APIUsageLog.status == 'success', 1), else_=0)
            ) / func.count()
        ).label("success_rate"),
        func.count(func.distinct(APIUsageLog.model_id)).label("unique_models_used"),
        func.sum(case((APIUsageLog.billing_processed == True, 1), else_=0)).label("processed_requests"),
        func.sum(case((APIUsageLog.billing_processed == False, 1), else_=0)).label("unprocessed_requests")
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
                AIModel.provider.label("model_provider"),
                func.count().label("total_requests"),
                func.sum(APIUsageLog.total_tokens).label("total_tokens"),
                func.sum(APIUsageLog.total_cost).label("total_cost"),
                func.avg(APIUsageLog.response_time_ms).label("avg_response_time")
            )
            .join(AIModel, AIModel.id == APIUsageLog.model_id)
            .where(
                APIUsageLog.user_id == current_user.id,
                extract('year', APIUsageLog.created_at) == year,
                extract('month', APIUsageLog.created_at) == month
            )
            .group_by(AIModel.id, AIModel.name, AIModel.provider)
            .order_by(desc(func.sum(APIUsageLog.total_cost)))
        )
        model_result = await db.execute(model_wise_stmt)
        model_rows = model_result.fetchall()

        response_data.append({
            "month": row.month,
            "total_requests": row.total_requests or 0,
            "total_cost": float(row.total_cost or 0),
            "total_tokens": row.total_tokens or 0,
            "avg_response_time": round(row.avg_response_time or 0, 2),
            "success_rate": round(float(row.success_rate or 0), 4),
            "unique_models_used": row.unique_models_used or 0,
            "processed_requests": row.processed_requests or 0,
            "unprocessed_requests": row.unprocessed_requests or 0,
            "model_wise_summary": [
                {
                    "model_name": model_row.model_name,
                    "model_provider": model_row.model_provider,
                    "total_requests": model_row.total_requests or 0,
                    "total_tokens": model_row.total_tokens or 0,
                    "total_cost": float(model_row.total_cost or 0),
                    "avg_response_time": round(model_row.avg_response_time or 0, 2)
                }
                for model_row in model_rows
            ]
        })
        
    return response_data

@router.get("/current-usage")
async def get_current_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current month usage with limits and remaining quota"""
    
    # Current month boundaries
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get current month usage
    usage_stmt = select(
        func.count().label("requests_used"),
        func.sum(APIUsageLog.total_tokens).label("tokens_used"),
        func.sum(APIUsageLog.total_cost).label("cost_used"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(case((APIUsageLog.status == 'success', 1), else_=0)) / func.count()
        ).label("success_rate")
    ).where(
        and_(
            APIUsageLog.user_id == current_user.id,
            APIUsageLog.created_at >= start_of_month
        )
    )
    
    usage_result = await db.execute(usage_stmt)
    usage_data = usage_result.fetchone()
    
    # Get user limits
    user_limits = {
        "monthly_request_limit": current_user.monthly_request_limit,
        "monthly_token_limit": current_user.monthly_token_limit,
        "monthly_cost_limit": float(current_user.monthly_cost_limit) if current_user.monthly_cost_limit else None
    }
    
    # Calculate remaining quotas
    requests_used = usage_data.requests_used or 0
    tokens_used = usage_data.tokens_used or 0
    cost_used = float(usage_data.cost_used or 0)
    
    remaining_requests = (user_limits["monthly_request_limit"] - requests_used) if user_limits["monthly_request_limit"] else None
    remaining_tokens = (user_limits["monthly_token_limit"] - tokens_used) if user_limits["monthly_token_limit"] else None
    remaining_cost = (user_limits["monthly_cost_limit"] - cost_used) if user_limits["monthly_cost_limit"] else None
    
    # Calculate usage percentages
    request_usage_percent = (requests_used / user_limits["monthly_request_limit"] * 100) if user_limits["monthly_request_limit"] else 0
    token_usage_percent = (tokens_used / user_limits["monthly_token_limit"] * 100) if user_limits["monthly_token_limit"] else 0
    cost_usage_percent = (cost_used / user_limits["monthly_cost_limit"] * 100) if user_limits["monthly_cost_limit"] else 0
    
    return {
        "current_month": start_of_month.strftime("%Y-%m"),
        "usage": {
            "requests_used": requests_used,
            "tokens_used": tokens_used,
            "cost_used": cost_used,
            "avg_response_time": round(usage_data.avg_response_time or 0, 2),
            "success_rate": round(float(usage_data.success_rate or 0), 4)
        },
        "limits": user_limits,
        "remaining": {
            "requests": remaining_requests,
            "tokens": remaining_tokens,
            "cost": remaining_cost
        },
        "usage_percentages": {
            "requests": round(request_usage_percent, 2),
            "tokens": round(token_usage_percent, 2),
            "cost": round(cost_usage_percent, 2)
        },
        "alerts": {
            "approaching_request_limit": request_usage_percent > 80,
            "approaching_token_limit": token_usage_percent > 80,
            "approaching_cost_limit": cost_usage_percent > 80
        }
    }

@router.get("/model-assignments")
async def get_user_model_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's assigned models with usage statistics"""
    
    # Get active model assignments
    assignments_stmt = select(
        UserModelAssignment,
        AIModel.name.label("model_name"),
        AIModel.provider.label("model_provider"),
        AIModel.status.label("model_status")
    ).join(
        AIModel, UserModelAssignment.model_id == AIModel.id
    ).where(
        UserModelAssignment.user_id == current_user.id,
        UserModelAssignment.is_active == True
    ).order_by(UserModelAssignment.assigned_at.desc())
    
    assignments_result = await db.execute(assignments_stmt)
    assignments_data = assignments_result.all()
    
    # Get usage stats for each assigned model (current month)
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    model_assignments = []
    for assignment, model_name, model_provider, model_status in assignments_data:
        # Get current month usage for this model
        model_usage_stmt = select(
            func.count().label("requests_this_month"),
            func.sum(APIUsageLog.total_tokens).label("tokens_this_month"),
            func.sum(APIUsageLog.total_cost).label("cost_this_month"),
            func.max(APIUsageLog.created_at).label("last_used")
        ).where(
            and_(
                APIUsageLog.user_id == current_user.id,
                APIUsageLog.model_id == assignment.model_id,
                APIUsageLog.created_at >= start_of_month
            )
        )
        
        usage_result = await db.execute(model_usage_stmt)
        usage_data = usage_result.fetchone()
        
        # Check limits
        limits_check = assignment.check_usage_limits(
            request_count=usage_data.requests_this_month or 0,
            token_count=usage_data.tokens_this_month or 0,
            cost=float(usage_data.cost_this_month or 0)
        )
        
        model_assignments.append({
            "assignment_id": assignment.id,
            "model_id": assignment.model_id,
            "model_name": model_name,
            "model_provider": model_provider,
            "model_status": model_status,
            "access_level": assignment.access_level,
            "assigned_at": assignment.assigned_at.isoformat(),
            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
            "current_month_usage": {
                "requests": usage_data.requests_this_month or 0,
                "tokens": usage_data.tokens_this_month or 0,
                "cost": float(usage_data.cost_this_month or 0),
                "last_used": usage_data.last_used.isoformat() if usage_data.last_used else None
            },
            "limits": {
                "daily_request_limit": assignment.daily_request_limit,
                "monthly_request_limit": assignment.monthly_request_limit,
                "daily_token_limit": assignment.daily_token_limit,
                "monthly_token_limit": assignment.monthly_token_limit,
                "rate_limits": {
                    "per_minute": assignment.requests_per_minute,
                    "per_hour": assignment.requests_per_hour
                }
            },
            "limits_status": limits_check,
            "total_usage": {
                "requests": assignment.total_requests_made,
                "tokens": assignment.total_tokens_used,
                "cost": float(assignment.total_cost_incurred)
            }
        })
    
    return {
        "total_assignments": len(model_assignments),
        "assignments": model_assignments
    }

@router.get("/api-keys")
async def get_user_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's API keys with usage statistics"""
    
    api_keys_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == current_user.id
    ).order_by(UserAPIKey.created_at.desc())
    
    api_keys_result = await db.execute(api_keys_stmt)
    api_keys = api_keys_result.scalars().all()
    
    # Get usage stats for each API key (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    api_key_data = []
    for api_key in api_keys:
        # Get recent usage for this API key
        key_usage_stmt = select(
            func.count().label("requests_last_30_days"),
            func.sum(APIUsageLog.total_cost).label("cost_last_30_days"),
            func.max(APIUsageLog.created_at).label("last_used")
        ).where(
            and_(
                APIUsageLog.user_id == current_user.id,
                APIUsageLog.api_key_id == api_key.id,
                APIUsageLog.created_at >= thirty_days_ago
            )
        )
        
        usage_result = await db.execute(key_usage_stmt)
        usage_data = usage_result.fetchone()
        
        api_key_data.append({
            "id": api_key.id,
            "key_name": api_key.key_name,
            "api_key_prefix": api_key.api_key_prefix,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at.isoformat(),
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "rate_limits": {
                "per_minute": api_key.rate_limit_per_minute,
                "per_hour": api_key.rate_limit_per_hour,
                "per_day": api_key.rate_limit_per_day
            },
            "usage_last_30_days": {
                "requests": usage_data.requests_last_30_days or 0,
                "cost": float(usage_data.cost_last_30_days or 0),
                "last_used": usage_data.last_used.isoformat() if usage_data.last_used else None
            },
            "status": {
                "is_expired": api_key.is_expired(),
                "is_accessible": api_key.is_active and not api_key.is_expired()
            }
        })
    
    return {
        "total_api_keys": len(api_key_data),
        "active_api_keys": sum(1 for key in api_key_data if key["status"]["is_accessible"]),
        "api_keys": api_key_data
    }

@router.get("/daily-usage")
async def get_daily_usage(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to retrieve"),
    model_id: Optional[int] = Query(None, description="Filter by specific model"),
    current_user: User = Depends(get_current_user)
):
    """Get daily usage breakdown for charts and analytics"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Build query with optional model filter
    base_filter = and_(
        APIUsageLog.user_id == current_user.id,
        APIUsageLog.created_at >= start_date
    )
    
    if model_id:
        base_filter = and_(base_filter, APIUsageLog.model_id == model_id)
    
    daily_stmt = select(
        func.date(APIUsageLog.created_at).label("usage_date"),
        func.count().label("total_requests"),
        func.sum(APIUsageLog.total_cost).label("total_cost"),
        func.sum(APIUsageLog.total_tokens).label("total_tokens"),
        func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
        (
            func.sum(case((APIUsageLog.status == 'success', 1), else_=0)) / func.count()
        ).label("success_rate")
    ).where(
        base_filter
    ).group_by(
        func.date(APIUsageLog.created_at)
    ).order_by(
        func.date(APIUsageLog.created_at)
    )
    
    daily_result = await db.execute(daily_stmt)
    daily_data = daily_result.fetchall()
    
    return {
        "period": {
            "days": days,
            "start_date": start_date.date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat()
        },
        "model_filter": model_id,
        "daily_usage": [
            {
                "date": row.usage_date.isoformat(),
                "total_requests": row.total_requests or 0,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": row.total_tokens or 0,
                "avg_response_time": round(row.avg_response_time or 0, 2),
                "success_rate": round(float(row.success_rate or 0), 4)
            }
            for row in daily_data
        ]
    }

@router.get("/usage-alerts")
async def get_usage_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage alerts and warnings for the user"""
    
    alerts = []
    
    # Check current month usage against limits
    current_usage = await get_current_usage(db, current_user)
    
    # Request limit alerts
    if current_usage["usage_percentages"]["requests"] > 90:
        alerts.append({
            "type": "critical",
            "category": "requests",
            "message": f"You've used {current_usage['usage_percentages']['requests']:.1f}% of your monthly request limit",
            "details": {
                "used": current_usage["usage"]["requests_used"],
                "limit": current_usage["limits"]["monthly_request_limit"],
                "remaining": current_usage["remaining"]["requests"]
            }
        })
    elif current_usage["usage_percentages"]["requests"] > 80:
        alerts.append({
            "type": "warning",
            "category": "requests",
            "message": f"You've used {current_usage['usage_percentages']['requests']:.1f}% of your monthly request limit",
            "details": {
                "used": current_usage["usage"]["requests_used"],
                "limit": current_usage["limits"]["monthly_request_limit"],
                "remaining": current_usage["remaining"]["requests"]
            }
        })
    
    # Token limit alerts
    if current_usage["usage_percentages"]["tokens"] > 90:
        alerts.append({
            "type": "critical",
            "category": "tokens",
            "message": f"You've used {current_usage['usage_percentages']['tokens']:.1f}% of your monthly token limit",
            "details": {
                "used": current_usage["usage"]["tokens_used"],
                "limit": current_usage["limits"]["monthly_token_limit"],
                "remaining": current_usage["remaining"]["tokens"]
            }
        })
    elif current_usage["usage_percentages"]["tokens"] > 80:
        alerts.append({
            "type": "warning",
            "category": "tokens",
            "message": f"You've used {current_usage['usage_percentages']['tokens']:.1f}% of your monthly token limit",
            "details": {
                "used": current_usage["usage"]["tokens_used"],
                "limit": current_usage["limits"]["monthly_token_limit"],
                "remaining": current_usage["remaining"]["tokens"]
            }
        })
    
    # Cost limit alerts
    if current_usage["usage_percentages"]["cost"] > 90:
        alerts.append({
            "type": "critical",
            "category": "cost",
            "message": f"You've used {current_usage['usage_percentages']['cost']:.1f}% of your monthly cost limit",
            "details": {
                "used": current_usage["usage"]["cost_used"],
                "limit": current_usage["limits"]["monthly_cost_limit"],
                "remaining": current_usage["remaining"]["cost"]
            }
        })
    elif current_usage["usage_percentages"]["cost"] > 80:
        alerts.append({
            "type": "warning",
            "category": "cost",
            "message": f"You've used {current_usage['usage_percentages']['cost']:.1f}% of your monthly cost limit",
            "details": {
                "used": current_usage["usage"]["cost_used"],
                "limit": current_usage["limits"]["monthly_cost_limit"],
                "remaining": current_usage["remaining"]["cost"]
            }
        })
    
    # Check for expiring API keys
    api_keys_data = await get_user_api_keys(db, current_user)
    for api_key in api_keys_data["api_keys"]:
        if api_key["expires_at"]:
            expires_at = datetime.fromisoformat(api_key["expires_at"].replace('Z', '+00:00'))
            days_until_expiry = (expires_at - datetime.utcnow()).days
            
            if days_until_expiry <= 7 and days_until_expiry > 0:
                alerts.append({
                    "type": "warning",
                    "category": "api_key",
                    "message": f"API key '{api_key['key_name']}' expires in {days_until_expiry} days",
                    "details": {
                        "api_key_id": api_key["id"],
                        "expires_at": api_key["expires_at"],
                        "days_remaining": days_until_expiry
                    }
                })
            elif days_until_expiry <= 0:
                alerts.append({
                    "type": "critical",
                    "category": "api_key",
                    "message": f"API key '{api_key['key_name']}' has expired",
                    "details": {
                        "api_key_id": api_key["id"],
                        "expires_at": api_key["expires_at"]
                    }
                })
    
    return {
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["type"] == "critical"]),
        "warning_alerts": len([a for a in alerts if a["type"] == "warning"]),
        "alerts": alerts
    }

# Legacy endpoint for backward compatibility
@router.get("/")
async def get_monthly_summary_legacy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy endpoint - redirects to monthly-summary"""
    return await get_monthly_summary(db, current_user)