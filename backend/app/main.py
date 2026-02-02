import sys
import asyncio
from fastapi import FastAPI
from app.api.routes import router

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="Browser Automation Agent (FastAPI + Playwright)")
app.include_router(router)
