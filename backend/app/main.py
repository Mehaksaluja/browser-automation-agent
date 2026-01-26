import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router

# Set Windows event loop policy - MUST be done before any async operations
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure event loop policy is set on startup
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    yield
    # Shutdown cleanup if needed
    pass

app = FastAPI(
    title="Browser Automation Agent (FastAPI + Playwright)",
    lifespan=lifespan
)
app.include_router(router)
