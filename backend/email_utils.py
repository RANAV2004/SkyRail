import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@trainscheduler.com")


def smtp_configured() -> bool:
    """True only when enough SMTP settings are present to actually send mail."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send the OTP. Returns True if a real email was sent, False in dev mode.

    Never raises to the caller: on any SMTP failure it falls back to logging the
    OTP so registration is not blocked by a mail outage.
    """
    if not smtp_configured():
        print(f"[DEV OTP] Verification code for {to_email}: {otp} (expires in 10 min)")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Your Train Scheduler verification code"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Welcome to Train Ticket Scheduler and Route Optimizer!\n\n"
        f"Your verification code (OTP) is: {otp}\n"
        f"It expires in 10 minutes.\n\n"
        f"If you did not request this, you can ignore this email."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[EMAIL] OTP sent to {to_email}")
        return True
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[EMAIL ERROR] Could not send to {to_email}: {exc}")
        print(f"[DEV OTP] Verification code for {to_email}: {otp}")
        return False
