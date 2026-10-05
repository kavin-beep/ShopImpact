"""Exercise the real Streamlit interface without a browser."""
import unittest
import os
import tempfile
from unittest.mock import patch
from accounts import Accounts
from accounts import AccountError
from sqlalchemy import text
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def by_label(elements, label):
    return next(item for item in elements if item.label == label)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.url = "sqlite:///" + (Path(self.tmp.name) / "ui.db").as_posix()
        self.env = patch.dict(os.environ, {"SHOPIMPACT_DATABASE_URL": self.url, "SHOPIMPACT_PUBLIC": "false", "SHOPIMPACT_EMAIL_ENABLED": "false"})
        self.env.start()
        self.require_verified_test = False
        self.db = Accounts(self.url)
        self.db.register("alice", "Testing only password 123")

    def tearDown(self):
        from account_ui import account_service
        account_service(self.url, False, False).engine.dispose()
        if self.require_verified_test:
            account_service(self.url, False, True).engine.dispose()
        account_service.clear()
        self.db.engine.dispose()
        self.env.stop()
        self.tmp.cleanup()

    def app(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)
        app.text_input(key="login_name").set_value("alice")
        app.text_input(key="login_password").set_value("Testing only password 123")
        by_label(app.button, "Sign in").click().run()
        self.assertFalse(app.exception)
        return app

    def test_initial_empty_dashboard(self):
        app = self.app()
        self.assertEqual(app.metric[0].value, "INR 0.00")
        self.assertEqual(app.session_state["account_data"]["purchases"], [])

    def test_themes_work_before_sign_in_and_preserve_account_data(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.selectbox(key="visual_theme").select("Night").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("si-night" in item.value for item in app.markdown))
        app.checkbox(key="scenery_motion").uncheck().run()
        self.assertTrue(any("si-night si-paused" in item.value for item in app.markdown))
        app.text_input(key="login_name").set_value("alice")
        app.text_input(key="login_password").set_value("Testing only password 123")
        by_label(app.button, "Sign in").click().run()
        self.assertEqual(app.selectbox(key="visual_theme").value, "Night")
        original = app.session_state["account_data"].copy()
        for theme in ["Day", "Normal", "Night"]:
            app.selectbox(key="visual_theme").select(theme).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["account_data"], original)
        app.checkbox(key="contrast").check().run()
        self.assertTrue(any(".si-scenery {display:none;}" in item.value for item in app.markdown))

    def test_deployment_refreshes_cached_rules_and_backup_version(self):
        import logic
        import storage
        from unittest.mock import patch
        with patch.object(logic, "VERSION", "epa-2022-inr-reference-v2"), patch.object(
            storage, "VERSION", "epa-2022-inr-reference-v2"
        ):
            app = self.app()
            self.assertFalse(app.exception)
            self.assertEqual(logic.VERSION, "useeio-2024-inr-reference-v3")
            self.assertEqual(storage.VERSION, logic.VERSION)

    def test_saved_estimates_change_only_after_confirmed_recalculation(self):
        from logic import make_purchase, VERSION
        from datetime import date
        row = make_purchase("New clothing", 1000, "Saved shop", date.today())
        row.update(methodology="epa-2022-inr-reference-v2", estimated_co2="1.53")
        token = self.db.login("alice", "Testing only password 123")
        saved = self.db.load(token)
        self.db.save(token, [row], saved["settings"], saved["revision"])
        app = self.app()
        self.assertEqual(app.metric[1].value, "1.53 kg")
        self.assertTrue(by_label(app.button, "Recalculate saved estimates").disabled)
        app.checkbox(key="approve_recalculation").check().run()
        by_label(app.button, "Recalculate saved estimates").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "1.24 kg")
        latest = self.db.load(token)
        self.assertEqual(latest["purchases"][0]["methodology"], VERSION)
        self.assertEqual(latest["settings"], saved["settings"])

    def test_invalid_email_configuration_does_not_block_accounts(self):
        # Misconfigured optional SMTP must not break sign-in or purchase saving.
        with patch.dict(os.environ, {"SHOPIMPACT_EMAIL_ENABLED": "true"}), patch(
            "account_ui.email_settings", return_value={
                "SHOPIMPACT_EMAIL_ENABLED": True,
                "SHOPIMPACT_SMTP_PORT": "PRIVATE_INVALID_SETTING",
            }
        ):
            app = self.app()
            self.assertEqual(app.metric[0].value, "INR 0.00")
            self.assertEqual(len(app.warning), 1)
            self.assertNotIn("PRIVATE_INVALID_SETTING", app.warning[0].value)
            app.text_input(key="new_brand").set_value("Local shop")
            app.button(key="add").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["account_data"]["purchases"]), 1)
            by_label(app.button, "Sign out").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(by_label(app.button, "Send password-reset email").disabled)


    def test_history_filters_limit_edit_choices_and_keep_saved_data(self):
        app = self.app()
        app.text_input(key="new_brand").set_value("First shop")
        app.button(key="add").click().run()
        app.text_input(key="new_brand").set_value("Second shop")
        app.button(key="add").click().run()
        by_label(app.text_input, "Search purchases").set_value("Second shop").run()
        choices = by_label(app.selectbox, "Choose a purchase to edit").options
        self.assertEqual(len(choices), 1)
        self.assertIn("Second shop", choices[0])
        by_label(app.text_input, "Search purchases").set_value("No matches").run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.label == "Choose a purchase to edit" for item in app.selectbox))
        self.assertEqual(len(app.session_state["account_data"]["purchases"]), 2)

    def test_insights_follow_logged_month_and_saved_goal(self):
        app = self.app()
        app.text_input(key="new_brand").set_value("Insight shop")
        app.button(key="add").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(by_label(app.metric, "Average purchase").value, "INR 500.00")
        self.assertEqual(by_label(app.metric, "Spending goal remaining").value, "INR 9,500.00")
        self.assertEqual(by_label(app.metric, "Change from previous month").value, "No prior entries")
        app.number_input(key="budget").set_value(100.0)
        by_label(app.button, "Save goals & appearance").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(by_label(app.metric, "Above spending goal").value, "INR 400.00")

    def test_incorrect_login_shows_message_without_crashing(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.text_input(key="login_name").set_value("alice")
        app.text_input(key="login_password").set_value("incorrect password")
        by_label(app.button, "Sign in").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Email, username or password is incorrect" in item.value for item in app.error))
        self.assertEqual(len(app.metric), 0)

    def test_blank_brand_rejected(self):
        app = self.app()
        app.button(key="add").click().run()
        self.assertEqual(len(app.error), 1)
        self.assertEqual(app.session_state["account_data"]["purchases"], [])

    def test_add_edit_delete(self):
        app = self.app()
        app.text_input(key="new_brand").set_value("Local repair shop")
        app.selectbox(key="new_category").select("Repair services")
        app.button(key="add").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "INR 500.00")
        self.assertTrue(any("Repair Champion" in item.value for item in app.success))
        by_label(app.number_input, "Edit price (INR)").set_value(800.0)
        by_label(app.button, "Save changes").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "INR 800.00")
        by_label(app.checkbox, "Confirm deletion of this purchase").check().run()
        by_label(app.button, "Delete selected purchase").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["account_data"]["purchases"], [])

    def test_refresh_retains_purchases_and_settings(self):
        app = self.app()
        self.assertFalse(any(r.label == "Workspace" for r in app.radio))
        app.text_input(key="new_brand").set_value("Saved shop")
        app.button(key="add").click().run()
        app.checkbox(key="contrast").check()
        app.number_input(key="budget").set_value(15000.0)
        by_label(app.button, "Save goals & appearance").click().run()
        by_label(app.button, "Sign out").click().run()
        self.assertEqual(len(app.metric), 0)
        fresh = self.app()
        self.assertEqual(fresh.metric[0].value, "INR 500.00")
        self.assertEqual(fresh.number_input(key="budget").value, 15000.0)
        self.assertTrue(fresh.checkbox(key="contrast").value)

    def test_registration_then_login(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual([tab.label for tab in app.tabs], ["Sign in", "Create account", "Recover account"])
        by_label(app.text_input, "Choose a username").set_value("bob")
        by_label(app.text_input, "Email address").set_value("bob@example.test")
        by_label(app.text_input, "Choose a password").set_value("Testing only password 123")
        by_label(app.text_input, "Confirm password").set_value("Testing only password 123")
        by_label(app.button, "Create account").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["recovery_code"])
        self.assertEqual(app.metric[0].value, "INR 0.00")
        self.assertTrue(app.session_state["auth_token"])
        self.assertTrue(app.session_state["account_created"])
        self.assertTrue(any(item.label == "Save your account recovery code" for item in app.expander))
        by_label(app.button, "Sign out").click().run()
        app.text_input(key="login_name").set_value("BOB@example.test")
        app.text_input(key="login_password").set_value("Testing only password 123")
        by_label(app.button, "Sign in").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["account_data"]["username"], "bob")
        self.assertEqual(app.session_state["account_data"]["email"], "bob@example.test")

    def test_existing_account_can_link_email_then_sign_in(self):
        app = self.app()
        by_label(app.text_input, "Sign-in email").set_value("alice@example.test")
        by_label(app.text_input, "Current password").set_value("Testing only password 123")
        by_label(app.button, "Save sign-in email").click().run()
        self.assertFalse(app.exception)
        by_label(app.button, "Sign out").click().run()
        app.text_input(key="login_name").set_value("alice@example.test")
        app.text_input(key="login_password").set_value("Testing only password 123")
        by_label(app.button, "Sign in").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["account_data"]["email"], "alice@example.test")

    def test_verification_link_is_removed_from_url_and_requires_confirmation(self):
        self.db.set_email(self.db.login("alice", "Testing only password 123"), "alice@example.test", "Testing only password 123")
        _, token = self.db.request_email_action("alice@example.test", "verify")
        app = AppTest.from_file(str(APP), default_timeout=30)
        app.query_params["email_action"] = "verify"
        app.query_params["email_token"] = token
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn("email_token", app.query_params)
        self.assertFalse(self.db.load(self.db.login("alice", "Testing only password 123"))["email_verified"])
        by_label(app.button, "Confirm email verification").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(self.db.load(self.db.login("alice", "Testing only password 123"))["email_verified"])
        self.assertFalse(any(token in item.value for item in app.code))

    def test_email_reset_screen_revokes_sessions(self):
        old = self.db.login("alice", "Testing only password 123")
        self.db.set_email(old, "alice@example.test", "Testing only password 123")
        _, verify = self.db.request_email_action("alice@example.test", "verify")
        self.db.consume_email_action(verify, "verify")
        with self.db.engine.begin() as db:
            db.execute(text("UPDATE email_requests SET next_allowed=0"))
        _, token = self.db.request_email_action("alice@example.test", "reset")
        app = AppTest.from_file(str(APP), default_timeout=30)
        app.query_params["email_action"] = "reset"
        app.query_params["email_token"] = token
        app.run()
        by_label(app.text_input, "New password").set_value("New temporary testing password 456")
        by_label(app.text_input, "Confirm new password").set_value("New temporary testing password 456")
        by_label(app.button, "Save new password").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["recovery_code"])
        with self.assertRaises(AccountError):
            self.db.load(old)
        self.assertTrue(self.db.login("alice@example.test", "New temporary testing password 456"))

    def test_email_enabled_registration_opens_home_before_verification(self):
        with patch("account_ui.configured_mailer", return_value=object()), patch("account_ui.queue_email_action") as deliver:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            by_label(app.text_input, "Choose a username").set_value("bob")
            by_label(app.text_input, "Email address").set_value("bob@example.test")
            by_label(app.text_input, "Choose a password").set_value("Testing only password 123")
            by_label(app.text_input, "Confirm password").set_value("Testing only password 123")
            by_label(app.button, "Create account").click().run()
            deliver.assert_called_once()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "INR 0.00")
            self.assertEqual(app.session_state["account_data"]["email"], "bob@example.test")
            self.assertFalse(app.session_state["account_data"]["email_verified"])
            self.assertTrue(app.session_state["auth_token"])


if __name__ == "__main__":
    unittest.main()
