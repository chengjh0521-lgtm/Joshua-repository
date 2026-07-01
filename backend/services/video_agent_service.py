import os
import subprocess
import sys
from pathlib import Path

from .user_config_service import video_runtime_config


ALLOWED_ACTIONS = {"status", "check-once", "upload-pending"}


class VideoAgentError(ValueError):
    pass


def run_video_agent(project_root: Path, username: str, action: str, timeout_seconds: int = 3600) -> dict:
    action = str(action or "").strip()
    if action not in ALLOWED_ACTIONS:
        raise VideoAgentError("不支持的视频 Agent 操作。")

    agent_root = project_root / "apps" / "video-publisher-agent"
    runtime_config = video_runtime_config(username)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["VIDEO_AGENT_CONFIG"] = str(runtime_config)

    command = [sys.executable, str(agent_root / "runner.py"), action]
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
            "stderr": f"视频 Agent 执行超时，已停止。超时时间：{timeout_seconds} 秒。",
            "returncode": 124,
        }

    return {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }
