from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from src.config import config
from src.db.session import init_db
from src.api.chatwoot import router as chatwoot_router
from src.api.customer import router as customer_router
from src.api.user import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (Create tables)
    await init_db()
    yield
    # Cleanup on shutdown

app = FastAPI(title="Chatwoot Agent Bot API", lifespan=lifespan)

# Include routers
app.include_router(chatwoot_router)
app.include_router(customer_router)
app.include_router(user_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agent API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")