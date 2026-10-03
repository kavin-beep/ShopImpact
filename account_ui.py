"""Small Streamlit account screens, separate from the shopping dashboard."""
import os
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from streamlit.errors import StreamlitSecretNotFoundError
from accounts import Accounts, AccountError
from email_delivery import mailer_from_settings, queue_email_action, queue_notice
from ui import brand_panel


@st.cache_resource
def _cached_account_service(url, public, require_verified_email, implementation_id):
    return Accounts(url or None, public=public, require_verified_email=require_verified_email)


def account_service(url, public, require_verified_email=False):
    # Streamlit can reload exception classes while retaining cached service objects.
    # Recreate the service when its implementation class changes, so errors are caught.
    return _cached_account_service(url, public, require_verified_email, id(Accounts))


account_service.clear = _cached_account_service.clear


def email_settings():
    keys = ["SHOPIMPACT_EMAIL_ENABLED", "SHOPIMPACT_SMTP_HOST", "SHOPIMPACT_SMTP_PORT",
            "SHOPIMPACT_SMTP_USERNAME", "SHOPIMPACT_SMTP_PASSWORD", "SHOPIMPACT_SMTP_FROM",
            "SHOPIMPACT_SMTP_SECURITY", "SHOPIMPACT_APP_URL"]
    settings = {}
    for key in keys:
        if key in os.environ:
            settings[key] = os.environ[key]
        else:
            try:
                if key in st.secrets:
                    settings[key] = st.secrets[key]
            except StreamlitSecretNotFoundError:
                pass
    return settings


def configured_mailer():
    if os.environ.get("SHOPIMPACT_EMAIL_ENABLED", "").lower() == "false":
        return None
    settings = email_settings()
    if str(settings.get("SHOPIMPACT_EMAIL_ENABLED", False)).lower() != "true":
        return None
    try:
        return mailer_from_settings(settings)
    except (ValueError, TypeError):
        # Email is optional: invalid owner settings must not lock users out.
        # Keep provider details and credentials out of the browser message.
        st.warning("Email delivery is temporarily unavailable. Sign-in and recovery codes still work. The app owner should check the email settings.")
        return None


EMAIL_REQUEST_MESSAGE = "If this address is eligible, an email will arrive shortly. Check spam too. Wait at least a minute before requesting another."


def email_link_screen(service, mailer):
    if "email_action" in st.query_params or "email_token" in st.query_params:
        action = st.query_params.get("email_action", "")
        token = st.query_params.get("email_token", "")
        if action in {"verify", "reset"} and 20 <= len(token) <= 100:
            st.session_state["email_link"] = (action, token)
        else:
            st.session_state["email_link"] = ("invalid", "")
        # Remove bearer credentials from the address bar before showing other content.
        st.query_params.clear()
    if "email_link" not in st.session_state:
        return
    action, token = st.session_state["email_link"]
    st.markdown('<meta name="referrer" content="no-referrer">', unsafe_allow_html=True)
    st.title("Verify your email" if action == "verify" else "Reset your password")
    if action == "verify":
        if st.button("Confirm email verification", type="primary"):
            try:
                service.consume_email_action(token, "verify")
                st.session_state.pop("account_data", None)
                st.session_state.pop("email_link", None)
                st.success("Email verified. You can now sign in.")
            except AccountError as error:
                st.error(str(error))
            except SQLAlchemyError:
                st.error("The database is unavailable. Please try again.")
    elif action == "reset":
        with st.form("email_password_reset", clear_on_submit=True):
            password = st.text_input("New password", type="password", max_chars=128)
            confirmation = st.text_input("Confirm new password", type="password", max_chars=128)
            submitted = st.form_submit_button("Save new password", type="primary")
        if submitted:
            try:
                if password != confirmation:
                    raise AccountError("Passwords do not match.")
                reset = service.consume_email_action(token, "reset", password)
                recovery = reset["recovery_code"]
                if mailer:
                    queue_notice(mailer, reset["email"], "ShopImpact password changed",
                                 "Your ShopImpact password was changed. All previous sign-in sessions were revoked. If you did not request this, use your recovery code to secure your account.")
                st.session_state.clear()
                st.session_state.recovery_code = recovery
                st.success("Password changed. All previous sessions were signed out. Save your new recovery code below.")
                st.code(recovery)
            except AccountError as error:
                st.error(str(error))
            except SQLAlchemyError:
                st.error("The database is unavailable. Please try again.")
    else:
        st.error("This link is invalid. Request a new email.")
    if st.button("Return to sign in"):
        st.session_state.pop("email_link", None)
        st.session_state.pop("auth_token", None)
        st.session_state.pop("account_data", None)
        st.rerun()
    st.stop()


def request_email_form(service, mailer, purpose):
    label = "Send verification email" if purpose == "verify" else "Send password-reset email"
    with st.form("request_" + purpose, clear_on_submit=True):
        email = st.text_input("Verification email address" if purpose == "verify" else "Password-reset email address", max_chars=254)
        submitted = st.form_submit_button(label, disabled=mailer is None)
    if submitted:
        try:
            queue_email_action(service, mailer, email, purpose)
            st.success(EMAIL_REQUEST_MESSAGE)
        except AccountError as error:
            st.error(str(error))


def sign_out(service):
    if st.session_state.get("auth_token"):
        service.logout(st.session_state.auth_token)
    st.session_state.clear()
    st.rerun()


def require_account():
    url = os.environ.get("SHOPIMPACT_DATABASE_URL", "")
    public = os.environ.get("SHOPIMPACT_PUBLIC", "false").lower() == "true"
    try:
        if "SHOPIMPACT_DATABASE_URL" not in os.environ and st.secrets.get("SHOPIMPACT_DATABASE_URL", None):
            url = st.secrets["SHOPIMPACT_DATABASE_URL"]
        if "SHOPIMPACT_PUBLIC" not in os.environ:
            public = bool(st.secrets.get("SHOPIMPACT_PUBLIC", False))
    except StreamlitSecretNotFoundError:
        pass
    try:
        mailer = configured_mailer()
    except Exception:
        st.error("Email delivery settings are incomplete. Contact the app owner.")
        st.stop()
    try:
        service = account_service(url, public, False)
    except (AccountError, SQLAlchemyError):
        st.error("The account database is unavailable or not configured for this deployment. Contact the app owner.")
        st.stop()

    email_link_screen(service, mailer)

    if st.session_state.get("auth_token"):
        try:
            saved = service.load(st.session_state.auth_token)
        except AccountError:
            st.session_state.clear()
            st.warning("Your session expired. Sign in again to open your saved purchases.")
            st.rerun()
        except SQLAlchemyError:
            st.error("We cannot reach your saved data. Please try again shortly.")
            st.stop()
        if "account_data" not in st.session_state:
            st.session_state.account_data = saved
        return service, st.session_state.account_data, mailer

    introduction, authentication = st.columns([1, 1.08], gap="large")
    with introduction:
        brand_panel()
    with authentication:
        st.title("Welcome to ShopImpact")
        st.write("A fresh start, or right where you left off.")
        login, register, recover = st.tabs(["Sign in", "Create account", "Recover account"])
        with login:
            with st.form("login"):
                name = st.text_input("Email or username", key="login_name", max_chars=254)
                password = st.text_input("Password", type="password", key="login_password", max_chars=128)
                if st.form_submit_button("Sign in", type="primary"):
                    try:
                        st.session_state.auth_token = service.login(name, password)
                        st.session_state.pop("recovery_code", None)
                        st.rerun()
                    except AccountError as error:
                        st.error(str(error))
                    except SQLAlchemyError:
                        st.error("Sign-in is temporarily unavailable. Please try again.")
        with register:
            with st.form("register", clear_on_submit=True):
                name = st.text_input("Choose a username", max_chars=40)
                email = st.text_input("Email address", max_chars=254, placeholder="name@example.com")
                password = st.text_input("Choose a password", type="password", max_chars=128,
                                         help="12–128 characters. A long, unique passphrase works well.")
                confirmation = st.text_input("Confirm password", type="password", max_chars=128)
                if st.form_submit_button("Create account"):
                    created = False
                    try:
                        if password != confirmation:
                            raise AccountError("Passwords do not match.")
                        st.session_state.recovery_code = service.register(name, password, email=email)
                        created = True
                        st.session_state.auth_token = service.login(email, password)
                        st.session_state.pop("account_data", None)
                        st.session_state.account_created = True
                        if mailer:
                            queue_email_action(service, mailer, email, "verify")
                        st.rerun()
                    except AccountError as error:
                        st.error(str(error))
                    except SQLAlchemyError:
                        st.error("Your account was created, but automatic sign-in is temporarily unavailable. Use Sign in to continue." if created else "We could not create the account. Please try again.")
        with recover:
            if mailer:
                st.write("Request a reset link for your verified email address.")
            else:
                st.info("Email delivery is unavailable. Use your saved recovery code below.")
            request_email_form(service, mailer, "reset")
            st.divider()
            st.write("Use the recovery code you saved when creating your account. Resetting your password signs out all existing sessions.")
            with st.form("recovery", clear_on_submit=True):
                name = st.text_input("Account email or username", max_chars=254)
                code = st.text_input("Recovery code", type="password", max_chars=100)
                password = st.text_input("New password", type="password", max_chars=128)
                confirmation = st.text_input("Confirm new password", type="password", max_chars=128)
                if st.form_submit_button("Reset password"):
                    try:
                        if password != confirmation:
                            raise AccountError("Passwords do not match.")
                        st.session_state.recovery_code = service.reset_password(name, code, password)
                        st.success("Password changed. Save your replacement recovery code and sign in.")
                    except AccountError as error:
                        st.error(str(error))
                    except SQLAlchemyError:
                        st.error("Password reset is temporarily unavailable.")
        if st.session_state.get("recovery_code"):
            st.warning("Save this recovery code privately before signing in. It can recover your account if email delivery is unavailable.")
            st.code(st.session_state.recovery_code)
            st.download_button("Download recovery code", st.session_state.recovery_code,
                               "shopimpact-recovery-code.txt", "text/plain")
        st.caption("Each account has its own saved purchases and settings. Passwords are hashed. Purchases are visible to the database administrator; they are not end-to-end encrypted.")
        st.caption("Password-reset emails are available for verified addresses." if mailer else "Email password resets are unavailable. Keep your recovery code safe.")
        st.stop()


def save_account(service, data, purchases=None, settings=None):
    purchases = data["purchases"] if purchases is None else purchases
    settings = data["settings"] if settings is None else settings
    try:
        revision = service.save(st.session_state.auth_token, purchases, settings, data["revision"])
    except AccountError as error:
        st.error(str(error))
        return False
    except SQLAlchemyError:
        st.error("The change was not saved. Your previous data is safe; please try again.")
        return False
    data.update(purchases=purchases, settings=settings, revision=revision)
    return True
