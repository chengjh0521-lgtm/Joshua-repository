# -*- coding: utf-8 -*-

import json
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import CONFIG


def load_state() -> Dict[str, Any]:
    state_file = Path(CONFIG["state_file"])

    if not state_file.exists():
        return {
            "channels": {}
        }

    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {
            "channels": {}
        }


def save_state(state: Dict[str, Any]) -> None:
    state_file = Path(CONFIG["state_file"])
    state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_latest_video(channel: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    使用 yt-dlp 获取单个频道最新视频。
    适合 RSS 不稳定或 RSS 返回 404 的频道。
    """

    channel_url = channel["url"]
    channel_no = channel["channel_no"]
    channel_name = channel.get("name", channel_no)

    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=web,android",
        "--flat-playlist",
        "--playlist-end", "1",
        "--print", "%(id)s|||%(title)s|||%(url)s|||%(timestamp>%Y-%m-%d %H:%M:%S)s",
        channel_url,
    ]

    print(f"正在检测频道：{channel_no} - {channel_name}")
    print(f"频道地址：{channel_url}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print("yt-dlp 检测频道失败：")
            print(result.stderr.strip())
            return None

        output = result.stdout.strip()

        if not output:
            print("yt-dlp 没有读取到频道视频。")
            return None

        first_line = output.splitlines()[0]
        parts = first_line.split("|||")

        if len(parts) < 3:
            print(f"yt-dlp 输出格式异常：{first_line}")
            return None

        video_id = parts[0].strip()
        title = parts[1].strip()
        url = parts[2].strip()
        published = parts[3].strip() if len(parts) >= 4 else ""

        if url.startswith("http"):
            video_url = url
        else:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            "channel_no": channel_no,
            "channel_name": channel_name,
            "channel_url": channel_url,
            "video_id": video_id,
            "title": title,
            "url": video_url,
            "published": published,
            "bilibili_title": channel.get("bilibili_title"),
            "douyin_collection": channel.get("douyin_collection"),
        }

    except subprocess.TimeoutExpired:
        print(f"频道检测超时：{channel_no} - {channel_name}")
        return None

    except Exception as e:
        print(f"频道检测异常：{channel_no} - {channel_name} - {e}")
        return None


def check_channel_once(channel: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    检测单个频道是否更新。
    """

    if not channel.get("enabled", True):
        print(f"频道已禁用，跳过：{channel.get('channel_no')}")
        return None

    state = load_state()

    channel_no = channel["channel_no"]
    channels_state = state.setdefault("channels", {})
    channel_state = channels_state.setdefault(channel_no, {
        "last_video_id": None,
        "processed_video_ids": []
    })

    latest_video = get_latest_video(channel)

    if not latest_video:
        return None

    latest_video_id = latest_video["video_id"]
    processed = set(channel_state.get("processed_video_ids", []))

    if latest_video_id in processed:
        print(f"无更新：{channel_no} - {latest_video['title']}")
        return None

    print("发现新视频：")
    print(f"频道编号：{channel_no}")
    print(f"频道名称：{latest_video['channel_name']}")
    print(f"标题：{latest_video['title']}")
    print(f"链接：{latest_video['url']}")

    channel_state["last_video_id"] = latest_video_id
    channel_state.setdefault("processed_video_ids", []).append(latest_video_id)
    channel_state["processed_video_ids"] = channel_state["processed_video_ids"][-300:]

    save_state(state)

    return latest_video


def check_all_channels_once() -> List[Dict[str, str]]:
    """
    检测所有频道。
    返回本轮发现的新视频列表。
    """

    new_videos = []

    for channel in CONFIG["youtube_channels"]:
        try:
            new_video = check_channel_once(channel)

            if new_video:
                new_videos.append(new_video)

        except Exception as e:
            print(f"检测频道异常：{channel.get('channel_no')} - {e}")

        # 多频道之间稍微停一下，降低风控
        time.sleep(5)

    return new_videos


def monitor_loop(on_new_video):
    print("YouTube 多频道监测启动")
    print(f"频道数量：{len(CONFIG['youtube_channels'])}")
    print(f"检测频率：{CONFIG['check_interval_seconds']} 秒")

    while True:
        try:
            new_videos = check_all_channels_once()

            for video_info in new_videos:
                on_new_video(video_info)

        except Exception as e:
            print(f"监测主循环异常：{e}")

        print(f"本轮检测完成，等待 {CONFIG['check_interval_seconds']} 秒")
        time.sleep(CONFIG["check_interval_seconds"])
