from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel
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

@router.post("/")
async def log_api_usage(data: UsageLogInput, db: AsyncSession = Depends(get_db)):
    # Fetch model costs
    stmt = select(AIModel).where(AIModel.id == data.model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Calculate tokens and cost
    total_tokens = data.input_tokens + data.output_tokens

    input_cost = (Decimal(data.input_tokens) / 1000) * model.input_cost_per_1k_tokens
    output_cost = (Decimal(data.output_tokens) / 1000) * model.output_cost_per_1k_tokens
    total_cost = input_cost + output_cost

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

    return {"message": "Usage logged successfully", "total_tokens": total_tokens, "total_cost": float(total_cost)}
