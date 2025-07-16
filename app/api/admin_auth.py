import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# --- Configuration ---
# Yeh secret key aapke admin tokens ko sign karne ke liye hai. Isko .env file mein rakhein.
# Yeh SUPABASE_JWT_SECRET se alag honi chahiye.
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "your_strong_admin_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # Token 60 minute tak valid rahega

# Password hashing ke liye
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer ek dependency hai jo 'Authorization' header se token nikalne mein madad karti hai.
# tokenUrl woh path hai jahan se admin login karke token lega.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/token")

# --- Pydantic Models ---
class TokenData(BaseModel):
    """Token ke andar store hone wale data ka structure."""
    username: Optional[str] = None

class AdminUser(BaseModel):
    """Admin user ka structure."""
    username: str
    full_name: Optional[str] = None
    role: str

# --- Dummy Database ---
# Asli application mein, aap yeh data database se fetch karenge.
# Abhi ke liye, hum ek dummy admin user bana rahe hain.
# Password ko hash karke store karein. Plain text mein kabhi na rakhein.
# To generate hash: pwd_context.hash("your_password")
dummy_admin_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "hashed_password": "$2b$12$EixZaYVK13nJ3c2/x.iS9.DP24tL12Fs2s.YAt2.2T9ihd43T3yv2", # "admin_password" ka hash
        "role": "superadmin"
    }
}

# --- Utility Functions ---

def verify_password(plain_password, hashed_password):
    """Plain password ko hashed password se compare karta hai."""
    return pwd_context.verify(plain_password, hashed_password)

def get_admin(username: str):
    """Dummy DB se admin user fetch karta hai."""
    if username in dummy_admin_db:
        user_dict = dummy_admin_db[username]
        return AdminUser(**user_dict)
    return None

def create_access_token(data: dict):
    """Admin ke liye naya JWT access token banata hai."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependency to Protect Routes ---

async def get_current_admin(token: str = Depends(oauth2_scheme)) -> AdminUser:
    """
    Yeh function hamara 'Guard' hai.
    1. Token ko decode karta hai.
    2. User ko validate karta hai.
    3. Agar sab sahi hai to user data return karta hai, warna error deta hai.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, ADMIN_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_admin(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user