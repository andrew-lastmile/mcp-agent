#!/usr/bin/env python3
import subprocess
import time
import os
import json
import sys
import signal
from threading import Thread
from queue import Queue, Empty

IDLE_TIMEOUT_SECONDS = 30     # seconds without new output
HARD_TIMEOUT_SECONDS = 600    # absolute max runtime


def _reader(pipe, queue: Queue):
    """Background reader that pulls lines from the child's stdout."""
    try:
        for line in iter(pipe.readline, ''):  # blocks inside the thread
            queue.put(line)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _kill_process_group(process: subprocess.Popen):
    """Kill the whole process group (child + any grandchildren)."""
    try:
        if os.name == "nt":
            # On Windows, create the process with CREATE_NEW_PROCESS_GROUP
            # so we can send CTRL_BREAK_EVENT to the whole group.
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
                process.wait(timeout=2)
                return
            except Exception:
                pass
            try:
                process.kill()
                return
            except Exception:
                pass
        else:
            # POSIX: start_new_session=True makes child the leader of a new process group
            os.killpg(process.pid, signal.SIGKILL)
    except Exception:
        # Fallback: attempt to kill just the child
        try:
            process.kill()
        except Exception:
            pass


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

    # Platform-specific process group flags
    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        start_new_session = True  # puts child in its own process group on POSIX

    start = time.time()
    try:
        # Run the client.py script in its own directory
        process = subprocess.Popen(
            [sys.executable, "-u", client_path, app_url],   # unbuffered, pass URL too
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**env, "PYTHONUNBUFFERED": "1"},
            cwd=script_dir,
            bufsize=1,
            start_new_session=start_new_session,
            creationflags=creationflags,
        )

        assert process.stdout is not None, "Failed to capture child stdout"

        # Start reader thread
        q: Queue[str] = Queue()
        t = Thread(target=_reader, args=(process.stdout, q), daemon=True)
        t.start()

        output = ""
        last = time.time()
        idle_timeout = IDLE_TIMEOUT_SECONDS
        hard_timeout = HARD_TIMEOUT_SECONDS

        # Main supervision loop (non-blocking, thanks to background reader)
        while True:
            now = time.time()

            # Drain what's available without blocking the main thread
            drained_any = False
            while True:
                try:
                    # Wait briefly for at least one line; after that, drain immediately
                    line = q.get(timeout=0.5 if not drained_any else 0.0)
                    drained_any = True
                    print(line, end="")
                    output += line
                    last = now
                except Empty:
                    break

            # If the process has exited and we've drained all output, we can stop
            if process.poll() is not None and q.empty():
                break

            # Enforce timeouts
            if (now - last) > idle_timeout or (now - start) > hard_timeout:
                print("⏱️ Killing stuck client.py (timeout).")
                _kill_process_group(process)
                break

        # Ensure the child is gone
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            try:
                process.wait(timeout=2)
            except Exception:
                pass

        latency = round(time.time() - start, 3)
        success = (process.returncode == 0)

        result = {
            "success": success,
            "latency_s": latency,
            "stdout": output[-500:],  # last 500 chars for compactness
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
