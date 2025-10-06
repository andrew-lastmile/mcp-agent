#!/usr/bin/env python3
import subprocess, time, json, re, datetime, sys, os

LOG_FILE = "canary_logs.jsonl"

def deploy_app():
    """Deploy app and return app_id (or None on failure)."""
    print("🚀 Starting deployment...")
    try:
        process = subprocess.Popen(
            ["uv", "run", "mcp-agent", "deploy", "basic-agent"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            stdin=subprocess.PIPE,
            text=True,
            cwd="basic-agent",
            bufsize=1,  # Line buffered
        )
        
        # Send responses for interactive prompts:
        # "y" to update existing app, "y" to update secrets, "1" for secret type
        process.stdin.write("y\ny\n1\n1\n1\n")
        process.stdin.flush()
        
        # Read output line by line and print in real-time
        output = ""
        for line in process.stdout:
            print(line, end='')  # Print to console in real-time
            output += line
        
        # Wait for process to complete
        process.wait()
        
        # Check for deployment success indicators
        deployment_success = "✅ MCP App deployed successfully!" in output or "App Status: ONLINE" in output
        deployment_failed = "❌ Deployment failed" in output
        
        # Extract app_id and app_url if present
        match = re.search(r"(app_[0-9a-f\-]+)", output)
        app_id = match.group(1) if match else None
        
        # Extract app URL
        url_match = re.search(r"App URL:\s+(https://[^\s]+)", output)
        app_url = url_match.group(1) if url_match else None
        
        if deployment_failed or process.returncode != 0:
            print(f"❌ Deploy failed with return code {process.returncode}")
            if app_id:
                print(f"   Failed app_id: {app_id}")
            # Return the app_id even on failure so it can be logged
            return app_id, None
        elif deployment_success and app_id:
            print(f"✅ Deployment successful! app_id: {app_id}")
            if app_url:
                print(f"📍 App URL: {app_url}")
            return app_id, app_url
        else:
            print("❌ Could not determine deployment status")
            if app_id:
                print(f"   Found app_id but uncertain status: {app_id}")
            return None, None
    except Exception as e:
        print("❌ Deploy failed:", str(e))
        return None, None


def call_mcp_client(app_url):
    """Run the MCP client code, return success/failure + runtime."""
    print(f"🔌 Running MCP client to test {app_url}...")
    start = time.time()
    try:
        # Set the app URL as an environment variable for the client
        env = os.environ.copy()
        env["MCP_APP_URL"] = app_url
        
        result = subprocess.run(
            ["python", "client.py"],  # Run client.py
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        runtime = time.time() - start
        success = result.returncode == 0
        
        # Print client output for debugging
        if result.stdout:
            print("Client output:")
            print(result.stdout)
        if result.stderr:
            print("Client errors:")
            print(result.stderr)
            
        return success, runtime, result.stdout, result.stderr
    except Exception as e:
        return False, time.time() - start, "", str(e)


def delete_app(app_id):
    """Delete app by ID."""
    print(f"🗑️  Deleting app {app_id}...")
    try:
        subprocess.run(
            ["uv", "run", "mcp-agent", "cloud", "apps", "delete", "--id", app_id, "-f"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ App {app_id} deleted successfully")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Delete failed:", e.stderr)
        return False


def log_result(status, app_id, latency, stdout="", stderr=""):
    entry = {
        "time": datetime.datetime.utcnow().isoformat() + "Z",
        "status": status,
        "app_id": app_id,
        "latency_s": latency,
        "stdout": stdout[-500:],  # keep only last 500 chars
        "stderr": stderr[-500:],
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Print formatted log entry with app_id highlighted
    print(f"\n📊 Log Entry [{app_id or 'NO_APP_ID'}]:")
    print(f"  Status: {status}")
    print(f"  Latency: {latency:.2f}s")
    print(f"  Time: {entry['time']}")


if __name__ == "__main__":
      app_id, app_url = deploy_app()
      
      # If deployment failed (no app_url), log and continue
      if not app_url:
          log_result("deploy_failed", app_id, 0)  # app_id might still exist for failed deployments
          time.sleep(30)
          continue

      # Test the deployed app with the client
      success, runtime, out, err = call_mcp_client(app_url)
      status = "success" if success else "call_failed"
      log_result(status, app_id, runtime, out, err)

      # Delete the app after testing
      if app_id:
          delete_app(app_id)
