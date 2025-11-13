import os
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import stripe
from datetime import datetime

from app.models.billing_summary import MonthlyBillingSummary
from app.database import async_session

router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

async def get_db():
    async with async_session() as session:
        yield session

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature, secret=STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        bill_id = session.get('metadata', {}).get('bill_id')
        invoice_id = session.get('invoice')

        if not bill_id or not invoice_id:
            return {"status": "metadata or invoice_id missing"}

        # Retrieve full invoice to get the URL
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            hosted_invoice_url = invoice.hosted_invoice_url
        except Exception as e:
            hosted_invoice_url = None

        # Update the database
        stmt = select(MonthlyBillingSummary).where(MonthlyBillingSummary.id == int(bill_id))
        result = await db.execute(stmt)
        bill_to_update = result.scalar_one_or_none()

        if bill_to_update and not bill_to_update.is_paid:
            bill_to_update.is_paid = True
            bill_to_update.paid_at = datetime.utcnow()
            bill_to_update.stripe_invoice_id = invoice_id
            bill_to_update.stripe_invoice_url = hosted_invoice_url
            await db.commit()

    return {"status": "success"}