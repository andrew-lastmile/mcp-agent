#!/usr/bin/env python3
import json
import datetime
import sys
import os

LOG_FILE = "canary_logs.jsonl"

def log_result(
    status,
    app_id,
    total_latency,
    deploy_latency,
    test_latency,
    deploy_stdout,
    deploy_stderr,
    test_stdout,
    test_stderr,
):
    """Write a single unified log entry for the full canary run."""

    # Normalize/sanitize potentially invalid Unicode sequences, then tail safely
    def safe_tail(s, n=3):
        """Return the last n lines of text."""
        if not isinstance(s, str):
            s = str(s)
        # Normalize Unicode
        s = s.encode("utf-8", "replace").decode("utf-8")
        # Split into lines and take last n
        lines = s.splitlines()
        return "\n".join(lines[-n:])

    entry = {
        "time": datetime.datetime.utcnow().isoformat() + "Z",
        "status": status,
        "app_id": app_id,
        "total_latency_s": float(total_latency),
        "deploy_latency_s": float(deploy_latency),
        "test_latency_s": float(test_latency),
        "deploy_stdout": safe_tail(deploy_stdout),
        "deploy_stderr": safe_tail(deploy_stderr),
        "test_stdout": safe_tail(test_stdout),
        "test_stderr": safe_tail(test_stderr),
    }

    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("📊 Canary result logged:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 9:
        print(
            "Usage: log_result.py <status> <app_id> <total_latency> <deploy_latency> <test_latency> "
            "<deploy_stdout> <deploy_stderr> <test_stdout> <test_stderr>"
        )
        sys.exit(1)

    # Accept the 9 args provided by your workflow (status..test_stderr)
    log_result(*sys.argv[1:10])
