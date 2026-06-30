import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


class EmailConfigError(ValueError):
    pass


class EmailSendError(RuntimeError):
    pass


def _truthy(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _get_attachment_path(agent_root: Path, relative_path: str) -> Path:
    output_root = (agent_root / "output").resolve()
    file_path = (output_root / relative_path).resolve()
    if output_root not in file_path.parents:
        raise FileNotFoundError("非法附件路径。")
    if not file_path.exists() or file_path.suffix.lower() != ".txt":
        raise FileNotFoundError("生成文件不存在。")
    return file_path


def send_generated_file_email(agent_root: Path, relative_path: str, to_address: str) -> None:
    if not to_address or "@" not in to_address:
        raise EmailConfigError("收件邮箱不正确。")

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_address = os.getenv("SMTP_FROM", username).strip()
    use_tls = _truthy(os.getenv("SMTP_USE_TLS", "true"))
    use_ssl = _truthy(os.getenv("SMTP_USE_SSL", "false")) or port == 465

    missing = [
        name
        for name, value in {
            "SMTP_HOST": host,
            "SMTP_USERNAME": username,
            "SMTP_PASSWORD": password,
            "SMTP_FROM": from_address,
        }.items()
        if not value
    ]
    if missing:
        raise EmailConfigError("缺少邮件配置：" + ", ".join(missing))

    attachment_path = _get_attachment_path(agent_root, relative_path)
    content = attachment_path.read_text(encoding="utf-8")

    message = EmailMessage()
    message["Subject"] = f"AI 创作平台生成内容：{attachment_path.name}"
    message["From"] = from_address
    message["To"] = to_address
    message.set_content("附件是本次生成的 txt 文件。")
    message.add_attachment(
        content,
        subtype="plain",
        filename=attachment_path.name,
    )

    try:
        if use_ssl:
            smtp_context = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            smtp_context = smtplib.SMTP(host, port, timeout=30)

        with smtp_context as smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
    except OSError as exc:
        raise EmailSendError(str(exc)) from exc
    except smtplib.SMTPException as exc:
        raise EmailSendError(str(exc)) from exc
