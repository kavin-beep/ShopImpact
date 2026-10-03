# Gmail verification and password-reset delivery

The flows are implemented, but live delivery remains disabled until private sender settings are configured and checked. Neon stores accounts and hashed action tokens; Gmail delivers the emails.

## Connect Gmail locally

1. In your Google Account, enable 2-Step Verification and create a Google app password named **ShopImpact** at https://myaccount.google.com/apppasswords. Some work/school accounts or account security configurations do not allow app passwords. Use Google's instructions: https://support.google.com/accounts/answer/185833.
2. Start the local setup page:

```powershell
.\.venv\Scripts\python.exe -m streamlit run tools/email_setup_ui.py --server.address 127.0.0.1 --server.port 8504
```

3. Open http://127.0.0.1:8504. Enter the sender Gmail address, its Google app password and the app address. During local testing use `http://127.0.0.1:8501`.
4. Choose **Connect Gmail and send test email**. The helper sends only to the sender address, verifies that Gmail accepts the message, and atomically saves settings to ignored `.streamlit/secrets.toml`. It preserves database settings. Check the inbox/spam folder; provider acceptance alone does not confirm inbox delivery.
5. Restart ShopImpact so Streamlit reloads its private settings. Stop the owner setup page after completion. It refuses to run on a non-local server address and must never be deployed publicly.

Do not put the normal Google password, app password, database password or action links in chat or GitHub. Public hosting uses private Streamlit Secrets and an HTTPS app URL in `SHOPIMPACT_APP_URL`. Never use a localhost address in public verification/reset emails. Check outbound SMTP access on the deployed host; local Gmail success does not prove cloud delivery.

## User experience

- Creating an account automatically signs the user in and opens the home page. Verification does not block dashboard access or subsequent sign-in. Existing purchases, passwords and usernames are preserved. Save the recovery code from the home page's expandable panel.
- The sign-in page has only **Sign in**, **Create account** and **Recover account** tabs. Optional verification is available under **Account email** in the signed-in sidebar. When delivery is enabled, registration sends a verification link in the background. Links last 24 hours and require pressing the confirmation button; merely opening a link does not consume it. Verify the address to enable email password resets.
- **Recover account** offers a reset email for a verified address and the original recovery-code option. Reset links last 30 minutes. A successful reset rotates the recovery code, revokes sessions and sends a change notice.
- Changing the sign-in email requires the current password, clears verification, invalidates old links and requests verification for the new address. The old address receives a change notice when delivery is enabled.

## Implementation and checks

Cryptographically random tokens are stored as SHA-256 hashes in `email_actions`, bound to action type, email address and the current password hash. PostgreSQL/SQLite `DELETE RETURNING` claims each token atomically. Invalid, expired, wrong-purpose, consumed and stale links are rejected. Password/recovery changes and deletion invalidate outstanding email links.

Email requests use a 60-second per-address cooldown stored in the database. The browser gives the same immediate response for known, unknown, ineligible and rate-limited addresses; delivery runs through a bounded background worker. SMTP uses SSL or required STARTTLS with certificate verification. Links use the private configured app address, not an incoming request host. Query tokens are removed from the address bar before the action screen renders.

The worker queue is in memory: a server restart can drop queued mail. Users can request again after the cooldown. Requests do not confirm that an account exists or that an email reached the inbox. A larger public service needs a durable delivery queue, delivery monitoring and wider abuse controls. Verify real inbox delivery and complete signup/reset flows before calling live email deployment complete.

References: [Python SMTP](https://docs.python.org/3/library/smtplib.html), [OWASP password-reset guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
