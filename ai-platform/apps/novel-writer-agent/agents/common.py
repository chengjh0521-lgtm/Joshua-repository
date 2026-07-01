from __future__ import annotations

import re


def section(text: str, name: str) -> str:
    pattern = rf"---{re.escape(name)}---\s*(.*?)(?=\n---[A-Z_]+---|\Z)"
    match = re.search(pattern, text, flags=re.S)
    return match.group(1).strip() if match else ""


def first_non_empty_line(text: str, fallback: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip().strip("#").strip()
        if cleaned:
            return cleaned
    return fallback
