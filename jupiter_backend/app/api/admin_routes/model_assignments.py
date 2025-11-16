from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, delete
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.api.deps import get_db, get_current_admin
from app.models.user_model_assignment import UserModelAssignment
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.admin import Admin

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class ModelAssignmentCreate(BaseModel):
    user_id: int
    model_id: int
    access_level: str = Field(default="read_write", description="Access level: read_only, read_write, admin")
    daily_request_limit: Optional[int] = Field(None, description="Daily request limit for this model")
    monthly_request_limit: Optional[int] = Field(None, description="Monthly request limit for this model")
    daily_token_limit: Optional[int] = Field(None, description="Daily token limit for this model")
    monthly_token_limit: Optional[int] = Field(None, description="Monthly token limit for this model")
    daily_cost_limit: Optional[float] = Field(None, description="Daily cost limit for this model")
    monthly_cost_limit: Optional[float] = Field(None, description="Monthly cost limit for this model")
    requests_per_minute: int = Field(default=10, description="Rate limit: requests per minute")
    requests_per_hour: int = Field(default=100, description="Rate limit: requests per hour")
    custom_pricing_enabled: bool = Field(default=False, description="Enable custom pricing")
    custom_cost_per_token: Optional[float] = Field(None, description="Custom cost per token")
    custom_cost_per_request: Optional[float] = Field(None, description="Custom cost per request")
    discount_percentage: float = Field(default=0, description="Discount percentage (0-100)")
    expires_in_days: Optional[int] = Field(None, description="Assignment expires in X days")
    assignment_reason: Optional[str] = Field(None, description="Reason for assignment")
    ip_whitelist: Optional[List[str]] = Field(None, description="Allowed IP addresses")
    model_config: Optional[Dict[str, Any]] = Field(None, description="Model-specific configuration")

class ModelAssignmentUpdate(BaseModel):
    access_level: Optional[str] = Field(None, description="Access level: read_only, read_write, admin")
    is_active: Optional[bool] = Field(None, description="Whether assignment is active")
    daily_request_limit: Optional[int] = None
    monthly_request_limit: Optional[int] = None
    daily_token_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    daily_cost_limit: Optional[float] = None
    monthly_cost_limit: Optional[float] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    custom_pricing_enabled: Optional[bool] = None
    custom_cost_per_token: Optional[float] = None
    custom_cost_per_request: Optional[float] = None
    discount_percentage: Optional[float] = None
    expires_in_days: Optional[int] = None
    assignment_reason: Optional[str] = None
    notes: Optional[str] = None
    ip_whitelist: Optional[List[str]] = None
    model_config: Optional[Dict[str, Any]] = None

class ModelAssignmentResponse(BaseModel):
    id: int
    user_id: int
    model_id: int
    is_active: bool
    access_level: str
    daily_request_limit: Optional[int]
    monthly_request_limit: Optional[int]
    daily_token_limit: Optional[int]
    monthly_token_limit: Optional[int]
    daily_cost_limit: Optional[float]
    monthly_cost_limit: Optional[float]
    requests_per_minute: int
    requests_per_hour: int
    custom_pricing_enabled: bool
    custom_cost_per_token: Optional[float]
    custom_cost_per_request: Optional[float]
    discount_percentage: float
    total_requests_made: int
    total_tokens_used: int
    total_cost_incurred: float
    last_used_at: Optional[datetime]
    assigned_at: datetime
    expires_at: Optional[datetime]
    assignment_reason: Optional[str]
    notes: Optional[str]
    
    # Related data
    user_email: Optional[str] = None
    user_organization: Optional[str] = None
    model_name: Optional[str] = None
    model_provider: Optional[str] = None

class BulkAssignmentCreate(BaseModel):
    user_ids: List[int]
    model_ids: List[int]
    assignment_template: ModelAssignmentCreate

class AssignmentStatsResponse(BaseModel):
    total_assignments: int
    active_assignments: int
    expired_assignments: int
    users_with_assignments: int
    models_assigned: int
    total_usage_cost: float

# --- CRUD Endpoints ---

@router.get("/model-assignments", response_model=List[ModelAssignmentResponse])
async def get_all_assignments(
    skip: int = Query(0, description="Records to skip"),
    limit: int = Query(100, description="Max records to return"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    access_level: Optional[str] = Query(None, description="Filter by access level"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all model assignments with filtering options"""
    
    # Build query with filters
    query = select(UserModelAssignment, User.email, User.organization_name, AIModel.name, AIModel.provider).join(
        User, UserModelAssignment.user_id == User.id
    ).join(
        AIModel, UserModelAssignment.model_id == AIModel.id
    )
    
    if user_id:
        query = query.where(UserModelAssignment.user_id == user_id)
    if model_id:
        query = query.where(UserModelAssignment.model_id == model_id)
    if is_active is not None:
        query = query.where(UserModelAssignment.is_active == is_active)
    if access_level:
        query = query.where(UserModelAssignment.access_level == access_level)
    
    query = query.order_by(UserModelAssignment.assigned_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    assignments_data = result.all()
    
    assignments = []
    for assignment, user_email, user_org, model_name, model_provider in assignments_data:
        assignment_dict = {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "model_id": assignment.model_id,
            "is_active": assignment.is_active,
            "access_level": assignment.access_level,
            "daily_request_limit": assignment.daily_request_limit,
            "monthly_request_limit": assignment.monthly_request_limit,
            "daily_token_limit": assignment.daily_token_limit,
            "monthly_token_limit": assignment.monthly_token_limit,
            "daily_cost_limit": float(assignment.daily_cost_limit) if assignment.daily_cost_limit else None,
            "monthly_cost_limit": float(assignment.monthly_cost_limit) if assignment.monthly_cost_limit else None,
            "requests_per_minute": assignment.requests_per_minute,
            "requests_per_hour": assignment.requests_per_hour,
            "custom_pricing_enabled": assignment.custom_pricing_enabled,
            "custom_cost_per_token": float(assignment.custom_cost_per_token) if assignment.custom_cost_per_token else None,
            "custom_cost_per_request": float(assignment.custom_cost_per_request) if assignment.custom_cost_per_request else None,
            "discount_percentage": float(assignment.discount_percentage),
            "total_requests_made": assignment.total_requests_made,
            "total_tokens_used": assignment.total_tokens_used,
            "total_cost_incurred": float(assignment.total_cost_incurred),
            "last_used_at": assignment.last_used_at,
            "assigned_at": assignment.assigned_at,
            "expires_at": assignment.expires_at,
            "assignment_reason": assignment.assignment_reason,
            "notes": assignment.notes,
            "user_email": user_email,
            "user_organization": user_org,
            "model_name": model_name,
            "model_provider": model_provider
        }
        assignments.append(ModelAssignmentResponse(**assignment_dict))
    
    return assignments

@router.post("/model-assignments", response_model=ModelAssignmentResponse)
async def create_assignment(
    assignment_data: ModelAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new user-model assignment"""
    
    # Validate user exists
    user_stmt = select(User).where(User.id == assignment_data.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {assignment_data.user_id} not found")
    
    # Validate model exists
    model_stmt = select(AIModel).where(AIModel.id == assignment_data.model_id)
    model_result = await db.execute(model_stmt)
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model with ID {assignment_data.model_id} not found")
    
    # Check if assignment already exists
    existing_stmt = select(UserModelAssignment).where(
        and_(
            UserModelAssignment.user_id == assignment_data.user_id,
            UserModelAssignment.model_id == assignment_data.model_id,
            UserModelAssignment.is_active == True
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing_assignment = existing_result.scalar_one_or_none()
    
    if existing_assignment:
        raise HTTPException(
            status_code=400, 
            detail=f"Active assignment already exists between user {assignment_data.user_id} and model {assignment_data.model_id}"
        )
    
    # Create the assignment
    assignment = UserModelAssignment(
        user_id=assignment_data.user_id,
        model_id=assignment_data.model_id,
        assigned_by=current_admin.id,
        access_level=assignment_data.access_level,
        daily_request_limit=assignment_data.daily_request_limit,
        monthly_request_limit=assignment_data.monthly_request_limit,
        daily_token_limit=assignment_data.daily_token_limit,
        monthly_token_limit=assignment_data.monthly_token_limit,
        daily_cost_limit=assignment_data.daily_cost_limit,
        monthly_cost_limit=assignment_data.monthly_cost_limit,
        requests_per_minute=assignment_data.requests_per_minute,
        requests_per_hour=assignment_data.requests_per_hour,
        custom_pricing_enabled=assignment_data.custom_pricing_enabled,
        custom_cost_per_token=assignment_data.custom_cost_per_token,
        custom_cost_per_request=assignment_data.custom_cost_per_request,
        discount_percentage=assignment_data.discount_percentage,
        assignment_reason=assignment_data.assignment_reason
    )
    
    # Set expiration if provided
    if assignment_data.expires_in_days:
        assignment.expires_at = datetime.utcnow() + timedelta(days=assignment_data.expires_in_days)
    
    # Set IP whitelist if provided
    if assignment_data.ip_whitelist:
        assignment.set_ip_whitelist(assignment_data.ip_whitelist)
    
    # Set model config if provided
    if assignment_data.model_config:
        assignment.set_model_config(assignment_data.model_config)
    
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    
    # Get the complete assignment data for response
    response_data = {
        "id": assignment.id,
        "user_id": assignment.user_id,
        "model_id": assignment.model_id,
        "is_active": assignment.is_active,
        "access_level": assignment.access_level,
        "daily_request_limit": assignment.daily_request_limit,
        "monthly_request_limit": assignment.monthly_request_limit,
        "daily_token_limit": assignment.daily_token_limit,
        "monthly_token_limit": assignment.monthly_token_limit,
        "daily_cost_limit": float(assignment.daily_cost_limit) if assignment.daily_cost_limit else None,
        "monthly_cost_limit": float(assignment.monthly_cost_limit) if assignment.monthly_cost_limit else None,
        "requests_per_minute": assignment.requests_per_minute,
        "requests_per_hour": assignment.requests_per_hour,
        "custom_pricing_enabled": assignment.custom_pricing_enabled,
        "custom_cost_per_token": float(assignment.custom_cost_per_token) if assignment.custom_cost_per_token else None,
        "custom_cost_per_request": float(assignment.custom_cost_per_request) if assignment.custom_cost_per_request else None,
        "discount_percentage": float(assignment.discount_percentage),
        "total_requests_made": assignment.total_requests_made,
        "total_tokens_used": assignment.total_tokens_used,
        "total_cost_incurred": float(assignment.total_cost_incurred),
        "last_used_at": assignment.last_used_at,
        "assigned_at": assignment.assigned_at,
        "expires_at": assignment.expires_at,
        "assignment_reason": assignment.assignment_reason,
        "notes": assignment.notes,
        "user_email": user.email,
        "user_organization": user.organization_name,
        "model_name": model.name,
        "model_provider": model.provider
    }
    
    logger.info(f"Admin {current_admin.username} created assignment {assignment.id} for user {user.email} and model {model.name}")
    
    return ModelAssignmentResponse(**response_data)

@router.get("/model-assignments/{assignment_id}", response_model=ModelAssignmentResponse)
async def get_assignment(
    assignment_id: int = Path(..., description="Assignment ID"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get a specific assignment by ID"""
    
    query = select(UserModelAssignment, User.email, User.organization_name, AIModel.name, AIModel.provider).join(
        User, UserModelAssignment.user_id == User.id
    ).join(
        AIModel, UserModelAssignment.model_id == AIModel.id
    ).where(UserModelAssignment.id == assignment_id)
    
    result = await db.execute(query)
    assignment_data = result.first()
    
    if not assignment_data:
        raise HTTPException(status_code=404, detail=f"Assignment with ID {assignment_id} not found")
    
    assignment, user_email, user_org, model_name, model_provider = assignment_data
    
    response_data = {
        "id": assignment.id,
        "user_id": assignment.user_id,
        "model_id": assignment.model_id,
        "is_active": assignment.is_active,
        "access_level": assignment.access_level,
        "daily_request_limit": assignment.daily_request_limit,
        "monthly_request_limit": assignment.monthly_request_limit,
        "daily_token_limit": assignment.daily_token_limit,
        "monthly_token_limit": assignment.monthly_token_limit,
        "daily_cost_limit": float(assignment.daily_cost_limit) if assignment.daily_cost_limit else None,
        "monthly_cost_limit": float(assignment.monthly_cost_limit) if assignment.monthly_cost_limit else None,
        "requests_per_minute": assignment.requests_per_minute,
        "requests_per_hour": assignment.requests_per_hour,
        "custom_pricing_enabled": assignment.custom_pricing_enabled,
        "custom_cost_per_token": float(assignment.custom_cost_per_token) if assignment.custom_cost_per_token else None,
        "custom_cost_per_request": float(assignment.custom_cost_per_request) if assignment.custom_cost_per_request else None,
        "discount_percentage": float(assignment.discount_percentage),
        "total_requests_made": assignment.total_requests_made,
        "total_tokens_used": assignment.total_tokens_used,
        "total_cost_incurred": float(assignment.total_cost_incurred),
        "last_used_at": assignment.last_used_at,
        "assigned_at": assignment.assigned_at,
        "expires_at": assignment.expires_at,
        "assignment_reason": assignment.assignment_reason,
        "notes": assignment.notes,
        "user_email": user_email,
        "user_organization": user_org,
        "model_name": model_name,
        "model_provider": model_provider
    }
    
    return ModelAssignmentResponse(**response_data)

@router.put("/model-assignments/{assignment_id}", response_model=ModelAssignmentResponse)
async def update_assignment(
    assignment_id: int = Path(..., description="Assignment ID"),
    assignment_update: ModelAssignmentUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Update an existing assignment"""
    
    stmt = select(UserModelAssignment).where(UserModelAssignment.id == assignment_id)
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment with ID {assignment_id} not found")
    
    # Update fields
    update_data = assignment_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "ip_whitelist" and value is not None:
            assignment.set_ip_whitelist(value)
        elif field == "model_config" and value is not None:
            assignment.set_model_config(value)
        elif field == "expires_in_days" and value is not None:
            assignment.expires_at = datetime.utcnow() + timedelta(days=value)
        elif hasattr(assignment, field):
            setattr(assignment, field, value)
    
    await db.commit()
    await db.refresh(assignment)
    
    # Return updated assignment (reuse get_assignment logic)
    return await get_assignment(assignment_id, db, current_admin)

@router.delete("/model-assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int = Path(..., description="Assignment ID"),
    permanent: bool = Query(False, description="Permanently delete instead of deactivating"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete or deactivate an assignment"""
    
    stmt = select(UserModelAssignment).where(UserModelAssignment.id == assignment_id)
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail=f"Assignment with ID {assignment_id} not found")
    
    if permanent:
        await db.delete(assignment)
        message = f"Assignment {assignment_id} permanently deleted"
    else:
        assignment.deactivate(f"Deactivated by admin {current_admin.username}")
        message = f"Assignment {assignment_id} deactivated"
    
    await db.commit()
    
    logger.info(f"Admin {current_admin.username} {'deleted' if permanent else 'deactivated'} assignment {assignment_id}")
    
    return {"message": message}

@router.post("/model-assignments/bulk", response_model=Dict[str, Any])
async def create_bulk_assignments(
    bulk_data: BulkAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create multiple assignments at once"""
    
    created_assignments = []
    failed_assignments = []
    
    for user_id in bulk_data.user_ids:
        for model_id in bulk_data.model_ids:
            try:
                # Create individual assignment
                assignment_data = bulk_data.assignment_template.model_copy()
                assignment_data.user_id = user_id
                assignment_data.model_id = model_id
                
                # Check if assignment already exists
                existing_stmt = select(UserModelAssignment).where(
                    and_(
                        UserModelAssignment.user_id == user_id,
                        UserModelAssignment.model_id == model_id,
                        UserModelAssignment.is_active == True
                    )
                )
                existing_result = await db.execute(existing_stmt)
                existing_assignment = existing_result.scalar_one_or_none()
                
                if existing_assignment:
                    failed_assignments.append({
                        "user_id": user_id,
                        "model_id": model_id,
                        "error": "Assignment already exists"
                    })
                    continue
                
                assignment = UserModelAssignment(
                    user_id=user_id,
                    model_id=model_id,
                    assigned_by=current_admin.id,
                    access_level=assignment_data.access_level,
                    daily_request_limit=assignment_data.daily_request_limit,
                    monthly_request_limit=assignment_data.monthly_request_limit,
                    requests_per_minute=assignment_data.requests_per_minute,
                    requests_per_hour=assignment_data.requests_per_hour,
                    custom_pricing_enabled=assignment_data.custom_pricing_enabled,
                    discount_percentage=assignment_data.discount_percentage,
                    assignment_reason=assignment_data.assignment_reason
                )
                
                if assignment_data.expires_in_days:
                    assignment.expires_at = datetime.utcnow() + timedelta(days=assignment_data.expires_in_days)
                
                db.add(assignment)
                created_assignments.append({"user_id": user_id, "model_id": model_id})
                
            except Exception as e:
                failed_assignments.append({
                    "user_id": user_id,
                    "model_id": model_id,
                    "error": str(e)
                })
    
    await db.commit()
    
    logger.info(f"Admin {current_admin.username} created {len(created_assignments)} bulk assignments")
    
    return {
        "created_count": len(created_assignments),
        "failed_count": len(failed_assignments),
        "created_assignments": created_assignments,
        "failed_assignments": failed_assignments
    }

@router.get("/model-assignments/stats/overview", response_model=AssignmentStatsResponse)
async def get_assignment_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get overview statistics for model assignments"""
    
    # Total assignments
    total_stmt = select(func.count()).select_from(UserModelAssignment)
    total_result = await db.execute(total_stmt)
    total_assignments = total_result.scalar() or 0
    
    # Active assignments
    active_stmt = select(func.count()).select_from(UserModelAssignment).where(UserModelAssignment.is_active == True)
    active_result = await db.execute(active_stmt)
    active_assignments = active_result.scalar() or 0
    
    # Expired assignments
    expired_stmt = select(func.count()).select_from(UserModelAssignment).where(
        and_(
            UserModelAssignment.expires_at.isnot(None),
            UserModelAssignment.expires_at < datetime.utcnow()
        )
    )
    expired_result = await db.execute(expired_stmt)
    expired_assignments = expired_result.scalar() or 0
    
    # Users with assignments
    users_stmt = select(func.count(func.distinct(UserModelAssignment.user_id))).select_from(UserModelAssignment)
    users_result = await db.execute(users_stmt)
    users_with_assignments = users_result.scalar() or 0
    
    # Models assigned
    models_stmt = select(func.count(func.distinct(UserModelAssignment.model_id))).select_from(UserModelAssignment)
    models_result = await db.execute(models_stmt)
    models_assigned = models_result.scalar() or 0
    
    # Total usage cost
    cost_stmt = select(func.sum(UserModelAssignment.total_cost_incurred)).select_from(UserModelAssignment)
    cost_result = await db.execute(cost_stmt)
    total_usage_cost = float(cost_result.scalar() or 0)
    
    return AssignmentStatsResponse(
        total_assignments=total_assignments,
        active_assignments=active_assignments,
        expired_assignments=expired_assignments,
        users_with_assignments=users_with_assignments,
        models_assigned=models_assigned,
        total_usage_cost=total_usage_cost
    )