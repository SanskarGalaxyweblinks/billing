import uvicorn
from app.main import create_app
from app.database import init_db
import asyncio

app = create_app()

# Run DB setup on startup
@app.on_event("startup")
async def on_startup():
    await init_db()

if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)
