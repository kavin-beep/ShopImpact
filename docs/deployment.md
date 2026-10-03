# Public deployment

Live app: [ShopImpact on Streamlit Community Cloud](https://shopimpact-duy7hphexgoshhqfexfmkt.streamlit.app/). The public sign-in page was checked in the browser after deployment: it loads without a startup error and shows Sign in, Create account and Recover account. This check did not create or modify any live account.

This workspace uses Neon PostgreSQL through ignored private settings. On 2 October 2026, connection, schema creation, registration, login, two-account isolation, persistence across new connections, stale-edit rejection and logout passed locally with Neon. Temporary QA accounts were deleted. Full account workflows on the public deployment, server redeployment and provider backup restoration still need verification. Without hosted settings, the app uses local SQLite.

## Prerequisites

Choose a GitHub repository, a hosted PostgreSQL provider and Streamlit Community Cloud account. Confirm database pricing and backup retention with the provider before provisioning. Use the assessment repository naming convention with the actual student ID and name. Never commit connection strings, private databases, session tokens or recovery codes.

## Configure

For first-time hosted setup, follow the [Neon walkthrough](neon-setup.md). The terminal helper validates the connection and saves credentials in ignored private settings.

Put these values in Streamlit Cloud's private Secrets settings, using real values from the database provider:

```toml
SHOPIMPACT_PUBLIC = true
SHOPIMPACT_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

Use the provider's recommended TLS connection string, preferably certificate-verified when supported. URL-encode special characters in credentials. Use a dedicated database user with access only to this app's database. The app creates users, sessions, attempts, email_actions and email_requests tables on first startup; the account needs those initial permissions. Consider reducing privileges after provisioning.

For local configuration, copy `.streamlit/secrets.example.toml` to ignored `.streamlit/secrets.toml` and replace the placeholders. Environment variables with the same names are also supported. Do not enable public mode with SQLite: startup will reject it. Streamlit's authentication and data connections must be served over HTTPS when public.

## Publish and verify

1. Upload source, data, assets, tests and documentation. Exclude `.venv`, `personal_data`, real secrets and scratch files.
2. Set app entrypoint `app.py`, Python 3.12 and install the pinned requirements.
3. Add the database secrets and deploy on Streamlit Community Cloud.
4. Create two temporary accounts. Verify one cannot see the other's purchases, exports or preferences. Verify recovery and sign-out.
5. Confirm saved entries survive a server restart/redeployment and that the database provider's backup restoration works.
6. Check narrow screens, keyboard use, contrast, uploads/downloads and recovery-code visibility.
7. Delete temporary test accounts. Add the actual live URL, GitHub URL and screenshots to the README and final submission.

## Operations and limits

Local and hosted modes share the SQLAlchemy storage layer. PostgreSQL-specific execution still needs the above deployment smoke tests. SQLite file backup is sufficient for local development only; back up safely while the local app is stopped. Account deletion removes live account data and sessions; provider backups may retain deleted records until their retention period ends.

This release supports email-or-username/password login and uses recovery codes for password recovery. Email verification and password-reset links are implemented and await private Gmail sender setup and real delivery checks; see email-setup.md. Signup signs the user in and opens the home page immediately. Verification is optional for dashboard access; email reset links require a verified address. Configure the actual public HTTPS app URL for links, check SMTP access from the hosting environment, and verify inbox delivery before public launch. Existing databases receive a nullable email column and unique index automatically; existing accounts keep working with their usernames and can link an email after confirming their password. New UI registrations require email. Recovery codes must be stored by the account holder; the app cannot retrieve the originals. Session expiry is 12 hours. Email and username aliases share a failed-attempt counter for an existing account; public growth would also require infrastructure-level abuse controls, monitoring, dependency updates and an independent security review. Do not describe the application as independently audited.

Official persistence guidance: https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
