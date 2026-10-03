"""Check private setup input and failure handling without a hosted database."""
import contextlib
import io
import unittest
from unittest.mock import patch

from tools import connect_database


class DatabaseSetupTests(unittest.TestCase):
    def test_connection_diagnostics_hide_provider_details_and_credentials(self):
        for marker, expected in (
            ("password authentication failed", "password"),
            ("failed to resolve host", "hostname"),
            ("connection timeout", "timed out"),
            ("Connection refused", "refused"),
            ("SSL certificate failed", "Secure connection"),
        ):
            with self.subTest(marker=marker):
                message = connect_database.connection_error_message(RuntimeError(marker + " PRIVATE_SECRET"))
                self.assertIn(expected, message)
                self.assertNotIn("PRIVATE_SECRET", message)

    def test_clipboard_failure_is_private_and_does_not_change_settings(self):
        output = io.StringIO()
        with patch("builtins.input", return_value=""), \
                patch.object(connect_database, "read_clipboard", side_effect=RuntimeError("PRIVATE_SECRET")), \
                patch.object(connect_database, "create_engine") as engine, \
                contextlib.redirect_stdout(output):
            self.assertEqual(connect_database.main(use_clipboard=True), 1)
        engine.assert_not_called()
        self.assertNotIn("PRIVATE_SECRET", output.getvalue())

    def test_clipboard_input_reaches_validation_without_being_printed(self):
        output = io.StringIO()
        uri = "postgresql://user:PRIVATE_SECRET@host/db?sslmode=require"
        with patch("builtins.input", return_value=""), \
                patch.object(connect_database, "read_clipboard", return_value=uri), \
                patch.object(connect_database, "create_engine", side_effect=RuntimeError("offline")) as engine, \
                contextlib.redirect_stdout(output):
            self.assertEqual(connect_database.main(use_clipboard=True), 1)
        self.assertEqual(engine.call_args.args[0].password, "PRIVATE_SECRET")
        self.assertNotIn("PRIVATE_SECRET", output.getvalue())

    def test_provider_uri_preserves_password_and_tls_parameters(self):
        url = connect_database.validate_url(
            "postgresql://user:p%40ss@host.example/shopimpact?sslmode=require&channel_binding=require"
        )
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.password, "p@ss")
        self.assertEqual(url.query["channel_binding"], "require")

    def test_rejects_insecure_incomplete_and_non_postgres_urls(self):
        for raw in (
            "sqlite:///local.db",
            "postgresql://user:secret@host/db",
            "postgresql://user:secret@host/db?sslmode=disable",
            "postgresql://user@host/db?sslmode=require",
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                connect_database.validate_url(raw)

    def test_invalid_input_does_not_echo_credentials(self):
        output = io.StringIO()
        with patch.object(connect_database.getpass, "getpass", return_value="PRIVATE_SECRET"), \
                patch.object(connect_database, "create_engine") as engine, \
                contextlib.redirect_stdout(output):
            self.assertEqual(connect_database.main(), 1)
        engine.assert_not_called()
        self.assertNotIn("PRIVATE_SECRET", output.getvalue())

    def test_connection_failure_does_not_echo_credentials_or_write_settings(self):
        output = io.StringIO()
        uri = "postgresql://user:PRIVATE_SECRET@host/db?sslmode=require"
        with patch.object(connect_database.getpass, "getpass", return_value=uri), \
                patch.object(connect_database, "create_engine", side_effect=RuntimeError(uri)), \
                patch.object(connect_database.os, "replace") as replace, \
                contextlib.redirect_stdout(output):
            self.assertEqual(connect_database.main(), 1)
        replace.assert_not_called()
        self.assertNotIn("PRIVATE_SECRET", output.getvalue())
