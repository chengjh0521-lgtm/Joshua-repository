# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_CONFIG_FILE = Path(os.getenv("VIDEO_AGENT_CONFIG", BASE_DIR / "runtime" / "config.json"))


DEFAULT_CHANNELS = [
    {
        "channel_no": "001",
        "name": "小黑爱跳舞",
        "url": "https://www.youtube.com/channel/UCoh8sf8c0r6pQ49NQk4xNhA/shorts",
        "enabled": True,
        "bilibili_title": "来自非洲的一群伙伴",
        "douyin_collection": "小黑爱跳舞",
    },
    {
        "channel_no": "002",
        "name": "小黑爱手工",
        "url": "https://www.youtube.com/@TowhidFromBangladesh/videos",
        "enabled": True,
        "bilibili_title": "小黑做点手工补贴家用",
        "douyin_collection": "小黑爱手工",
    },
]


def _load_runtime_config() -> dict:
    if not RUNTIME_CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(RUNTIME_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _path(value: str | None, fallback: Path) -> Path:
    if not value:
        return fallback
    return Path(value)


_runtime = _load_runtime_config()
_runtime_dir = _path(_runtime.get("runtime_dir"), BASE_DIR / "runtime")
_runtime_dir.mkdir(parents=True, exist_ok=True)

CONFIG = {
    "youtube_channels": _runtime.get("youtube_channels") or DEFAULT_CHANNELS,
    "email_notify_enabled": bool(_runtime.get("email_notify_enabled", False)),
    "deno_path": _runtime.get("deno_path", "/root/.deno/bin/deno"),
    "email_smtp_host": _runtime.get("email_smtp_host", os.getenv("SMTP_HOST", "")),
    "email_smtp_port": int(_runtime.get("email_smtp_port", os.getenv("SMTP_PORT", "465"))),
    "email_sender": _runtime.get("email_sender", os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", ""))),
    "email_password": _runtime.get("email_password", os.getenv("SMTP_PASSWORD", "")),
    "email_receiver": _runtime.get("email_receiver", ""),
    "check_interval_seconds": int(_runtime.get("check_interval_seconds", 600)),
    "state_file": _path(_runtime.get("state_file"), _runtime_dir / "state.json"),
    "failed_file": _path(_runtime.get("failed_file"), _runtime_dir / "failed.txt"),
    "base_output_dir": _path(_runtime.get("base_output_dir"), _runtime_dir / "youtube素材库"),
    "download_enabled": bool(_runtime.get("download_enabled", True)),
    "auto_publish": bool(_runtime.get("auto_publish", False)),
    "auto_publish_bilibili": bool(_runtime.get("auto_publish_bilibili", False)),
    "auto_publish_douyin": bool(_runtime.get("auto_publish_douyin", False)),
    "publish_to_bilibili": bool(_runtime.get("publish_to_bilibili", False)),
    "bilibili_enabled": bool(_runtime.get("bilibili_enabled", False)),
    "bilibili_state_file": _path(_runtime.get("bilibili_state_file"), _runtime_dir / "bilibili_state.json"),
    "publish_tasks_file": _path(_runtime.get("publish_tasks_file"), _runtime_dir / "publish_tasks.json"),
    "bilibili_headless": bool(_runtime.get("bilibili_headless", True)),
    "bilibili_upload_url": _runtime.get("bilibili_upload_url", "https://member.bilibili.com/platform/upload/video/frame"),
    "bilibili_auto_submit": bool(_runtime.get("bilibili_auto_submit", False)),
    "bilibili_default_tags": _runtime.get("bilibili_default_tags", ["搞笑", "短视频"]),
    "bilibili_desc_suffix": _runtime.get("bilibili_desc_suffix", ""),
    "publish_to_douyin": bool(_runtime.get("publish_to_douyin", False)),
    "douyin_enabled": bool(_runtime.get("douyin_enabled", False)),
    "douyin_upload_url": _runtime.get("douyin_upload_url", "https://creator.douyin.com/creator-micro/content/upload"),
    "douyin_state_file": _path(_runtime.get("douyin_state_file"), _runtime_dir / "douyin_state.json"),
    "douyin_headless": bool(_runtime.get("douyin_headless", True)),
    "douyin_auto_submit": bool(_runtime.get("douyin_auto_submit", False)),
    "douyin_default_tags": _runtime.get("douyin_default_tags", ["国外视频", "搞笑", "短视频"]),
    "douyin_desc_suffix": _runtime.get("douyin_desc_suffix", ""),
    "douyin_collection_map": _runtime.get("douyin_collection_map", {}),
    "youtube_cookie_file": _runtime.get("youtube_cookie_file", ""),
    "ffmpeg_location": _runtime.get("ffmpeg_location", "/usr/bin"),
}
