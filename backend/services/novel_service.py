import os
import subprocess
import sys
from pathlib import Path

from .file_service import latest_output_file


ALLOWED_ACTIONS = {"generate", "init", "status", "short", "write", "next"}
ARTICLE_TYPES = {"long", "short"}


class NovelActionError(ValueError):
    pass


def _optional_text(payload: dict, key: str) -> str:
    return str(payload.get(key) or "").strip()


def _coerce_int(value: object, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NovelActionError(f"{field_name} 必须是数字。") from exc


def _build_generate_command(agent_root: Path, payload: dict) -> list[str]:
    article_type = _optional_text(payload, "article_type")
    if article_type not in ARTICLE_TYPES:
        raise NovelActionError("文章类型必须选择长篇或短篇。")

    description = _optional_text(payload, "description") or _optional_text(payload, "goal")
    style = _optional_text(payload, "style")
    if not description:
        raise NovelActionError("描述不能为空。")
    if not style:
        raise NovelActionError("风格不能为空。")

    min_words = _coerce_int(payload.get("min_words"), "最小字数")
    max_words = _coerce_int(payload.get("max_words") or payload.get("words"), "最大字数")
    if min_words is None or max_words is None:
        raise NovelActionError("最小字数和最大字数都必须填写。")
    if min_words < 100:
        raise NovelActionError("最小字数不能小于 100。")
    if max_words < min_words:
        raise NovelActionError("最大字数不能小于最小字数。")
    if max_words > 50000:
        raise NovelActionError("最大字数不能超过 50000。")

    command = [
        sys.executable,
        str(agent_root / "main.py"),
        "short" if article_type == "short" else "write",
        "--goal",
        description,
        "--style",
        style,
        "--min-words",
        str(min_words),
        "--max-words",
        str(max_words),
    ]
    genre = _optional_text(payload, "genre")
    if genre:
        command.extend(["--genre", genre])
    if bool(payload.get("de_ai")):
        command.append("--de-ai")
    return command


def build_command(agent_root: Path, payload: dict) -> list[str]:
    action = _optional_text(payload, "action") or "generate"
    if action not in ALLOWED_ACTIONS:
        raise NovelActionError("不支持的 action。")

    if action == "generate":
        return _build_generate_command(agent_root, payload)

    command = [sys.executable, str(agent_root / "main.py"), action]
    goal = _optional_text(payload, "goal") or _optional_text(payload, "description")
    genre = _optional_text(payload, "genre")
    style = _optional_text(payload, "style")
    words = _coerce_int(payload.get("words") or payload.get("max_words"), "words")
    min_words = _coerce_int(payload.get("min_words"), "最小字数")

    if action in {"short", "write", "next"} and goal:
        command.extend(["--goal", goal])
    if genre:
        command.extend(["--genre", genre])
    if style:
        command.extend(["--style", style])
    if min_words is not None:
        command.extend(["--min-words", str(min_words)])
    if words is not None:
        command.extend(["--max-words", str(words)])
    if bool(payload.get("de_ai")):
        command.append("--de-ai")

    return command


def run_novel_agent(agent_root: Path, payload: dict, timeout_seconds: int = 900) -> dict:
    command = build_command(agent_root, payload)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        completed = subprocess.run(
            command,
            cwd=agent_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "stdout": exc.stdout or "",
            "stderr": f"Agent 执行超时，已停止。超时时间：{timeout_seconds} 秒。",
            "returncode": 124,
            "latest_file": latest_output_file(agent_root),
        }

    return {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
        "latest_file": latest_output_file(agent_root),
    }
