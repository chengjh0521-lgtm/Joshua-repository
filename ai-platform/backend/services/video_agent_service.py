import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .user_config_service import (
    bilibili_login_files,
    ensure_bilibili_state_target,
    list_video_channels,
    public_config,
    video_service_files,
    video_runtime_config,
)


ALLOWED_ACTIONS = {"status", "check-once", "monitor-loop", "upload-pending"}


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


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def video_monitor_status(username: str) -> dict:
    files = video_service_files(username)
    pid = _read_pid(files["pid_file"])
    running = bool(pid and _pid_running(pid))
    tail = ""
    if files["log_file"].exists():
        lines = files["log_file"].read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-80:])
    if pid and not running:
        files["pid_file"].unlink(missing_ok=True)
    return {
        "running": running,
        "pid": pid if running else None,
        "log_tail": tail,
    }


def start_video_monitor(project_root: Path, username: str) -> dict:
    config = public_config(username)
    if not list_video_channels(username):
        raise VideoAgentError("当前账户暂无监测频道，请先添加监测池。")
    if config.get("video_publish_mode") == "bilibili" and not config.get("has_bilibili_state"):
        raise VideoAgentError("发布到 B 站前，请先添加 B 站登录态文件。")

    current = video_monitor_status(username)
    if current["running"]:
        return {"started": False, "message": "视频监控服务已经在运行。", **current}

    agent_root = project_root / "apps" / "video-publisher-agent"
    runtime_config = video_runtime_config(username)
    files = video_service_files(username)
    files["stop_file"].unlink(missing_ok=True)
    files["log_file"].parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["VIDEO_AGENT_CONFIG"] = str(runtime_config)
    env["VIDEO_AGENT_STOP_FILE"] = str(files["stop_file"])

    log_handle = files["log_file"].open("a", encoding="utf-8")
    command = [sys.executable, str(agent_root / "runner.py"), "monitor-loop"]
    try:
        process = subprocess.Popen(
            command,
            cwd=agent_root,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            shell=False,
        )
    except OSError as exc:
        log_handle.close()
        raise VideoAgentError(f"无法启动视频持续监控服务：{exc}") from exc
    finally:
        try:
            log_handle.close()
        except Exception:
            pass

    files["pid_file"].write_text(str(process.pid), encoding="utf-8")
    status = video_monitor_status(username)
    return {"started": True, "message": "视频持续监控服务已启动。", **status}


def stop_video_monitor(username: str) -> dict:
    files = video_service_files(username)
    pid = _read_pid(files["pid_file"])
    files["stop_file"].write_text("stop", encoding="utf-8")

    if pid and _pid_running(pid):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, text=True, timeout=10)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    deadline = time.time() + 8
    while pid and time.time() < deadline:
        if not _pid_running(pid):
            break
        time.sleep(0.5)

    if pid and _pid_running(pid):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=10)
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    files["pid_file"].unlink(missing_ok=True)
    status = video_monitor_status(username)
    return {"stopped": True, "message": "视频持续监控服务已终止。", **status}


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
