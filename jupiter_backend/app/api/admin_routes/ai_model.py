from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, desc, or_
from app.models.ai_model import AIModel, AIModelStatus, CostCalculationType
from app.models.organization_model import OrganizationModel
from app.models.user_model_assignment import UserModelAssignment
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.api.deps import get_db, get_current_admin
from app.models.admin import Admin
from datetime import datetime, timedelta
import enum
import logging

router = APIRouter()

# ------------------- Pydantic Schemas -------------------

# NEW: Pydantic enum for CostCalculationType for request validation
class PydanticCostCalculationType(str, enum.Enum):
    tokens = "tokens"
    request = "request"

class AIModelCreate(BaseModel):
    name: str
    provider: str
    model_identifier: str
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    max_tokens: int = 4096
    context_window: int = 8192
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    status: AIModelStatus
    substitute_model_id: Optional[int] = None
    # NEW FIELDS for Create Schema
    request_cost: float = 0.0
    cost_calculation_type: PydanticCostCalculationType = PydanticCostCalculationType.tokens

class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_identifier: Optional[str] = None
    input_cost_per_1k_tokens: Optional[float] = None
    output_cost_per_1k_tokens: Optional[float] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None
    status: Optional[AIModelStatus] = None
    substitute_model_id: Optional[int] = None
    # NEW FIELDS for Update Schema
    request_cost: Optional[float] = None
    cost_calculation_type: Optional[PydanticCostCalculationType] = None


class AIModelOut(BaseModel):
    id: int
    name: str
    provider: str
    model_identifier: str
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None
    status: AIModelStatus
    substitute_model_id: Optional[int] = None
    created_at: Optional[datetime] = None
    # NEW FIELDS for Output Schema
    request_cost: float
    cost_calculation_type: PydanticCostCalculationType


    class Config:
        from_attributes = True # This is crucial for SQLAlchemy models

# ------------------- CRUD Endpoints -------------------

@router.get("/models", response_model=List[AIModelOut])
async def get_all_models(db: AsyncSession = Depends(get_db)):
    """
    CHANGED: This endpoint now performs a LEFT JOIN to fetch the substitute_model_id
    for each model, if one exists. The new cost fields are automatically selected.
    """
    stmt = (
        select(AIModel, ModelSubstitution.substitute_model_id)
        .outerjoin(ModelSubstitution, AIModel.id == ModelSubstitution.original_model_id)
        .order_by(AIModel.created_at.desc())
    )
    result = await db.execute(stmt)
    
    # Process results to combine model and its substitution ID
    models_out = []
    for model, sub_id in result.all():
        model_data = model.__dict__
        model_data['substitute_model_id'] = sub_id
        # Ensure capabilities is handled as a dict if it comes as None/str from DB
        if 'capabilities' in model_data and model_data['capabilities'] is None:
            model_data['capabilities'] = {}
        models_out.append(AIModelOut.model_validate(model_data)) # Use model_validate for Pydantic v2
            
    return models_out


@router.get("/models/{model_id}", response_model=AIModelOut)
async def get_model_by_id(model_id: int = Path(...), db: AsyncSession = Depends(get_db)):
    """
    CHANGED: This endpoint also performs a LEFT JOIN to ensure the substitute_model_id
    is included in the response for a single model. The new cost fields are automatically selected.
    """
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
    model_data = model.__dict__
    model_data['substitute_model_id'] = sub_id
    # Ensure capabilities is handled as a dict if it comes as None/str from DB
    if 'capabilities' in model_data and model_data['capabilities'] is None:
        model_data['capabilities'] = {}
    
    return AIModelOut.model_validate(model_data) # Use model_validate for Pydantic v2


@router.post("/models", response_model=AIModelOut)
async def create_model(payload: AIModelCreate, db: AsyncSession = Depends(get_db)):
    """
    CHANGED: The response now correctly includes the substitute_model_id if provided,
    and also handles the new cost_calculation_type and request_cost fields.
    """
    # Exclude substitute_model_id when creating the AIModel object itself
    model_data = payload.model_dump(exclude={"substitute_model_id"}) # Use model_dump for Pydantic v2
    new_model = AIModel(**model_data)
    
    db.add(new_model)
    await db.flush() # Use flush to get the new_model.id before committing fully

    # Create substitution if status is under_updation
    if payload.status == AIModelStatus.under_updation:
        if not payload.substitute_model_id:
            raise HTTPException(status_code=400, detail="substitute_model_id is required when status is 'under_updation'")
        
        substitution = ModelSubstitution(
            original_model_id=new_model.id,
            substitute_model_id=payload.substitute_model_id,
        )
        db.add(substitution)

    await db.commit()
    await db.refresh(new_model)

    # Construct the response object
    response_data = AIModelOut.model_validate(new_model).model_dump() # Use model_validate and model_dump for Pydantic v2
    response_data['substitute_model_id'] = payload.substitute_model_id if payload.status == AIModelStatus.under_updation else None
    
    return AIModelOut(**response_data)


@router.put("/models/{model_id}", response_model=AIModelOut)
async def update_model(
    model_id: int,
    payload: AIModelUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AIModel).where(AIModel.id == model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Use model_dump for Pydantic v2, exclude_unset=True only applies to model_dump
    update_data = payload.model_dump(exclude_unset=True, exclude={"substitute_model_id"})
    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)

    # Handle substitution logic
    if payload.status == AIModelStatus.under_updation:
        if payload.substitute_model_id:
            # Check if substitution already exists
            existing_stmt = select(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
            sub_result = await db.execute(existing_stmt)
            existing = sub_result.scalar_one_or_none()

            if existing:
                existing.substitute_model_id = payload.substitute_model_id
                existing.valid_to = None  # Extend validity
            else:
                db.add(ModelSubstitution(
                    original_model_id=model.id,
                    substitute_model_id=payload.substitute_model_id,
                ))
            await db.commit()
        else:
            # No substitute provided, clear existing substitution
            await db.execute(
                delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
            )
            await db.commit()
    elif model.status != AIModelStatus.under_updation: # If status changes from under_updation to active/inactive, clear substitution
        await db.execute(
            delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model.id)
        )
        await db.commit()
        
    # Construct the response object including substitute_model_id if it exists after update
    # Fetch the substitute_model_id again if it was just handled or if the status changed.
    # This ensures the most up-to-date state is returned.
    stmt_after_update = (
        select(AIModel, ModelSubstitution.substitute_model_id)
        .outerjoin(ModelSubstitution, AIModel.id == ModelSubstitution.original_model_id)
        .where(AIModel.id == model_id)
    )
    result_after_update = await db.execute(stmt_after_update)
    model_after_update, sub_id_after_update = result_after_update.one_or_none()

    if not model_after_update:
        raise HTTPException(status_code=404, detail="Model not found after update refresh")

    model_data_after_update = model_after_update.__dict__
    model_data_after_update['substitute_model_id'] = sub_id_after_update
    if 'capabilities' in model_data_after_update and model_data_after_update['capabilities'] is None:
        model_data_after_update['capabilities'] = {}

    return AIModelOut.model_validate(model_data_after_update)


@router.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(AIModel).where(AIModel.id == model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # The database cascade should handle deletion, but explicit is safer
    await db.execute(delete(ModelSubstitution).where(ModelSubstitution.original_model_id == model_id))
    await db.delete(model)
    await db.commit()
    return None # Return no content on successful deletion