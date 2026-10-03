"""Security and persistence checks use disposable databases."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import text
from accounts import Accounts, AccountError, ConflictError, DEFAULT_SETTINGS
from logic import make_purchase

PASSWORD = "Testing only passphrase 123"


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.url = "sqlite:///" + (Path(self.tmp.name) / "accounts.db").as_posix()
        self.db = Accounts(self.url)
        self.recovery = self.db.register("alice", PASSWORD)
        self.token = self.db.login("alice", PASSWORD)

    def tearDown(self):
        self.db.engine.dispose()
        self.tmp.cleanup()

    def test_private_data_and_restart(self):
        purchase = make_purchase("New clothing", 100, "Shop", "2026-10-01")
        self.db.save(self.token, [purchase], DEFAULT_SETTINGS, 0)
        self.db.register("bob", PASSWORD)
        bob = self.db.login("bob", PASSWORD)
        self.assertEqual(self.db.load(bob)["purchases"], [])
        restarted = Accounts(self.url)
        self.assertEqual(restarted.load(self.token)["purchases"], [purchase])
        restarted.engine.dispose()

    def test_passwords_are_salted_hashes(self):
        self.db.register("bob", PASSWORD)
        with self.db.engine.connect() as connection:
            hashes = connection.execute(text("SELECT password_hash FROM users")).scalars().all()
        self.assertNotEqual(hashes[0], hashes[1])
        self.assertTrue(all(value.startswith("$argon2id$") for value in hashes))

    def test_duplicate_and_weak_password(self):
        for name, password in [("ALICE", PASSWORD), ("eve", "short"), ("' OR 1=1", PASSWORD)]:
            with self.assertRaises(AccountError):
                self.db.register(name, password)

    def test_failed_login_rate_limit(self):
        for _ in range(5):
            with self.assertRaises(AccountError):
                self.db.login("alice", "incorrect")
        with self.assertRaisesRegex(AccountError, "15 minutes"):
            self.db.login("alice", PASSWORD)

    def test_concurrent_edits_do_not_overwrite(self):
        self.db.save(self.token, [], {**DEFAULT_SETTINGS, "budget": 20000}, 0)
        with self.assertRaises(ConflictError):
            self.db.save(self.token, [], DEFAULT_SETTINGS, 0)
        self.assertEqual(self.db.load(self.token)["settings"]["budget"], 20000)

    def test_recovery_revokes_sessions_and_rotates_code(self):
        replacement = self.db.reset_password("alice", self.recovery, "A new long passphrase")
        self.assertNotEqual(self.recovery, replacement)
        with self.assertRaises(AccountError):
            self.db.load(self.token)
        with self.assertRaises(AccountError):
            self.db.reset_password("alice", self.recovery, PASSWORD)
        self.assertTrue(self.db.login("alice", "A new long passphrase"))

    def test_password_reset_during_login_cannot_issue_old_session(self):
        from accounts import HASHER
        original = HASHER.verify

        def reset_after_verification(encoded, password):
            result = original(encoded, password)
            self.db.reset_password("alice", self.recovery, "A changed long passphrase")
            return result

        with patch("accounts.HASHER", wraps=HASHER) as hasher:
            hasher.verify.side_effect = reset_after_verification
            with self.assertRaises(AccountError):
                self.db.login("alice", PASSWORD)
        self.assertTrue(self.db.login("alice", "A changed long passphrase"))

    def test_logout_and_expired_sessions(self):
        self.db.logout(self.token)
        with self.assertRaises(AccountError):
            self.db.load(self.token)
        token = self.db.login("alice", PASSWORD)
        with self.db.engine.begin() as connection:
            connection.execute(text("UPDATE sessions SET expires_at=0"))
        with self.assertRaises(AccountError):
            self.db.load(token)

    def test_delete_requires_password_and_removes_account(self):
        with self.assertRaises(AccountError):
            self.db.delete_account(self.token, "wrong")
        self.db.delete_account(self.token, PASSWORD)
        with self.assertRaises(AccountError):
            self.db.load(self.token)

    def test_hosted_mode_rejects_local_database(self):
        with self.assertRaises(AccountError):
            Accounts(self.url, public=True)

    def test_email_login_normalizes_case_and_preserves_username(self):
        self.db.register("bob", PASSWORD, email=" Bob+shop@Example.Test ")
        token = self.db.login(" BOB+SHOP@example.test ", PASSWORD)
        self.assertEqual(self.db.load(token)["username"], "bob")
        self.assertEqual(self.db.load(token)["email"], "bob+shop@example.test")
        self.assertTrue(self.db.login("bob", PASSWORD))

    def test_invalid_and_duplicate_emails_are_rejected(self):
        self.db.register("bob", PASSWORD, email="bob@example.test")
        for email in ("", "plain", "a@", "a@host", ".a@example.test", "a..b@example.test", "a b@example.test", "a@-host.test", "x" * 65 + "@example.test", "BOB@EXAMPLE.TEST"):
            with self.subTest(email=email), self.assertRaises(AccountError):
                self.db.register("charlie", PASSWORD, email=email)

    def test_link_email_requires_password_and_preserves_saved_data(self):
        purchase = make_purchase("Repair services", 100, "Shop", "2026-10-02")
        self.db.save(self.token, [purchase], DEFAULT_SETTINGS, 0)
        with self.assertRaises(AccountError):
            self.db.set_email(self.token, "alice@example.test", "wrong")
        self.assertIsNone(self.db.load(self.token)["email"])
        self.db.set_email(self.token, "alice@example.test", PASSWORD)
        token = self.db.login("alice@example.test", PASSWORD)
        self.assertEqual(self.db.load(token)["purchases"], [purchase])
        self.db.register("bob", PASSWORD, email="bob@example.test")
        with self.assertRaises(AccountError):
            self.db.set_email(token, "bob@example.test", PASSWORD)
        self.assertEqual(self.db.load(token)["email"], "alice@example.test")
        self.db.set_email(token, "updated@example.test", PASSWORD)
        with self.assertRaises(AccountError):
            self.db.login("alice@example.test", PASSWORD)
        self.assertTrue(self.db.login("updated@example.test", PASSWORD))

    def test_email_and_username_share_login_rate_limit(self):
        self.db.set_email(self.token, "alice@example.test", PASSWORD)
        for alias in ("alice", "alice@example.test", "ALICE", "ALICE@example.test", "alice"):
            with self.assertRaises(AccountError):
                self.db.login(alias, "wrong")
        with self.assertRaisesRegex(AccountError, "15 minutes"):
            self.db.login("alice@example.test", PASSWORD)

    def test_email_recovery_revokes_existing_sessions(self):
        self.db.set_email(self.token, "alice@example.test", PASSWORD)
        replacement = self.db.reset_password("ALICE@example.test", self.recovery, "A new email passphrase")
        self.assertNotEqual(replacement, self.recovery)
        with self.assertRaises(AccountError):
            self.db.load(self.token)
        self.assertTrue(self.db.login("alice@example.test", "A new email passphrase"))

    def test_existing_database_migration_keeps_accounts_and_purchases(self):
        purchase = make_purchase("Repair services", 100, "Shop", "2026-10-02")
        self.db.save(self.token, [purchase], DEFAULT_SETTINGS, 0)
        with self.db.engine.begin() as connection:
            connection.execute(text("DROP INDEX users_email_unique"))
            connection.execute(text("ALTER TABLE users DROP COLUMN email"))
        for _ in range(2):
            migrated = Accounts(self.url)
            try:
                saved = migrated.load(self.token)
                self.assertIsNone(saved["email"])
                self.assertEqual(saved["purchases"], [purchase])
                self.assertTrue(migrated.login("alice", PASSWORD))
            finally:
                migrated.engine.dispose()


if __name__ == "__main__":
    unittest.main()
