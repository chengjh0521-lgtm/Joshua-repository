import json
import re
from pathlib import Path

from fastapi import UploadFile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
USERS_ROOT = PROJECT_ROOT / "backend" / "data" / "users"


def safe_username(username: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", username).strip("._")
    return cleaned or "user"


def user_root(username: str) -> Path:
    root = USERS_ROOT / safe_username(username)
    root.mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    (root / "video_runtime").mkdir(parents=True, exist_ok=True)
    return root


def config_path(username: str) -> Path:
    return user_root(username) / "config.json"


def default_config() -> dict:
    return {
        "email_receiver": "",
        "bilibili_state_file": "",
        "douyin_state_file": "",
        "youtube_cookie_file": "",
        "auto_publish": False,
        "auto_publish_bilibili": False,
        "auto_publish_douyin": False,
    }


def load_config(username: str) -> dict:
    path = config_path(username)
    if not path.exists():
        config = default_config()
        save_config(username, config)
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    return {**default_config(), **data}


def save_config(username: str, config: dict) -> dict:
    root = user_root(username)
    merged = {**default_config(), **config}
    path = root / "config.json"
    temp_path = root / "config.json.tmp"
    temp_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return merged


def public_config(username: str) -> dict:
    config = load_config(username)
    return {
        "email_receiver": config.get("email_receiver", ""),
        "auto_publish": bool(config.get("auto_publish", False)),
        "auto_publish_bilibili": bool(config.get("auto_publish_bilibili", False)),
        "auto_publish_douyin": bool(config.get("auto_publish_douyin", False)),
        "has_bilibili_state": bool(config.get("bilibili_state_file")) and Path(config["bilibili_state_file"]).exists(),
        "has_douyin_state": bool(config.get("douyin_state_file")) and Path(config["douyin_state_file"]).exists(),
        "has_youtube_cookie": bool(config.get("youtube_cookie_file")) and Path(config["youtube_cookie_file"]).exists(),
    }


def update_config(username: str, payload: dict) -> dict:
    config = load_config(username)
    for key in ("email_receiver", "auto_publish", "auto_publish_bilibili", "auto_publish_douyin"):
        if key in payload:
            config[key] = payload[key]
    return save_config(username, config)


async def save_upload(username: str, key: str, upload: UploadFile) -> dict:
    allowed = {
        "bilibili_state": ("bilibili_state_file", "bilibili_state.json"),
        "douyin_state": ("douyin_state_file", "douyin_state.json"),
        "youtube_cookie": ("youtube_cookie_file", "cookies.txt"),
    }
    if key not in allowed:
        raise ValueError("不支持的文件类型。")

    config_key, filename = allowed[key]
    target = user_root(username) / "uploads" / filename
    content = await upload.read()
    target.write_bytes(content)

    config = load_config(username)
    config[config_key] = str(target.resolve())
    save_config(username, config)
    return public_config(username)


def video_runtime_config(username: str) -> Path:
    root = user_root(username)
    runtime_dir = root / "video_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(username)

    runtime_config = {
        "runtime_dir": str(runtime_dir.resolve()),
        "email_receiver": config.get("email_receiver", ""),
        "email_notify_enabled": bool(config.get("email_receiver")),
        "download_enabled": True,
        "auto_publish": bool(config.get("auto_publish", False)),
        "auto_publish_bilibili": bool(config.get("auto_publish_bilibili", False)),
        "auto_publish_douyin": bool(config.get("auto_publish_douyin", False)),
        "publish_to_bilibili": bool(config.get("auto_publish_bilibili", False)),
        "bilibili_enabled": bool(config.get("auto_publish_bilibili", False)),
        "publish_to_douyin": bool(config.get("auto_publish_douyin", False)),
        "douyin_enabled": bool(config.get("auto_publish_douyin", False)),
        "bilibili_state_file": config.get("bilibili_state_file", ""),
        "douyin_state_file": config.get("douyin_state_file", ""),
        "youtube_cookie_file": config.get("youtube_cookie_file", ""),
        "state_file": str((runtime_dir / "state.json").resolve()),
        "failed_file": str((runtime_dir / "failed.txt").resolve()),
        "publish_tasks_file": str((runtime_dir / "publish_tasks.json").resolve()),
        "base_output_dir": str((runtime_dir / "youtube素材库").resolve()),
    }
    path = runtime_dir / "config.json"
    path.write_text(json.dumps(runtime_config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
