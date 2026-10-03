"""Private Gmail/SMTP delivery and bounded background email requests."""
from dataclasses import dataclass, field
from email.message import EmailMessage
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from urllib.parse import urlencode, urlsplit

from accounts import email_key


class EmailConfigurationError(ValueError):
    pass


@dataclass(repr=False)
class Mailer:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    sender: str
    base_url: str
    security: str = "ssl"

    def __post_init__(self):
        self.sender = email_key(self.sender)
        parsed = urlsplit(self.base_url)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (parsed.scheme != "https" and not (local and parsed.scheme == "http")) or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise EmailConfigurationError("Use the app's HTTPS address, or its localhost HTTP address for local testing.")
        self.base_url = self.base_url.rstrip("/")
        if not self.host or any(character in self.host for character in "\r\n /") or not self.username or not self.password:
            raise EmailConfigurationError("Complete the private email-provider settings.")
        if self.security not in {"ssl", "starttls"} or not 1 <= int(self.port) <= 65535:
            raise EmailConfigurationError("Use SSL or STARTTLS with a valid SMTP port.")

    def _connect(self):
        context = ssl.create_default_context()
        if self.security == "ssl":
            connection = smtplib.SMTP_SSL(self.host, int(self.port), timeout=15, context=context)
        else:
            connection = smtplib.SMTP(self.host, int(self.port), timeout=15)
            try:
                connection.ehlo()
                connection.starttls(context=context)
                connection.ehlo()
            except Exception:
                connection.close()
                raise
        try:
            connection.login(self.username, self.password)
        except Exception:
            connection.close()
            raise
        return connection

    def check_login(self):
        with self._connect():
            pass

    def send_message(self, recipient, subject, body):
        recipient = email_key(recipient)
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with self._connect() as connection:
            connection.send_message(message)

    def send_action(self, recipient, token, purpose):
        if purpose not in {"verify", "reset"}:
            raise EmailConfigurationError("Unknown email action.")
        link = self.base_url + "/?" + urlencode({"email_action": purpose, "email_token": token})
        title, expiry = ("Verify your ShopImpact email", "24 hours") if purpose == "verify" else ("Reset your ShopImpact password", "30 minutes")
        self.send_message(recipient, title,
                          f"{title}\n\nOpen this link and follow the instructions:\n{link}\n\n"
                          f"The link expires in {expiry} and can be used once.\n"
                          "If you did not request this, you can ignore this email.\n\nShopImpact")


def mailer_from_settings(settings):
    return Mailer(host=str(settings.get("SHOPIMPACT_SMTP_HOST", "smtp.gmail.com")),
                  port=int(settings.get("SHOPIMPACT_SMTP_PORT", 465)),
                  username=str(settings.get("SHOPIMPACT_SMTP_USERNAME", "")),
                  password=str(settings.get("SHOPIMPACT_SMTP_PASSWORD", "")),
                  sender=str(settings.get("SHOPIMPACT_SMTP_FROM", "")),
                  base_url=str(settings.get("SHOPIMPACT_APP_URL", "")),
                  security=str(settings.get("SHOPIMPACT_SMTP_SECURITY", "ssl")))


_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="shopimpact-mail")
_slots = BoundedSemaphore(8)


def queue_email_action(service, mailer, email, purpose):
    """The browser gets the same immediate response for every address."""
    email = email_key(email)
    if not _slots.acquire(blocking=False):
        return

    def deliver():
        try:
            payload = service.request_email_action(email, purpose)
            if payload:
                mailer.send_action(*payload, purpose)
        except Exception:
            # Never log SMTP errors, credentials, recipient addresses or bearer tokens.
            pass
        finally:
            _slots.release()
    try:
        _workers.submit(deliver)
    except Exception:
        _slots.release()


def queue_notice(mailer, email, subject, body):
    if not email or not _slots.acquire(blocking=False):
        return
    def deliver():
        try:
            mailer.send_message(email, subject, body)
        except Exception:
            pass
        finally:
            _slots.release()
    try:
        _workers.submit(deliver)
    except Exception:
        _slots.release()
