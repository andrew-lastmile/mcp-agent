#!/usr/bin/env python3
import json
import datetime
import sys

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
    test_stderr
):
    """Write a single unified log entry for the full canary run."""
    entry = {
        "time": datetime.datetime.utcnow().isoformat() + "Z",
        "status": status,
        "app_id": app_id,
        "total_latency_s": float(total_latency),
        "deploy_latency_s": float(deploy_latency),
        "test_latency_s": float(test_latency),
        "deploy_stdout": deploy_stdout[-500:],
        "deploy_stderr": deploy_stderr[-500:],
        "test_stdout": test_stdout[-500:],
        "test_stderr": test_stderr[-500:],
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Print for visibility in GitHub Actions logs
    print("📊 Canary result logged:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Expect 12 arguments (besides script name)
    if len(sys.argv) < 9:
        print(
            "Usage: log_result.py <status> <app_id> <total_latency> <deploy_latency> <test_latency> "
            "<deploy_stdout> <deploy_stderr> <test_stdout> <test_stderr> "
        )
        sys.exit(1)

    log_result(*sys.argv[1:13])
