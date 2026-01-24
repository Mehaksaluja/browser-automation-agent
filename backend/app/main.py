from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Browser Automation Agent")
app.include_router(router)
