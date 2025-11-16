from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.database import init_db
from app.api.routes import router as api_router
from app.api.admin_routes import router as admin_router
from app.api.routes.stripe_webhooks import router as webhook_router
from app.utils.billing_processor import BillingProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for the FastAPI application.
    """
    # Startup events
    logger.info("Starting JupiterBrains Billing Platform...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start background billing processor
    asyncio.create_task(background_billing_processor())
    logger.info("Background billing processor started")
    
    yield
    
    # Shutdown events
    logger.info("Shutting down JupiterBrains Billing Platform...")

def create_app() -> FastAPI:
    app = FastAPI(
        title="JupiterBrains Billing Platform",
        description="Multi-tier B2B SaaS billing platform with AI model usage tracking",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Billing Request Logging Middleware
    @app.middleware("http")
    async def log_billing_requests(request: Request, call_next):
        """
        Log billing-related requests for monitoring and debugging.
        """
        start_time = asyncio.get_event_loop().time()
        
        # Log billing requests
        if request.url.path.startswith("/api/billing"):
            client_ip = request.client.host
            if request.headers.get("X-Forwarded-For"):
                client_ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
            
            logger.info(f"Billing request: {request.method} {request.url.path} from {client_ip}")
        
        response = await call_next(request)
        
        # Log response time for billing requests
        if request.url.path.startswith("/api/billing"):
            process_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"Billing response: {response.status_code} in {process_time:.3f}s")
        
        return response

    # Include routers
    app.include_router(api_router)
    app.include_router(admin_router)
    app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Application health check"""
        return {
            "status": "healthy",
            "service": "jupiterbrains-billing",
            "version": "1.0.0"
        }

    # Billing system status endpoint
    @app.get("/billing-status")
    async def billing_system_status():
        """Check billing system status"""
        try:
            # Get some basic stats about unprocessed entries
            unprocessed = await BillingProcessor.get_unprocessed_entries(limit=1)
            
            return {
                "billing_system": "operational",
                "unprocessed_entries_exist": len(unprocessed) > 0,
                "background_processor": "running"
            }
        except Exception as e:
            logger.error(f"Error checking billing status: {str(e)}")
            return {
                "billing_system": "error",
                "error": str(e)
            }

    return app

async def background_billing_processor():
    """
    Background task that periodically processes unprocessed billing entries.
    This ensures that any billing data that failed to process gets retried.
    """
    while True:
        try:
            # Process unprocessed entries every 30 seconds
            await asyncio.sleep(30)
            
            # Get and process unprocessed entries
            unprocessed_entries = await BillingProcessor.get_unprocessed_entries(limit=50)
            
            if unprocessed_entries:
                logger.info(f"Processing {len(unprocessed_entries)} unprocessed billing entries")
                
                for entry in unprocessed_entries:
                    try:
                        await BillingProcessor.process_billing_entry(entry.id)
                    except Exception as e:
                        logger.error(f"Failed to process billing entry {entry.id}: {str(e)}")
            
            # Every 5 minutes, retry failed entries
            if asyncio.get_event_loop().time() % 300 < 30:  # Rough 5-minute interval
                logger.info("Retrying failed billing entries...")
                retry_results = await BillingProcessor.reprocess_failed_entries(max_retries=3)
                if retry_results["total_found"] > 0:
                    logger.info(f"Retry results: {retry_results}")
                
        except Exception as e:
            logger.error(f"Error in background billing processor: {str(e)}")
            # Sleep a bit longer if there's an error to avoid rapid retries
            await asyncio.sleep(60)

# Create the app instance
app = create_app()

# Optional: Add startup event for immediate processing
@app.on_event("startup")
async def startup_billing_processing():
    """
    Process any existing unprocessed billing entries on startup.
    """
    try:
        logger.info("Processing existing unprocessed billing entries...")
        unprocessed = await BillingProcessor.get_unprocessed_entries(limit=100)
        
        if unprocessed:
            logger.info(f"Found {len(unprocessed)} unprocessed entries, processing...")
            for entry in unprocessed[:10]:  # Process first 10 on startup
                try:
                    await BillingProcessor.process_billing_entry(entry.id)
                except Exception as e:
                    logger.error(f"Startup processing failed for entry {entry.id}: {str(e)}")
        else:
            logger.info("No unprocessed billing entries found")
            
    except Exception as e:
        logger.error(f"Error during startup billing processing: {str(e)}")