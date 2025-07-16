from fastapi import APIRouter
from .dashboard import router as dashboard_router
from .usage import router as usage_router
from .limits import router as limits_router
from .api_log import router as api_log_router
from .users import router as users_router
from .resolve_model import router as resolve_model
from .billing import router as billing_router
from .checkout_session import router as checkout_session_router

router = APIRouter()

router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(usage_router, prefix="/usage", tags=["Usage"])
router.include_router(limits_router, prefix="/limits", tags=["Limits"])
router.include_router(api_log_router, prefix="/api_log", tags=["ApiLog"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(resolve_model, prefix="/resolve-model", tags=["Resolve_Model"])
router.include_router(billing_router, prefix="/billing", tags=["Billing"])
router.include_router(checkout_session_router, prefix="/stripe", tags=["Checkout Session"])