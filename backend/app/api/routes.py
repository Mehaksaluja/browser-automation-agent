from fastapi import APIRouter, HTTPException

from app.schemas.session import (
    StartSessionRequest,
    StartSessionResponse,
    NavigateRequest,
    ScreenshotRequest,
    ScreenshotResponse,
)
from app.schemas.actions import (
    ClickRequest,
    TypeRequest,
    ObserveResponse
)
from app.services.browser_manager import BrowserManager

router = APIRouter()
browser_manager = BrowserManager()

@router.get("/health")
async def health():
    return {"ok": True, "service": "browser-automation-agent-backend"}

# ---------------------------
# Sessions
# ---------------------------
@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(payload: StartSessionRequest):
    session_id = await browser_manager.create_session(headless=payload.headless)
    return StartSessionResponse(session_id=session_id, message="✅ Session started")

@router.post("/session/navigate")
async def navigate(payload: NavigateRequest):
    try:
        await browser_manager.navigate(payload.session_id, payload.url)
        return {"ok": True, "message": f"✅ Navigated to {payload.url}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Navigation failed: {str(e)}")

@router.post("/session/screenshot", response_model=ScreenshotResponse)
async def screenshot(payload: ScreenshotRequest):
    try:
        img_b64 = await browser_manager.screenshot_base64(payload.session_id)
        return ScreenshotResponse(session_id=payload.session_id, image_base64=img_b64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")

@router.post("/session/close")
async def close_session(payload: ScreenshotRequest):
    try:
        await browser_manager.close_session(payload.session_id)
        return {"ok": True, "message": "✅ Session closed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Close failed: {str(e)}")


# ---------------------------
# Actions (Universal Skills)
# ---------------------------
@router.post("/action/click")
async def action_click(payload: ClickRequest):
    try:
        await browser_manager.click(payload.session_id, payload.selector, payload.timeout_ms)
        return {"ok": True, "message": f"✅ Clicked {payload.selector}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Click failed: {str(e)}")

@router.post("/action/type")
async def action_type(payload: TypeRequest):
    try:
        await browser_manager.type_text(
            payload.session_id,
            payload.selector,
            payload.text,
            payload.clear_first,
            payload.timeout_ms
        )
        return {"ok": True, "message": f"✅ Typed into {payload.selector}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Type failed: {str(e)}")

@router.get("/observe/basic", response_model=ObserveResponse)
async def observe_basic(session_id: str):
    try:
        data = await browser_manager.observe_basic(session_id)
        return ObserveResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Observe failed: {str(e)}")
