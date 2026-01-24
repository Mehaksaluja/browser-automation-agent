from pydantic import BaseModel
from typing import Optional

class ClickRequest(BaseModel):
    session_id: str
    selector: str
    timeout_ms: int = 8000

class TypeRequest(BaseModel):
    session_id: str
    selector: str
    text: str
    clear_first: bool = True
    timeout_ms: int = 8000

class ObserveResponse(BaseModel):
    url: str
    title: str
