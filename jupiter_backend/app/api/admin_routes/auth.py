from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.models.admin import Admin
from app.security import create_access_token, verify_password

router = APIRouter()

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    stmt = select(Admin).where(Admin.username == form_data.username)
    result = await db.execute(stmt)
    admin_user = result.scalar_one_or_none()
    
    if not admin_user or not verify_password(form_data.password, admin_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": admin_user.username, "role": admin_user.role})
    return {"access_token": access_token, "token_type": "bearer"}