#!/usr/bin/env python3
"""
Fixed database check script that handles asyncpg URL format
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def check_existing_models():
    """Check all existing model identifiers in the database using raw SQL"""
    
    # Load environment variables
    load_dotenv()
    
    # Get database URL and fix the format
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    # Fix the URL format for asyncpg (remove +asyncpg)
    if "+asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"🔗 Connecting to database...")
    
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(database_url)
        
        # Get all models
        models = await conn.fetch("""
            SELECT id, name, model_identifier, provider, status, created_at
            FROM ai_models 
            ORDER BY created_at DESC;
        """)
        
        print("🔍 Existing AI Models in Database:")
        print("=" * 90)
        print(f"{'ID':<5} {'Name':<25} {'Model Identifier':<20} {'Provider':<15} {'Status':<10}")
        print("-" * 90)
        
        if not models:
            print("✅ No models found in database - you can use any identifier!")
        else:
            for model in models:
                name = (model['name'] or '')[:24]
                identifier = (model['model_identifier'] or '')[:19]
                provider = (model['provider'] or '')[:14]
                status = (model['status'] or '')[:9]
                print(f"{model['id']:<5} {name:<25} {identifier:<20} {provider:<15} {status:<10}")
        
        print("=" * 90)
        print(f"Total models: {len(models)}")
        
        # Check for 'Classifier' specifically
        classifier_models = await conn.fetch("""
            SELECT * FROM ai_models 
            WHERE model_identifier = 'Classifier';
        """)
        
        if classifier_models:
            print(f"\n🎯 FOUND THE PROBLEM! {len(classifier_models)} model(s) with identifier 'Classifier':")
            for model in classifier_models:
                print(f"  ❌ ID: {model['id']}, Name: '{model['name']}', Provider: '{model['provider']}'")
                print(f"     Created: {model['created_at']}")
                print(f"\n💡 SOLUTION: Either delete this model or use a different identifier like:")
                print(f"     - ClassifierV2")
                print(f"     - DocClassifier")
                print(f"     - JupiterClassifier")
        else:
            print("\n✅ No models found with identifier 'Classifier' - this is strange!")
            print("The error might be from a different source.")
        
        # Show all identifiers for reference
        all_identifiers = [model['model_identifier'] for model in models if model['model_identifier']]
        if all_identifiers:
            print(f"\n📋 All existing identifiers: {', '.join(all_identifiers)}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    asyncio.run(check_existing_models())