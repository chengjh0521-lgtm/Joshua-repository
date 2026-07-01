# -*- coding: utf-8 -*-

import json
from pathlib import Path
from datetime import datetime

from config import CONFIG


def append_publish_task(video_info: dict, download_result: dict):
    """
    把下载完成的视频写入 publish_tasks.jsonl。
    后续上传程序读取这个文件。
    """

    if not download_result.get("success"):
        return False

    tasks_file = Path(CONFIG["publish_tasks_file"])

    task = {
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "channel_no": video_info.get("channel_no"),
        "channel_name": video_info.get("channel_name"),
        "source_channel_url": video_info.get("channel_url"),
        "douyin_collection": video_info.get("douyin_collection"),
        "source_video_id": video_info.get("video_id"),
        "source_video_title": video_info.get("title"),
        "source_video_url": video_info.get("url"),
        "source_published": video_info.get("published"),
        "bilibili_title": video_info.get("bilibili_title"),
        "download_output_dir": download_result.get("output_dir"),
        "download_title": download_result.get("title"),
        "download_uploader": download_result.get("uploader"),

        # 后续上传程序可以根据这个目录找 mp4
        "local_video_path": download_result.get("local_video_path"),

        "platforms": {
            "bilibili": {
                "enabled": CONFIG.get("publish_to_bilibili", False),
                "status": "pending",
                "uploaded_at": None,
                "publish_url": None,
            },
            "douyin": {
                "enabled": CONFIG.get("publish_to_douyin", False),
                "status": "pending",
                "uploaded_at": None,
                "publish_url": None,
            }
        }
    }

    with tasks_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")

    print(f"已写入发布任务：{tasks_file}")
    return True