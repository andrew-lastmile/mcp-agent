#!/usr/bin/env python3
import subprocess
import json
import sys

def run_and_stream(cmd, name):
    """Run a subprocess and stream its output live to console."""
    print(f"\n▶️ Running {name}: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,  # direct stream to console
        stderr=sys.stderr,
        text=True,
    )
    process.wait()
    print(f"🏁 {name} exited with code {process.returncode}\n")
    return process.returncode


def main():
    # ---- Step 1: Deploy ----
    deploy_cmd = ["python", "deploy_app.py"]
    if run_and_stream(deploy_cmd, "deploy_app") != 0:
        print("❌ Deployment failed.")
        sys.exit(1)

    # ---- Step 2: Read deploy output ----
    # Deploy_app.py should still print a JSON blob at the end.
    # We’ll capture it by running it again in capture mode for data parsing.
    deploy_output = subprocess.run(
        deploy_cmd, capture_output=True, text=True
    ).stdout.strip().splitlines()[-1]
    try:
        deploy_data = json.loads(deploy_output)
        app_url = deploy_data.get("app_url")
        app_id = deploy_data.get("app_id")
    except Exception as e:
        print(f"⚠️  Failed to parse deploy output: {e}")
        sys.exit(1)

    # ---- Step 3: Test ----
    test_cmd = ["python", "test_app.py", app_url]
    run_and_stream(test_cmd, "test_app")

    # ---- Step 4: Delete ----
    delete_cmd = ["python", "delete_app.py", app_id]
    run_and_stream(delete_cmd, "delete_app")

if __name__ == "__main__":
    main()