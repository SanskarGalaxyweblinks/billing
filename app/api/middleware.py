from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from dotenv import load_dotenv
import os

load_dotenv()

EXEMPT_PATHS = {"/docs", "/openapi.json", "/favicon.ico", "/api_log", "/api_log/", "/resolve-model/", "/stripe/stripe-webhook", "/stripe/stripe-webhook/"}

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

async def extract_user_info(request: Request, call_next):
    path = request.url.path
    if (
        request.method == "OPTIONS" or
        path in EXEMPT_PATHS or
        path.startswith("/admin")
    ):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing Authorization header"})

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # ✅ Fix: ignore audience check
        )
        request.state.user_info = payload
    except JWTError as e:
        print("JWT Decode Error:", e)
        return JSONResponse(status_code=401, content={"error": "Invalid token"})

    return await call_next(request)
