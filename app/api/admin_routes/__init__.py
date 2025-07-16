from fastapi import APIRouter
from .users import router as user_router
from .ai_model import router as ai_model_router
from .organization import router as organization_router
from .usage_summary import router as usage_summary
from .dashboard import router as dashboard
from .subscription_tiers import router as tier_router
from .billing_overview import router as billing_overview

router = APIRouter()

router.include_router(user_router, prefix="/admin", tags=["Admin_users"])
router.include_router(ai_model_router, prefix="/admin", tags=["Admin_ai_model"])
router.include_router(organization_router, prefix="/admin", tags=["Admin_organization"])
router.include_router(usage_summary, prefix="/admin", tags=["Usage_summary"])
router.include_router(dashboard, prefix="/admin", tags=["Dashboard"])
router.include_router(tier_router, prefix="/admin", tags=["Admin_subscription_tiers"])
router.include_router(billing_overview, prefix="/admin", tags=["Billing_overview"])

