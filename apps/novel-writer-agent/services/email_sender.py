from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

from pydantic import BaseModel

from config import PROJECT_ROOT


class EmailConfig(BaseModel):
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    sender_email: str = ""
    authorization_code: str = ""


def load_email_config(path: Path | None = None) -> EmailConfig:
    config_path = path or PROJECT_ROOT / "email_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Email config not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    config = EmailConfig(**data)
    if not config.sender_email or not config.authorization_code:
        raise ValueError("email_config.json must include sender_email and authorization_code before sending email.")
    return config


def send_email(*, to_email: str, subject: str, body: str, attachment_path: Path | None = None) -> None:
    config = load_email_config()
    message = EmailMessage()
    message["From"] = config.sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if attachment_path:
        content = attachment_path.read_text(encoding="utf-8")
        message.add_attachment(
            content.encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=attachment_path.name,
        )

    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
        smtp.login(config.sender_email, config.authorization_code)
        smtp.send_message(message)
