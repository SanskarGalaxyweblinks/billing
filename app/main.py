from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.middleware import extract_user_info
from app.api.routes import router as api_router 
from app.api.admin_routes import router as admin_router 

def create_app() -> FastAPI:
    app = FastAPI()

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(extract_user_info)

    # Include routes
    app.include_router(api_router)
    app.include_router(admin_router)


    return app
