import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import Base, engine, async_session
from app.models.admin import Admin
from app.security import get_password_hash
from dotenv import load_dotenv

load_dotenv()

async def create_default_admin():
    async with async_session() as session:
        stmt = select(Admin).where(Admin.username == "admin")
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is None:
            hashed_password = get_password_hash(os.getenv("DEFAULT_ADMIN_PASSWORD", "admin"))
            default_admin = Admin(
                username="admin",
                hashed_password=hashed_password,
                full_name="Default Admin",
                role="superadmin"
            )
            session.add(default_admin)
            await session.commit()
            print("Default admin user created.")
        else:
            print("Admin user already exists.")

async def init_db():
    async with engine.begin() as conn:
        from app.models import (
            api_usage_log, billing_summary,
            ai_model, user, admin, subscription_tier, model_substitutions,
            discount_rule
        )
        await conn.run_sync(Base.metadata.create_all)
    await create_default_admin()


if __name__ == "__main__":
    print("Initializing database and creating default admin user...")
    asyncio.run(init_db())