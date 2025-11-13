# jupiter_backend/create_user_model_access_migration.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, Base
from app.models.user_model_access import UserModelAccess

async def create_user_model_access_table():
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import user, ai_model, admin
        
        # Create only the new table
        await conn.run_sync(UserModelAccess.__table__.create, checkfirst=True)
        print("user_model_access table created successfully!")

if __name__ == "__main__":
    asyncio.run(create_user_model_access_table())