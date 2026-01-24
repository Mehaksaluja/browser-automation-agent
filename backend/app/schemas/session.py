from pydantic import BaseModel

class StartSessionRequest(BaseModel):
    headless: bool = False

class StartSessionResponse(BaseModel):
    session_id: str
    message: str

class NavigateRequest(BaseModel):
    session_id: str
    url: str

class ScreenshotRequest(BaseModel):
    session_id: str

class ScreenshotResponse(BaseModel):
    session_id: str
    image_base64: str
