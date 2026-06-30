import os
import subprocess
import sys
from pathlib import Path

from .file_service import latest_output_file


ALLOWED_ACTIONS = {"init", "status", "short", "write", "next"}


class NovelActionError(ValueError):
    pass


def build_command(agent_root: Path, payload: dict) -> list[str]:
    action = str(payload.get("action", "")).strip()
    if action not in ALLOWED_ACTIONS:
        raise NovelActionError("不支持的 action。")

    command = [sys.executable, str(agent_root / "main.py"), action]
    goal = str(payload.get("goal") or "").strip()
    genre = str(payload.get("genre") or "").strip()
    style = str(payload.get("style") or "").strip()
    words = payload.get("words")

    if action in {"short", "write", "next"} and goal:
        command.extend(["--goal", goal])
    if genre:
        command.extend(["--genre", genre])
    if style:
        command.extend(["--style", style])
    if words not in (None, ""):
        try:
            words_value = int(words)
        except (TypeError, ValueError) as exc:
            raise NovelActionError("words 必须是数字。") from exc
        command.extend(["--words", str(words_value)])

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
