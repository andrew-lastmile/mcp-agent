#!/usr/bin/env python3
import subprocess
import time
import os
import json
import sys

def call_mcp_client(app_url):
    print(f"🔌 Running MCP client to test {app_url}...")
    env = os.environ.copy()
    env["MCP_APP_URL"] = app_url

    start = time.time()
    try:
        # Run client and stream output live
        process = subprocess.Popen(
            ["python", "client.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        output = ""
        for line in process.stdout:
            print(line, end="")  # stream to console in real time
            output += line

        process.wait()
        end = time.time()
        latency = round(end - start, 3)
        success = process.returncode == 0

        result = {
            "success": success,
            "latency_s": latency,
            "stdout": output[-500:],
            "stderr": "",
        }

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if success else 1)

    except Exception as e:
        end = time.time()
        latency = round(end - start, 3)
        err = str(e)
        print(f"❌ MCP client failed: {err}")
        result = {
            "success": False,
            "latency_s": latency,
            "stdout": "",
            "stderr": err[-500:]
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_app.py <app_url>")
        sys.exit(1)
    call_mcp_client(sys.argv[1])