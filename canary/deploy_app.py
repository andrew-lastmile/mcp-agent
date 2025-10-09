#!/usr/bin/env python3
import subprocess
import re
import json
import sys
import time
import os

api_key = os.environ.get("MCPAC_API_KEY")

cwd_path = os.path.join(os.path.dirname(__file__), "basic-agent")

def deploy_app():
    print("🚀 Starting deployment...")
    start = time.time()

    process = subprocess.Popen(
        ["uv", "run", "mcp-agent", "deploy", "woodstock-canary", "--api-key", api_key],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True,
        cwd=cwd_path,
        bufsize=1,
    )

    # Respond to interactive prompts
    process.stdin.write("y\ny\n1\n1\n1\n")
    process.stdin.flush()

    output = ""
    for line in process.stdout:
        print(line, end="")  # real-time streaming
        output += line

    process.wait()
    end = time.time()
    latency = round(end - start, 3)

    # Deployment success detection
    success = "✅ MCP App deployed successfully!" in output or "App Status: ONLINE" in output
    app_id_match = re.search(r"(app_[0-9a-f\-]+)", output)
    app_url_match = re.search(r"App URL:\s+(https://[^\s]+)", output)

    result = {
        "success": success,
        "app_id": app_id_match.group(1) if app_id_match else None,
        "app_url": app_url_match.group(1) if app_url_match else None,
        "output": output[-2000:],  # tail for log brevity
        "return_code": process.returncode,
        "latency_s": latency,
    }

    # Print structured JSON for downstream parsing
    print(json.dumps(result, ensure_ascii=False))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    deploy_app()
