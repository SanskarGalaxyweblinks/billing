from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.models.api_usage_log import APIUsageLog
from app.models.user import User
from app.models.ai_model import AIModel
from app.models.user_api_key import UserAPIKey
from app.database import async_session

# Configure logging
logger = logging.getLogger(__name__)

class BillingProcessor:
    """
    Utility class for processing billing entries and mapping them to users/models.
    """
    
    @staticmethod
    async def find_user_by_company(company_name: str, db: AsyncSession) -> Optional[User]:
        """
        Find user by company name using various matching strategies.
        """
        if not company_name:
            return None
        
        company_lower = company_name.lower().strip()
        
        # Strategy 1: Exact match on organization_name
        stmt = select(User).where(
            func.lower(User.organization_name) == company_lower
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"Found user by exact match: {user.organization_name}")
            return user
        
        # Strategy 2: Partial match (company name contains organization name or vice versa)
        stmt = select(User).where(
            or_(
                func.lower(User.organization_name).contains(company_lower),
                func.literal(company_lower).contains(func.lower(User.organization_name))
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"Found user by partial match: {user.organization_name} for company: {company_name}")
            return user
        
        # Strategy 3: Check if company name matches any part of email domain
        email_domain = f"@{company_lower}"
        stmt = select(User).where(
            func.lower(User.email).contains(email_domain)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"Found user by email domain match: {user.email} for company: {company_name}")
            return user
        
        logger.warning(f"No user found for company: {company_name}")
        return None
    
    @staticmethod
    async def find_model_by_name(model_name: str, db: AsyncSession) -> Optional[AIModel]:
        """
        Find AI model by model name using various matching strategies.
        """
        if not model_name:
            return None
        
        model_lower = model_name.lower().strip()
        
        # Strategy 1: Exact match on model_identifier
        stmt = select(AIModel).where(
            func.lower(AIModel.model_identifier) == model_lower
        )
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            logger.info(f"Found model by exact identifier match: {model.model_identifier}")
            return model
        
        # Strategy 2: Exact match on name
        stmt = select(AIModel).where(
            func.lower(AIModel.name) == model_lower
        )
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            logger.info(f"Found model by exact name match: {model.name}")
            return model
        
        # Strategy 3: Partial match - model name contains any part
        stmt = select(AIModel).where(
            or_(
                func.lower(AIModel.name).contains(model_lower),
                func.lower(AIModel.model_identifier).contains(model_lower)
            )
        )
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            logger.info(f"Found model by partial match: {model.name} for input: {model_name}")
            return model
        
        # Strategy 4: Extract model type and search (e.g., "email_classifier" from "company_email_classifier")
        if '_' in model_name:
            # Try matching against the model type part
            model_type = '_'.join(model_name.split('_')[1:])  # Get everything after first underscore
            stmt = select(AIModel).where(
                or_(
                    func.lower(AIModel.name).contains(model_type.lower()),
                    func.lower(AIModel.model_identifier).contains(model_type.lower())
                )
            )
            result = await db.execute(stmt)
            model = result.scalar_one_or_none()
            if model:
                logger.info(f"Found model by type match: {model.name} for type: {model_type}")
                return model
        
        logger.warning(f"No model found for: {model_name}")
        return None
    
    @staticmethod
    async def calculate_model_cost(
        log_entry: APIUsageLog, 
        ai_model: Optional[AIModel] = None
    ) -> float:
        """
        Calculate cost for a log entry based on model pricing.
        """
        try:
            if ai_model:
                # Use actual model pricing
                if log_entry.total_tokens and ai_model.input_cost_per_1k_tokens:
                    # Token-based pricing
                    cost_per_token = ai_model.input_cost_per_1k_tokens / 1000
                    base_cost = log_entry.total_tokens * cost_per_token
                elif ai_model.request_cost:
                    # Request-based pricing
                    base_cost = float(ai_model.request_cost)
                else:
                    # Fallback to default pricing
                    base_cost = 0.01
            else:
                # Default pricing when no model found
                if log_entry.total_tokens:
                    base_cost = log_entry.total_tokens * 0.0001  # $0.0001 per token
                else:
                    base_cost = 0.01  # $0.01 per request
            
            # Apply any discounts
            discount_amount = base_cost * (log_entry.applied_discount / 100)
            final_cost = base_cost - discount_amount
            
            return max(0, final_cost)  # Ensure cost is never negative
            
        except Exception as e:
            logger.error(f"Error calculating cost: {str(e)}")
            return 0.01  # Fallback minimal cost

    @staticmethod
    async def process_billing_entry(log_id: int) -> Dict[str, Any]:
        """
        Main function to process a billing entry.
        Returns processing results for monitoring.
        """
        async with async_session() as db:
            try:
                # Get the log entry
                stmt = select(APIUsageLog).where(APIUsageLog.id == log_id)
                result = await db.execute(stmt)
                log_entry = result.scalar_one_or_none()
                
                if not log_entry:
                    return {
                        "success": False,
                        "error": f"Log entry {log_id} not found"
                    }
                
                processing_results = {
                    "log_id": log_id,
                    "company_name": log_entry.company_name,
                    "model_name": log_entry.raw_model_name,
                    "user_found": False,
                    "model_found": False,
                    "cost_calculated": False,
                    "errors": []
                }
                
                # Find and map user
                if log_entry.company_name:
                    user = await BillingProcessor.find_user_by_company(
                        log_entry.company_name, db
                    )
                    if user:
                        log_entry.user_id = user.id
                        processing_results["user_found"] = True
                        processing_results["user_id"] = user.id
                        processing_results["user_organization"] = user.organization_name
                    else:
                        error_msg = f"No user found for company: {log_entry.company_name}"
                        log_entry.error_message = error_msg
                        processing_results["errors"].append(error_msg)
                
                # Find and map model
                if log_entry.raw_model_name:
                    ai_model = await BillingProcessor.find_model_by_name(
                        log_entry.raw_model_name, db
                    )
                    if ai_model:
                        log_entry.model_id = ai_model.id
                        processing_results["model_found"] = True
                        processing_results["model_id"] = ai_model.id
                        processing_results["model_name_matched"] = ai_model.name
                        
                        # Recalculate cost with actual model pricing
                        new_cost = await BillingProcessor.calculate_model_cost(log_entry, ai_model)
                        log_entry.original_cost = new_cost
                        log_entry.total_cost = new_cost * (1 - log_entry.applied_discount / 100)
                        processing_results["cost_calculated"] = True
                        processing_results["final_cost"] = float(log_entry.total_cost)
                    else:
                        error_msg = f"No AI model found for: {log_entry.raw_model_name}"
                        log_entry.error_message = error_msg
                        processing_results["errors"].append(error_msg)
                
                # Mark as processed
                log_entry.mark_as_processed(log_entry.user_id, log_entry.model_id)
                
                await db.commit()
                
                processing_results["success"] = True
                processing_results["processed_at"] = datetime.utcnow().isoformat()
                
                logger.info(f"Successfully processed billing entry {log_id}: "
                          f"User={processing_results['user_found']}, "
                          f"Model={processing_results['model_found']}")
                
                return processing_results
                
            except Exception as e:
                error_msg = f"Error processing billing entry {log_id}: {str(e)}"
                logger.error(error_msg)
                
                # Update log entry with error
                try:
                    if log_entry:
                        log_entry.error_message = str(e)
                        log_entry.retry_count += 1
                        await db.commit()
                except:
                    pass  # Don't let error handling fail
                
                return {
                    "success": False,
                    "log_id": log_id,
                    "error": error_msg
                }

    @staticmethod
    async def get_unprocessed_entries(limit: int = 100) -> List[APIUsageLog]:
        """
        Get unprocessed billing entries for batch processing.
        """
        async with async_session() as db:
            stmt = (
                select(APIUsageLog)
                .where(APIUsageLog.billing_processed == False)
                .order_by(APIUsageLog.created_at.asc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def reprocess_failed_entries(max_retries: int = 3) -> Dict[str, Any]:
        """
        Reprocess failed billing entries that haven't exceeded max retries.
        """
        async with async_session() as db:
            stmt = (
                select(APIUsageLog)
                .where(
                    and_(
                        APIUsageLog.billing_processed == False,
                        APIUsageLog.error_message.isnot(None),
                        APIUsageLog.retry_count < max_retries
                    )
                )
                .order_by(APIUsageLog.created_at.asc())
                .limit(50)  # Process in batches
            )
            result = await db.execute(stmt)
            failed_entries = result.scalars().all()
            
            results = {
                "total_found": len(failed_entries),
                "processed": 0,
                "successful": 0,
                "failed": 0
            }
            
            for entry in failed_entries:
                try:
                    processing_result = await BillingProcessor.process_billing_entry(entry.id)
                    results["processed"] += 1
                    
                    if processing_result.get("success", False):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to reprocess entry {entry.id}: {str(e)}")
                    results["failed"] += 1
            
            return results

# Convenience function for background tasks
async def process_billing_entry(log_id: int, model_name: str = None):
    """
    Convenience function for background task processing.
    """
    processor = BillingProcessor()
    return await processor.process_billing_entry(log_id)