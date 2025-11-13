from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional

from app.database import async_session
from app.security import ALGORITHM, SECRET_KEY
from app.models.user import User
from app.models.admin import Admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None

async def get_db():
    async with async_session() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role != "user":
            raise credentials_exception
        token_data = TokenData(sub=email, role=role)
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.email == token_data.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials for admin",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or "admin" not in role: # Allows for 'admin', 'superadmin'
            raise credentials_exception
        token_data = TokenData(sub=username, role=role)
    except JWTError:
        raise credentials_exception

    stmt = select(Admin).where(Admin.username == token_data.sub)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()
    
    if admin is None:
        raise credentials_exception
    return admin