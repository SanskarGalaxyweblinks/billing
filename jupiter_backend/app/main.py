from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.routes import router as api_router
from app.api.admin_routes import router as admin_router
from app.api.routes.stripe_webhooks import router as webhook_router

def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(admin_router)
    app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])

    return app