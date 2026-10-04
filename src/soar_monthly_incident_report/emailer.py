"""SMTP delivery of the rendered report."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .config import MailSettings


def build_message(
    settings: MailSettings, html_body: str, attachment: Path | None = None
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = settings.subject
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)
    if settings.cc:
        message["Cc"] = ", ".join(settings.cc)

    message.set_content(
        "The monthly incident report is attached. Open this mail in an HTML-capable client to view it inline."
    )
    message.add_alternative(html_body, subtype="html")

    if attachment is not None:
        message.add_attachment(
            attachment.read_bytes(), maintype="application", subtype="pdf", filename=attachment.name
        )
    return message


def send_report(settings: MailSettings, html_body: str, attachment: Path | None = None) -> None:
    message = build_message(settings, html_body, attachment)
    with smtplib.SMTP(settings.host, settings.port, timeout=60) as smtp:
        if settings.use_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.username:
            smtp.login(settings.username, settings.password or "")
        smtp.send_message(message)
