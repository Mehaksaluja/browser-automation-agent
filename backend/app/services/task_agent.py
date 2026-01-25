import uuid
import json
from typing import Dict, List, Optional, Any
from app.schemas.task import (
    TaskPlan, TaskStep, TaskStatus, InformationRequest,
    TaskExecutionState, TaskRequest
)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. Install with: pip install openai")

class TaskAgent:
    """
    AI-powered task agent that interprets user prompts, plans actions,
    and determines what information is needed.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
        elif not OPENAI_AVAILABLE:
            print("Warning: OpenAI library not installed. Task planning will use fallback logic.")
    
    async def analyze_task(self, prompt: str, current_url: Optional[str] = None) -> TaskPlan:
        """
        Analyze a user prompt and create a task plan with required information and steps.
        """
        task_id = str(uuid.uuid4())
        
        if self.client:
            return await self._analyze_with_llm(prompt, current_url, task_id)
        else:
            return await self._analyze_fallback(prompt, current_url, task_id)
    
    async def _analyze_with_llm(
        self, 
        prompt: str, 
        current_url: Optional[str],
        task_id: str
    ) -> TaskPlan:
        """Use LLM to analyze task and create plan."""
        
        system_prompt = """You are a browser automation expert. Analyze user tasks and create detailed execution plans.

For each task, you need to:
1. Identify what information is required (e.g., for booking tickets: number of tickets, origin, destination, date, phone number)
2. Break down the task into specific browser automation steps
3. Each step should be actionable (click, type, navigate, wait, observe)

Return a JSON object with:
- task_description: Clear description of what needs to be done
- required_information: List of objects with {field_name, question, field_type, required}
- steps: List of step objects with {step_number, action, description, selector (if applicable), value (if applicable), wait_for, expected_result}

Actions can be: navigate, click, type, wait, observe, select (for dropdowns), scroll
Selectors should be CSS selectors or text-based locators."""

        user_prompt = f"""Task: {prompt}
Current URL: {current_url or "Not on any page yet"}

Create a detailed execution plan for this task."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return TaskPlan(
                task_id=task_id,
                task_description=result.get("task_description", prompt),
                required_information=result.get("required_information", []),
                steps=[
                    TaskStep(**step) for step in result.get("steps", [])
                ],
                current_step=0
            )
        except Exception as e:
            print(f"LLM analysis failed: {e}, using fallback")
            return await self._analyze_fallback(prompt, current_url, task_id)
    
    async def _analyze_fallback(
        self,
        prompt: str,
        current_url: Optional[str],
        task_id: str
    ) -> TaskPlan:
        """Fallback analysis for when LLM is not available."""
        
        prompt_lower = prompt.lower()
        
        # Simple pattern matching for common tasks
        if "book" in prompt_lower and "ticket" in prompt_lower:
            return TaskPlan(
                task_id=task_id,
                task_description="Book tickets",
                required_information=[
                    {
                        "field_name": "number_of_tickets",
                        "question": "How many tickets do you need?",
                        "field_type": "number",
                        "required": True
                    },
                    {
                        "field_name": "origin",
                        "question": "Where are you traveling from?",
                        "field_type": "text",
                        "required": True
                    },
                    {
                        "field_name": "destination",
                        "question": "Where are you traveling to?",
                        "field_type": "text",
                        "required": True
                    },
                    {
                        "field_name": "travel_date",
                        "question": "What date do you want to travel?",
                        "field_type": "date",
                        "required": True
                    },
                    {
                        "field_name": "phone_number",
                        "question": "What is your phone number?",
                        "field_type": "phone",
                        "required": True
                    }
                ],
                steps=[
                    TaskStep(
                        step_number=1,
                        action="navigate",
                        description="Navigate to booking website",
                        value="https://example-booking-site.com"
                    ),
                    TaskStep(
                        step_number=2,
                        action="click",
                        description="Click on booking/search button",
                        selector="button[type='submit'], .search-button, #search-btn"
                    ),
                    TaskStep(
                        step_number=3,
                        action="wait",
                        description="Wait for search results",
                        wait_for=".results, .search-results"
                    )
                ],
                current_step=0
            )
        elif "apply" in prompt_lower and "job" in prompt_lower:
            return TaskPlan(
                task_id=task_id,
                task_description="Apply to a job",
                required_information=[
                    {
                        "field_name": "job_url",
                        "question": "What is the URL of the job posting?",
                        "field_type": "url",
                        "required": True
                    },
                    {
                        "field_name": "full_name",
                        "question": "What is your full name?",
                        "field_type": "text",
                        "required": True
                    },
                    {
                        "field_name": "email",
                        "question": "What is your email address?",
                        "field_type": "email",
                        "required": True
                    },
                    {
                        "field_name": "phone",
                        "question": "What is your phone number?",
                        "field_type": "phone",
                        "required": True
                    },
                    {
                        "field_name": "resume_path",
                        "question": "What is the path to your resume file?",
                        "field_type": "file",
                        "required": True
                    }
                ],
                steps=[
                    TaskStep(
                        step_number=1,
                        action="navigate",
                        description="Navigate to job posting",
                        value="{job_url}"
                    ),
                    TaskStep(
                        step_number=2,
                        action="click",
                        description="Click apply button",
                        selector="button:has-text('Apply'), .apply-button, #apply-btn"
                    ),
                    TaskStep(
                        step_number=3,
                        action="wait",
                        description="Wait for application form",
                        wait_for="form, .application-form"
                    )
                ],
                current_step=0
            )
        else:
            # Generic task
            return TaskPlan(
                task_id=task_id,
                task_description=prompt,
                required_information=[],
                steps=[
                    TaskStep(
                        step_number=1,
                        action="observe",
                        description="Observe current page state",
                    )
                ],
                current_step=0
            )
    
    def create_information_requests(
        self,
        task_plan: TaskPlan,
        gathered_info: Dict[str, Any]
    ) -> List[InformationRequest]:
        """Create information requests for missing required fields."""
        requests = []
        
        for field_info in task_plan.required_information:
            field_name = field_info.get("field_name")
            if field_name not in gathered_info:
                requests.append(InformationRequest(
                    session_id="",  # Will be set by caller
                    task_id=task_plan.task_id,
                    question=field_info.get("question", f"Please provide {field_name}"),
                    field_name=field_name,
                    field_type=field_info.get("field_type", "text"),
                    required=field_info.get("required", True)
                ))
        
        return requests
    
    async def get_next_action(
        self,
        task_plan: TaskPlan,
        current_step: int,
        page_state: Dict[str, Any],
        gathered_info: Dict[str, Any]
    ) -> Optional[TaskStep]:
        """Get the next action to execute based on current state."""
        if current_step >= len(task_plan.steps):
            return None
        
        step = task_plan.steps[current_step]
        
        # Replace placeholders in step values with gathered information
        if step.value and "{" in step.value:
            step.value = step.value.format(**gathered_info)
        
        return step
    
    async def adapt_plan(
        self,
        task_plan: TaskPlan,
        observation: Dict[str, Any],
        execution_log: List[str]
    ) -> TaskPlan:
        """Adapt the plan based on observations during execution."""
        # This could use LLM to analyze the current state and adjust the plan
        # For now, return the plan as-is
        return task_plan
