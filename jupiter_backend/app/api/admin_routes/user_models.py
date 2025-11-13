# jupiter_backend/app/api/admin_routes/user_models.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from pydantic import BaseModel

from app.models.user import User
from app.models.ai_model import AIModel
from app.models.user_model_access import UserModelAccess
from app.api.deps import get_db

router = APIRouter()

class UserModelAssignment(BaseModel):
    user_id: int
    model_ids: List[int]

class UserModelResponse(BaseModel):
    user_id: int
    assigned_models: List[dict]

@router.get("/users/{user_id}/models", response_model=UserModelResponse)
async def get_user_assigned_models(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all models assigned to a specific user"""
    stmt = (
        select(AIModel, UserModelAccess)
        .join(UserModelAccess, AIModel.id == UserModelAccess.model_id)
        .where(UserModelAccess.user_id == user_id)
        .where(UserModelAccess.is_active == True)
    )
    result = await db.execute(stmt)
    models_data = result.all()
    
    assigned_models = [
        {
            "id": model.id,
            "name": model.name,
            "provider": model.provider,
            "status": model.status,
            "granted_at": access.granted_at.isoformat()
        }
        for model, access in models_data
    ]
    
    return UserModelResponse(user_id=user_id, assigned_models=assigned_models)

@router.post("/users/{user_id}/models")
async def assign_models_to_user(
    user_id: int, 
    assignment: UserModelAssignment, 
    db: AsyncSession = Depends(get_db)
):
    """Assign multiple models to a user (replaces existing assignments)"""
    
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove existing assignments
    delete_stmt = delete(UserModelAccess).where(UserModelAccess.user_id == user_id)
    await db.execute(delete_stmt)
    
    # Add new assignments
    for model_id in assignment.model_ids:
        # Verify model exists
        model_stmt = select(AIModel).where(AIModel.id == model_id)
        model = (await db.execute(model_stmt)).scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        access = UserModelAccess(user_id=user_id, model_id=model_id)
        db.add(access)
    
    await db.commit()
    return {"message": f"Successfully assigned {len(assignment.model_ids)} models to user {user_id}"}

@router.delete("/users/{user_id}/models/{model_id}")
async def remove_model_from_user(user_id: int, model_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a specific model assignment from user"""
    stmt = select(UserModelAccess).where(
        UserModelAccess.user_id == user_id,
        UserModelAccess.model_id == model_id
    )
    access = (await db.execute(stmt)).scalar_one_or_none()
    
    if not access:
        raise HTTPException(status_code=404, detail="Model assignment not found")
    
    await db.delete(access)
    await db.commit()
    return {"message": "Model assignment removed successfully"}