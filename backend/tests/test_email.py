"""app.auth.email - provider-agnostic email sending.

Uses a mocked SMTP layer throughout (unittest.mock.patch on smtplib.SMTP) -
no real SMTP provider is contacted by these tests, per this phase's
requirement to test production email behavior without needing a live
provider in CI/local runs.
"""
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


def _reload_email():
    sys.modules.pop("app.settings", None)
    sys.modules.pop("app.auth.email", None)
    return importlib.import_module("app.auth.email")


@pytest.fixture(autouse=True)
def _restore():
    yield
    sys.modules.pop("app.settings", None)
    sys.modules.pop("app.auth.email", None)


def test_console_provider_does_not_claim_delivery(monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    email = _reload_email()

    with caplog.at_level("INFO"):
        result = email.send_email("user@example.com", "Subject", "Body text")

    assert result.delivered is False
    assert result.provider == "console"
    assert "user@example.com" in caplog.text


def test_smtp_provider_sends_with_correct_message_and_reports_delivered(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "apikey")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cret")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "no-reply@example.com")
    email = _reload_email()

    mock_server = MagicMock()
    mock_smtp_cm = MagicMock()
    mock_smtp_cm.__enter__.return_value = mock_server
    mock_smtp_cm.__exit__.return_value = False

    with patch("smtplib.SMTP", return_value=mock_smtp_cm) as mock_smtp_ctor:
        result = email.send_email("user@example.com", "Verify your email", "Click here: https://x")

    mock_smtp_ctor.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("apikey", "s3cret")
    assert mock_server.send_message.call_count == 1
    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["To"] == "user@example.com"
    assert sent_message["From"] == "no-reply@example.com"
    assert sent_message["Subject"] == "Verify your email"
    assert sent_message.get_content().strip() == "Click here: https://x"

    assert result.delivered is True
    assert result.provider == "smtp"


def test_smtp_provider_with_incomplete_credentials_falls_back_to_console(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    email = _reload_email()

    with patch("smtplib.SMTP") as mock_smtp_ctor:
        result = email.send_email("user@example.com", "Subject", "Body")

    mock_smtp_ctor.assert_not_called()
    assert result.delivered is False
    assert result.provider == "console"


def test_smtp_send_failure_is_caught_and_reported_without_raising(monkeypatch):
    import smtplib

    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "apikey")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cret")
    email = _reload_email()

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPConnectError(421, "cannot connect")):
        result = email.send_email("user@example.com", "Subject", "Body")

    assert result.delivered is False
    assert result.provider == "smtp"
    assert "failed" in result.detail.lower()


def test_smtp_connection_refused_is_caught_and_reported_without_raising(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "apikey")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cret")
    email = _reload_email()

    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("connection refused")):
        result = email.send_email("user@example.com", "Subject", "Body")

    assert result.delivered is False
    assert result.provider == "smtp"


def test_smtp_failure_detail_never_contains_the_password(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "apikey")
    monkeypatch.setenv("SMTP_PASSWORD", "s3cret-password-value")
    email = _reload_email()

    with patch("smtplib.SMTP", side_effect=OSError("network unreachable")):
        result = email.send_email("user@example.com", "Subject", "Body")

    assert "s3cret-password-value" not in result.detail
