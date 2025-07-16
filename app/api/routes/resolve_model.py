from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db
from app.models.organization import Organization
from app.models.ai_model import AIModel
from app.models.model_substitutions import ModelSubstitution

router = APIRouter()

class ResolveModelInput(BaseModel):
    organization_id: int
    model_name: str

@router.post("/")
async def resolve_model(data: ResolveModelInput, db: AsyncSession = Depends(get_db)):
    # 1. Check organization
    org_stmt = select(Organization).where(Organization.id == data.organization_id)
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.status != "active":
        raise HTTPException(status_code=403, detail="Organization is suspended")

    # 2. Find requested model
    model_stmt = select(AIModel).where(AIModel.model_identifier == data.model_name)
    model_result = await db.execute(model_stmt)
    model = model_result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="AI model not found")

    # 3. If model is under_updation, look for substitution
    if model.status == "under_updation":
        sub_stmt = select(ModelSubstitution).where(
            and_(
                ModelSubstitution.original_model_id == model.id,
                or_(
                    ModelSubstitution.valid_to.is_(None),
                    ModelSubstitution.valid_to > datetime.utcnow()
                )
            )
        )
        sub_result = await db.execute(sub_stmt)
        substitution = sub_result.scalar_one_or_none()

        if not substitution:
            raise HTTPException(status_code=503, detail="Model is under update and no substitute available")

        # Get the substitute model
        sub_model_stmt = select(AIModel).where(AIModel.id == substitution.substitute_model_id)
        sub_model_result = await db.execute(sub_model_stmt)
        substitute_model = sub_model_result.scalar_one_or_none()

        if not substitute_model or substitute_model.status != "active":
            raise HTTPException(status_code=503, detail="Substitute model is unavailable or inactive")

        return {
            "model_name": substitute_model.name,
            "endpoint": substitute_model.endpoint
        }

    # 4. Model is active — return its endpoint
    if model.status != "active":
        raise HTTPException(status_code=403, detail="Model is not currently available")

    return {
        "model_name": model.name,
        "endpoint": model.endpoint
    }
