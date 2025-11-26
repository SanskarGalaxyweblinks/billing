from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, desc, or_
from app.models.ai_model import AIModel, AIModelStatus, CostCalculationType
from app.models.model_substitutions import ModelSubstitution
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.api.deps import get_db, get_current_admin
from app.models.admin import Admin
from datetime import datetime, timedelta
import enum
import logging

# Import optional models with fallbacks
try:
    from app.models.organization_model import OrganizationModel
except ImportError:
    OrganizationModel = None

try:
    from app.models.user_model_assignment import UserModelAssignment
except ImportError:
    UserModelAssignment = None

logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------- Pydantic Schemas -------------------

class PydanticCostCalculationType(str, enum.Enum):
    tokens = "tokens"
    request = "request"

class AIModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    model_identifier: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    input_cost_per_1k_tokens: float = Field(default=0.0, ge=0)
    output_cost_per_1k_tokens: float = Field(default=0.0, ge=0)
    max_tokens: int = Field(default=4096, gt=0)
    context_window: int = Field(default=8192, gt=0)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    status: AIModelStatus = Field(default=AIModelStatus.active)
    substitute_model_id: Optional[int] = None
    request_cost: float = Field(default=0.0, ge=0)
    cost_calculation_type: PydanticCostCalculationType = Field(default=PydanticCostCalculationType.tokens)
    endpoint: Optional[str] = Field(None, max_length=500)
    is_public: bool = Field(default=True)

class AIModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider: Optional[str] = Field(None, min_length=1, max_length=100)
    model_identifier: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    input_cost_per_1k_tokens: Optional[float] = Field(None, ge=0)
    output_cost_per_1k_tokens: Optional[float] = Field(None, ge=0)
    max_tokens: Optional[int] = Field(None, gt=0)
    context_window: Optional[int] = Field(None, gt=0)
    capabilities: Optional[Dict[str, Any]] = None
    status: Optional[AIModelStatus] = None
    substitute_model_id: Optional[int] = None
    request_cost: Optional[float] = Field(None, ge=0)
    cost_calculation_type: Optional[PydanticCostCalculationType] = None
    endpoint: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None

class AIModelOut(BaseModel):
    id: int
    name: str
    provider: str
    model_identifier: str
    description: Optional[str] = None
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None
    status: AIModelStatus
    substitute_model_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_used_at: Optional[str] = None
    request_cost: float
    cost_calculation_type: PydanticCostCalculationType
    endpoint: Optional[str] = None
    is_public: bool

    class Config:
        from_attributes = True

# ------------------- CRUD Endpoints -------------------

@router.get("/models", response_model=List[AIModelOut])
async def get_all_models(
    skip: int = Query(0, description="Records to skip"),
    limit: int = Query(100, description="Max records to return"),
    status: Optional[AIModelStatus] = Query(None, description="Filter by status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all AI models with optional filtering and pagination"""
    
    # Build base query with LEFT JOIN for substitutions
    stmt = (
        select(AIModel, ModelSubstitution.substitute_model_id)
        .outerjoin(ModelSubstitution, AIModel.id == ModelSubstitution.original_model_id)
    )
    
    # Apply filters
    if status:
        stmt = stmt.where(AIModel.status == status)
    if provider:
        stmt = stmt.where(AIModel.provider.ilike(f"%{provider}%"))
    
    stmt = stmt.order_by(AIModel.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    
    # Process results
    models_out = []
    for model, sub_id in result.all():
        # Use the model's to_dict() method for consistent serialization
        model_dict = model.to_dict()
        model_dict['substitute_model_id'] = sub_id
        models_out.append(AIModelOut(**model_dict))
            
    return models_out

@router.get("/models/{model_id}", response_model=AIModelOut)
async def get_model_by_id(
    model_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get a specific AI model by ID"""
    
    stmt = (
        select(AIModel, ModelSubstitution.substitute_model_id)
        .outerjoin(ModelSubstitution, AIModel.id == ModelSubstitution.original_model_id)
        .where(AIModel.id == model_id)
    )
    result = await db.execute(stmt)
    record = result.one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Model not found")

    model, sub_id = record
    model_dict = model.to_dict()
    model_dict['substitute_model_id'] = sub_id
    
    return AIModelOut(**model_dict)

@router.post("/models", response_model=AIModelOut)
async def create_model(
    payload: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new AI model"""
    
    # Check if model_identifier already exists
    existing_stmt = select(AIModel).where(AIModel.model_identifier == payload.model_identifier)
    existing_result = await db.execute(existing_stmt)
    existing_model = existing_result.scalar_one_or_none()
    
    if existing_model:
        raise HTTPException(
            status_code=400, 
            detail=f"Model with identifier '{payload.model_identifier}' already exists"
        )
    
    # Exclude substitute_model_id when creating the AIModel object
    model_data = payload.model_dump(exclude={"substitute_model_id"})
    new_model = AIModel(**model_data)
    
    db.add(new_model)
    await db.flush()  # Get the new model ID

    # Create substitution if status is under_updation
    if payload.status == AIModelStatus.under_updation:
        if not payload.substitute_model_id:
            raise HTTPException(
                status_code=400, 
                detail="substitute_model_id is required when status is 'under_updation'"
            )
        
        # Verify substitute model exists
        substitute_stmt = select(AIModel).where(AIModel.id == payload.substitute_model_id)
        substitute_result = await db.execute(substitute_stmt)
        substitute_model = substitute_result.scalar_one_or_none()
        
        if not substitute_model:
            raise HTTPException(
                status_code=400,
                detail=f"Substitute model with ID {payload.substitute_model_id} does not exist"
            )
        
        substitution = ModelSubstitution(
            original_model_id=new_model.id,
            substitute_model_id=payload.substitute_model_id,
        )
        db.add(substitution)

    await db.commit()
    await db.refresh(new_model)

    # Construct response
    response_data = new_model.to_dict()
    response_data['substitute_model_id'] = payload.substitute_model_id if payload.status == AIModelStatus.under_updation else None
    
    logger.info(f"Admin {current_admin.username} created AI model: {new_model.name}")
    
    return AIModelOut(**response_data)

@router.put("/models/{model_id}", response_model=AIModelOut)
async def update_model(
    model_id: int,
    payload: AIModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Update an existing AI model"""
    
    stmt = select(AIModel).where(AIModel.id == model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Update model fields
    update_data = payload.model_dump(exclude_unset=True, exclude={"substitute_model_id"})
    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)

    # Handle substitution logic
    if payload.status == AIModelStatus.under_updation and payload.substitute_model_id:
        # Verify substitute model exists
        substitute_stmt = select(AIModel).where(AIModel.id == payload.substitute_model_id)
        substitute_result = await db.execute(substitute_stmt)
        substitute_model = substitute_result.scalar_one_or_none()
        
        if not substitute_model:
            raise HTTPException(
                status_code=400,
                detail=f"Substitute model with ID {payload.substitute_model_id} does not exist"
            )
        
        # Check if substitution already exists
        existing_stmt = select(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
        sub_result = await db.execute(existing_stmt)
        existing = sub_result.scalar_one_or_none()

        if existing:
            existing.substitute_model_id = payload.substitute_model_id
            existing.valid_to = None
        else:
            db.add(ModelSubstitution(
                original_model_id=model.id,
                substitute_model_id=payload.substitute_model_id,
            ))
        await db.commit()
    elif model.status != AIModelStatus.under_updation:
        # Clear existing substitution if status is no longer under_updation
        await db.execute(
            delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
        )
        await db.commit()
    
    # Get updated model with substitution info
    stmt_after = (
        select(AIModel, ModelSubstitution.substitute_model_id)
        .outerjoin(ModelSubstitution, AIModel.id == ModelSubstitution.original_model_id)
        .where(AIModel.id == model_id)
    )
    result_after = await db.execute(stmt_after)
    model_after, sub_id_after = result_after.one()

    response_data = model_after.to_dict()
    response_data['substitute_model_id'] = sub_id_after
    
    logger.info(f"Admin {current_admin.username} updated AI model: {model.name}")
    
    return AIModelOut(**response_data)

@router.delete("/models/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    force_delete: bool = Query(False, description="Force delete even with dependencies"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete an AI model"""
    
    stmt = select(AIModel).where(AIModel.id == model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check for dependencies if not force deleting
    if not force_delete:
        # Check for API usage logs
        usage_count = await db.execute(
            select(func.count()).where(APIUsageLog.model_id == model_id)
        )
        if usage_count.scalar() > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete model with existing usage logs. Use force_delete=true to override."
            )
    
    # Delete substitutions first
    await db.execute(delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model_id))
    await db.execute(delete(ModelSubstitution).where(ModelSubstitution.substitute_model_id == model_id))
    
    # Delete the model
    await db.delete(model)
    await db.commit()
    
    logger.info(f"Admin {current_admin.username} deleted AI model: {model.name}")
    
    return None

# ------------------- Model Analytics -------------------

@router.get("/models/{model_id}/usage-stats")
async def get_model_usage_stats(
    model_id: int = Path(...),
    days: int = Query(30, description="Number of days to analyze", gt=0, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get usage statistics for a specific model"""
    
    # Verify model exists
    model_stmt = select(AIModel).where(AIModel.id == model_id)
    model_result = await db.execute(model_stmt)
    model = model_result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get usage statistics
    stats_query = (
        select(
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.count(func.distinct(APIUsageLog.user_id)).label("unique_users"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            func.sum(func.case((APIUsageLog.status == 'success', 1), else_=0)).label("successful_requests")
        )
        .where(
            and_(
                APIUsageLog.model_id == model_id,
                APIUsageLog.created_at >= start_date
            )
        )
    )
    
    stats_result = await db.execute(stats_query)
    stats = stats_result.fetchone()
    
    # Calculate success rate
    success_rate = 0.0
    if stats.total_requests and stats.total_requests > 0:
        success_rate = (stats.successful_requests or 0) / stats.total_requests
    
    return {
        "model_id": model_id,
        "model_name": model.name,
        "analysis_period_days": days,
        "total_requests": stats.total_requests or 0,
        "total_cost": float(stats.total_cost or 0),
        "total_tokens": stats.total_tokens or 0,
        "unique_users": stats.unique_users or 0,
        "avg_response_time": round(float(stats.avg_response_time or 0), 2),
        "success_rate": round(success_rate, 4),
        "successful_requests": stats.successful_requests or 0
    }

@router.get("/models/analytics/overview")
async def get_models_overview(
    days: int = Query(30, description="Number of days to analyze", gt=0, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get overview analytics for all models"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get model performance overview
    performance_query = (
        select(
            AIModel.id.label("model_id"),
            AIModel.name.label("model_name"),
            AIModel.provider.label("provider"),
            AIModel.status.label("status"),
            func.count(APIUsageLog.id).label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_revenue"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            func.count(func.distinct(APIUsageLog.user_id)).label("unique_users")
        )
        .outerjoin(APIUsageLog, and_(
            AIModel.id == APIUsageLog.model_id,
            APIUsageLog.created_at >= start_date
        ))
        .group_by(AIModel.id, AIModel.name, AIModel.provider, AIModel.status)
        .order_by(func.sum(APIUsageLog.total_cost).desc().nullslast())
    )
    
    performance_result = await db.execute(performance_query)
    performance_data = performance_result.fetchall()
    
    # Get overall statistics
    total_models = await db.execute(select(func.count()).select_from(AIModel))
    active_models = await db.execute(
        select(func.count()).where(AIModel.status == AIModelStatus.active)
    )
    
    return {
        "analysis_period_days": days,
        "overview_stats": {
            "total_models": total_models.scalar() or 0,
            "active_models": active_models.scalar() or 0
        },
        "model_performance": [
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "provider": row.provider,
                "status": row.status,
                "total_requests": row.total_requests or 0,
                "total_revenue": float(row.total_revenue or 0),
                "avg_response_time": round(float(row.avg_response_time or 0), 2),
                "unique_users": row.unique_users or 0
            }
            for row in performance_data
        ]
    }