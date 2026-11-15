import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as StdEmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


# Filled only when EMAIL_BACKEND=memory (tests read verification/reset links here).
OUTBOX: list[EmailMessage] = []


def _send_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    mail = StdEmailMessage()
    mail["From"] = settings.smtp_from
    mail["To"] = message.to
    mail["Subject"] = message.subject
    mail.set_content(message.body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(mail)


async def send_email(message: EmailMessage) -> None:
    """Never raises: email problems must not fail the request that triggered them."""
    settings = get_settings()
    if settings.email_backend == "memory":
        OUTBOX.append(message)
        return
    if settings.email_backend == "console":
        if settings.environment == "production":
            logger.warning("EMAIL_BACKEND=console in production: email dropped")
        else:
            logger.info("email to=%s subject=%s\n%s", message.to, message.subject, message.body)
        return
    try:
        await asyncio.to_thread(_send_smtp, message)
    except Exception:
        logger.exception("failed to send email subject=%s", message.subject)
