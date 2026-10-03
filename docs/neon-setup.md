# Set up the hosted database with Neon

Neon provides managed PostgreSQL and offers a Free plan. Review the plan displayed during signup; do not choose a paid plan or add billing unless you intend to do so. See https://neon.com/pricing for current limits.

1. Open https://console.neon.tech/ and sign up or sign in. You can choose the GitHub sign-in option for your own GitHub account.
2. Create a project named `shopimpact`. Select the Free plan if asked. Keep the default PostgreSQL version. Select a region close to the eventual Streamlit app server, or the nearest offered region if it is not known yet.
3. Use the project's **Connect** panel to copy its PostgreSQL connection string. Keep `sslmode=require` and any provider-supplied security parameters. Copy the URI beginning `postgresql://`, not the surrounding `psql` command.
4. In the SA PYTHON folder's VS Code terminal run:

```powershell
.\.venv\Scripts\python.exe tools/connect_database.py
```

5. Paste the connection string into the hidden terminal prompt and press Enter. The script checks the connection, creates the account tables and saves `.streamlit/secrets.toml`, which Git ignores. It does not print the credential.
   If terminal pasting does not work on Windows, run the helper with `--clipboard`. Copy the URI from Neon, return to the setup window and press Enter. No pasting is needed; the helper reads the local clipboard privately.
6. Restart the app. Register a new hosted account and test saving a purchase, refreshing and signing in again. Local SQLite accounts are not automatically migrated. You can export purchases from the local account before switching and restore them into your hosted account; recovery codes and passwords are not part of purchase exports.

When publishing to Streamlit Cloud, put the same private settings into the app's Secrets panel. Do not upload the secrets file to GitHub or paste the connection string into chat. Complete the two-account isolation and restart checks in `deployment.md` before marking the public launch ready.

References: https://neon.com/docs/get-started-with-neon/connect-neon and https://neon.com/pricing

## Browser setup alternative

If the terminal window or paste shortcut is unavailable, start a local setup page:

```powershell
.\.venv\Scripts\python.exe -m streamlit run tools/database_setup_ui.py --server.address 127.0.0.1 --server.port 8503
```

Open http://127.0.0.1:8503 and paste the current URI into the password field, then choose **Connect database**. This helper refuses to run on a non-local server address. It is an owner setup tool; do not deploy it publicly. Stop it when configuration is complete.
