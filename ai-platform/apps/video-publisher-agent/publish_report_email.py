# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from datetime import datetime

from config import CONFIG


def build_publish_report_body(video_info: dict, download_result: dict, publish_results: list) -> str:
    """
    生成发布结果汇总邮件正文。
    """

    lines = []

    lines.append("YouTube 视频自动发布结果汇总")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("【视频信息】")
    lines.append(f"频道编号：{video_info.get('channel_no')}")
    lines.append(f"频道名称：{video_info.get('channel_name')}")
    lines.append(f"YouTube标题：{video_info.get('title')}")
    lines.append(f"YouTube链接：{video_info.get('url')}")
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
    lines.append("=" * 40)
    lines.append("说明：")
    lines.append("如果平台状态为 filled_waiting_manual_submit，表示已上传并填写信息，但未自动点击最终发布。")
    lines.append("如果平台状态为 submitted_unknown_result，表示程序已点击发布按钮，但仍建议到平台后台确认。")

    return "\n".join(lines)


def send_publish_report_email(video_info: dict, download_result: dict, publish_results: list) -> bool:
    """
    发送发布结果汇总邮件。
    复用 config.py 里的邮箱配置。
    """

    if not CONFIG.get("email_notify_enabled", False):
        print("邮件通知未开启，跳过发布结果邮件。")
        return False

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

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [receiver_email], message.as_string())

        print(f"发布结果汇总邮件发送成功：{receiver_email}")
        return True

    except Exception as e:
        print(f"发布结果汇总邮件发送失败：{e}")
        return False