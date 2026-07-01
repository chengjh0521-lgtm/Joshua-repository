# -*- coding: utf-8 -*-
"""
yt_dlp_click_run.py

使用方式：
1. 安装依赖：
   pip install -U yt-dlp

2. 安装 FFmpeg：
   winget install Gyan.FFmpeg

3. 修改下面 CONFIG 里的参数

4. 在 VS Code / PyCharm 里直接点击运行
"""

from pathlib import Path
import yt_dlp
from datetime import datetime


# =========================
# 只需要改这里
# =========================

CONFIG = {
    # 下载模式：
    # "single" = 下载单个视频
    # "batch"  = 批量下载 urls.txt 里的视频
    "mode": "single",

    # 单个视频链接，mode = "single" 时使用
    "url": "https://www.youtube.com/shorts/N2Dkpz_Qlkk",

    # 批量链接文件，mode = "batch" 时使用
    # 一行一个 YouTube 链接
    "url_file": "urls.txt",

    # 下载保存目录
    # 基础保存目录
    "base_output_dir": "youtube素材库",

    # 是否按当前时间创建子文件夹
    "use_time_folder": True,

    # 最大清晰度：720 / 1080 / 1440 / 2160
    "max_height": 1080,

    # 是否下载字幕
    "download_subtitles": False,

    # 是否下载自动字幕
    "download_auto_subtitles": False,

    # 字幕语言
    # zh-Hans = 简体中文
    # zh-Hant = 繁体中文
    # zh = 中文
    # en = 英文
    "subtitle_languages": ["zh-Hans", "zh-Hant", "zh", "en"],

    # 是否下载缩略图
    "download_thumbnail": True,

    # 是否保存视频信息 json
    "save_info_json": True,

    # 是否只下载单个视频，不下载播放列表
    "no_playlist": True,

    # 输出格式：mp4 推荐
    "merge_format": "mp4",

    # 文件名模板
    # 默认保存为：下载目录 / 频道名 / 视频标题-视频ID.mp4
    "filename_template": "%(uploader)s/%(title).120s-%(id)s.%(ext)s",
    "sleep_before_each_video_min": 8,
    "sleep_before_each_video_max": 20,

    # yt-dlp 每次请求之间等待
    "sleep_interval_requests": 3,

    # yt-dlp 下载前随机等待
    "sleep_interval": 5,
    "max_sleep_interval": 15,
    "cookiefile": "cookies.txt",
    # 下载限速，避免太像机器请求
    # 例如 "2M" = 每秒 2MB；不想限速就填 None
    "rate_limit": "2M",
}
RUN_TIME_FOLDER = datetime.now().strftime("%Y-%m-%d_%H%M")
def get_output_dir(channel_no: str):
    """
    下载目录：
    youtube素材库/频道编号/下载日期/
    例如：
    youtube素材库/ch001/2026-06-16/
    """
    today = datetime.now().strftime("%Y-%m-%d")

    base_dir = Path(CONFIG["base_output_dir"])
    output_dir = base_dir / channel_no / today

    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir
# =========================
# 以下代码一般不用改
# =========================

def read_urls_from_file(file_path: str):
    """读取 urls.txt，一行一个链接，自动忽略空行和 # 注释"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"找不到批量链接文件：{file_path}")

    urls = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()

            if not url:
                continue

            if url.startswith("#"):
                continue

            urls.append(url)

    return urls


def progress_hook(status):
    """下载进度显示"""
    if status.get("status") == "downloading":
        percent = status.get("_percent_str", "").strip()
        speed = status.get("_speed_str", "").strip()
        eta = status.get("_eta_str", "").strip()

        print(f"\r下载中：{percent} | 速度：{speed} | 剩余：{eta}", end="", flush=True)

    elif status.get("status") == "finished":
        print("\n下载完成，正在合并音视频...")


def build_ydl_options(output_dir):
    """构建 yt-dlp 下载参数"""
    max_height = CONFIG["max_height"]

    ydl_options = {
        "outtmpl": str(output_dir / CONFIG["filename_template"]),

        # 关键：优先 mp4 + m4a，失败再降级
        "format": (
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]/"
            "best"
        ),
        "file_access_retries": 10,
        "merge_output_format": CONFIG["merge_format"],

        # 关键：只下载当前视频，不下载 playlist
        "noplaylist": True,
        "remote_components": {"ejs:github"},
        # Avoid the YouTube TV client for Shorts; it can return
        # "content is not available on this app" even when the video is playable.
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"]
            }
        },
        "cookiefile": CONFIG.get("cookiefile") or None,
        # 如果你本地电脑有梯子，且 PowerShell 里 Proxy map 是 127.0.0.1:12334
        # 就加这一行；如果不是这个端口，改成你的实际代理端口
        "proxy": None,

        # 先不要启用 cookiefile，等普通下载跑通后再加
        # "cookiefile": r"C:\Users\1\cookies.txt",

        "windowsfilenames": True,
        "continuedl": True,
        "ignoreerrors": False,

        # 打开详细日志，方便判断脚本到底用的是什么参数
        "verbose": True,

        # 延时和重试
        "sleep_interval_requests": 3,
        "sleep_interval": 5,
        "max_sleep_interval": 15,
        "retries": 10,
        "fragment_retries": 10,

        # 限速
        "ratelimit": 2*1024*1024,

        # 强制 IPv4
        "force_ipv4": True,
        "ffmpeg_location": "/usr/bin",
        # "writesubtitles": True,
        # "writeautomaticsub": True,
        # "subtitleslangs": ["zh", "en"],
        # "subtitlesformat": "srt/best",

        # 元信息
        "writethumbnail": True,
        "writeinfojson": True,
    }
    if CONFIG.get("proxy"):
        ydl_options["proxy"] = CONFIG["proxy"]

    if CONFIG.get("ffmpeg_location"):
        ydl_options["ffmpeg_location"] = CONFIG["ffmpeg_location"]

    if CONFIG.get("deno_path"):
        ydl_options["js_runtimes"] = {
            "deno": {
                "path": CONFIG["deno_path"]
            }
        }
    # 下载缩略图
    if CONFIG["download_thumbnail"]:
        ydl_options["writethumbnail"] = True

    # 保存视频信息 json
    if CONFIG["save_info_json"]:
        ydl_options["writeinfojson"] = True

    # 字幕设置
    if CONFIG["download_subtitles"]:
        ydl_options["writesubtitles"] = True
        ydl_options["subtitleslangs"] = CONFIG["subtitle_languages"]
        ydl_options["subtitlesformat"] = "srt/best"

    # 自动字幕设置
    if CONFIG["download_auto_subtitles"]:
        ydl_options["writeautomaticsub"] = True
        ydl_options["subtitleslangs"] = CONFIG["subtitle_languages"]
        ydl_options["subtitlesformat"] = "srt/best"

    return ydl_options


def get_download_urls():
    """根据 CONFIG 获取要下载的链接"""
    mode = CONFIG["mode"]

    if mode == "single":
        url = CONFIG["url"].strip()

        if not url or "xxxx" in url:
            raise ValueError("请先在 CONFIG['url'] 里填写真实 YouTube 视频链接。")

        return [url]

    if mode == "batch":
        return read_urls_from_file(CONFIG["url_file"])

    raise ValueError("CONFIG['mode'] 只能填写 'single' 或 'batch'。")


def download():
    """执行下载"""
    urls = get_download_urls()

    if not urls:
        print("没有找到需要下载的视频链接。")
        return

    print(f"本次准备下载 {len(urls)} 个视频。")
    print(f"最高画质：{CONFIG['max_height']}P")
    print("-" * 50)

    ydl_options = build_ydl_options()

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        for index, url in enumerate(urls, start=1):
            print(f"\n[{index}/{len(urls)}] 开始下载：")
            print(url)

            try:
                ydl.download([url])
            except Exception as e:
                print(f"\n下载失败：{url}")
                print(f"错误信息：{e}")

    print("\n全部任务处理完成。")

def download_video(video_url: str, channel_no: str = "unknown") -> dict:
    output_dir = get_output_dir(channel_no)
    ydl_options = build_ydl_options(output_dir)

    print("=" * 60)
    print("开始下载视频")
    print(f"频道编号：{channel_no}")
    print(f"链接：{video_url}")
    print(f"保存目录：{output_dir}")
    print("=" * 60)

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(video_url, download=True)

        local_video_file = find_latest_video_file(output_dir)

        return {
            "success": True,
            "video_id": info.get("id"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "channel_no": channel_no,
            "url": video_url,
            "output_dir": str(output_dir),
            "local_video_path": str(local_video_file) if local_video_file else None,
            "message": "下载成功",
        }

    except Exception as e:
        return {
            "success": False,
            "video_id": None,
            "title": None,
            "uploader": None,
            "channel_no": channel_no,
            "url": video_url,
            "output_dir": str(output_dir),
            "message": str(e),
        }

def find_latest_video_file(output_dir: Path):
    """
    在下载目录里查找最新的视频文件。
    """

    video_exts = [".mp4", ".mkv", ".webm"]

    files = []

    for ext in video_exts:
        files.extend(output_dir.rglob(f"*{ext}"))

    # 排除未完成文件
    files = [
        f for f in files
        if not str(f).endswith(".part")
    ]

    if not files:
        return None

    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    return latest_file
if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=8lWAJ1DL2sA"
    result = download_video(test_url)
    print(result)
