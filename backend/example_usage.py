"""
Example usage of the Browser Automation Agent API.

This script demonstrates how to interact with the agent to automate tasks.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"


def start_session(headless: bool = False):
    """Start a new browser session."""
    response = requests.post(
        f"{BASE_URL}/session/start",
        json={"headless": headless}
    )
    response.raise_for_status()
    data = response.json()
    print(f"✅ Session started: {data['session_id']}")
    return data["session_id"]


def start_task(session_id: str, prompt: str, context: dict = None):
    """Start a new automation task."""
    payload = {
        "session_id": session_id,
        "prompt": prompt
    }
    if context:
        payload["context"] = context
    
    response = requests.post(
        f"{BASE_URL}/task/start",
        json=payload
    )
    response.raise_for_status()
    return response.json()


def provide_information(session_id: str, task_id: str, field_name: str, value):
    """Provide information requested by the agent."""
    response = requests.post(
        f"{BASE_URL}/task/provide-information",
        json={
            "session_id": session_id,
            "task_id": task_id,
            "field_name": field_name,
            "value": value
        }
    )
    response.raise_for_status()
    return response.json()


def get_task_status(task_id: str):
    """Get the current status of a task."""
    response = requests.get(f"{BASE_URL}/task/status/{task_id}")
    response.raise_for_status()
    return response.json()


def get_task_log(task_id: str):
    """Get the execution log for a task."""
    response = requests.get(f"{BASE_URL}/task/log/{task_id}")
    response.raise_for_status()
    return response.json()


def interactive_task_execution(session_id: str, prompt: str):
    """
    Execute a task interactively, providing information as needed.
    """
    print(f"\n🚀 Starting task: {prompt}\n")
    
    # Start the task
    task_data = start_task(session_id, prompt)
    task_id = task_data["task_id"]
    
    print(f"Task ID: {task_id}")
    print(f"Status: {task_data['status']}\n")
    
    # Handle information gathering
    while task_data.get("needs_information"):
        print("📋 The agent needs some information:\n")
        
        for info_req in task_data["information_requests"]:
            question = info_req["question"]
            field_name = info_req["field_name"]
            field_type = info_req["field_type"]
            
            print(f"❓ {question}")
            
            # Get user input
            if field_type == "number":
                value = int(input("Your answer: "))
            elif field_type == "email":
                value = input("Your answer: ").strip()
            elif field_type == "phone":
                value = input("Your answer: ").strip()
            else:
                value = input("Your answer: ").strip()
            
            # Provide the information
            task_data = provide_information(session_id, task_id, field_name, value)
            print(f"✅ Provided: {field_name} = {value}\n")
    
    # Monitor task execution
    print("⚙️  Task is executing...\n")
    
    while task_data["status"] in ["executing", "waiting_for_user"]:
        print(f"Step {task_data.get('current_step', 0)}/{task_data.get('total_steps', 0)}")
        print(f"Status: {task_data['status']}")
        print(f"Message: {task_data['message']}\n")
        
        if task_data["status"] == "waiting_for_user":
            input("Press Enter to continue...")
            task_data = requests.post(
                f"{BASE_URL}/task/continue/{task_id}"
            ).json()
        else:
            time.sleep(2)  # Wait a bit before checking again
            task_data = get_task_status(task_id)
    
    # Final status
    print(f"\n{'✅' if task_data['status'] == 'completed' else '❌'} Task {task_data['status']}")
    print(f"Message: {task_data['message']}\n")
    
    # Show execution log
    log = get_task_log(task_id)
    print("Execution Log:")
    print("-" * 50)
    for entry in log["log"]:
        print(f"  • {entry}")
    print("-" * 50)
    
    return task_data


if __name__ == "__main__":
    print("=" * 60)
    print("Browser Automation Agent - Example Usage")
    print("=" * 60)
    
    try:
        # Check if server is running
        health = requests.get(f"{BASE_URL}/health")
        health.raise_for_status()
        print("✅ Server is running\n")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server.")
        print("   Make sure the server is running:")
        print("   cd backend && uvicorn app.main:app --reload")
        exit(1)
    
    # Start a session
    session_id = start_session(headless=False)
    
    # Example 1: Book tickets
    print("\n" + "=" * 60)
    print("Example 1: Booking Tickets")
    print("=" * 60)
    
    interactive_task_execution(
        session_id,
        "Book tickets from New York to Los Angeles"
    )
    
    # You can add more examples here
    # Example 2: Apply to a job
    # interactive_task_execution(
    #     session_id,
    #     "Apply to a job at https://example.com/jobs/123"
    # )
