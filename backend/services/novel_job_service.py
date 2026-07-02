from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from . import auth_service
from .email_service import EmailConfigError, EmailSendError, send_generated_file_email
from .novel_service import build_command, run_novel_agent
from .user_config_service import user_root


_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _jobs_root(username: str) -> Path:
    root = user_root(username) / "novel" / "jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_path(username: str, job_id: str) -> Path:
    return _jobs_root(username) / f"{job_id}.json"


def _save_job(username: str, job: dict) -> dict:
    path = _job_path(username, job["id"])
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return job


def _load_job(username: str, job_id: str) -> dict:
    path = _job_path(username, job_id)
    if not path.exists():
        raise FileNotFoundError("任务不存在。")
    return json.loads(path.read_text(encoding="utf-8"))


def _update_job(username: str, job_id: str, **changes: object) -> dict:
    with _LOCK:
        job = _load_job(username, job_id)
        job.update(changes)
        job["updated_at"] = _now()
        return _save_job(username, job)


def start_novel_job(
    *,
    username: str,
    agent_root: Path,
    payload: dict,
    selected_state: dict,
    output_agent_root: Path,
    extra_env: dict[str, str],
    consume_quota_on_success: bool,
    send_email: bool,
    email_to: str | None,
) -> dict:
    build_command(agent_root, payload)

    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "username": username,
        "state_id": selected_state["id"],
        "status": "queued",
        "created_at": _now(),
        "updated_at": _now(),
        "completed_at": "",
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "latest_file": None,
        "state": selected_state,
        "email": {"requested": send_email, "sent": False, "message": ""},
        "account": None,
    }
    with _LOCK:
        _save_job(username, job)

    thread = threading.Thread(
        target=_run_job,
        kwargs={
            "username": username,
            "job_id": job_id,
            "agent_root": agent_root,
            "payload": payload,
            "output_agent_root": output_agent_root,
            "extra_env": extra_env,
            "consume_quota_on_success": consume_quota_on_success,
            "send_email": send_email,
            "email_to": email_to,
        },
        name=f"novel-job-{job_id}",
        daemon=True,
    )
    thread.start()
    return job


def get_novel_job(username: str, job_id: str) -> dict:
    with _LOCK:
        return _load_job(username, job_id)


def _run_job(
    *,
    username: str,
    job_id: str,
    agent_root: Path,
    payload: dict,
    output_agent_root: Path,
    extra_env: dict[str, str],
    consume_quota_on_success: bool,
    send_email: bool,
    email_to: str | None,
) -> None:
    _update_job(username, job_id, status="running")
    try:
        result = run_novel_agent(
            agent_root,
        payload,
        output_agent_root=output_agent_root,
        extra_env=extra_env,
        timeout_seconds=3600,
    )
    except Exception as exc:
        _update_job(
            username,
            job_id,
            status="failed",
            completed_at=_now(),
            returncode=1,
            stderr=f"后台任务异常：{exc}",
        )
        return
    latest_file = result.get("latest_file")
    if latest_file:
        latest_file["state_id"] = payload.get("state_id")

    email_result = {"requested": send_email, "sent": False, "message": ""}
    if send_email and result.get("returncode") == 0 and latest_file:
        try:
            send_generated_file_email(
                agent_root=output_agent_root,
                relative_path=latest_file["relative_path"],
                to_address=email_to or "",
            )
            email_result = {
                "requested": True,
                "sent": True,
                "message": f"已发送到 {email_to}",
            }
        except (EmailConfigError, EmailSendError, FileNotFoundError) as exc:
            email_result = {
                "requested": True,
                "sent": False,
                "message": f"邮件未发送：{exc}",
            }

    account = None
    if consume_quota_on_success and result.get("returncode") == 0:
        try:
            account = {"authenticated": True, **auth_service.consume_quota(username)}
        except Exception as exc:
            result["stderr"] = "\n".join(
                part for part in [result.get("stderr", ""), f"配额更新失败：{exc}"] if part
            )

    status = "succeeded" if result.get("returncode") == 0 else "failed"
    _update_job(
        username,
        job_id,
        status=status,
        completed_at=_now(),
        returncode=result.get("returncode"),
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        latest_file=latest_file,
        email=email_result,
        account=account,
    )
