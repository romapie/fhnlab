import smtplib

from email.message import EmailMessage
from .base import Notifier


class EmailNotifier(Notifier):
    def __init__(self, smtp_host, smtp_port, user, password, to):
        self.host = smtp_host
        self.port = smtp_port
        self.user = user
        self.password = password
        self.to = to

    def notify(self, message: str):
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = self.to
        msg["Subject"] = "SLURM Notification"
        msg.set_content(message)

        with smtplib.SMTP_SSL(self.host, self.port) as s:
            s.login(self.user, self.password)
            s.send_message(msg)
