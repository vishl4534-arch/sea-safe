"""Email for watched trips (owner, 13 Nov 2026): a confirmation when watching starts, and the verdict change.

Sent through Gmail's SMTP server with an app password, set in .env (never in code or config):
    SMTP_USER=the Gmail address the emails come from
    SMTP_PASSWORD=the 16-character app password from Google (Account > Security > App passwords)
Optional: SMTP_HOST (default smtp.gmail.com) and SMTP_PORT (default 465, SSL).
Without them, watching still works by phone notification and the page says email is not set up.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger("seasafe.mail")


class MailError(Exception):
    pass


def _user() -> str:
    return os.getenv("SMTP_USER", "").strip()


def _password() -> str:
    return os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()      # Google shows it in groups of four


def available() -> bool:
    """Email is set up on this server."""
    return bool(_user() and _password())


def _real_send(to: str, subject: str, body: str) -> None:
    """One plain-text email. Raises MailError when it cannot be sent (not set up, refused, no connection)."""
    if not available():
        raise MailError("email is not set up (SMTP_USER and SMTP_PASSWORD in .env)")
    msg = EmailMessage()
    msg["From"] = f"Sea Safe <{_user()}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465")),
                              timeout=15) as server:
            server.login(_user(), _password())
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(str(e)) from e
    log.info("email sent: %s", subject)


send = _real_send
