from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime

from app.database import async_session
from app.security import ALGORITHM, SECRET_KEY
from app.models.user import User
from app.models.admin import Admin
from app.models.user_api_key import UserAPIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
security = HTTPBearer()

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

# New function for API key authentication
async def get_user_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate user using API key instead of JWT token.
    This is used for API requests where users provide their API key.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    # Validate API key format
    if not api_key.startswith("jb_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )
    
    # Hash the provided API key to compare with stored hash
    api_key_hash = UserAPIKey.hash_api_key(api_key)
    
    # Find the API key in database
    stmt = select(UserAPIKey).where(
        UserAPIKey.api_key_hash == api_key_hash,
        UserAPIKey.is_active == True
    )
    result = await db.execute(stmt)
    user_api_key = result.scalar_one_or_none()
    
    if not user_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Check if API key has expired
    if user_api_key.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )
    
    # Get the user associated with this API key
    stmt = select(User).where(User.id == user_api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    # Update last used timestamp
    user_api_key.update_last_used()
    await db.commit()
    
    return user

async def get_user_from_api_key_with_ip_check(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Enhanced API key authentication with IP address validation.
    Use this for stricter API access control.
    """
    # First get the user using standard API key validation
    user = await get_user_from_api_key(credentials, db)
    
    # Get the API key record for additional validation
    api_key = credentials.credentials
    api_key_hash = UserAPIKey.hash_api_key(api_key)
    
    stmt = select(UserAPIKey).where(UserAPIKey.api_key_hash == api_key_hash)
    result = await db.execute(stmt)
    user_api_key = result.scalar_one_or_none()
    
    # Get client IP address
    client_ip = request.client.host
    if request.headers.get("X-Forwarded-For"):
        client_ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        client_ip = request.headers.get("X-Real-IP")
    
    # Check IP restrictions if any are set
    if not user_api_key.is_ip_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API access not allowed from IP: {client_ip}",
        )
    
    return user

# Flexible authentication function that supports both JWT and API key
async def get_current_user_flexible(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Flexible authentication that accepts either JWT token or API key.
    Useful for endpoints that need to support both authentication methods.
    """
    # Try JWT token first
    if token:
        try:
            return await get_current_user(token, db)
        except HTTPException:
            pass  # Fall through to API key authentication
    
    # Try API key authentication
    if credentials:
        try:
            return await get_user_from_api_key(credentials, db)
        except HTTPException:
            pass
    
    # If both methods fail, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid JWT token or API key required",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Rate limiting dependency (can be used with API keys)
async def check_api_rate_limits(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserAPIKey:
    """
    Check rate limits for API key usage.
    Returns the API key record for further processing.
    """
    # This is a simplified implementation
    # In production, you'd want to use Redis or similar for rate limiting
    
    api_key = credentials.credentials
    api_key_hash = UserAPIKey.hash_api_key(api_key)
    
    stmt = select(UserAPIKey).where(UserAPIKey.api_key_hash == api_key_hash)
    result = await db.execute(stmt)
    user_api_key = result.scalar_one_or_none()
    
    if not user_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Here you would implement actual rate limiting logic
    # For now, we just return the API key record
    return user_api_key