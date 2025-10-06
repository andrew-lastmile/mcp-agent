#!/usr/bin/env python3
import subprocess
import sys
import time
import json
import os

api_key = os.environ.get("OPENAI_API_KEY")

def delete_app(app_id):
    print(f"🗑️  Deleting app {app_id}...")
    start = time.time()
    success = False
    err = ""

    try:
        subprocess.run(
            ["uv", "run", "mcp-agent", "cloud", "apps", "delete", "--id", app_id, "-f", "--api_key", api_key],
            check=True,
            text=True,
            capture_output=True,
        )
        success = True
        print("✅ App deleted successfully")
    except subprocess.CalledProcessError as e:
        err = e.stderr or str(e)
        print(f"❌ Delete failed: {err}")

    end = time.time()
    latency = round(end - start, 3)

    # Emit JSON result for run_canary.py to parse
    result = {
        "success": success,
        "latency_s": latency,
        "stderr": err[-500:],  # keep the tail of stderr for log trimming
    }
    print(json.dumps(result, ensure_ascii=False))

    # Exit code (0 if success, 1 if failure)
    return 0 if success else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: delete_app.py <app_id>")
        sys.exit(1)
    sys.exit(delete_app(sys.argv[1]))