"""Local-only browser alternative to terminal database setup."""
import contextlib
import io
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.connect_database import configure_database, validate_url

st.set_page_config(page_title="ShopImpact database setup", page_icon="🌿", layout="centered")

if st.get_option("server.address") not in {"127.0.0.1", "localhost", "::1"}:
    st.error("This setup page must run locally with --server.address 127.0.0.1.")
    st.stop()

st.title("🌿 ShopImpact database setup")
st.write("Copy the current PostgreSQL connection string from Neon's Connect panel, then paste it below.")
st.caption("This page runs on your computer. The connection string is saved in private app settings after a successful connection.")
st.info("Local accounts stay in the local database. Export purchases before switching if you want to bring them into a hosted account.")

with st.form("database_setup", clear_on_submit=True):
    connection_string = st.text_input("Database connection string", type="password",
                                      placeholder="postgresql://…", max_chars=4096)
    connect = st.form_submit_button("Connect database", type="primary")

if connect:
    try:
        url = validate_url(connection_string)
    except Exception:
        st.error("Copy the full PostgreSQL URI from Neon, including sslmode=require. Your connection string has not been saved.")
    else:
        messages = io.StringIO()
        with st.spinner("Checking the database connection…"), contextlib.redirect_stdout(messages):
            result = configure_database(url)
        if result == 0:
            st.success("Connected. Private settings saved. Return to the chat so we can restart ShopImpact.")
            st.link_button("Open ShopImpact", "http://127.0.0.1:8501")
        else:
            st.error(messages.getvalue().strip())
