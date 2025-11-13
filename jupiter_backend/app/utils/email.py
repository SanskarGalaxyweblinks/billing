from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config import settings
import random
import string

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False  # UPDATED: Set to False for local development to bypass SSL error
)

def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))

async def send_verification_email(email_to: str, otp: str):
    """Sends a verification email with the OTP."""
    html_content = f"""
    <html>
        <body>
            <h2>Welcome to Jupiter Billing Platform!</h2>
            <p>Thank you for registering. Please use the following One-Time Password (OTP) to verify your email address:</p>
            <h3 style="font-size: 24px; letter-spacing: 2px; text-align: center; margin: 20px 0;">{otp}</h3>
            <p>This OTP will expire in 10 minutes.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
    </html>
    """
    message = MessageSchema(
        subject="Your Email Verification Code",
        recipients=[email_to],
        body=html_content,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

async def send_password_reset_email(email_to: str, reset_link: str):
    """Sends a password reset email with a link."""
    html_content = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You are receiving this email because a password reset was requested for your account.</p>
            <p>Please click the link below to reset your password:</p>
            <a href="{reset_link}">{reset_link}</a>
            <p>This link will expire in 15 minutes.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
    </html>
    """
    message = MessageSchema(
        subject="Your Password Reset Link",
        recipients=[email_to],
        body=html_content,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)