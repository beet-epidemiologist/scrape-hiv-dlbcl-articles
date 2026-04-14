from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from src.config import Settings


def send_email_if_configured(settings: Settings, markdown_file: Path) -> bool:
    if not all([
        settings.email_host,
        settings.email_port,
        settings.email_user,
        settings.email_password,
        settings.email_to,
    ]):
        return False

    content = markdown_file.read_text(encoding="utf-8")
    main_content = "\n".join(content.splitlines()[:200])

    msg = EmailMessage()
    msg["Subject"] = "HIV/DLBCL 每日文献监测日报"
    msg["From"] = settings.email_user
    msg["To"] = settings.email_to
    msg.set_content(main_content)

    with smtplib.SMTP(settings.email_host, settings.email_port, timeout=30) as server:
        server.starttls()
        server.login(settings.email_user, settings.email_password)
        server.send_message(msg)
    return True
