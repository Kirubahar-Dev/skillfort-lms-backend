import httpx
from app.utils.config import get_settings


BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class MailService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.brevo_api_key
        self.sender_email = settings.smtp_user or "Info@skillfortinstitute.com"
        self.enabled = bool(self.api_key)

    def _headers(self):
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def send(self, recipient: str, subject: str, body: str):
        if not self.enabled:
            return {"status": "skipped", "reason": "Brevo API key not configured"}
        payload = {
            "sender": {"name": "Skillfort Institute", "email": self.sender_email},
            "to": [{"email": recipient}],
            "subject": subject,
            "htmlContent": body,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(BREVO_URL, json=payload, headers=self._headers())
            if r.status_code in (200, 201):
                return {"status": "sent"}
            return {"status": "failed", "reason": r.text}

    async def send_welcome(self, recipient: str, full_name: str):
        return await self.send(
            recipient,
            "Welcome to Skillfort Institute 🎓",
            _template(
                title="Welcome to Skillfort!",
                preview="Your account is ready. Start learning today.",
                content=f"""
                <h2 style="color:#0f172a;margin:0 0 8px">Welcome, {full_name}!</h2>
                <p style="color:#475569;margin:0 0 20px">Your Skillfort Institute account has been created successfully.
                You now have access to world-class training in Full Stack Development, Java, Python, AWS, and more.</p>
                <a href="https://frontend-theta-flax-35.vercel.app/courses"
                   style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;
                          padding:12px 28px;border-radius:10px;font-weight:600;font-size:15px">
                  Browse Courses &rarr;
                </a>
                <p style="color:#94a3b8;margin:24px 0 0;font-size:13px">Login: <strong>{recipient}</strong></p>
                """,
            ),
        )

    async def send_password_reset(self, recipient: str, reset_link: str):
        return await self.send(
            recipient,
            "Reset your Skillfort password",
            _template(
                title="Reset Your Password",
                preview="Click the link below to reset your password.",
                content=f"""
                <h2 style="color:#0f172a;margin:0 0 8px">Password Reset Request</h2>
                <p style="color:#475569;margin:0 0 20px">
                  We received a request to reset your Skillfort account password.<br>
                  This link expires in <strong>1 hour</strong>.
                </p>
                <a href="{reset_link}"
                   style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;
                          padding:12px 28px;border-radius:10px;font-weight:600;font-size:15px">
                  Reset Password &rarr;
                </a>
                <p style="color:#94a3b8;margin:24px 0 0;font-size:13px">
                  If you didn't request this, you can safely ignore this email.
                </p>
                """,
            ),
        )

    async def send_enrollment_confirmation(self, recipient: str, full_name: str, course_title: str, order_id: str):
        return await self.send(
            recipient,
            f"Enrolled: {course_title} ✅",
            _template(
                title="Enrollment Confirmed! 🚀",
                preview=f"You're enrolled in {course_title}. Start learning now!",
                content=f"""
                <h2 style="color:#0f172a;margin:0 0 8px">You're enrolled, {full_name}!</h2>
                <p style="color:#475569;margin:0 0 16px">Your payment was successful. You now have full access to:</p>
                <div style="background:#f8fafc;border-left:4px solid #6366f1;padding:16px 20px;border-radius:8px;margin:0 0 20px">
                  <p style="color:#0f172a;font-weight:700;font-size:18px;margin:0">{course_title}</p>
                  <p style="color:#94a3b8;font-size:13px;margin:6px 0 0">Order ID: {order_id}</p>
                </div>
                <a href="https://frontend-theta-flax-35.vercel.app/my-courses"
                   style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;
                          padding:12px 28px;border-radius:10px;font-weight:600;font-size:15px">
                  Start Learning &rarr;
                </a>
                """,
            ),
        )

    async def send_certificate_ready(self, recipient: str, full_name: str, course_title: str, course_id: int):
        return await self.send(
            recipient,
            f"Certificate Ready: {course_title} 🏆",
            _template(
                title="Your Certificate is Ready! 🏆",
                preview=f"Congratulations! You completed {course_title}.",
                content=f"""
                <h2 style="color:#0f172a;margin:0 0 8px">Congratulations, {full_name}! 🎉</h2>
                <p style="color:#475569;margin:0 0 16px">
                  You have successfully completed <strong>{course_title}</strong>.<br>
                  Your certificate of completion is ready to download.
                </p>
                <a href="https://frontend-theta-flax-35.vercel.app/certificate/{course_id}"
                   style="display:inline-block;background:#f59e0b;color:#0f172a;text-decoration:none;
                          padding:12px 28px;border-radius:10px;font-weight:700;font-size:15px">
                  View &amp; Download Certificate &rarr;
                </a>
                """,
            ),
        )


def _template(title: str, preview: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <span style="display:none;max-height:0;overflow:hidden">{preview}</span>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px">
        <tr><td style="background:#0f172a;border-radius:16px 16px 0 0;padding:28px 36px;text-align:center">
          <p style="color:#f59e0b;font-size:22px;font-weight:800;margin:0;letter-spacing:1px">SKILLFORT INSTITUTE</p>
          <p style="color:#475569;font-size:12px;margin:4px 0 0">Professional Development &amp; Placement Training</p>
        </td></tr>
        <tr><td style="background:#ffffff;padding:36px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0">
          {content}
        </td></tr>
        <tr><td style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 16px 16px;padding:20px 36px;text-align:center">
          <p style="color:#94a3b8;font-size:12px;margin:0">
            &copy; 2026 Skillfort Institute &middot;
            <a href="https://frontend-theta-flax-35.vercel.app" style="color:#6366f1;text-decoration:none">skillfortinstitute.com</a>
          </p>
          <p style="color:#cbd5e1;font-size:11px;margin:6px 0 0">
            You received this because you have an account at Skillfort Institute.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
