import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.enabled = bool(settings.smtp_host and settings.notification_email)

    def send_lead_notification(self, lead_data: dict) -> bool:
        if not self.enabled:
            logger.info("Email notifications disabled")
            return False

        subject = f"New Lead: {lead_data.get('full_name', 'Unknown')}"
        
        body_lines = ["<h2>New Quote Request</h2>", "<table>"]
        for key, value in lead_data.items():
            if key == "form_data" and isinstance(value, dict):
                for fk, fv in value.items():
                    body_lines.append(f"<tr><td><strong>{fk}</strong></td><td>{fv}</td></tr>")
            elif key not in ("id", "created_at", "updated_at"):
                body_lines.append(f"<tr><td><strong>{key.replace('_', ' ').title()}</strong></td><td>{value}</td></tr>")
        body_lines.append("</table>")
        body = "".join(body_lines)

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_email
        msg["To"] = settings.notification_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_tls:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            logger.info("Lead notification sent to %s", settings.notification_email)
            return True
        except Exception as e:
            logger.error("Failed to send lead notification: %s", e)
            return False
