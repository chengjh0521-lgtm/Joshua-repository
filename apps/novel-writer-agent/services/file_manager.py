from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, OUTPUT_DIR, PROJECT_ROOT


WINDOWS_FORBIDDEN = r'<>:"/\|?*'


def sanitize_filename_part(value: str, fallback: str = "未命名") -> str:
    cleaned = "".join("_" if char in WINDOWS_FORBIDDEN else char for char in value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:80] or fallback


def ensure_directories() -> None:
    for path in [
        PROJECT_ROOT / "agents",
        PROJECT_ROOT / "services",
        PROJECT_ROOT / "prompts",
        DATA_DIR,
        OUTPUT_DIR / "chapters_clean",
        OUTPUT_DIR / "chapters_with_notes",
        OUTPUT_DIR / "short_stories",
        OUTPUT_DIR / "short_stories_with_notes",
        OUTPUT_DIR / "subtitles",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "\n\n" if current.strip() else ""
    path.write_text(current.rstrip() + separator + content.rstrip() + "\n", encoding="utf-8")


def chapter_filename(chapter_number: int, title: str) -> str:
    safe_title = sanitize_filename_part(title)
    return f"第{chapter_number:03d}章_{safe_title}.txt"


def short_story_filename(title: str) -> str:
    safe_title = sanitize_filename_part(title, fallback="短篇小说")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"短篇_{stamp}_{safe_title}.txt"


def list_clean_chapters() -> list[Path]:
    chapter_dir = OUTPUT_DIR / "chapters_clean"
    if not chapter_dir.exists():
        return []
    return sorted(chapter_dir.glob("第*.txt"))


def next_chapter_number() -> int:
    used_numbers: set[int] = set()
    for path in list_clean_chapters():
        match = re.match(r"第(\d+)章_", path.name)
        if match:
            used_numbers.add(int(match.group(1)))

    chapter_number = 1
    while chapter_number in used_numbers:
        chapter_number += 1
    return chapter_number
