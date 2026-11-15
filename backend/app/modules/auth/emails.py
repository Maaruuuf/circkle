from app.core.config import get_settings
from app.core.email import EmailMessage, send_email


def _link(path: str, token: str) -> str:
    return f"{get_settings().frontend_url.rstrip('/')}{path}?token={token}"


async def send_verification_email(email: str, username: str, token: str) -> None:
    hours = get_settings().email_verify_expire_hours
    await send_email(
        EmailMessage(
            to=email,
            subject="Verify your Circkle email",
            body=(
                f"Hi {username},\n\n"
                f"Confirm your email address by opening this link (valid {hours} hours):\n"
                f"{_link('/verify-email', token)}\n\n"
                "If you did not create a Circkle account, you can ignore this email."
            ),
        )
    )


async def send_password_reset_email(email: str, username: str, token: str) -> None:
    minutes = get_settings().password_reset_expire_minutes
    await send_email(
        EmailMessage(
            to=email,
            subject="Reset your Circkle password",
            body=(
                f"Hi {username},\n\n"
                f"Choose a new password with this link (valid {minutes} minutes):\n"
                f"{_link('/reset-password', token)}\n\n"
                "If you did not ask for this, ignore this email: your password is unchanged."
            ),
        )
    )
