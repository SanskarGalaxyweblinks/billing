from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from app.api.deps import get_db
from app.models.api_usage_log import APIUsageLog
from app.models.ai_model import AIModel, CostCalculationType
from app.models.discount_rule import DiscountRule
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

router = APIRouter()

class UsageLogInput(BaseModel):
    user_id: int
    model_id: int
    status: str
    response_time_ms: int
    input_tokens: int
    output_tokens: int

@router.post("/")
async def log_api_usage(data: UsageLogInput, db: AsyncSession = Depends(get_db)):
    stmt = select(AIModel).where(AIModel.id == data.model_id)
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    original_cost = Decimal(0)
    total_tokens = data.input_tokens + data.output_tokens

    if data.status == 'success':
        if model.cost_calculation_type == CostCalculationType.tokens:
            input_cost = (Decimal(data.input_tokens) / 1000) * model.input_cost_per_1k_tokens
            output_cost = (Decimal(data.output_tokens) / 1000) * model.output_cost_per_1k_tokens
            original_cost = input_cost + output_cost
        elif model.cost_calculation_type == CostCalculationType.request:
            original_cost = model.request_cost

    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    request_count_stmt = select(func.count()).select_from(APIUsageLog).where(
        APIUsageLog.user_id == data.user_id,
        APIUsageLog.created_at >= start_of_month
    )
    request_count = (await db.execute(request_count_stmt)).scalar() or 0

    discount_stmt = select(DiscountRule).where(
        and_(
            DiscountRule.is_active == True,
            DiscountRule.user_id == data.user_id,
            DiscountRule.model_id == data.model_id,
            DiscountRule.min_requests <= request_count,
            (DiscountRule.max_requests == None) | (DiscountRule.max_requests >= request_count)
        )
    ).order_by(DiscountRule.priority)
    
    discount_result = await db.execute(discount_stmt)
    applicable_discount = discount_result.scalars().first()
    
    applied_discount_percentage = Decimal(0)
    if applicable_discount:
        applied_discount_percentage = Decimal(applicable_discount.discount_percentage)

    total_cost = original_cost * (1 - (applied_discount_percentage / 100))

    log_entry = APIUsageLog(
        user_id=data.user_id,
        model_id=data.model_id,
        total_tokens=total_tokens,
        original_cost=original_cost,
        applied_discount=applied_discount_percentage,
        total_cost=total_cost,
        status=data.status,
        response_time_ms=data.response_time_ms
    )

    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    return {"message": "Usage logged successfully", "log_id": log_entry.id, "total_cost": float(total_cost)}