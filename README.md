# Browser Automation Agent

An intelligent browser automation system that can understand natural language prompts, gather required information interactively, and execute complex multi-step tasks automatically.

## Features

- 🤖 **AI-Powered Task Interpretation**: Uses LLM to understand user prompts and create execution plans
- 💬 **Interactive Information Gathering**: Asks for missing information during task execution
- 🔄 **Multi-Step Workflow Execution**: Handles complex tasks with multiple steps
- 🌐 **Browser Automation**: Built on Playwright for reliable browser control
- 📸 **Visual Feedback**: Provides screenshots at each step
- 🔍 **Enhanced Observation**: Analyzes page state to make informed decisions

## Use Cases

- **Booking Tickets**: "Book 2 tickets from New York to Los Angeles on January 30th"
- **Job Applications**: "Apply to the job at https://example.com/jobs/123"
- **Form Filling**: "Fill out the contact form with my information"
- **Data Collection**: "Extract product information from this page"
- **Any Custom Task**: The agent can adapt to various automation needs

## Setup

### Prerequisites

- Python 3.8+
- Playwright browsers (installed automatically)

### Installation

1. **Clone the repository** (if not already done)

2. **Install dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

3. **Install Playwright browsers**:
```bash
playwright install chromium
```

4. **Set up environment variables** (optional but recommended):
```bash
# Create a .env file in the backend directory
OPENAI_API_KEY=your_openai_api_key_here
```

   > **Note**: The agent works without OpenAI API key using fallback logic, but for best results, provide an API key.

5. **Run the server**:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

### Interactive API Docs

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### 1. Start a Browser Session
```http
POST /session/start
Content-Type: application/json

{
  "headless": false
}
```

Response:
```json
{
  "session_id": "uuid-here",
  "message": "✅ Session started"
}
```

#### 2. Start a Task
```http
POST /task/start
Content-Type: application/json

{
  "session_id": "your-session-id",
  "prompt": "Book tickets from New York to Los Angeles",
  "context": {}
}
```

Response (if information is needed):
```json
{
  "task_id": "task-uuid",
  "status": "gathering_info",
  "message": "I need some information to proceed with this task.",
  "needs_information": true,
  "information_requests": [
    {
      "session_id": "your-session-id",
      "task_id": "task-uuid",
      "question": "How many tickets do you need?",
      "field_name": "number_of_tickets",
      "field_type": "number",
      "required": true
    },
    {
      "session_id": "your-session-id",
      "task_id": "task-uuid",
      "question": "Where are you traveling from?",
      "field_name": "origin",
      "field_type": "text",
      "required": true
    }
  ],
  "screenshot": "base64-encoded-image"
}
```

#### 3. Provide Information
```http
POST /task/provide-information
Content-Type: application/json

{
  "session_id": "your-session-id",
  "task_id": "task-uuid",
  "field_name": "number_of_tickets",
  "value": 2
}
```

Continue providing information until `needs_information` is `false`.

#### 4. Check Task Status
```http
GET /task/status/{task_id}
```

Response:
```json
{
  "task_id": "task-uuid",
  "status": "executing",
  "message": "Task is executing",
  "current_step": 3,
  "total_steps": 5,
  "screenshot": "base64-encoded-image"
}
```

#### 5. Get Task Execution Log
```http
GET /task/log/{task_id}
```

## Usage Examples

### Example 1: Booking Tickets

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Start a session
session_resp = requests.post(f"{BASE_URL}/session/start", json={"headless": False})
session_id = session_resp.json()["session_id"]

# 2. Start the task
task_resp = requests.post(
    f"{BASE_URL}/task/start",
    json={
        "session_id": session_id,
        "prompt": "Book tickets from New York to Los Angeles"
    }
)
task_data = task_resp.json()
task_id = task_data["task_id"]

# 3. Provide information as requested
while task_data.get("needs_information"):
    for info_req in task_data["information_requests"]:
        field_name = info_req["field_name"]
        question = info_req["question"]
        
        # In a real app, you'd prompt the user
        print(f"Question: {question}")
        value = input("Your answer: ")
        
        # Provide the information
        info_resp = requests.post(
            f"{BASE_URL}/task/provide-information",
            json={
                "session_id": session_id,
                "task_id": task_id,
                "field_name": field_name,
                "value": value
            }
        )
        task_data = info_resp.json()

# 4. Task is now executing or completed
print(f"Task status: {task_data['status']}")
print(f"Message: {task_data['message']}")

# 5. Check status periodically
status_resp = requests.get(f"{BASE_URL}/task/status/{task_id}")
print(status_resp.json())
```

### Example 2: Using cURL

```bash
# Start session
SESSION_ID=$(curl -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -d '{"headless": false}' | jq -r '.session_id')

# Start task
TASK_RESP=$(curl -X POST http://localhost:8000/task/start \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"prompt\": \"Book tickets from New York to Los Angeles\"
  }")

TASK_ID=$(echo $TASK_RESP | jq -r '.task_id')

# Provide information (repeat as needed)
curl -X POST http://localhost:8000/task/provide-information \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"task_id\": \"$TASK_ID\",
    \"field_name\": \"number_of_tickets\",
    \"value\": 2
  }"
```

## Task Status Values

- `planning`: Task is being analyzed and planned
- `gathering_info`: Waiting for user to provide required information
- `executing`: Task steps are being executed
- `waiting_for_user`: Paused, waiting for user action
- `completed`: Task finished successfully
- `failed`: Task encountered an error
- `paused`: Task is paused

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for LLM-powered task planning (optional but recommended)

### Without OpenAI API Key

The system includes fallback logic that works without an API key for common tasks like:
- Booking tickets
- Applying to jobs
- Generic form filling

However, for best results and to handle custom tasks, provide an OpenAI API key.

## Architecture

```
┌─────────────────┐
│   API Routes     │  ← HTTP endpoints
└────────┬────────┘
         │
┌────────▼─────────────────┐
│  Workflow Executor       │  ← Orchestrates task execution
└────────┬─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐  ┌─▼──────────┐
│ Task  │  │ Browser    │
│ Agent │  │ Manager    │
└───────┘  └────────────┘
    │            │
    │            │
┌───▼────────────▼───┐
│   Playwright       │  ← Browser automation
└────────────────────┘
```

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── schemas/
│   │   ├── actions.py          # Action schemas
│   │   ├── session.py          # Session schemas
│   │   └── task.py             # Task schemas
│   ├── services/
│   │   ├── browser_manager.py  # Browser control
│   │   ├── task_agent.py       # AI task planning
│   │   └── workflow_executor.py # Task execution
│   └── main.py                 # FastAPI app
└── requirements.txt
```

## Troubleshooting

### Playwright browsers not found
```bash
playwright install chromium
```

### OpenAI API errors
- Check that your API key is set correctly
- The system will fall back to pattern matching if API is unavailable

### Task execution fails
- Check the task log: `GET /task/log/{task_id}`
- Verify selectors are correct for the target website
- Some websites may have anti-bot measures

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
