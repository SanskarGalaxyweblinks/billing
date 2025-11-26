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
        # Import the core models that should always exist
        try:
            from app.models import (
                api_usage_log, 
                billing_summary, 
                ai_model, 
                user
            )
            print("✅ Core models imported successfully")
        except ImportError as e:
            print(f"❌ Error importing core models: {e}")
            raise
        
        # Import optional models with error handling
        optional_models = [
            "admin", 
            "subscription_tier", 
            "model_substitutions", 
            "discount_rule"
        ]
        
        for model_name in optional_models:
            try:
                exec(f"from app.models import {model_name}")
                print(f"✅ Imported optional model: {model_name}")
            except ImportError as e:
                print(f"⚠️  Warning: Could not import {model_name}: {e}")
                continue
        
        print("🔄 Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")