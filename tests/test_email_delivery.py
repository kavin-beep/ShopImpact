"""Check secure SMTP and links without contacting an email provider."""
import unittest
from unittest.mock import Mock, patch
from email_delivery import Mailer, EmailConfigurationError, queue_email_action


class DeliveryTests(unittest.TestCase):
    def mailer(self, **options):
        values = dict(host="smtp.example.test", port=465, username="sender@example.test",
                      password="PRIVATE_TEST_PASSWORD", sender="sender@example.test",
                      base_url="https://shop.example.test")
        values.update(options)
        return Mailer(**values)

    def test_rejects_untrusted_link_addresses_and_insecure_transport(self):
        for address in ("http://shop.example.test", "https://user:secret@shop.example.test", "https://shop.example.test?next=evil", "javascript:alert(1)"):
            with self.subTest(address=address), self.assertRaises(EmailConfigurationError):
                self.mailer(base_url=address)
        with self.assertRaises(EmailConfigurationError):
            self.mailer(security="plain")
        self.mailer(base_url="http://127.0.0.1:8501")

    def test_representation_does_not_contain_credentials(self):
        self.assertNotIn("PRIVATE_TEST_PASSWORD", repr(self.mailer()))

    def test_link_and_expiry_use_trusted_config_and_correct_purpose(self):
        mailer = self.mailer()
        with patch.object(Mailer, "send_message") as send:
            mailer.send_action("alice@example.test", "opaque_token", "reset")
        body = send.call_args.args[2]
        self.assertIn("https://shop.example.test/?email_action=reset&email_token=opaque_token", body)
        self.assertIn("30 minutes", body)
        self.assertNotIn("PRIVATE_TEST_PASSWORD", body)

    def test_ssl_transport_authenticates_without_plaintext_connection(self):
        with patch("email_delivery.smtplib.SMTP_SSL") as secure, patch("email_delivery.smtplib.SMTP") as plain:
            self.mailer().check_login()
        secure.return_value.login.assert_called_once()
        plain.assert_not_called()
        self.assertIsNotNone(secure.call_args.kwargs["context"])

    def test_starttls_happens_before_login(self):
        with patch("email_delivery.smtplib.SMTP") as plain:
            self.mailer(port=587, security="starttls").check_login()
        connection = plain.return_value
        names = [call[0] for call in connection.method_calls]
        self.assertLess(names.index("starttls"), names.index("login"))

    def test_unknown_address_never_sends_and_worker_errors_do_not_escape(self):
        service = Mock()
        service.request_email_action.return_value = None
        mailer = Mock()
        with patch("email_delivery._workers") as worker:
            worker.submit.side_effect = lambda action: action()
            queue_email_action(service, mailer, "unknown@example.test", "reset")
            service.request_email_action.side_effect = RuntimeError("PRIVATE_TEST_PASSWORD")
            queue_email_action(service, mailer, "unknown@example.test", "reset")
        mailer.send_action.assert_not_called()
