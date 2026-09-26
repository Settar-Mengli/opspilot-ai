#!/usr/bin/env python3
"""F2a proof: no legacy API paths in frontend/src/api."""
import re
import subprocess
import sys

pattern = re.compile(
    r"""["'}`]/(health|runs?|briefing|ai-briefing|triage|ask|evening-summary|insights|inputs|capabilities|api/settings)\b"""
)
result = subprocess.run(
    ["git", "grep", "-n", ".", "--", "frontend/src/api"],
    capture_output=True,
    text=True,
    check=False,
)
hits = []
for line in result.stdout.splitlines():
    # Only check string/path-like occurrences matching F2a.
    if pattern.search(line) and "/api/v1/" not in line.split(":", 2)[-1]:
        # Allow API_PREFIX = '/api/v1' and comments mentioning paths.
        content = line.split(":", 2)[-1]
        if "API_PREFIX" in content or content.strip().startswith("//") or content.strip().startswith("*"):
            continue
        # generated.ts documents path keys under /api/v1 — skip those.
        if "frontend/src/api/generated.ts" in line and "/api/v1/" in content:
            continue
        hits.append(line)

if hits:
    print("F2a FAIL:")
    print("\n".join(hits))
    sys.exit(1)
print("F2a OK: zero legacy API client paths")
