import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .user_config_service import (
    bilibili_login_files,
    ensure_bilibili_state_target,
    public_config,
    video_runtime_config,
)


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


def _read_login_status(username: str) -> dict:
    files = bilibili_login_files(username)
    status_file = files["status_file"]
    if not status_file.exists():
        return {"status": "idle", "message": ""}
    try:
        return json.loads(status_file.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "unknown", "message": status_file.read_text(encoding="utf-8", errors="replace")}


def start_bilibili_login(project_root: Path, username: str) -> dict:
    agent_root = project_root / "apps" / "video-publisher-agent"
    ensure_bilibili_state_target(username)
    runtime_config = video_runtime_config(username)
    files = bilibili_login_files(username)

    for path in files.values():
        if path.exists():
            path.unlink()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["VIDEO_AGENT_CONFIG"] = str(runtime_config)
    env["BILIBILI_LOGIN_DONE_FILE"] = str(files["done_file"])
    env["BILIBILI_LOGIN_STATUS_FILE"] = str(files["status_file"])

    command = [sys.executable, str(agent_root / "bilibili_login_session.py")]
    try:
        subprocess.Popen(
            command,
            cwd=agent_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            shell=False,
        )
    except OSError as exc:
        raise VideoAgentError(f"无法启动 B 站登录态采集：{exc}") from exc

    return {
        "started": True,
        "message": "已尝试打开 B 站登录页面。登录完成后点击“我已登录”。",
        "config": public_config(username),
    }


def complete_bilibili_login(username: str, wait_seconds: int = 20) -> dict:
    files = bilibili_login_files(username)
    files["done_file"].parent.mkdir(parents=True, exist_ok=True)
    files["done_file"].write_text("done", encoding="utf-8")

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        config = public_config(username)
        status = _read_login_status(username)
        if config.get("has_bilibili_state"):
            return {
                "saved": True,
                "status": status,
                "message": "B 站登录态已保存到账户信息。",
                "config": config,
            }
        if status.get("status") in {"error", "timeout"}:
            return {
                "saved": False,
                "status": status,
                "message": status.get("message") or "B 站登录态采集失败。",
                "config": config,
            }
        time.sleep(1)

    return {
        "saved": False,
        "status": _read_login_status(username),
        "message": "已发送保存指令，但暂未检测到登录态文件。请稍后刷新配置。",
        "config": public_config(username),
    }
