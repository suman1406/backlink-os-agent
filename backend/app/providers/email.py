import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASS
        self.testing_email = settings.TESTING_EMAIL_ADDRESS

    def send_email(self, to_email: str, subject: str, body_text: str) -> bool:
        if not self.user or not self.password:
            logger.warning("SMTP credentials not set. Mocking email send.")
            logger.info(f"Mock send to {to_email}: {subject}")
            return True
            
        recipient = self.testing_email if self.testing_email else to_email
        logger.info(f"Sending email to {recipient} with subject: {subject}")

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
