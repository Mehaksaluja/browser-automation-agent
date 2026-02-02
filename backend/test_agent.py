"""
Quick test script for Browser Automation Agent.
Run: python test_agent.py
"""
import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


def main():
    print("Browser Automation Agent - Quick Test\n" + "=" * 50)

    # 1. Health
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        r.raise_for_status()
        print("1. Health: OK")
    except Exception as e:
        print(f"1. Health: FAIL - {e}")
        print("   Start server: uvicorn app.main:app --reload")
        sys.exit(1)

    # 2. Start session
    try:
        r = requests.post(f"{BASE}/session/start", json={"headless": True}, timeout=30)
        r.raise_for_status()
        session_id = r.json()["session_id"]
        print(f"2. Session: OK (id={session_id[:8]}...)")
    except requests.exceptions.HTTPError as e:
        print(f"2. Session: FAIL - {e}")
        if e.response is not None and e.response.status_code == 500:
            try:
                detail = e.response.json().get("detail", e.response.text)
                print(f"   Server says: {detail}")
                if "playwright install" in str(detail).lower():
                    print("   Fix: Run in terminal: playwright install chromium")
            except Exception:
                print(f"   Response: {e.response.text[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"2. Session: FAIL - {e}")
        sys.exit(1)

    # 3. Start task
    try:
        r = requests.post(
            f"{BASE}/task/start",
            json={"session_id": session_id, "prompt": "Book tickets from Delhi to Mumbai"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        task_id = data["task_id"]
        status = data["status"]
        needs_info = data.get("needs_information", False)
        print(f"3. Task start: OK (task_id={task_id[:8]}..., status={status}, needs_info={needs_info})")
        if needs_info and data.get("information_requests"):
            n = len(data["information_requests"])
            print(f"   Agent is asking for {n} piece(s) of information.")
    except Exception as e:
        print(f"3. Task start: FAIL - {e}")
        requests.post(f"{BASE}/session/close", json={"session_id": session_id})
        sys.exit(1)

    # 4. Close session
    try:
        requests.post(f"{BASE}/session/close", json={"session_id": session_id}, timeout=5)
        print("4. Session closed: OK")
    except Exception as e:
        print(f"4. Close: {e}")

    print("\n" + "=" * 50)
    print("All checks passed. Agent is working.")
    print("\nTo test interactively: run test_agent.py then use /task/provide-information")
    print("Or open: " + BASE + "/docs")


if __name__ == "__main__":
    main()
