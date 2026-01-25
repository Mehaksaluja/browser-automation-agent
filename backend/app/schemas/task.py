from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class TaskStatus(str, Enum):
    PLANNING = "planning"
    GATHERING_INFO = "gathering_info"
    EXECUTING = "executing"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class TaskRequest(BaseModel):
    session_id: str
    prompt: str
    context: Optional[Dict[str, Any]] = None  # Additional context for the task

class InformationRequest(BaseModel):
    session_id: str
    task_id: str
    question: str
    field_name: str
    field_type: str = "text"  # text, number, email, phone, date, etc.
    required: bool = True

class InformationResponse(BaseModel):
    session_id: str
    task_id: str
    field_name: str
    value: Any

class TaskStep(BaseModel):
    step_number: int
    action: str  # click, type, navigate, wait, observe, etc.
    description: str
    selector: Optional[str] = None
    value: Optional[str] = None
    wait_for: Optional[str] = None  # selector to wait for
    expected_result: Optional[str] = None

class TaskPlan(BaseModel):
    task_id: str
    task_description: str
    required_information: List[Dict[str, Any]]  # List of fields needed
    steps: List[TaskStep]
    current_step: int = 0

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    needs_information: bool = False
    information_requests: Optional[List[InformationRequest]] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    screenshot: Optional[str] = None  # base64 encoded screenshot
    error: Optional[str] = None

class TaskExecutionState(BaseModel):
    task_id: str
    session_id: str
    status: TaskStatus
    plan: Optional[TaskPlan] = None
    gathered_information: Dict[str, Any] = {}
    current_step_index: int = 0
    execution_log: List[str] = []
