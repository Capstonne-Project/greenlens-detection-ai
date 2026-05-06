#!/usr/bin/env python3
"""Minimal shell safety hint for Cursor beforeShellExecution (fail-open)."""

from __future__ import annotations

import json
import re
import sys

# Patterns that deserve an extra prompt (adjust to team policy).
SENSITIVE = re.compile(
    r"(^|\s)("
    r"curl\s|wget\s|Invoke-WebRequest|iwr\s|fetch\(|"
    r"docker\s+(system\s+)?prune|docker\s+rmi\s|"
    r"DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+"
    r")",
    re.IGNORECASE,
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.stdout.write('{"permission": "allow"}')
        return 0

    command = payload.get("command") or ""

    # Very rough destructive hints (POSIX-ish); still useful on mixed shells.
    destructive = re.search(
        r"(\brm\b.*-rf\b|>\s/dev/|diskutil\s+erase|\bformat\b\s+c:)", command, re.I
    )

    if destructive:
        sys.stdout.write(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": "Lệnh có vẻ mang tính hủy dữ liệu hoặc hệ thống. Xác nhận trước khi chạy.",
                    "agent_message": "Hook flagged a potentially destructive shell command.",
                }
            )
        )
        return 0

    if SENSITIVE.search(command):
        sys.stdout.write(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": "Lệnh có network hoặc tác động môi trường. Kiểm tra lại.",
                    "agent_message": "Hook flagged network or environment-affecting command.",
                }
            )
        )
        return 0

    sys.stdout.write('{"permission": "allow"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
