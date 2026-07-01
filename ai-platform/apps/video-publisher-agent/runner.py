# -*- coding: utf-8 -*-

import argparse
import json
import traceback
from pathlib import Path

from config import CONFIG


def configure_downloader() -> None:
    import downloader

    downloader.CONFIG["base_output_dir"] = str(CONFIG["base_output_dir"])
    downloader.CONFIG["cookiefile"] = CONFIG.get("youtube_cookie_file") or ""
    downloader.CONFIG["ffmpeg_location"] = CONFIG.get("ffmpeg_location") or "/usr/bin"


def file_status() -> dict:
    return {
        "youtube_cookie_file": {
            "path": str(CONFIG.get("youtube_cookie_file") or ""),
            "exists": bool(CONFIG.get("youtube_cookie_file")) and Path(CONFIG["youtube_cookie_file"]).exists(),
        },
        "bilibili_state_file": {
            "path": str(CONFIG["bilibili_state_file"]),
            "exists": Path(CONFIG["bilibili_state_file"]).exists(),
        },
        "douyin_state_file": {
            "path": str(CONFIG["douyin_state_file"]),
            "exists": Path(CONFIG["douyin_state_file"]).exists(),
        },
        "publish_tasks_file": {
            "path": str(CONFIG["publish_tasks_file"]),
            "exists": Path(CONFIG["publish_tasks_file"]).exists(),
        },
        "base_output_dir": {
            "path": str(CONFIG["base_output_dir"]),
            "exists": Path(CONFIG["base_output_dir"]).exists(),
        },
    }


def status() -> int:
    payload = {
        "agent": "video-publisher-agent",
        "email_receiver": CONFIG.get("email_receiver", ""),
        "download_enabled": CONFIG.get("download_enabled", False),
        "auto_publish": CONFIG.get("auto_publish", False),
        "auto_publish_bilibili": CONFIG.get("auto_publish_bilibili", False),
        "auto_publish_douyin": CONFIG.get("auto_publish_douyin", False),
        "channels": len(CONFIG.get("youtube_channels", [])),
        "files": file_status(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def check_once() -> int:
    configure_downloader()
    from monitor_youtube import check_all_channels_once
    from main import on_new_video

    new_videos = check_all_channels_once()
    print(f"本轮发现新视频：{len(new_videos)}")
    for video_info in new_videos:
        on_new_video(video_info)
    return 0


def upload_pending() -> int:
    from main import run_auto_publishers

    results = run_auto_publishers()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="video-publisher-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("check-once")
    sub.add_parser("upload-pending")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "status":
            return status()
        if args.command == "check-once":
            return check_once()
        if args.command == "upload-pending":
            return upload_pending()
    except Exception as exc:
        print(f"video-publisher-agent 执行失败：{exc}")
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
