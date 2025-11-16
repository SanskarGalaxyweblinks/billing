from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime, timedelta

from app.api.deps import get_db
from app.models.user import User
from app.models.user_api_key import UserAPIKey
from app.security import create_access_token, get_password_hash, verify_password
from app.utils.email import send_verification_email, generate_otp, send_password_reset_email

router = APIRouter()

# --- Pydantic Models ---
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class APIKeyCreate(BaseModel):
    key_name: str
    expires_days: int = None  # Optional expiration in days
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    rate_limit_per_day: int = 10000

class APIKeyResponse(BaseModel):
    id: int
    key_name: str
    api_key_prefix: str
    is_active: bool
    created_at: datetime
    expires_at: datetime = None
    last_used_at: datetime = None

# --- Helper Function ---
async def resend_otp(user: User, db: AsyncSession, background_tasks: BackgroundTasks):
    """Generates a new OTP, updates the user, and sends the email."""
    otp = generate_otp()
    user.email_verification_token = get_password_hash(otp)
    user.email_verification_token_expires = datetime.utcnow() + timedelta(minutes=10)
    await db.commit()
    background_tasks.add_task(send_verification_email, user.email, otp)

# --- Registration & Authentication Routes ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.email_verified:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            # User exists but is not verified, resend OTP and ask them to verify
            await resend_otp(existing_user, db, background_tasks)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Email already registered but not verified. A new verification code has been sent."
            )

    hashed_password = get_password_hash(user_in.password)
    otp = generate_otp()
    
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        organization_name=user_in.organization_name,
        auth_id=str(uuid.uuid4()),
        email_verified=False,
        email_verification_token=get_password_hash(otp),
        email_verification_token_expires=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(new_user)
    await db.commit()
    
    # Create default API key for new user
    await _create_default_api_key(new_user, db)
    
    background_tasks.add_task(send_verification_email, user_in.email, otp)

    return {"message": "Registration successful. Please check your email for a verification code."}

@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    if user.email_verification_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")
    if not verify_password(payload.token, user.email_verification_token):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_token_expires = None
    await db.commit()

    return {"message": "Email verified successfully. You can now log in."}
    
@router.post("/resend-verification-email")
async def resend_verification_email(
    payload: ResendVerificationRequest, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
        
    await resend_otp(user, db, background_tasks)
    
    return {"message": "A new verification email has been sent."}

@router.post("/login/token")
async def login_user_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    if not user.email_verified:
        # Resend OTP in the background and tell the user to verify
        await resend_otp(user, db, background_tasks)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. We've sent you a new verification code.",
        )

    access_token = create_access_token(data={"sub": user.email, "role": "user"})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Generate a secure, single-use token for password reset
        reset_token = create_access_token(
            data={"sub": user.email, "scope": "password_reset"}, 
            expires_delta=timedelta(minutes=15)
        )
        user.password_reset_token = get_password_hash(reset_token)
        user.password_reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
        await db.commit()

        reset_link = f"http://localhost:8080/reset-password?token={reset_token}"
        background_tasks.add_task(send_password_reset_email, user.email, reset_link)

    return {"message": "If an account with that email exists, we have sent password reset instructions."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        users = (await db.execute(select(User).where(User.password_reset_token.isnot(None)))).scalars().all()
        
        user_to_update = None
        for user in users:
            if verify_password(payload.token, user.password_reset_token):
                user_to_update = user
                break

        if not user_to_update:
            raise HTTPException(status_code=400, detail="Invalid token")

        if user_to_update.password_reset_token_expires < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token has expired")
            
        user_to_update.hashed_password = get_password_hash(payload.new_password)
        user_to_update.password_reset_token = None
        user_to_update.password_reset_token_expires = None
        await db.commit()

        return {"message": "Password has been reset successfully."}
        
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# --- API Key Management Routes ---
@router.post("/api-keys", response_model=dict)
async def create_api_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key for the current user"""
    # Generate API key
    full_key, key_hash, prefix = UserAPIKey.generate_api_key()
    
    # Set expiration if provided
    expires_at = None
    if payload.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_days)
    
    # Create API key record
    api_key = UserAPIKey(
        user_id=current_user.id,
        key_name=payload.key_name,
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        expires_at=expires_at,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        rate_limit_per_hour=payload.rate_limit_per_hour,
        rate_limit_per_day=payload.rate_limit_per_day
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return {
        "api_key": full_key,  # Only returned once!
        "key_info": {
            "id": api_key.id,
            "key_name": api_key.key_name,
            "api_key_prefix": api_key.api_key_prefix,
            "expires_at": api_key.expires_at,
            "created_at": api_key.created_at
        },
        "warning": "Save this API key securely. It will not be shown again."
    }

@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys for the current user"""
    stmt = select(UserAPIKey).where(UserAPIKey.user_id == current_user.id).order_by(UserAPIKey.created_at.desc())
    result = await db.execute(stmt)
    api_keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=key.id,
            key_name=key.key_name,
            api_key_prefix=key.api_key_prefix,
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at
        )
        for key in api_keys
    ]

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key"""
    stmt = select(UserAPIKey).where(
        UserAPIKey.id == key_id,
        UserAPIKey.user_id == current_user.id
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    await db.delete(api_key)
    await db.commit()
    
    return {"message": "API key deleted successfully"}

@router.put("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle API key active status"""
    stmt = select(UserAPIKey).where(
        UserAPIKey.id == key_id,
        UserAPIKey.user_id == current_user.id
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = not api_key.is_active
    await db.commit()
    
    status_text = "activated" if api_key.is_active else "deactivated"
    return {"message": f"API key {status_text} successfully"}

# --- Helper Functions ---
async def _create_default_api_key(user: User, db: AsyncSession):
    """Create a default API key for new users"""
    full_key, key_hash, prefix = UserAPIKey.generate_api_key()
    
    default_api_key = UserAPIKey(
        user_id=user.id,
        key_name="Default API Key",
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000,
        rate_limit_per_day=10000
    )
    
    db.add(default_api_key)
    await db.commit()