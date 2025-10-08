#!/usr/bin/env python3
import argparse
import os
import re
import sys
import tempfile

def fail(msg: str, code: int = 1):
    # No secret contents are ever printed.
    print(f"[openai_key] {msg}", file=sys.stderr)
    sys.exit(code)

def load_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        fail(f"File not found: {path}")

def atomic_write(path: str, content: str):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_inject_", dir=d, text=True)
    try:
        os.fchmod(fd, 0o600)  # tighten perms on temp file
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)  # atomic on POSIX
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def inject_key_into_text(text: str, key: str) -> str:
    """
    Minimal YAML-safe editing without requiring PyYAML.
    - Finds an `openai:` block (case-insensitive).
    - Replaces/creates `api_key: "<KEY>"` within that block.
    - If no `openai:` block exists, appends one to the end.
    """
    lines = text.splitlines()

    # Find 'openai:' block (case-insensitive)
    openai_idx = None
    openai_indent = 0
    for i, line in enumerate(lines):
        if re.match(r'^\s*openai:\s*$', line, flags=re.IGNORECASE):
            openai_idx = i
            openai_indent = len(re.match(r'^(\s*)', line).group(1))
            break

    if openai_idx is None:
        # Append a new block at EOF
        block = [
            "",
            "openai:",
            f'  api_key: "{key}"',
        ]
        return ("\n".join(lines) + "\n" + "\n".join(block) + "\n").lstrip("\n")

    # Determine block end (next non-empty, non-comment line with indent <= openai_indent)
    end = len(lines)
    for j in range(openai_idx + 1, len(lines)):
        ln = lines[j]
        if not ln.strip():
            continue
        if ln.lstrip().startswith("#"):
            continue
        indent = len(re.match(r'^(\s*)', ln).group(1))
        if indent <= openai_indent:
            end = j
            break

    # Search for api_key within the block
    api_line_idx = None
    for j in range(openai_idx + 1, end):
        if re.match(r'^\s*api_key\s*:', lines[j], flags=re.IGNORECASE):
            api_line_idx = j
            break

    if api_line_idx is not None:
        # Replace existing api_key line in-place (preserve indentation)
        indent = re.match(r'^(\s*)', lines[api_line_idx]).group(1)
        lines[api_line_idx] = f'{indent}api_key: "{key}"'
    else:
        # Insert right after the 'openai:' line with +2 spaces indentation
        insertion = f'{" " * (openai_indent + 2)}api_key: "{key}"'
        lines.insert(openai_idx + 1, insertion)

    return "\n".join(lines) + ("\n" if not text.endswith("\n") else "")

def main():
    parser = argparse.ArgumentParser(description="Add OPENAI_API_KEY into mcp_agent.secrets.yaml safely.")
    parser.add_argument("--file", default="canary/basic-agent/mcp_agent.secrets.yaml",
                        help="Path to mcp_agent.secrets.yaml")
    args = parser.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        fail("Environment variable OPENAI_API_KEY is not set.")

    # Never print the key. Just modify the file atomically.
    original = load_text(args.file)
    updated = inject_key_into_text(original, key)

    # Only write if changed
    if updated != original:
        atomic_write(args.file, updated)
        print("[add_openai_key] Injection complete.")
    else:
        print("[add_openai_key] No changes needed.")

if __name__ == "__main__":
    main()
