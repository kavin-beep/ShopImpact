"""Configure hosted PostgreSQL privately from the project's terminal."""
import getpass
import argparse
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import toml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def validate_url(raw):
    url = make_url(raw.strip())
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("Use a PostgreSQL connection string, starting with postgresql://.")
    if not url.host or not url.database or not url.username or not url.password:
        raise ValueError("The connection string must contain host, database, username and password.")
    if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("Use your provider's TLS connection string, including sslmode=require or stronger.")
    return url.set(drivername="postgresql+psycopg")


def read_clipboard():
    """Read locally without putting credentials in arguments or terminal output."""
    if os.name != "nt":
        raise ValueError("Clipboard setup requires Windows.")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); Get-Clipboard -Raw"],
        capture_output=True, encoding="utf-8", timeout=10, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.stdout.strip()


def main(use_clipboard=False):
    print("ShopImpact hosted database setup")
    if use_clipboard:
        print("Copy your NEW PostgreSQL connection string from Neon's Connect panel.")
        print("Return to this window and press Enter. You do not need to paste anything.")
    else:
        print("Paste only the PostgreSQL URI, not a psql command. Input is hidden.")
    print("This creates ShopImpact tables in the chosen database and saves private app settings.")
    try:
        if use_clipboard:
            input("Press Enter after copying the connection string: ")
            raw = read_clipboard()
        else:
            raw = getpass.getpass("Database connection string: ")
        url = validate_url(raw)
    except Exception:
        # Do not echo parsing errors: third-party errors may include credentials.
        print("Invalid connection string. Use the complete PostgreSQL URI with TLS from the provider's Connect panel.")
        return 1
    return configure_database(url)


def connection_error_message(error):
    """Classify internally; never expose provider error text or credentials."""
    message = str(error).lower()
    reasons = [
        (("password authentication failed", "authentication failed"),
         "Neon rejected the database password. Copy a fresh connection string from Neon after resetting the role password."),
        (("could not translate host name", "failed to resolve host", "getaddrinfo"),
         "The database hostname could not be resolved. Check the copied host and internet connection."),
        (("timeout", "timed out"),
         "The database connection timed out. Check that Neon is active and your network allows PostgreSQL connections on port 5432."),
        (("connection refused", "network is unreachable", "permission denied"),
         "The network or database refused the connection. Check network access and the Neon endpoint."),
        (("channel binding", "ssl", "certificate"),
         "Secure connection negotiation failed. Copy the complete provider URI, keeping its TLS parameters."),
    ]
    for markers, reason in reasons:
        if any(marker in message for marker in markers):
            return reason + " No settings were changed."
    return "Connection failed. Check the database is active, the copied credentials, TLS and network access. No settings were changed."


def configure_database(url):
    """Validate connectivity and save settings; all output is credential-free."""
    engine = None
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 15})
        with engine.connect() as db:
            db.execute(text("SELECT 1"))
        from accounts import Accounts
        bounded_url = url.update_query_dict({"connect_timeout": "15"})
        accounts = Accounts(bounded_url.render_as_string(hide_password=False), public=True)
        accounts.engine.dispose()
    except Exception as error:
        print(connection_error_message(error))
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    destination = ROOT / ".streamlit/secrets.toml"
    destination.parent.mkdir(exist_ok=True)
    try:
        settings = toml.loads(destination.read_text(encoding="utf-8")) if destination.exists() else {}
        settings.update(SHOPIMPACT_PUBLIC=True, SHOPIMPACT_DATABASE_URL=url.render_as_string(hide_password=False))
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".private-", suffix=".tmp", delete=False) as output:
            output.write(toml.dumps(settings))
            temp_path = Path(output.name)
        os.replace(temp_path, destination)
    except Exception:
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)
        print("Database connected, but private settings could not be saved. Check folder permissions.")
        return 1
    print("Connected. Private settings saved to .streamlit/secrets.toml (excluded from Git).")
    print("Restart Streamlit to use the hosted database. Existing local accounts are not moved automatically.")
    print("For Streamlit Cloud, copy these settings into the app's private Secrets panel, never into the repository.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clipboard", action="store_true", help="Copy the URI and press Enter; no paste required (Windows).")
    raise SystemExit(main(use_clipboard=parser.parse_args().clipboard))
