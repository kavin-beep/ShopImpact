"""Owner-only local Gmail setup. Never deploy this page publicly."""
from pathlib import Path
import os
import sys
import tempfile

import streamlit as st
import toml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from accounts import email_key
from email_delivery import Mailer

st.set_page_config(page_title="ShopImpact Gmail setup", page_icon="✉️", layout="centered")
if st.get_option("server.address") not in {"127.0.0.1", "localhost", "::1"}:
    st.error("This setup page must run locally with --server.address 127.0.0.1.")
    st.stop()

st.title("✉️ ShopImpact Gmail setup")
st.write("Connect the Gmail account that will send ShopImpact verification and password-reset emails.")
st.markdown("1. Enable Google **2-Step Verification**.\n2. Create an app password named **ShopImpact**.\n3. Enter it below with your Gmail address.")
st.link_button("Create a Google app password", "https://myaccount.google.com/apppasswords")
st.caption("Use a Google app password, not your normal Google password. Keep it out of chat and GitHub.")
st.info("Connecting sends one test email to the sender address. Verification is optional for sign-in and dashboard access; a verified address enables email password resets. Existing purchases remain saved.")
with st.form("gmail_setup", clear_on_submit=True):
    sender = st.text_input("Sender Gmail address", max_chars=254, placeholder="yourname@gmail.com")
    password = st.text_input("Google app password", type="password", max_chars=100)
    app_url = st.text_input("ShopImpact app address", value="http://127.0.0.1:8501", max_chars=500,
                            help="Use the localhost address while testing. Replace it with the live HTTPS URL after deployment.")
    connect = st.form_submit_button("Connect Gmail and send test email", type="primary")

if connect:
    temporary = None
    try:
        sender = email_key(sender)
        password = password.replace(" ", "").strip()
        if not password:
            raise ValueError("Missing app password")
        mailer = Mailer("smtp.gmail.com", 465, sender, password, sender, app_url)
        with st.spinner("Checking Gmail and sending your test email…"):
            mailer.send_message(sender, "ShopImpact email setup test",
                                "ShopImpact can send emails through this Gmail account. Return to the setup page and the chat to finish enabling verification and password-reset links.")
        destination = ROOT / ".streamlit/secrets.toml"
        settings = toml.loads(destination.read_text(encoding="utf-8")) if destination.exists() else {}
        settings.update(SHOPIMPACT_EMAIL_ENABLED=True, SHOPIMPACT_SMTP_HOST="smtp.gmail.com",
                        SHOPIMPACT_SMTP_PORT=465, SHOPIMPACT_SMTP_SECURITY="ssl",
                        SHOPIMPACT_SMTP_USERNAME=sender, SHOPIMPACT_SMTP_FROM=sender,
                        SHOPIMPACT_SMTP_PASSWORD=password, SHOPIMPACT_APP_URL=mailer.base_url)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".private-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(toml.dumps(settings))
        os.replace(temporary, destination)
        st.success("Gmail connected and test email accepted by Gmail. Private settings saved. Check your inbox, then tell us to restart ShopImpact.")
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        st.error("Gmail setup failed. Check your Gmail address, Google app password, app address and internet access. Private settings were not changed. Google may require 2-Step Verification or may restrict app passwords on some accounts.")
