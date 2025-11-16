from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.api.deps import get_db
from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.utils.billing_processor import process_billing_entry  # We'll create this utility

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class BillingData(BaseModel):
    model_name: str = Field(..., description="Model name in format: company_name_model_type")
    predicted_label: Optional[str] = Field(None, description="Model prediction result")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    timestamp: Optional[str] = Field(None, description="Request timestamp")
    status: str = Field(default="success", description="Request status")
    total_tokens: Optional[int] = Field(None, description="Number of tokens processed")
    user_identifier: Optional[str] = Field(None, description="Optional user identifier")
    additional_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class BillingResponse(BaseModel):
    success: bool
    message: str
    log_id: Optional[int] = None
    processed: bool = False

# --- Main Billing Endpoint ---
@router.post("/billing", response_model=BillingResponse)
async def receive_billing_data(
    billing_data: BillingData,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive billing data from external models.
    This endpoint accepts billing data from models like:
    - cadex_email_classifier
    - markettrends_sentiment_analyzer
    - etc.
    """
    try:
        logger.info(f"Received billing data for model: {billing_data.model_name}")
        
        # Extract client information
        client_ip = request.client.host
        if request.headers.get("X-Forwarded-For"):
            client_ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent", "")
        
        # Create API usage log entry
        log_entry = APIUsageLog.create_from_billing_data(billing_data.dict())
        log_entry.client_ip = client_ip
        log_entry.user_agent = user_agent
        
        # Add to database
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        
        logger.info(f"Created log entry with ID: {log_entry.id} for company: {log_entry.company_name}")
        
        # Process billing entry in background to map user and model
        background_tasks.add_task(
            process_billing_entry_async, 
            log_entry.id, 
            billing_data.model_name
        )
        
        return BillingResponse(
            success=True,
            message="Billing data received successfully",
            log_id=log_entry.id,
            processed=False
        )
        
    except Exception as e:
        logger.error(f"Error processing billing data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process billing data: {str(e)}"
        )

@router.post("/billing/batch", response_model=Dict[str, Any])
async def receive_batch_billing_data(
    billing_batch: list[BillingData],
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive multiple billing entries in a single request.
    Useful for models that batch their billing data.
    """
    try:
        log_ids = []
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        
        for billing_data in billing_batch:
            # Create log entry
            log_entry = APIUsageLog.create_from_billing_data(billing_data.dict())
            log_entry.client_ip = client_ip
            log_entry.user_agent = user_agent
            
            db.add(log_entry)
            log_ids.append(log_entry.id)
        
        await db.commit()
        
        # Process each entry in background
        for i, billing_data in enumerate(billing_batch):
            background_tasks.add_task(
                process_billing_entry_async,
                log_ids[i],
                billing_data.model_name
            )
        
        logger.info(f"Processed batch of {len(billing_batch)} billing entries")
        
        return {
            "success": True,
            "message": f"Processed {len(billing_batch)} billing entries",
            "log_ids": log_ids,
            "processed_count": len(log_ids)
        }
        
    except Exception as e:
        logger.error(f"Error processing batch billing data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process batch billing data: {str(e)}"
        )

@router.get("/billing/status/{log_id}")
async def get_billing_status(
    log_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Check the processing status of a billing entry.
    """
    stmt = select(APIUsageLog).where(APIUsageLog.id == log_id)
    result = await db.execute(stmt)
    log_entry = result.scalar_one_or_none()
    
    if not log_entry:
        raise HTTPException(status_code=404, detail="Billing entry not found")
    
    return {
        "log_id": log_id,
        "status": log_entry.status,
        "processed": log_entry.billing_processed,
        "company_name": log_entry.company_name,
        "user_mapped": log_entry.user_id is not None,
        "model_mapped": log_entry.model_id is not None,
        "total_cost": float(log_entry.total_cost) if log_entry.total_cost else 0,
        "created_at": log_entry.created_at.isoformat(),
        "processed_at": log_entry.processed_at.isoformat() if log_entry.processed_at else None,
        "error_message": log_entry.error_message
    }

@router.get("/billing/company/{company_name}/recent")
async def get_recent_billing_by_company(
    company_name: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent billing entries for a specific company.
    Useful for debugging and monitoring.
    """
    stmt = (
        select(APIUsageLog)
        .where(APIUsageLog.company_name == company_name.lower())
        .order_by(APIUsageLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    log_entries = result.scalars().all()
    
    return {
        "company_name": company_name,
        "recent_entries": [
            {
                "log_id": entry.id,
                "model_name": entry.raw_model_name,
                "status": entry.status,
                "cost": float(entry.total_cost) if entry.total_cost else 0,
                "processed": entry.billing_processed,
                "created_at": entry.created_at.isoformat()
            }
            for entry in log_entries
        ],
        "total_found": len(log_entries)
    }

# --- Background Processing Function ---
async def process_billing_entry_async(log_id: int, model_name: str):
    """
    Background task to process billing entry:
    1. Map company name to user
    2. Map model name to AI model
    3. Calculate final costs
    4. Mark as processed
    """
    from app.database import async_session
    
    async with async_session() as db:
        try:
            # Get the log entry
            stmt = select(APIUsageLog).where(APIUsageLog.id == log_id)
            result = await db.execute(stmt)
            log_entry = result.scalar_one_or_none()
            
            if not log_entry:
                logger.error(f"Log entry {log_id} not found")
                return
            
            # Find user by company name
            if log_entry.company_name:
                user_stmt = select(User).where(
                    User.organization_name.ilike(f"%{log_entry.company_name}%")
                )
                user_result = await db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                
                if user:
                    log_entry.user_id = user.id
                    logger.info(f"Mapped log {log_id} to user {user.id} ({user.organization_name})")
                else:
                    log_entry.error_message = f"No user found for company: {log_entry.company_name}"
                    logger.warning(f"No user found for company: {log_entry.company_name}")
            
            # Find AI model by model name pattern
            model_stmt = select(AIModel).where(
                AIModel.name.ilike(f"%{log_entry.raw_model_name}%")
            )
            model_result = await db.execute(model_stmt)
            ai_model = model_result.scalar_one_or_none()
            
            if ai_model:
                log_entry.model_id = ai_model.id
                # Recalculate cost based on actual model pricing
                model_pricing = {
                    'cost_per_token': ai_model.input_cost_per_1k_tokens / 1000,
                    'cost_per_request': ai_model.request_cost
                }
                log_entry.calculate_cost(model_pricing)
                logger.info(f"Mapped log {log_id} to model {ai_model.id} ({ai_model.name})")
            else:
                log_entry.error_message = f"No AI model found matching: {log_entry.raw_model_name}"
                logger.warning(f"No AI model found matching: {log_entry.raw_model_name}")
            
            # Mark as processed
            log_entry.mark_as_processed(log_entry.user_id, log_entry.model_id)
            
            await db.commit()
            logger.info(f"Successfully processed billing entry {log_id}")
            
        except Exception as e:
            logger.error(f"Error processing billing entry {log_id}: {str(e)}")
            # Update log entry with error
            if log_entry:
                log_entry.error_message = str(e)
                log_entry.retry_count += 1
                await db.commit()

# --- Health Check ---
@router.get("/billing/health")
async def billing_health_check():
    """Simple health check for billing service"""
    return {
        "status": "healthy",
        "service": "billing_receiver",
        "timestamp": datetime.utcnow().isoformat()
    }