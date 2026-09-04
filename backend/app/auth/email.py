"""Provider-agnostic email sending.

Two adapters:
  - "console" (default, dev-safe): logs the email instead of sending it, and
    returns delivered=False. Never claims a real email was sent.
  - "smtp": sends via a real SMTP server using SMTP_* settings. Only used
    when EMAIL_PROVIDER=smtp is explicitly configured.

Callers (app.auth.service) must use the returned `delivered` flag to decide
what to tell the user - e.g. "if that address is registered, we've emailed
a reset link" is only accurate framing when a real provider is configured;
in console mode the honest response instead surfaces that no real email
service is configured (see docs/AUTHENTICATION.md).
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.settings import (
    EMAIL_FROM_ADDRESS,
    EMAIL_PROVIDER,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    delivered: bool
    provider: str
    detail: str


def send_email(to_address: str, subject: str, body: str) -> EmailSendResult:
    if EMAIL_PROVIDER == "smtp":
        return _send_via_smtp(to_address, subject, body)
    return _send_via_console(to_address, subject, body)


def _send_via_console(to_address: str, subject: str, body: str) -> EmailSendResult:
    logger.info("DEV EMAIL (not actually sent - EMAIL_PROVIDER=console) to=%s subject=%s\n%s", to_address, subject, body)
    return EmailSendResult(
        delivered=False,
        provider="console",
        detail="No real email provider is configured (EMAIL_PROVIDER=console); the message was logged, not delivered.",
    )


def _send_via_smtp(to_address: str, subject: str, body: str) -> EmailSendResult:
    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD):
        logger.error("EMAIL_PROVIDER=smtp but SMTP credentials are incomplete; falling back to console logging.")
        return _send_via_console(to_address, subject, body)

    message = EmailMessage()
    message["From"] = EMAIL_FROM_ADDRESS
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        return EmailSendResult(delivered=True, provider="smtp", detail=f"Sent via {SMTP_HOST}.")
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("SMTP send failed to %s: %s", to_address, exc)
        return EmailSendResult(delivered=False, provider="smtp", detail=f"SMTP send failed: {exc}")
