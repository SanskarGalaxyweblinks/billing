from fastapi import APIRouter, Depends
from .users import router as user_router
from .ai_model import router as ai_model_router
from .model_assignments import router as model_assignments_router  # NEW: Import model assignments router
from .usage_summary import router as usage_summary
from .dashboard import router as dashboard
from .subscription_tiers import router as tier_router
from .billing_overview import router as billing_overview
from .auth import router as auth_router
from .discounts import router as discount_router
from app.api.deps import get_current_admin

router = APIRouter()

# Public admin login
router.include_router(auth_router, prefix="/admin", tags=["Admin Authentication"])

# Protected admin router
protected_admin_api = APIRouter(dependencies=[Depends(get_current_admin)])
protected_admin_api.include_router(user_router, tags=["Admin Users"])
protected_admin_api.include_router(ai_model_router, tags=["Admin AI Models"])
protected_admin_api.include_router(model_assignments_router, tags=["Admin Model Assignments"])  # NEW: Include model assignments router
protected_admin_api.include_router(usage_summary, tags=["Admin Usage Summary"])
protected_admin_api.include_router(dashboard, tags=["Admin Dashboard"])
protected_admin_api.include_router(tier_router, tags=["Admin Subscription Tiers"])
protected_admin_api.include_router(billing_overview, tags=["Admin Billing Overview"])

# CORRECTED LINE: Removed the `prefix` to avoid creating `/admin/discounts/discounts`
protected_admin_api.include_router(discount_router, tags=["Admin Discounts"])

router.include_router(protected_admin_api, prefix="/admin")