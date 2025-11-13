import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import stripe
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.billing_summary import MonthlyBillingSummary

router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

class CreateCheckoutSessionRequest(BaseModel):
    bill_id: int

@router.post("/create-checkout-session")
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(MonthlyBillingSummary).where(
        MonthlyBillingSummary.id == payload.bill_id,
        MonthlyBillingSummary.user_id == current_user.id,
        MonthlyBillingSummary.is_paid == False
    )
    result = await db.execute(stmt)
    bill = result.scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail="Unpaid bill not found for this user")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Jupiter AI - Invoice for {bill.month}/{bill.year}',
                        },
                        'unit_amount': int(bill.total_cost * 100),
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url="http://localhost:8080/payment-status?status=success",
            cancel_url="http://localhost:8080/payment-status?status=cancelled",
            metadata={
                'bill_id': bill.id
            },
            invoice_creation={'enabled': True}
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))