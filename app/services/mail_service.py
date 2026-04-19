from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.utils.config import get_settings


class MailService:
    def __init__(self):
        settings = get_settings()
        self.enabled = bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.smtp_user,
            MAIL_PASSWORD=settings.smtp_password,
            MAIL_FROM=settings.smtp_user or "noreply@skillfortinstitute.com",
            MAIL_PORT=settings.smtp_port,
            MAIL_SERVER=settings.smtp_host,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=False,
        )

    async def send(self, recipient: str, subject: str, body: str):
        if not self.enabled:
            return {"status": "skipped", "reason": "SMTP not configured"}
        message = MessageSchema(
            subject=subject,
            recipients=[recipient],
            body=body,
            subtype=MessageType.html,
        )
        fm = FastMail(self.conf)
        await fm.send_message(message)
        return {"status": "sent"}
