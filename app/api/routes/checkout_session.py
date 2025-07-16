import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import stripe
from app.models.user import User
from app.models.billing_summary import MonthlyBillingSummary
from app.api.deps import get_db, get_user_info
from pydantic import BaseModel
from decimal import Decimal
import json # Import json for parsing webhook payload

router = APIRouter()

# --- Stripe Configuration ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

# Stripe Webhook Secret - VERY IMPORTANT for security
# Get this from your Stripe Dashboard -> Developers -> Webhooks -> Select your endpoint -> Reveal secret
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_191560790114051a0f4f591f3171b8f57d8722b04ff548bb41f93bc580e556a0")

# Define a Pydantic model for the incoming request body for checkout session creation
class CreateCheckoutSessionRequest(BaseModel):
    bill_id: int

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: Request,
    payload: CreateCheckoutSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a Stripe Checkout Session for a given unpaid bill.
    """
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user by Supabase auth ID to get organization_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    # Fetch the specific unpaid bill
    bill_stmt = (
        select(MonthlyBillingSummary)
        .where(
            MonthlyBillingSummary.id == payload.bill_id,
            MonthlyBillingSummary.organization_id == db_user.organization_id,
            MonthlyBillingSummary.is_paid == False # Ensure only unpaid bills can be paid
        )
    )
    bill_result = await db.execute(bill_stmt)
    bill = bill_result.scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found or already paid.")

    # Convert total_cost to cents (Stripe requires amount in smallest currency unit)
    total_cost_decimal = Decimal(str(bill.total_cost))
    amount_cents = int(total_cost_decimal * 100)

    # Define success and cancel URLs.
    YOUR_DOMAIN = os.getenv("FRONTEND_URL", "http://192.168.29.213:8080")
    success_url = f"{YOUR_DOMAIN}/payment-status?status=success&bill_id={bill.id}"
    cancel_url = f"{YOUR_DOMAIN}/payment-status?status=cancelled&bill_id={bill.id}"

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"Monthly Bill - {bill.month}/{bill.year}",
                            'description': (
                                f"Usage cost: ${bill.usage_cost}, "
                                f"Subscription cost: ${bill.subscription_cost}"
                            ),
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "bill_id": str(bill.id),
                "organization_id": str(bill.organization_id),
            },
            customer_email=db_user.email if db_user.email else None,
        )
        return {"checkout_url": checkout_session.url}
    except stripe.error.StripeError as e:
        print(f"Stripe Error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"An unexpected error occurred during checkout session creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkout session creation.")


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Stripe webhook endpoint to handle payment events.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print(f"Webhook Error: Invalid payload - {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Webhook Error: Invalid signature - {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"Webhook Error: Unexpected error - {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing webhook")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Extract bill_id from metadata
        bill_id = session.get('metadata', {}).get('bill_id')
        invoice_id = session.get('invoice') # This will be the Stripe Invoice ID
        print("inv", invoice_id)

        if not bill_id:
            print("Webhook Warning: checkout.session.completed event missing bill_id in metadata.")
            return Response(status_code=200) # Still return 200 to Stripe to avoid retries

        try:
            # Convert bill_id to integer
            bill_id_int = int(bill_id)

            # Fetch the bill from your database
            stmt = select(MonthlyBillingSummary).where(MonthlyBillingSummary.id == bill_id_int)
            result = await db.execute(stmt)
            bill = result.scalar_one_or_none()

            if bill:
                if not bill.is_paid: # Only update if not already paid
                    bill.is_paid = True
                    bill.paid_at = func.now()
                    bill.stripe_invoice_id = invoice_id
                    await db.commit()
                    await db.refresh(bill)
                    print(f"Bill {bill.id} marked as paid. Stripe Invoice ID: {invoice_id}")
                else:
                    print(f"Bill {bill.id} already marked as paid. Skipping update.")
            else:
                print(f"Webhook Warning: Bill with ID {bill_id} not found in DB for session {session.id}.")

        except Exception as e:
            print(f"Error processing checkout.session.completed for bill {bill_id}: {e}")
            # Depending on your error handling strategy, you might re-raise or log more severely
            raise HTTPException(status_code=500, detail="Failed to update bill status.")

    elif event['type'] == 'payment_intent.succeeded':
        # This event is also useful, but checkout.session.completed is usually sufficient for one-time payments
        # You might use this for more complex payment flows or if you directly create PaymentIntents
        print(f"Payment Intent Succeeded: {event['data']['object']['id']}")


    return Response(status_code=200) # Acknowledge receipt of the event


@router.get("/billing/invoice/{bill_id}")
async def get_bill_invoice_id(
    bill_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches the Stripe invoice ID for a specific bill, ensuring the user has access.
    """
    user = get_user_info(request)
    auth_id = user.get("sub")

    if not auth_id:
        raise HTTPException(status_code=401, detail="Invalid Supabase UID")

    # Lookup user by Supabase auth ID to get organization_id
    user_stmt = select(User).where(User.auth_id == auth_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user or not db_user.organization_id:
        raise HTTPException(status_code=400, detail="User or organization not found")

    # Fetch the bill, ensuring it belongs to the user's organization and is paid
    stmt = (
        select(MonthlyBillingSummary)
        .where(
            MonthlyBillingSummary.id == bill_id,
            MonthlyBillingSummary.organization_id == db_user.organization_id,
            MonthlyBillingSummary.is_paid == True
        )
    )
    result = await db.execute(stmt)
    bill = result.scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail="Paid bill not found for this user/organization.")

    return {
        "bill_id": bill.id,
        "stripe_invoice_id": bill.stripe_invoice_id,
        "is_paid": bill.is_paid,
        "paid_at": bill.paid_at.isoformat() if bill.paid_at else None
    }

