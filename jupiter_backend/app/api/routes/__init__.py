from fastapi import APIRouter, Depends
from .dashboard import router as dashboard_router
from .usage import router as usage_router
from .limits import router as limits_router
from .api_log import router as api_log_router
from .users import router as users_router
from .resolve_model import router as resolve_model
from .billing import router as billing_router
from .checkout_session import router as checkout_session_router
from .auth import router as auth_router
from .billing_receiver import router as billing_receiver_router  # NEW IMPORT
from app.api.deps import get_current_user

router = APIRouter()

# Public auth routes
router.include_router(auth_router, tags=["Authentication"])

# Public billing receiver routes (no user session needed for external models)
router.include_router(billing_receiver_router, prefix="/api", tags=["Billing Receiver"])

# Protected user routes are now protected at the router level
protected_user_api = APIRouter(dependencies=[Depends(get_current_user)])
protected_user_api.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
protected_user_api.include_router(usage_router, prefix="/usage", tags=["Usage"])
protected_user_api.include_router(limits_router, prefix="/limits", tags=["Limits"])
protected_user_api.include_router(users_router, prefix="/users", tags=["Users"])
protected_user_api.include_router(billing_router, prefix="/billing", tags=["Billing"])
protected_user_api.include_router(checkout_session_router, prefix="/stripe", tags=["Checkout Session"])

router.include_router(protected_user_api)

# Public service routes (no user session needed)
router.include_router(api_log_router, prefix="/api_log", tags=["ApiLog"])
router.include_router(resolve_model, prefix="/resolve-model", tags=["Resolve Model"])