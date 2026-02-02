import os
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
from app.schemas.task import (
    TaskRequest,
    TaskResponse,
    InformationResponse,
)
from app.services.browser_manager import BrowserManager
from app.services.task_agent import TaskAgent
from app.services.workflow_executor import WorkflowExecutor

router = APIRouter()
browser_manager = BrowserManager()

# Task agent: Gemini (GEMINI_API_KEY) or fallback
gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
task_agent = TaskAgent(api_key=gemini_api_key)
workflow_executor = WorkflowExecutor(browser_manager, task_agent)

@router.get("/health")
async def health():
    return {"ok": True, "service": "browser-automation-agent-backend"}

# ---------------------------
# Sessions
# ---------------------------
@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(payload: StartSessionRequest):
    try:
        session_id = await browser_manager.create_session(headless=payload.headless)
        return StartSessionResponse(session_id=session_id, message="✅ Session started")
    except NotImplementedError as e:
        raise HTTPException(
            status_code=500,
            detail="Windows asyncio subprocess issue. Restart server with: set UVICORN_USE_SELECTOR=1 && uvicorn app.main:app --reload"
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        detail = str(e)
        if "playwright install" in detail.lower() or "chromium" in detail.lower():
            detail = f"{detail} (Run in terminal: playwright install chromium)"
        raise HTTPException(status_code=500, detail=f"Session start failed: {detail}") from e

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


# ---------------------------
# Task Orchestration
# ---------------------------
@router.post("/task/start", response_model=TaskResponse)
async def start_task(payload: TaskRequest):
    """
    Start a new automation task based on a natural language prompt.
    The agent will analyze the task, determine what information is needed,
    and begin execution.
    
    Example prompts:
    - "Book tickets from New York to Los Angeles"
    - "Apply to a job at https://example.com/jobs/123"
    - "Fill out a contact form"
    """
    try:
        response = await workflow_executor.start_task(
            session_id=payload.session_id,
            prompt=payload.prompt,
            context=payload.context
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task start failed: {str(e)}")


@router.post("/task/provide-information", response_model=TaskResponse)
async def provide_information(payload: InformationResponse):
    """
    Provide information requested by the task agent.
    This is called when the agent needs additional details to proceed.
    """
    try:
        response = await workflow_executor.provide_information(
            task_id=payload.task_id,
            field_name=payload.field_name,
            value=payload.value
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Information provision failed: {str(e)}")


@router.post("/task/continue/{task_id}", response_model=TaskResponse)
async def continue_task(task_id: str):
    """
    Continue execution of a paused or waiting task.
    """
    try:
        response = await workflow_executor.continue_task(task_id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task continuation failed: {str(e)}")


@router.get("/task/status/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get the current status of a task.
    """
    try:
        response = await workflow_executor.get_task_status(task_id)
        if not response:
            raise HTTPException(status_code=404, detail="Task not found")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/task/log/{task_id}")
async def get_task_log(task_id: str):
    """
    Get the execution log for a task.
    """
    try:
        log = workflow_executor.get_execution_log(task_id)
        if log is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, "log": log}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task log: {str(e)}")
