# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from email.header import Header

from config import CONFIG


def send_email_notification(video_info: dict):
    """
    发送 YouTube 更新通知邮件
    """

    if not CONFIG.get("email_notify_enabled", False):
        print("邮件通知未开启，跳过。")
        return False

    smtp_host = CONFIG["email_smtp_host"]
    smtp_port = CONFIG["email_smtp_port"]
    sender_email = CONFIG["email_sender"]
    sender_password = CONFIG["email_password"]
    receiver_email = CONFIG["email_receiver"]

    title = video_info.get("title", "未知标题")
    url = video_info.get("url", "")
    published = video_info.get("published", "")

    subject = f"YouTube频道更新：{title}"

    body = f"""检测到 YouTube 频道更新：

标题：{title}

链接：{url}

发布时间：{published}

程序已开始进入自动下载流程。
"""

    message = MIMEText(body, "plain", "utf-8")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = Header(subject, "utf-8")

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [receiver_email], message.as_string())

        print(f"邮件通知发送成功：{receiver_email}")
        return True

    except Exception as e:
        print(f"邮件通知发送失败：{e}")
        return False