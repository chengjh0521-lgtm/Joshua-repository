import os
import subprocess
import sys
from pathlib import Path

from .file_service import latest_output_file


ALLOWED_ACTIONS = {"generate", "init", "status", "short", "write", "next"}
ARTICLE_TYPES = {"long", "short"}
STATE_MODES = {"long", "short"}


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


def _state_mode(payload: dict) -> str:
    mode = _optional_text(payload, "state_mode")
    if mode in STATE_MODES:
        return mode
    article_type = _optional_text(payload, "article_type")
    if article_type in ARTICLE_TYPES:
        return article_type
    return "short"


def _build_generate_command(agent_root: Path, payload: dict) -> list[str]:
    state_mode = _state_mode(payload)

    description = _optional_text(payload, "description") or _optional_text(payload, "goal")
    style = _optional_text(payload, "style") or _optional_text(payload, "state_style")
    state_setting = _optional_text(payload, "state_setting")
    if not description:
        raise NovelActionError("描述不能为空。")
    style = style or "自然、有画面感、叙事完整"

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
        "短篇" if state_mode == "short" else "长篇",
        "\n".join(part for part in [f"长期设定：{state_setting}" if state_setting else "", f"风格参考：{style}", description] if part),
        "--min-words",
        str(min_words),
        "--max-words",
        str(max_words),
        "--max-paragraphs",
        str(_max_paragraphs(state_mode, max_words)),
    ]
    if bool(payload.get("de_ai")):
        command.append("--remove-ai")
    return command


def _max_paragraphs(state_mode: str, max_words: int) -> int:
    if state_mode == "short":
        return max(4, min(24, max_words // 180))
    return max(6, min(36, max_words // 160))


def build_command(agent_root: Path, payload: dict) -> list[str]:
    action = _optional_text(payload, "action") or "generate"
    if action not in ALLOWED_ACTIONS:
        raise NovelActionError("不支持的 action。")

    if action == "generate":
        return _build_generate_command(agent_root, payload)

    if action == "init" and _state_mode(payload) == "long":
        command = [sys.executable, str(agent_root / "main.py"), "build"]
        genre = _optional_text(payload, "state_genre") or _optional_text(payload, "genre")
        style = _optional_text(payload, "state_style") or _optional_text(payload, "style")
        command.extend(["--genre", genre or "原创类型小说"])
        command.extend(["--style", style or "自然、有画面感、叙事完整"])
        return command

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
        command.append("--remove-ai")

    return command


def run_novel_agent(
    agent_root: Path,
    payload: dict,
    output_agent_root: Path | None = None,
    extra_env: dict[str, str] | None = None,
    timeout_seconds: int = 900,
) -> dict:
    command = build_command(agent_root, payload)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        env.update(extra_env)
    output_root = output_agent_root or agent_root
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
            "latest_file": latest_output_file(output_root),
        }

    return {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
        "latest_file": latest_output_file(output_root),
    }
