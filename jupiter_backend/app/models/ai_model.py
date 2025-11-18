from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from app.database import Base


class AIModelStatus(str, enum.Enum):
    """Lifecycle states for a base AI model."""

    active = "active"
    inactive = "inactive"
    under_updation = "under_updation"


class CostCalculationType(str, enum.Enum):
    """Cost strategies for billing a model."""

    tokens = "tokens"
    request = "request"


def _capabilities_default() -> Dict[str, Any]:
    return {}


class AIModel(Base):
    """
    Core SQLAlchemy model for managing base AI models that power the platform.

    Previously the file accidentally contained admin router logic and no longer
    defined the ORM entity. The absence of this definition caused FastAPI to
    crash when importing `app.models.ai_model`. This class reintroduces the
    database schema so other modules (usage logs, assignments, analytics, etc.)
    can function correctly.
    """

    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    model_identifier = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Pricing & costing
    input_cost_per_1k_tokens = Column(Numeric(12, 6), default=0, nullable=False)
    output_cost_per_1k_tokens = Column(Numeric(12, 6), default=0, nullable=False)
    request_cost = Column(Numeric(12, 6), default=0, nullable=False)
    cost_calculation_type = Column(
        SAEnum(CostCalculationType, name="ai_model_cost_type"),
        default=CostCalculationType.tokens,
        nullable=False,
    )

    # Capabilities & limits
    max_tokens = Column(Integer, nullable=True)
    context_window = Column(Integer, nullable=True)
    capabilities = Column(JSON, default=_capabilities_default, nullable=True)
    endpoint = Column(String(500), nullable=True)

    # Metadata
    status = Column(
        SAEnum(AIModelStatus, name="ai_model_status"),
        default=AIModelStatus.active,
        nullable=False,
    )
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True)

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------

    def get_capabilities(self) -> Dict[str, Any]:
        """Return capabilities as a dictionary."""
        value = self.capabilities
        if value in (None, "", {}):
            return {}
        if isinstance(value, dict):
            return value
        # JSON columns may come back as strings depending on the driver
        try:
            import json

            return json.loads(value) if isinstance(value, str) else dict(value)
        except (ValueError, TypeError):
            return {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model fields into a plain dictionary for responses."""

        def _to_float(val: Optional[Numeric]) -> float:
            return float(val or 0)

        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model_identifier": self.model_identifier,
            "description": self.description,
            "input_cost_per_1k_tokens": _to_float(self.input_cost_per_1k_tokens),
            "output_cost_per_1k_tokens": _to_float(self.output_cost_per_1k_tokens),
            "request_cost": _to_float(self.request_cost),
            "cost_calculation_type": self.cost_calculation_type,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "capabilities": self.get_capabilities(),
            "status": self.status,
            "endpoint": self.endpoint,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AIModel id={self.id} name={self.name!r} provider={self.provider!r} status={self.status}>"
    organization_name: Optional[str] = None
    base_model_name: Optional[str] = None

class ModelUsageStatsResponse(BaseModel):
    model_id: int
    model_name: str
    total_requests: int
    total_cost: float
    total_tokens: int
    unique_users: int
    avg_response_time: float
    success_rate: float
    last_30_days_requests: int
    last_30_days_revenue: float

# ------------------- Core AI Model CRUD -------------------

@router.get("/models", response_model=List[AIModelOut])
async def get_all_models(
    skip: int = Query(0, description="Records to skip"),
    limit: int = Query(100, description="Max records to return"),
    status: Optional[AIModelStatus] = Query(None, description="Filter by status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    include_usage_stats: bool = Query(True, description="Include usage statistics"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all AI models with enhanced statistics"""
    
    # Build base query
    stmt = select(AIModel)
    
    # Apply filters
    if status:
        stmt = stmt.where(AIModel.status == status)
    if provider:
        stmt = stmt.where(AIModel.provider.ilike(f"%{provider}%"))
    
    stmt = stmt.order_by(AIModel.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    models_data = result.all()
    
    models_out = []
    for model, sub_id in models_data:
        model_dict = model.to_dict()
        model_dict['substitute_model_id'] = sub_id
        
        if include_usage_stats:
            # Get assignment statistics
            assignment_stats = await db.execute(
                select(
                    func.count().label("total"),
                    func.sum(func.cast(UserModelAssignment.is_active, Integer)).label("active")
                ).where(UserModelAssignment.model_id == model.id)
            )
            assignment_data = assignment_stats.fetchone()
            
            # Get usage statistics
            usage_stats = await db.execute(
                select(
                    func.count().label("requests"),
                    func.sum(APIUsageLog.total_cost).label("revenue")
                ).where(APIUsageLog.model_id == model.id)
            )
            usage_data = usage_stats.fetchone()
            
            # Get organization models count
            org_models_count = await db.execute(
                select(func.count()).where(OrganizationModel.base_model_id == model.id)
            )
            org_count = org_models_count.scalar() or 0
            
            model_dict.update({
                "total_assignments": assignment_data.total or 0,
                "active_assignments": assignment_data.active or 0,
                "total_usage_requests": usage_data.requests or 0,
                "total_revenue": float(usage_data.revenue or 0),
                "organization_models_count": org_count
            })
        
        models_out.append(AIModelOut(**model_dict))
    
    return models_out

@router.get("/models/{model_id}", response_model=AIModelOut)
async def get_model_by_id(
    model_id: int = Path(...),
    include_detailed_stats: bool = Query(True, description="Include detailed statistics"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get specific AI model with detailed statistics"""
    
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
    
    if include_detailed_stats:
        # Get detailed assignment statistics
        assignment_stats = await db.execute(
            select(
                func.count().label("total"),
                func.sum(func.cast(UserModelAssignment.is_active, Integer)).label("active")
            ).where(UserModelAssignment.model_id == model.id)
        )
        assignment_data = assignment_stats.fetchone()
        
        # Get detailed usage statistics
        usage_stats = await db.execute(
            select(
                func.count().label("requests"),
                func.sum(APIUsageLog.total_cost).label("revenue")
            ).where(APIUsageLog.model_id == model.id)
        )
        usage_data = usage_stats.fetchone()
        
        # Get organization models count
        org_models_count = await db.execute(
            select(func.count()).where(OrganizationModel.base_model_id == model.id)
        )
        org_count = org_models_count.scalar() or 0
        
        model_dict.update({
            "total_assignments": assignment_data.total or 0,
            "active_assignments": assignment_data.active or 0,
            "total_usage_requests": usage_data.requests or 0,
            "total_revenue": float(usage_data.revenue or 0),
            "organization_models_count": org_count
        })
    
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
    await db.flush()

    # Create substitution if status is under_updation
    if payload.status == AIModelStatus.under_updation:
        if not payload.substitute_model_id:
            raise HTTPException(
                status_code=400, 
                detail="substitute_model_id is required when status is 'under_updation'"
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
    response_data.update({
        "total_assignments": 0,
        "active_assignments": 0,
        "total_usage_requests": 0,
        "total_revenue": 0.0,
        "organization_models_count": 0
    })
    
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
    if payload.status == AIModelStatus.under_updation:
        if payload.substitute_model_id:
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
        else:
            await db.execute(
                delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
            )
            await db.commit()
    elif model.status != AIModelStatus.under_updation:
        await db.execute(
            delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
        )
        await db.commit()
    
    logger.info(f"Admin {current_admin.username} updated AI model: {model.name}")
    
    return await get_model_by_id(model_id, True, db, current_admin)

@router.delete("/models/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    force_delete: bool = Query(False, description="Force delete even with active assignments"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete an AI model"""
    
    stmt = select(AIModel).where(AIModel.id == model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check for active assignments
    if not force_delete:
        active_assignments = await db.execute(
            select(func.count()).where(
                and_(
                    UserModelAssignment.model_id == model_id,
                    UserModelAssignment.is_active == True
                )
            )
        )
        if active_assignments.scalar() > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete model with active user assignments. Use force_delete=true to override."
            )
    
    # Delete substitutions and model
    await db.execute(delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model_id))
    await db.delete(model)
    await db.commit()
    
    logger.info(f"Admin {current_admin.username} deleted AI model: {model.name}")
    
    return None

# ------------------- Organization Model Management -------------------

@router.get("/organization-models", response_model=List[OrganizationModelOut])
async def get_organization_models(
    skip: int = Query(0),
    limit: int = Query(100),
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all organization-specific models"""
    
    # Build query with joins for related data
    stmt = (
        select(
            OrganizationModel,
            User.organization_name.label("org_name"),
            AIModel.name.label("base_model_name")
        )
        .join(User, OrganizationModel.organization_id == User.id)
        .outerjoin(AIModel, OrganizationModel.base_model_id == AIModel.id)
    )
    
    # Apply filters
    if organization_id:
        stmt = stmt.where(OrganizationModel.organization_id == organization_id)
    if is_active is not None:
        stmt = stmt.where(OrganizationModel.is_active == is_active)
    
    stmt = stmt.order_by(OrganizationModel.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    models_data = result.all()
    
    return [
        OrganizationModelOut(
            **org_model.to_dict(),
            organization_name=org_name,
            base_model_name=base_model_name
        )
        for org_model, org_name, base_model_name in models_data
    ]

@router.post("/organization-models", response_model=OrganizationModelOut)
async def create_organization_model(
    payload: OrganizationModelCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Create a new organization-specific model"""
    
    # Validate organization exists
    org_stmt = select(User).where(User.id == payload.organization_id)
    org_result = await db.execute(org_stmt)
    organization = org_result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if model name already exists for this organization
    existing_stmt = select(OrganizationModel).where(
        and_(
            OrganizationModel.organization_id == payload.organization_id,
            OrganizationModel.model_name == payload.model_name
        )
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Model '{payload.model_name}' already exists for this organization"
        )
    
    # Create organization model
    org_model = OrganizationModel.create_organization_model(
        organization_id=payload.organization_id,
        model_name=payload.model_name,
        display_name=payload.display_name,
        model_type=payload.model_type,
        created_by_id=current_admin.id,
        endpoint_url=payload.endpoint_url,
        cost_per_request=payload.cost_per_request,
        description=payload.description,
        base_model_id=payload.base_model_id
    )
    
    # Set additional properties
    org_model.pricing_model = payload.pricing_model
    org_model.is_public = payload.is_public
    org_model.max_requests_per_minute = payload.max_requests_per_minute
    org_model.max_requests_per_hour = payload.max_requests_per_hour
    org_model.supported_languages = payload.supported_languages
    org_model.input_types = payload.input_types
    org_model.output_types = payload.output_types
    
    db.add(org_model)
    await db.commit()
    await db.refresh(org_model)
    
    logger.info(f"Admin {current_admin.username} created organization model: {org_model.model_name} for org: {organization.organization_name}")
    
    return OrganizationModelOut(
        **org_model.to_dict(),
        organization_name=organization.organization_name,
        base_model_name=None
    )

# ------------------- Model Usage Analytics -------------------

@router.get("/models/{model_id}/usage-stats", response_model=ModelUsageStatsResponse)
async def get_model_usage_stats(
    model_id: int = Path(...),
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get detailed usage statistics for a specific model"""
    
    # Verify model exists
    model_stmt = select(AIModel).where(AIModel.id == model_id)
    model_result = await db.execute(model_stmt)
    model = model_result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Calculate date ranges
    end_date = datetime.utcnow()
    start_date_all = datetime.min
    start_date_recent = end_date - timedelta(days=days)
    
    # Get all-time statistics
    all_time_stats = await db.execute(
        select(
            func.count().label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_cost"),
            func.sum(APIUsageLog.total_tokens).label("total_tokens"),
            func.count(func.distinct(APIUsageLog.user_id)).label("unique_users"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            (
                func.sum(func.cast(APIUsageLog.status == 'success', Integer)) / func.count()
            ).label("success_rate")
        ).where(APIUsageLog.model_id == model_id)
    )
    all_time_data = all_time_stats.fetchone()
    
    # Get recent statistics
    recent_stats = await db.execute(
        select(
            func.count().label("recent_requests"),
            func.sum(APIUsageLog.total_cost).label("recent_revenue")
        ).where(
            and_(
                APIUsageLog.model_id == model_id,
                APIUsageLog.created_at >= start_date_recent
            )
        )
    )
    recent_data = recent_stats.fetchone()
    
    return ModelUsageStatsResponse(
        model_id=model_id,
        model_name=model.name,
        total_requests=all_time_data.total_requests or 0,
        total_cost=float(all_time_data.total_cost or 0),
        total_tokens=all_time_data.total_tokens or 0,
        unique_users=all_time_data.unique_users or 0,
        avg_response_time=round(all_time_data.avg_response_time or 0, 2),
        success_rate=round(float(all_time_data.success_rate or 0), 4),
        last_30_days_requests=recent_data.recent_requests or 0,
        last_30_days_revenue=float(recent_data.recent_revenue or 0)
    )

@router.get("/models/{model_id}/assignments")
async def get_model_assignments(
    model_id: int = Path(...),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all user assignments for a specific model"""
    
    # Verify model exists
    model_stmt = select(AIModel).where(AIModel.id == model_id)
    model_result = await db.execute(model_stmt)
    model = model_result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Get assignments with user details
    assignments_stmt = (
        select(
            UserModelAssignment,
            User.email.label("user_email"),
            User.organization_name.label("user_organization")
        )
        .join(User, UserModelAssignment.user_id == User.id)
        .where(UserModelAssignment.model_id == model_id)
    )
    
    if is_active is not None:
        assignments_stmt = assignments_stmt.where(UserModelAssignment.is_active == is_active)
    
    assignments_stmt = assignments_stmt.order_by(UserModelAssignment.assigned_at.desc())
    
    assignments_result = await db.execute(assignments_stmt)
    assignments_data = assignments_result.all()
    
    return {
        "model_id": model_id,
        "model_name": model.name,
        "total_assignments": len(assignments_data),
        "assignments": [
            {
                "assignment_id": assignment.id,
                "user_id": assignment.user_id,
                "user_email": user_email,
                "user_organization": user_organization,
                "access_level": assignment.access_level,
                "is_active": assignment.is_active,
                "assigned_at": assignment.assigned_at.isoformat(),
                "total_requests": assignment.total_requests_made,
                "total_cost": float(assignment.total_cost_incurred),
                "last_used_at": assignment.last_used_at.isoformat() if assignment.last_used_at else None
            }
            for assignment, user_email, user_organization in assignments_data
        ]
    }

@router.get("/models/analytics/overview")
async def get_models_analytics_overview(
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get overview analytics for all models"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get model performance overview
    models_performance = await db.execute(
        select(
            AIModel.id.label("model_id"),
            AIModel.name.label("model_name"),
            AIModel.provider.label("provider"),
            AIModel.status.label("status"),
            func.count(APIUsageLog.id).label("total_requests"),
            func.sum(APIUsageLog.total_cost).label("total_revenue"),
            func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
            func.count(func.distinct(APIUsageLog.user_id)).label("unique_users"),
            (
                func.sum(func.cast(APIUsageLog.status == 'success', Integer)) / func.count()
            ).label("success_rate")
        )
        .outerjoin(APIUsageLog, AIModel.id == APIUsageLog.model_id)
        .where(
            or_(
                APIUsageLog.created_at >= start_date,
                APIUsageLog.created_at.is_(None)
            )
        )
        .group_by(AIModel.id, AIModel.name, AIModel.provider, AIModel.status)
        .order_by(desc(func.sum(APIUsageLog.total_cost)))
    )
    
    performance_data = models_performance.fetchall()
    
    # Get overall statistics
    overall_stats = await db.execute(
        select(
            func.count(func.distinct(AIModel.id)).label("total_models"),
            func.sum(func.cast(AIModel.status == AIModelStatus.active, Integer)).label("active_models"),
            func.count(func.distinct(UserModelAssignment.id)).label("total_assignments"),
            func.sum(func.cast(UserModelAssignment.is_active, Integer)).label("active_assignments")
        )
        .outerjoin(UserModelAssignment, AIModel.id == UserModelAssignment.model_id)
    )
    
    stats_data = overall_stats.fetchone()
    
    return {
        "analysis_period_days": days,
        "overview_stats": {
            "total_models": stats_data.total_models or 0,
            "active_models": stats_data.active_models or 0,
            "total_assignments": stats_data.total_assignments or 0,
            "active_assignments": stats_data.active_assignments or 0
        },
        "model_performance": [
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "provider": row.provider,
                "status": row.status,
                "total_requests": row.total_requests or 0,
                "total_revenue": float(row.total_revenue or 0),
                "avg_response_time": round(row.avg_response_time or 0, 2),
                "unique_users": row.unique_users or 0,
                "success_rate": round(float(row.success_rate or 0), 4)
            }
            for row in performance_data
        ]
    }
