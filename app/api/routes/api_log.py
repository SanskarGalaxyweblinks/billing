from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel, CostCalculationType # Import CostCalculationType
from pydantic import BaseModel
from decimal import Decimal

router = APIRouter()

class UsageLogInput(BaseModel):
    organization_id: int
    model_id: int
    status: str  # e.g., 'success' or 'error'
    response_time_ms: int
    input_tokens: int
    output_tokens: int
    # Note: input_tokens and output_tokens are kept for general logging/analytics
    # even if cost is per request, as they might still be relevant for other metrics.

@router.post("/")
async def log_api_usage(data: UsageLogInput, db: AsyncSession = Depends(get_db)):
    # Fetch model details, including the new cost fields and cost_calculation_type
    stmt = select(AIModel).where(AIModel.id == data.model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    total_cost = Decimal(0)
    total_tokens = data.input_tokens + data.output_tokens # Total tokens are always logged

    # Only calculate cost if status is 'success'
    if data.status == 'success':
        # Determine cost calculation based on model's cost_calculation_type
        if model.cost_calculation_type == CostCalculationType.tokens:
            # Calculate cost based on tokens
            input_cost = (Decimal(data.input_tokens) / 1000) * model.input_cost_per_1k_tokens
            output_cost = (Decimal(data.output_tokens) / 1000) * model.output_cost_per_1k_tokens
            total_cost = input_cost + output_cost
        elif model.cost_calculation_type == CostCalculationType.request:
            # Use fixed request cost
            total_cost = model.request_cost
        else:
            # Fallback or error handling for unknown cost calculation type
            # This case should ideally not happen if enum is strictly enforced
            raise HTTPException(status_code=500, detail="Unknown cost calculation type for model")

    # Insert usage log
    log_entry = APIUsageLog(
        organization_id=data.organization_id,
        model_id=data.model_id,
        total_tokens=total_tokens,
        total_cost=total_cost,
        status=data.status,
        response_time_ms=data.response_time_ms
    )

    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry) # Refresh to get any default values or generated IDs

    return {"message": "Usage logged successfully", "log_id": log_entry.id, "total_tokens": total_tokens, "total_cost": float(total_cost)}