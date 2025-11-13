from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# engine = create_async_engine(settings.DATABASE_URL, echo=True)
engine = create_async_engine(settings.DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        # Import all models here before calling create_all
        from app.models import api_usage_log, billing_summary, ai_model, user
        await conn.run_sync(Base.metadata.create_all)