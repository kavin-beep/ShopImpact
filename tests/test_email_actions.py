"""Single-use email actions use disposable databases and no real email delivery."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from sqlalchemy import text

from accounts import Accounts, AccountError, digest

PASSWORD = "Temporary testing password 123"
NEW_PASSWORD = "Changed temporary password 456"


class EmailActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Accounts("sqlite:///" + (Path(self.tmp.name) / "mail.db").as_posix(), require_verified_email=True)
        self.recovery = self.db.register("alice", PASSWORD, "alice@example.test")

    def tearDown(self):
        self.db.engine.dispose()
        self.tmp.cleanup()

    def allow_request(self):
        with self.db.engine.begin() as db:
            db.execute(text("UPDATE email_requests SET next_allowed=0"))

    def verify(self):
        _, token = self.db.request_email_action("alice@example.test", "verify")
        self.db.consume_email_action(token, "verify")
        self.allow_request()

    def test_verification_gates_login_stores_hash_and_is_single_use(self):
        for alias in ("alice", "alice@example.test"):
            with self.assertRaisesRegex(AccountError, "Verify your email"):
                self.db.login(alias, PASSWORD)
        _, token = self.db.request_email_action("alice@example.test", "verify")
        with self.db.engine.connect() as db:
            stored = db.execute(text("SELECT token_hash FROM email_actions")).scalar()
        self.assertEqual(stored, digest(token))
        self.assertNotEqual(stored, token)
        self.db.consume_email_action(token, "verify")
        self.assertTrue(self.db.load(self.db.login("alice", PASSWORD))["email_verified"])
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "verify")

    def test_expired_and_wrong_purpose_links_cannot_verify(self):
        _, token = self.db.request_email_action("alice@example.test", "verify")
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "reset", NEW_PASSWORD)
        with self.db.engine.begin() as db:
            db.execute(text("UPDATE email_actions SET expires_at=0"))
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "verify")
        with self.assertRaisesRegex(AccountError, "Verify your email"):
            self.db.login("alice", PASSWORD)

    def test_reset_request_requires_verified_email_and_unknown_is_silent(self):
        self.assertIsNone(self.db.request_email_action("alice@example.test", "reset"))
        self.assertIsNone(self.db.request_email_action("unknown@example.test", "reset"))
        with self.db.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT count(*) FROM email_actions")).scalar(), 0)

    def test_resend_is_limited_and_new_request_invalidates_old_link(self):
        _, first = self.db.request_email_action("alice@example.test", "verify")
        self.assertIsNone(self.db.request_email_action("ALICE@example.test", "verify"))
        self.allow_request()
        _, second = self.db.request_email_action("alice@example.test", "verify")
        with self.assertRaises(AccountError):
            self.db.consume_email_action(first, "verify")
        self.db.consume_email_action(second, "verify")

    def test_reset_revokes_sessions_rotates_recovery_and_rejects_replay(self):
        self.verify()
        session = self.db.login("alice", PASSWORD)
        _, token = self.db.request_email_action("alice@example.test", "reset")
        result = self.db.consume_email_action(token, "reset", NEW_PASSWORD)
        self.assertEqual(result["email"], "alice@example.test")
        self.assertNotEqual(result["recovery_code"], self.recovery)
        with self.assertRaises(AccountError):
            self.db.load(session)
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "reset", PASSWORD)
        with self.assertRaises(AccountError):
            self.db.login("alice", PASSWORD)
        self.assertTrue(self.db.login("alice@example.test", NEW_PASSWORD))
        with self.assertRaises(AccountError):
            self.db.reset_password("alice", self.recovery, PASSWORD)

    def test_email_change_invalidates_old_links_and_requires_reverification(self):
        self.verify()
        session = self.db.login("alice", PASSWORD)
        _, token = self.db.request_email_action("alice@example.test", "reset")
        self.db.set_email(session, "updated@example.test", PASSWORD)
        self.assertFalse(self.db.load(session)["email_verified"])
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "reset", NEW_PASSWORD)
        with self.assertRaisesRegex(AccountError, "Verify your email"):
            self.db.login("alice", PASSWORD)
        _, verification = self.db.request_email_action("updated@example.test", "verify")
        self.db.consume_email_action(verification, "verify")
        self.assertTrue(self.db.login("updated@example.test", PASSWORD))

    def test_recovery_code_reset_invalidates_email_reset_links(self):
        self.verify()
        _, token = self.db.request_email_action("alice@example.test", "reset")
        self.db.reset_password("alice", self.recovery, NEW_PASSWORD)
        with self.assertRaises(AccountError):
            self.db.consume_email_action(token, "reset", PASSWORD)

    def test_simultaneous_reset_claims_only_one_token(self):
        self.verify()
        _, token = self.db.request_email_action("alice@example.test", "reset")
        def consume():
            try:
                self.db.consume_email_action(token, "reset", NEW_PASSWORD)
                return True
            except AccountError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consume(), range(2)))
        self.assertEqual(sorted(results), [False, True])

    def test_account_deletion_removes_email_actions(self):
        self.verify()
        session = self.db.login("alice", PASSWORD)
        self.db.request_email_action("alice@example.test", "reset")
        self.db.delete_account(session, PASSWORD)
        with self.db.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT count(*) FROM email_actions")).scalar(), 0)
