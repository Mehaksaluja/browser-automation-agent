"""
Task Agent - Interprets user prompts and creates execution plans.
Supports Gemini API with fallback logic for common tasks.
"""
import uuid
import json
from typing import Dict, List, Optional, Any
from app.schemas.task import (
    TaskPlan,
    TaskStep,
    InformationRequest,
)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class TaskAgent:
    """
    AI-powered task agent that interprets user prompts, plans actions,
    and determines what information is needed using Google Gemini.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.client = None

        if GEMINI_AVAILABLE and api_key:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
        elif not GEMINI_AVAILABLE:
            print("Warning: google-generativeai not installed. Using fallback logic.")

    async def analyze_task(
        self, prompt: str, current_url: Optional[str] = None
    ) -> TaskPlan:
        """Analyze a user prompt and create a task plan."""
        task_id = str(uuid.uuid4())
        if self.client:
            return await self._analyze_with_llm(prompt, current_url, task_id)
        return await self._analyze_fallback(prompt, current_url, task_id)

    async def _analyze_with_llm(
        self, prompt: str, current_url: Optional[str], task_id: str
    ) -> TaskPlan:
        """Use Gemini to analyze task and create plan."""
        system = """You are a browser automation expert. Analyze user tasks and create execution plans.
Return ONLY a valid JSON object (no markdown) with:
- task_description: string
- required_information: list of {field_name, question, field_type, required}
- steps: list of {step_number, action, description, selector?, value?, wait_for?}
Actions: navigate, click, type, wait, observe, select, scroll."""

        user = f"Task: {prompt}\nCurrent URL: {current_url or 'none'}\nReturn JSON plan."

        try:
            response = self.client.generate_content(
                f"{system}\n\n{user}",
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            result = json.loads(text)
            steps = result.get("steps", [])
            return TaskPlan(
                task_id=task_id,
                task_description=result.get("task_description", prompt),
                required_information=result.get("required_information", []),
                steps=[TaskStep(**s) for s in steps],
                current_step=0,
            )
        except Exception as e:
            print(f"Gemini failed: {e}, using fallback")
            return await self._analyze_fallback(prompt, current_url, task_id)

    async def _analyze_fallback(
        self, prompt: str, current_url: Optional[str], task_id: str
    ) -> TaskPlan:
        """Fallback plans for common tasks without LLM."""
        pl = prompt.lower()
        if "book" in pl and "ticket" in pl:
            return TaskPlan(
                task_id=task_id,
                task_description="Book tickets",
                required_information=[
                    {"field_name": "number_of_tickets", "question": "How many tickets?", "field_type": "number", "required": True},
                    {"field_name": "origin", "question": "From where?", "field_type": "text", "required": True},
                    {"field_name": "destination", "question": "To where?", "field_type": "text", "required": True},
                    {"field_name": "travel_date", "question": "Travel date?", "field_type": "date", "required": True},
                    {"field_name": "phone_number", "question": "Your phone number?", "field_type": "phone", "required": True},
                ],
                steps=[
                    TaskStep(step_number=1, action="navigate", description="Go to booking site", value="https://www.irctc.co.in/"),
                    TaskStep(step_number=2, action="observe", description="Observe page"),
                ],
                current_step=0,
            )
        if "apply" in pl and "job" in pl:
            return TaskPlan(
                task_id=task_id,
                task_description="Apply to job",
                required_information=[
                    {"field_name": "job_url", "question": "Job posting URL?", "field_type": "url", "required": True},
                    {"field_name": "full_name", "question": "Your name?", "field_type": "text", "required": True},
                    {"field_name": "email", "question": "Email?", "field_type": "email", "required": True},
                ],
                steps=[
                    TaskStep(step_number=1, action="navigate", description="Open job page", value="{job_url}"),
                    TaskStep(step_number=2, action="observe", description="Observe page"),
                ],
                current_step=0,
            )
        # Generic
        return TaskPlan(
            task_id=task_id,
            task_description=prompt,
            required_information=[],
            steps=[
                TaskStep(step_number=1, action="observe", description="Observe current page"),
            ],
            current_step=0,
        )

    def create_information_requests(
        self, task_plan: TaskPlan, gathered_info: Dict[str, Any]
    ) -> List[InformationRequest]:
        """Build info requests for missing fields."""
        out = []
        for fi in task_plan.required_information:
            fn = fi.get("field_name")
            if fn not in gathered_info:
                out.append(
                    InformationRequest(
                        session_id="",
                        task_id=task_plan.task_id,
                        question=fi.get("question", f"Provide {fn}"),
                        field_name=fn,
                        field_type=fi.get("field_type", "text"),
                        required=fi.get("required", True),
                    )
                )
        return out

    async def get_next_action(
        self,
        task_plan: TaskPlan,
        current_step: int,
        page_state: Dict[str, Any],
        gathered_info: Dict[str, Any],
    ) -> Optional[TaskStep]:
        """Return next step; fill placeholders in value."""
        if current_step >= len(task_plan.steps):
            return None
        step = task_plan.steps[current_step]
        if step.value and "{" in step.value:
            try:
                step = TaskStep(
                    step_number=step.step_number,
                    action=step.action,
                    description=step.description,
                    selector=step.selector,
                    value=step.value.format(**gathered_info),
                    wait_for=step.wait_for,
                    expected_result=step.expected_result,
                )
            except KeyError:
                pass
        return step
