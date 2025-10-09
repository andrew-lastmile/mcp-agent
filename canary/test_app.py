#!/usr/bin/env python3
import subprocess
import time
import os
import json
import sys

def call_mcp_client(app_url):
    print(f"🔌 Running MCP client to test {app_url}...")

    # Copy environment and inject MCP_APP_URL
    env = os.environ.copy()
    env["MCP_APP_URL"] = app_url

    # Find the absolute path to client.py (same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    client_path = os.path.join(script_dir, "client.py")

    if not os.path.exists(client_path):
        print(f"❌ client.py not found at {client_path}")
        result = {
            "success": False,
            "latency_s": 0.0,
            "stdout": "",
            "stderr": f"client.py not found at {client_path}"
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    start = time.time()
    try:
        # Run the client.py script in its own directory
        process = subprocess.Popen(
            [sys.executable, "-u", client_path, app_url],   # <-- unbuffered, pass URL too
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**env, "PYTHONUNBUFFERED": "1"},
            cwd=script_dir,
            bufsize=1,
        )
        
        output = ""
        last = time.time()
        idle_timeout = 30      # seconds without new output
        hard_timeout = 600     # max runtime

        while True:
            line = process.stdout.readline()
            now = time.time()
            if line:
                print(line, end="")
                output += line
                last = now
            elif process.poll() is not None:
                break
            elif now - last > idle_timeout or now - start > hard_timeout:
                process.kill()
                print("⏱️ Killing stuck client.py (timeout).")
                break
        
        process.wait(timeout=5)
        latency = round(time.time() - start, 3)
        success = process.returncode == 0

        result = {
            "success": success,
            "latency_s": latency,
            "stdout": output[-3000:],  # last 3000 chars for debugging
            "stderr": "",
        }

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if success else 1)

    except Exception as e:
        latency = round(time.time() - start, 3)
        err = str(e)
        print(f"❌ MCP client failed: {err}")
        result = {
            "success": False,
            "latency_s": latency,
            "stdout": "",
            "stderr": err[-500:],
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_app.py <app_url>")
        sys.exit(1)
    call_mcp_client(sys.argv[1])
