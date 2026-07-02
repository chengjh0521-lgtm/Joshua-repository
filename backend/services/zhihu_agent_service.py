import json
import os
import subprocess
import sys
import base64
from pathlib import Path


ALLOWED_KINDS = {"article", "idea"}
DEFAULT_TARGET_WORD_COUNT = 1800
MIN_TARGET_WORD_COUNT = 800
MAX_TARGET_WORD_COUNT = 3500


class ZhihuAgentError(ValueError):
    pass


def encode_file_id(relative_path: str) -> str:
    raw = relative_path.replace("\\", "/").encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_file_id(file_id: str) -> str:
    padding = "=" * (-len(file_id) % 4)
    return base64.urlsafe_b64decode((file_id + padding).encode("ascii")).decode("utf-8")


def _attach_file_id(agent_root: Path, result: dict | None) -> None:
    if not result:
        return
    latest_file = result.get("latest_file")
    if not latest_file or not latest_file.get("path"):
        return
    path = Path(latest_file["path"]).resolve()
    root = agent_root.resolve()
    if root not in path.parents:
        return
    latest_file["id"] = encode_file_id(path.relative_to(root).as_posix())


def _clamp_target_word_count(value: int | None) -> int:
    try:
        target = int(value) if value is not None else DEFAULT_TARGET_WORD_COUNT
    except (TypeError, ValueError):
        target = DEFAULT_TARGET_WORD_COUNT
    return max(MIN_TARGET_WORD_COUNT, min(MAX_TARGET_WORD_COUNT, target))


def run_zhihu_agent(
    project_root: Path,
    kind: str,
    topic: str,
    target_word_count: int | None = None,
    timeout_seconds: int = 900,
) -> dict:
    kind = str(kind or "").strip()
    topic = str(topic or "").strip()
    target_word_count = _clamp_target_word_count(target_word_count)
    if kind not in ALLOWED_KINDS:
        raise ZhihuAgentError("不支持的知乎 Agent 类型。")
    if len(topic) < 2:
        raise ZhihuAgentError("请填写至少 2 个字符的知乎选题。")

    agent_root = project_root / "apps" / "zhihu-writer-agent"
    command = [
        sys.executable,
        str(agent_root / "runner.py"),
        "--kind",
        kind,
        "--topic",
        topic,
        "--target-word-count",
        str(target_word_count),
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(agent_root)

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
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": f"知乎 Agent 执行超时，已停止。超时时间：{timeout_seconds} 秒。",
            "returncode": 124,
        }

    parsed: dict = {}
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = {}

    result = parsed.get("result")
    _attach_file_id(agent_root, result)

    return {
        "ok": completed.returncode == 0 and bool(parsed.get("ok", False)),
        "result": result,
        "error": parsed.get("error", ""),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }


def get_zhihu_output_file(project_root: Path, file_id: str) -> tuple[str, str]:
    agent_root = (project_root / "apps" / "zhihu-writer-agent").resolve()
    relative_path = decode_file_id(file_id)
    path = (agent_root / relative_path).resolve()
    allowed_roots = [
        (agent_root / "txt_outputs").resolve(),
        (agent_root / "backend" / "data" / "articles").resolve(),
    ]
    if not any(root == path.parent or root in path.parents for root in allowed_roots):
        raise FileNotFoundError("非法文件路径。")
    if not path.exists() or path.suffix.lower() not in {".txt", ".md"}:
        raise FileNotFoundError("文件不存在。")
    return path.name, path.read_text(encoding="utf-8")
