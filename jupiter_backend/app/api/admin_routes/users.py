from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

from app.models.user import User
from app.models.user_model_assignment import UserModelAssignment
from app.models.user_api_key import UserAPIKey
from app.models.ai_model import AIModel
from app.api.deps import get_db, get_current_admin
from app.models.admin import Admin

router = APIRouter()

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    subscription_tier_id: Optional[int] = None
    monthly_request_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    monthly_cost_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None

class ModelAssignmentSummary(BaseModel):
    assignment_id: int
    model_id: int
    model_name: str
    access_level: str
    is_active: bool
    total_requests: int
    total_cost: float
    last_used_at: Optional[datetime]

class APIKeySummary(BaseModel):
    id: int
    key_name: str
    api_key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime

class UserDetailedResponse(BaseModel):
    id: int
    auth_id: str
    email: str
    full_name: str
    is_active: bool
    created_at: Optional[str]
    organization_name: Optional[str]
    subscription_tier_id: Optional[int]
    monthly_request_limit: Optional[int]
    monthly_token_limit: Optional[int]
    monthly_cost_limit: Optional[Decimal]
    
    # Enhanced information
    model_assignments: List[ModelAssignmentSummary] = []
    api_keys: List[APIKeySummary] = []
    total_assigned_models: int = 0
    active_assignments: int = 0
    total_api_keys: int = 0
    active_api_keys: int = 0
    total_usage_cost: float = 0
    last_login: Optional[datetime] = None

class UserResponse(BaseModel):
    id: int
    auth_id: str
    email: str
    full_name: str
    is_active: bool
    created_at: Optional[str]
    organization_name: Optional[str]
    subscription_tier_id: Optional[int]
    monthly_request_limit: Optional[int]
    monthly_token_limit: Optional[int]
    monthly_cost_limit: Optional[Decimal]

class UserStatsResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    users_with_models: int
    users_with_api_keys: int
    total_model_assignments: int
    total_api_keys: int

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, description="Records to skip"),
    limit: int = Query(100, description="Max records to return"),
    search: Optional[str] = Query(None, description="Search by email or organization"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_assignments: Optional[bool] = Query(None, description="Filter users with model assignments"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches all users from the database with filtering options.
    This is an admin-only endpoint.
    """
    query = select(User)
    
    # Apply filters
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            User.email.ilike(search_term) | 
            User.organization_name.ilike(search_term) |
            User.full_name.ilike(search_term)
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if has_assignments is not None:
        if has_assignments:
            # Users with at least one model assignment
            query = query.where(
                User.id.in_(
                    select(UserModelAssignment.user_id).where(
                        UserModelAssignment.is_active == True
                    )
                )
            )
        else:
            # Users without any model assignments
            query = query.where(
                ~User.id.in_(
                    select(UserModelAssignment.user_id).where(
                        UserModelAssignment.is_active == True
                    )
                )
            )
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "auth_id": user.auth_id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "organization_name": user.organization_name,
            "subscription_tier_id": user.subscription_tier_id,
            "monthly_request_limit": user.monthly_request_limit,
            "monthly_token_limit": user.monthly_token_limit,
            "monthly_cost_limit": user.monthly_cost_limit,
        }
        for user in users
    ]

@router.get("/users/{user_id}", response_model=UserDetailedResponse)
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific user including assignments and API keys.
    """
    # Get user
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get model assignments with model details
    assignments_stmt = select(UserModelAssignment, AIModel.name).join(
        AIModel, UserModelAssignment.model_id == AIModel.id
    ).where(UserModelAssignment.user_id == user_id)
    assignments_result = await db.execute(assignments_stmt)
    assignments_data = assignments_result.all()
    
    model_assignments = []
    total_usage_cost = 0
    active_assignments = 0
    
    for assignment, model_name in assignments_data:
        if assignment.is_active:
            active_assignments += 1
        total_usage_cost += float(assignment.total_cost_incurred)
        
        model_assignments.append(ModelAssignmentSummary(
            assignment_id=assignment.id,
            model_id=assignment.model_id,
            model_name=model_name,
            access_level=assignment.access_level,
            is_active=assignment.is_active,
            total_requests=assignment.total_requests_made,
            total_cost=float(assignment.total_cost_incurred),
            last_used_at=assignment.last_used_at
        ))
    
    # Get API keys
    api_keys_stmt = select(UserAPIKey).where(UserAPIKey.user_id == user_id)
    api_keys_result = await db.execute(api_keys_stmt)
    api_keys_data = api_keys_result.scalars().all()
    
    api_keys = []
    active_api_keys = 0
    
    for api_key in api_keys_data:
        if api_key.is_active:
            active_api_keys += 1
            
        api_keys.append(APIKeySummary(
            id=api_key.id,
            key_name=api_key.key_name,
            api_key_prefix=api_key.api_key_prefix,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at
        ))
    
    return UserDetailedResponse(
        id=user.id,
        auth_id=user.auth_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        organization_name=user.organization_name,
        subscription_tier_id=user.subscription_tier_id,
        monthly_request_limit=user.monthly_request_limit,
        monthly_token_limit=user.monthly_token_limit,
        monthly_cost_limit=user.monthly_cost_limit,
        model_assignments=model_assignments,
        api_keys=api_keys,
        total_assigned_models=len(model_assignments),
        active_assignments=active_assignments,
        total_api_keys=len(api_keys),
        active_api_keys=active_api_keys,
        total_usage_cost=total_usage_cost
    )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Updates a user's details.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "auth_id": user.auth_id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "organization_name": user.organization_name,
        "subscription_tier_id": user.subscription_tier_id,
        "monthly_request_limit": user.monthly_request_limit,
        "monthly_token_limit": user.monthly_token_limit,
        "monthly_cost_limit": user.monthly_cost_limit,
    }

@router.get("/users/{user_id}/model-assignments")
async def get_user_model_assignments(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all model assignments for a specific user.
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    assignments_stmt = select(UserModelAssignment, AIModel.name, AIModel.provider).join(
        AIModel, UserModelAssignment.model_id == AIModel.id
    ).where(UserModelAssignment.user_id == user_id).order_by(UserModelAssignment.assigned_at.desc())
    
    assignments_result = await db.execute(assignments_stmt)
    assignments_data = assignments_result.all()
    
    assignments = []
    for assignment, model_name, model_provider in assignments_data:
        assignments.append({
            "assignment_id": assignment.id,
            "model_id": assignment.model_id,
            "model_name": model_name,
            "model_provider": model_provider,
            "access_level": assignment.access_level,
            "is_active": assignment.is_active,
            "daily_request_limit": assignment.daily_request_limit,
            "monthly_request_limit": assignment.monthly_request_limit,
            "total_requests_made": assignment.total_requests_made,
            "total_cost_incurred": float(assignment.total_cost_incurred),
            "last_used_at": assignment.last_used_at,
            "assigned_at": assignment.assigned_at,
            "expires_at": assignment.expires_at
        })
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "user_organization": user.organization_name,
        "assignments": assignments,
        "total_assignments": len(assignments),
        "active_assignments": sum(1 for a in assignments if a["is_active"])
    }

@router.get("/users/{user_id}/api-keys")
async def get_user_api_keys(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all API keys for a specific user.
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    api_keys_stmt = select(UserAPIKey).where(UserAPIKey.user_id == user_id).order_by(UserAPIKey.created_at.desc())
    api_keys_result = await db.execute(api_keys_stmt)
    api_keys = api_keys_result.scalars().all()
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "api_keys": [
            {
                "id": key.id,
                "key_name": key.key_name,
                "api_key_prefix": key.api_key_prefix,
                "is_active": key.is_active,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at,
                "created_at": key.created_at,
                "rate_limits": {
                    "per_minute": key.rate_limit_per_minute,
                    "per_hour": key.rate_limit_per_hour,
                    "per_day": key.rate_limit_per_day
                }
            }
            for key in api_keys
        ],
        "total_keys": len(api_keys),
        "active_keys": sum(1 for key in api_keys if key.is_active)
    }

@router.post("/users/{user_id}/deactivate-api-keys")
async def deactivate_user_api_keys(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Deactivate all API keys for a user (useful for security purposes).
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update all active API keys to inactive
    api_keys_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == user_id,
        UserAPIKey.is_active == True
    )
    api_keys_result = await db.execute(api_keys_stmt)
    api_keys = api_keys_result.scalars().all()
    
    deactivated_count = 0
    for api_key in api_keys:
        api_key.is_active = False
        deactivated_count += 1
    
    await db.commit()
    
    return {
        "message": f"Deactivated {deactivated_count} API keys for user {user.email}",
        "deactivated_count": deactivated_count,
        "user_id": user_id
    }

@router.get("/users/stats", response_model=UserStatsResponse)
async def get_users_stats(db: AsyncSession = Depends(get_db)):
    """
    Get overview statistics for all users.
    """
    # Total users
    total_users_stmt = select(func.count()).select_from(User)
    total_users_result = await db.execute(total_users_stmt)
    total_users = total_users_result.scalar() or 0
    
    # Active users
    active_users_stmt = select(func.count()).select_from(User).where(User.is_active == True)
    active_users_result = await db.execute(active_users_stmt)
    active_users = active_users_result.scalar() or 0
    
    # Users with model assignments
    users_with_models_stmt = select(func.count(func.distinct(UserModelAssignment.user_id))).select_from(UserModelAssignment).where(UserModelAssignment.is_active == True)
    users_with_models_result = await db.execute(users_with_models_stmt)
    users_with_models = users_with_models_result.scalar() or 0
    
    # Users with API keys
    users_with_keys_stmt = select(func.count(func.distinct(UserAPIKey.user_id))).select_from(UserAPIKey).where(UserAPIKey.is_active == True)
    users_with_keys_result = await db.execute(users_with_keys_stmt)
    users_with_api_keys = users_with_keys_result.scalar() or 0
    
    # Total model assignments
    total_assignments_stmt = select(func.count()).select_from(UserModelAssignment)
    total_assignments_result = await db.execute(total_assignments_stmt)
    total_model_assignments = total_assignments_result.scalar() or 0
    
    # Total API keys
    total_keys_stmt = select(func.count()).select_from(UserAPIKey)
    total_keys_result = await db.execute(total_keys_stmt)
    total_api_keys = total_keys_result.scalar() or 0
    
    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=total_users - active_users,
        users_with_models=users_with_models,
        users_with_api_keys=users_with_api_keys,
        total_model_assignments=total_model_assignments,
        total_api_keys=total_api_keys
    )