import json
import os
import subprocess
import sys
from pathlib import Path


ALLOWED_KINDS = {"article", "idea"}


class ZhihuAgentError(ValueError):
    pass


def run_zhihu_agent(project_root: Path, kind: str, topic: str, timeout_seconds: int = 900) -> dict:
    kind = str(kind or "").strip()
    topic = str(topic or "").strip()
    if kind not in ALLOWED_KINDS:
        raise ZhihuAgentError("不支持的知乎 Agent 类型。")
    if len(topic) < 2:
        raise ZhihuAgentError("请填写至少 2 个字符的知乎选题。")

    agent_root = project_root / "apps" / "zhihu-writer-agent"
    command = [sys.executable, str(agent_root / "runner.py"), "--kind", kind, "--topic", topic]
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

    return {
        "ok": completed.returncode == 0 and bool(parsed.get("ok", False)),
        "result": parsed.get("result"),
        "error": parsed.get("error", ""),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }
