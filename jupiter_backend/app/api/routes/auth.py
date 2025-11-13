from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime, timedelta

from app.api.deps import get_db
from app.models.user import User
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

# --- Helper Function ---
async def resend_otp(user: User, db: AsyncSession, background_tasks: BackgroundTasks):
    """Generates a new OTP, updates the user, and sends the email."""
    otp = generate_otp()
    user.email_verification_token = get_password_hash(otp)
    user.email_verification_token_expires = datetime.utcnow() + timedelta(minutes=10)
    await db.commit()
    background_tasks.add_task(send_verification_email, user.email, otp)

# --- Routes ---
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
    
    background_tasks.add_task(send_verification_email, user_in.email, otp)

    return {"message": "Registration successful. Please check your email for a verification code."}

@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    # Same logic as before, no changes needed here
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
        user.password_reset_token = get_password_hash(reset_token) # Store hashed token
        user.password_reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
        await db.commit()

        reset_link = f"http://localhost:8080/reset-password?token={reset_token}"
        background_tasks.add_task(send_password_reset_email, user.email, reset_link)

    # Always return a success message to prevent email enumeration attacks
    return {"message": "If an account with that email exists, we have sent password reset instructions."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        # We can't query by the raw token, so we must iterate (not ideal for huge user bases)
        # A better approach for scale would be a separate token table. For now, this is okay.
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