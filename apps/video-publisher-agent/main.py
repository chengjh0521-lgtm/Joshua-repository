# -*- coding: utf-8 -*-

import traceback
from datetime import datetime

from monitor_youtube import monitor_loop
from downloader import download_video
from config import CONFIG
from email_notifier import send_email_notification
from publish_task import append_publish_task


def build_fallback_result(platform: str, platform_name: str, error: Exception):
    """
    当某个平台上传脚本异常时，生成统一的失败结果。
    """
    return {
        "platform": platform,
        "platform_name": platform_name,
        "total": 1,
        "success": 0,
        "failed": 1,
        "skipped": 0,
        "details": [
            {
                "title": None,
                "channel_no": None,
                "channel_name": None,
                "source_url": None,
                "local_video_path": None,
                "status": "exception",
                "message": str(error),
            }
        ],
    }


def run_auto_publishers():
    """
    下载完成后自动执行 B站 / 抖音上传任务。

    注意：
    uploader_bilibili.py 和 uploader_douyin.py 需要都有 run_pending_uploads() 函数。
    如果某个上传器还没有返回 result_summary，也不影响主程序运行。
    """

    publish_results = []

    if not CONFIG.get("auto_publish", False):
        print("当前 auto_publish=False，不执行自动发布。")
        return publish_results

    # =========================
    # B站自动上传
    # =========================
    if CONFIG.get("auto_publish_bilibili", False):
        try:
            print("=" * 60)
            print("开始执行 B站自动上传任务")
            print("=" * 60)

            from uploader_bilibili import run_pending_uploads as run_bilibili_uploads

            bilibili_result = run_bilibili_uploads()

            if bilibili_result:
                publish_results.append(bilibili_result)
            else:
                publish_results.append({
                    "platform": "bilibili",
                    "platform_name": "B站",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "details": [
                        {
                            "title": None,
                            "channel_no": None,
                            "channel_name": None,
                            "source_url": None,
                            "local_video_path": None,
                            "status": "no_return",
                            "message": "B站上传脚本已执行，但没有返回结果。建议后续给 uploader_bilibili.py 补 result_summary。",
                        }
                    ],
                })

            print("B站自动上传任务执行完成")

        except Exception as e:
            print(f"B站自动上传异常：{e}")
            traceback.print_exc()

            publish_results.append(
                build_fallback_result(
                    platform="bilibili",
                    platform_name="B站",
                    error=e,
                )
            )

    # =========================
    # 抖音自动上传
    # =========================
    if CONFIG.get("auto_publish_douyin", False):
        try:
            print("=" * 60)
            print("开始执行抖音自动上传任务")
            print("=" * 60)

            from uploader_douyin import run_pending_uploads as run_douyin_uploads

            douyin_result = run_douyin_uploads()

            if douyin_result:
                publish_results.append(douyin_result)
            else:
                publish_results.append({
                    "platform": "douyin",
                    "platform_name": "抖音",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "details": [
                        {
                            "title": None,
                            "channel_no": None,
                            "channel_name": None,
                            "source_url": None,
                            "local_video_path": None,
                            "status": "no_return",
                            "message": "抖音上传脚本已执行，但没有返回结果。建议后续给 uploader_douyin.py 补 result_summary。",
                        }
                    ],
                })

            print("抖音自动上传任务执行完成")

        except Exception as e:
            print(f"抖音自动上传异常：{e}")
            traceback.print_exc()

            publish_results.append(
                build_fallback_result(
                    platform="douyin",
                    platform_name="抖音",
                    error=e,
                )
            )

    return publish_results


def build_publish_report_body(video_info: dict, download_result: dict, publish_results: list) -> str:
    """
    生成发布结果汇总邮件正文。
    这里直接写在 main.py 里，避免你还要额外新建 publish_report_email.py。
    """

    lines = []

    lines.append("YouTube 视频自动发布结果汇总")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("【视频信息】")
    lines.append(f"频道编号：{video_info.get('channel_no')}")
    lines.append(f"频道名称：{video_info.get('channel_name')}")
    lines.append(f"YouTube标题：{video_info.get('title')}")
    lines.append(f"YouTube链接：{video_info.get('url')}")
    lines.append(f"发布时间：{video_info.get('published')}")
    lines.append("")

    lines.append("【下载信息】")

    if download_result.get("success"):
        lines.append("下载状态：成功")
        lines.append(f"本地文件：{download_result.get('local_video_path')}")
        lines.append(f"下载目录：{download_result.get('output_dir')}")
    else:
        lines.append("下载状态：失败")
        lines.append(f"失败原因：{download_result.get('message')}")

    lines.append("")
    lines.append("【平台发布结果】")

    if not publish_results:
        lines.append("未执行平台上传任务。")
    else:
        for item in publish_results:
            if not item:
                continue

            platform_name = item.get("platform_name") or item.get("platform") or "未知平台"

            lines.append("")
            lines.append("-" * 40)
            lines.append(f"平台：{platform_name}")
            lines.append(f"任务数：{item.get('total', 0)}")
            lines.append(f"成功：{item.get('success', 0)}")
            lines.append(f"失败：{item.get('failed', 0)}")
            lines.append(f"跳过：{item.get('skipped', 0)}")

            details = item.get("details") or []

            if details:
                lines.append("明细：")

                for idx, detail in enumerate(details, 1):
                    lines.append(f"  {idx}. 标题：{detail.get('title')}")
                    lines.append(f"     频道：{detail.get('channel_no')} / {detail.get('channel_name')}")
                    lines.append(f"     状态：{detail.get('status')}")
                    lines.append(f"     说明：{detail.get('message')}")
                    lines.append(f"     来源：{detail.get('source_url')}")
                    lines.append(f"     文件：{detail.get('local_video_path')}")
            else:
                lines.append("明细：无")

    lines.append("")
    lines.append("=" * 50)
    lines.append("状态说明：")
    lines.append("filled_waiting_manual_submit：已上传并填写信息，等待人工确认发布。")
    lines.append("submitted_unknown_result：程序已点击发布按钮，但仍建议到平台后台确认。")
    lines.append("failed：上传失败。")
    lines.append("no_return：上传脚本执行了，但没有返回结构化结果。")

    return "\n".join(lines)


def send_publish_report_email(video_info: dict, download_result: dict, publish_results: list) -> bool:
    """
    发送发布结果汇总邮件。
    直接复用 config.py 里的邮箱配置。
    """

    if not CONFIG.get("email_notify_enabled", False):
        print("邮件通知未开启，跳过发布结果汇总邮件。")
        return False
    if CONFIG.get("video_notify_mode") != "update_publish":
        print("当前不是“更新与发布时均通知”模式，跳过发布结果汇总邮件。")
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header
        from email.utils import formataddr

        smtp_host = CONFIG["email_smtp_host"]
        smtp_port = CONFIG["email_smtp_port"]
        sender_email = CONFIG["email_sender"]
        sender_password = CONFIG["email_password"]
        receiver_email = CONFIG["email_receiver"]

        channel_name = video_info.get("channel_name") or "未知频道"
        title = video_info.get("title") or "未知标题"

        subject = f"自动发布结果：{channel_name} - {title}"

        body = build_publish_report_body(
            video_info=video_info,
            download_result=download_result,
            publish_results=publish_results,
        )

        message = MIMEText(body, "plain", "utf-8")
        message["From"] = formataddr(("YouTube Auto Publisher", sender_email))
        message["To"] = formataddr(("Receiver", receiver_email))
        message["Subject"] = str(Header(subject, "utf-8"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [receiver_email], message.as_string())

        print(f"发布结果汇总邮件发送成功：{receiver_email}")
        return True

    except Exception as e:
        print(f"发布结果汇总邮件发送失败：{e}")
        traceback.print_exc()
        return False


def on_new_video(video_info):
    """
    监测到 YouTube 新视频后的完整处理流程。
    """

    video_url = video_info["url"]
    title = video_info["title"]
    channel_no = video_info["channel_no"]
    channel_name = video_info["channel_name"]

    print("=" * 60)
    print("收到新视频信号")
    print(f"频道编号：{channel_no}")
    print(f"频道名称：{channel_name}")
    print(f"标题：{title}")
    print(f"链接：{video_url}")
    print("=" * 60)

    # 1. 发送新视频通知邮件
    try:
        send_email_notification(video_info)
    except Exception as e:
        print(f"新视频通知邮件发送异常：{e}")
        traceback.print_exc()

    # 2. 判断是否下载
    if not CONFIG.get("download_enabled", True):
        print("当前 download_enabled=False，只发送通知，不下载。")
        return

    # 3. 下载视频
    result = download_video(
        video_url=video_url,
        channel_no=channel_no,
    )

    if not result.get("success"):
        print("下载失败：")
        print(result.get("message"))

        # 下载失败也发一封汇总邮件
        send_publish_report_email(
            video_info=video_info,
            download_result=result,
            publish_results=[],
        )

        return

    print("下载成功")
    print(f"下载目录：{result.get('output_dir')}")
    print(f"视频文件：{result.get('local_video_path')}")

    # 4. 写入发布任务
    try:
        append_publish_task(video_info, result)
        print("发布任务已写入 publish_tasks.jsonl")
    except Exception as e:
        print(f"写入发布任务失败：{e}")
        traceback.print_exc()

        send_publish_report_email(
            video_info=video_info,
            download_result=result,
            publish_results=[
                {
                    "platform": "publish_task",
                    "platform_name": "发布任务写入",
                    "total": 1,
                    "success": 0,
                    "failed": 1,
                    "skipped": 0,
                    "details": [
                        {
                            "title": title,
                            "channel_no": channel_no,
                            "channel_name": channel_name,
                            "source_url": video_url,
                            "local_video_path": result.get("local_video_path"),
                            "status": "failed",
                            "message": str(e),
                        }
                    ],
                }
            ],
        )

        return

    # 5. 下载成功后自动执行 B站 / 抖音上传
    publish_results = run_auto_publishers()

    # 6. 发送发布结果汇总邮件
    send_publish_report_email(
        video_info=video_info,
        download_result=result,
        publish_results=publish_results,
    )


if __name__ == "__main__":
    monitor_loop(on_new_video)
