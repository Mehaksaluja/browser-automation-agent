import asyncio
from typing import Dict, Optional, List, Any
from app.schemas.task import (
    TaskExecutionState, TaskStatus, TaskPlan, TaskStep,
    TaskResponse, InformationRequest
)
from app.services.browser_manager import BrowserManager
from app.services.task_agent import TaskAgent


class WorkflowExecutor:
    """
    Executes multi-step browser automation workflows.
    Manages task state, information gathering, and step-by-step execution.
    """
    
    def __init__(self, browser_manager: BrowserManager, task_agent: TaskAgent):
        self.browser_manager = browser_manager
        self.task_agent = task_agent
        self.active_tasks: Dict[str, TaskExecutionState] = {}
    
    async def start_task(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskResponse:
        """Start a new task execution."""
        try:
            # Get current page state
            page_state = await self.browser_manager.observe_basic(session_id)
            current_url = page_state.get("url")
            
            # Analyze task and create plan
            task_plan = await self.task_agent.analyze_task(prompt, current_url)
            
            # Create execution state
            execution_state = TaskExecutionState(
                task_id=task_plan.task_id,
                session_id=session_id,
                status=TaskStatus.PLANNING,
                plan=task_plan,
                gathered_information=context or {},
                current_step_index=0,
                execution_log=[f"Task started: {prompt}"]
            )
            
            self.active_tasks[task_plan.task_id] = execution_state
            
            # Check if information is needed
            info_requests = self.task_agent.create_information_requests(
                task_plan,
                execution_state.gathered_information
            )
            
            if info_requests:
                execution_state.status = TaskStatus.GATHERING_INFO
                # Set session_id for info requests
                for req in info_requests:
                    req.session_id = session_id
                
                screenshot = await self.browser_manager.screenshot_base64(session_id)
                
                return TaskResponse(
                    task_id=task_plan.task_id,
                    status=TaskStatus.GATHERING_INFO,
                    message="I need some information to proceed with this task.",
                    needs_information=True,
                    information_requests=info_requests,
                    screenshot=screenshot
                )
            else:
                # Start execution
                return await self.continue_task(task_plan.task_id)
        
        except Exception as e:
            return TaskResponse(
                task_id="",
                status=TaskStatus.FAILED,
                message=f"Failed to start task: {str(e)}",
                error=str(e)
            )
    
    async def provide_information(
        self,
        task_id: str,
        field_name: str,
        value: Any
    ) -> TaskResponse:
        """Provide information requested by the task."""
        if task_id not in self.active_tasks:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message="Task not found",
                error="Invalid task_id"
            )
        
        execution_state = self.active_tasks[task_id]
        execution_state.gathered_information[field_name] = value
        execution_state.execution_log.append(f"Information provided: {field_name} = {value}")
        
        # Check if we still need more information
        info_requests = self.task_agent.create_information_requests(
            execution_state.plan,
            execution_state.gathered_information
        )
        
        if info_requests:
            # Still need more info
            for req in info_requests:
                req.session_id = execution_state.session_id
            
            screenshot = await self.browser_manager.screenshot_base64(execution_state.session_id)
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.GATHERING_INFO,
                message=f"Thank you! I still need some more information.",
                needs_information=True,
                information_requests=info_requests,
                screenshot=screenshot
            )
        else:
            # All information gathered, start execution
            execution_state.status = TaskStatus.EXECUTING
            return await self.continue_task(task_id)
    
    async def continue_task(self, task_id: str) -> TaskResponse:
        """Continue executing the task from current step."""
        if task_id not in self.active_tasks:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message="Task not found",
                error="Invalid task_id"
            )
        
        execution_state = self.active_tasks[task_id]
        execution_state.status = TaskStatus.EXECUTING
        
        try:
            # Execute steps one by one
            while execution_state.current_step_index < len(execution_state.plan.steps):
                step = await self.task_agent.get_next_action(
                    execution_state.plan,
                    execution_state.current_step_index,
                    await self.browser_manager.observe_basic(execution_state.session_id),
                    execution_state.gathered_information
                )
                
                if not step:
                    break
                
                # Execute the step
                result = await self._execute_step(
                    execution_state.session_id,
                    step,
                    execution_state.gathered_information
                )
                
                execution_state.execution_log.append(
                    f"Step {step.step_number}: {step.description} - {result}"
                )
                
                # Check if step execution requires user input
                if result.get("needs_user_input"):
                    execution_state.status = TaskStatus.WAITING_FOR_USER
                    screenshot = await self.browser_manager.screenshot_base64(execution_state.session_id)
                    
                    return TaskResponse(
                        task_id=task_id,
                        status=TaskStatus.WAITING_FOR_USER,
                        message=result.get("message", "Waiting for user action"),
                        current_step=execution_state.current_step_index + 1,
                        total_steps=len(execution_state.plan.steps),
                        screenshot=screenshot
                    )
                
                execution_state.current_step_index += 1
                
                # Small delay between steps
                await asyncio.sleep(0.5)
            
            # Task completed
            execution_state.status = TaskStatus.COMPLETED
            screenshot = await self.browser_manager.screenshot_base64(execution_state.session_id)
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                message=f"Task completed successfully! Executed {len(execution_state.plan.steps)} steps.",
                current_step=len(execution_state.plan.steps),
                total_steps=len(execution_state.plan.steps),
                screenshot=screenshot
            )
        
        except Exception as e:
            execution_state.status = TaskStatus.FAILED
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message=f"Task execution failed: {str(e)}",
                error=str(e),
                current_step=execution_state.current_step_index + 1,
                total_steps=len(execution_state.plan.steps)
            )
    
    async def _execute_step(
        self,
        session_id: str,
        step: TaskStep,
        gathered_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step."""
        try:
            if step.action == "navigate":
                if step.value:
                    await self.browser_manager.navigate(session_id, step.value)
                    return {"success": True, "message": f"Navigated to {step.value}"}
            
            elif step.action == "click":
                if step.selector:
                    await self.browser_manager.click(session_id, step.selector)
                    return {"success": True, "message": f"Clicked {step.selector}"}
            
            elif step.action == "type":
                if step.selector and step.value:
                    await self.browser_manager.type_text(
                        session_id,
                        step.selector,
                        step.value
                    )
                    return {"success": True, "message": f"Typed into {step.selector}"}
            
            elif step.action == "wait":
                if step.wait_for:
                    await self.browser_manager.wait_for_element(
                        session_id,
                        step.wait_for,
                        timeout_ms=10000
                    )
                    return {"success": True, "message": f"Waited for {step.wait_for}"}
                else:
                    await asyncio.sleep(2)
                    return {"success": True, "message": "Waited 2 seconds"}
            
            elif step.action == "observe":
                observation = await self.browser_manager.observe_enhanced(session_id)
                return {
                    "success": True,
                    "message": "Page observed",
                    "observation": observation
                }
            
            elif step.action == "scroll":
                await self.browser_manager.scroll(session_id, step.value or "down")
                return {"success": True, "message": "Scrolled"}
            
            elif step.action == "select":
                if step.selector and step.value:
                    await self.browser_manager.select_option(
                        session_id,
                        step.selector,
                        step.value
                    )
                    return {"success": True, "message": f"Selected {step.value} in {step.selector}"}
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown action: {step.action}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Step execution failed: {str(e)}",
                "error": str(e)
            }
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResponse]:
        """Get current status of a task."""
        if task_id not in self.active_tasks:
            return None
        
        execution_state = self.active_tasks[task_id]
        screenshot = await self.browser_manager.screenshot_base64(execution_state.session_id)
        
        return TaskResponse(
            task_id=task_id,
            status=execution_state.status,
            message=f"Task is {execution_state.status.value}",
            current_step=execution_state.current_step_index + 1,
            total_steps=len(execution_state.plan.steps) if execution_state.plan else 0,
            screenshot=screenshot
        )
    
    def get_execution_log(self, task_id: str) -> Optional[List[str]]:
        """Get execution log for a task."""
        if task_id not in self.active_tasks:
            return None
        return self.active_tasks[task_id].execution_log
