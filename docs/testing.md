# Test evidence

Verified on 3 October 2026 with Python 3.12.14 and Streamlit 1.55.0.

## Automated checks

All 83 tests pass using `python -m unittest discover -s tests -v`. `python -m pip check` reports no broken requirements.

Twenty core tests cover Decimal arithmetic, validation, month/year boundaries, totals, badge thresholds, category alternatives, source-factor derivation, no invented reuse discount, backup validation, explicit legacy migration and CSV formula neutralization. Sixteen account tests cover isolation, persistence across a new database connection, salted hashes, weak/duplicate credentials, lockout, conflicting saves, recovery rotation, session revocation/expiry, password-reset races during login, deletion and rejection of SQLite in public mode. Thirteen Streamlit tests cover the login gate, empty state, invalid input, purchase editing/deletion, persistent preferences, registration, filtered edit choices and immediate goal changes in Insights.

Seven Insights tests cover year boundaries, empty calendar months, exact totals and rounded averages, missing versus zero-spend baselines, combined filters and numeric sorting without changing saved records.

Seven setup-helper tests verify TLS requirements, provider parameters, hidden credentials in error messages and unchanged settings after connection failure, including clipboard setup and safe connection diagnostics. They use mocks and do not connect to an external database.

All automated account tests use temporary databases. They do not write to personal accounts. The sample purchase fixture has 15 synthetic records and is not loaded into the live application.

Email coverage includes case-insensitive matching, invalid and duplicate email rejection, shared login lockout across aliases, password-confirmed linking/change, recovery by email and repeatable migration of an existing SQLite database with purchases and sessions preserved. UI checks exercise email registration/login and adding an email to an existing account. Explicit environment settings override private file settings, so UI tests stay isolated even when this workspace is configured for Neon.

The email migration was also applied to Neon and verified with a temporary account: case-insensitive email login, username login, duplicate-email rejection and password-confirmed email change passed. The temporary account was deleted. Chrome confirmed the hosted-configured app shows the email-or-username sign-in field and email registration field, and the sign-in screenshot was refreshed.

On 3 October 2026, nine email-action tests and six SMTP/link tests passed with no real email delivery. They cover verification gating, hashed and single-use tokens, expiry, purpose isolation, resend cooldown, email-change invalidation, recovery-code invalidation, concurrent token claims, reset session revocation, deletion cleanup, trusted link addresses and verified SSL/STARTTLS. Three additional interface tests cover verification confirmation, query-token removal, reset completion and immediate home-page access after signup even when delivery is enabled. The sign-in screen has no Verify email tab; optional verification remains in the signed-in sidebar.

Neon checks also passed for verification gating, verification completion, email-link password reset, session revocation and replay rejection. The temporary account was deleted. Real Gmail authentication and inbox delivery are awaiting private sender configuration; no genuine message delivery is claimed yet.

## Browser evidence

On 3 October 2026, the redesigned sign-in page, dashboard, Insights, filtered history, rewards and saved contrast settings were reviewed in Chrome. At 390 pixels, the sign-in and collapsed-sidebar dashboard had no horizontal document overflow. Searching to zero matches hides edit/delete controls without changing saved purchases. Caption opacity was corrected so the chosen text colours remain readable. Updated images use 15 synthetic entries in a separate SQLite database. Streamlit's startup secret-file loading required explicitly directing this preview to its own settings file; it did not use real Neon accounts. The actual Neon-configured app's sign-in screen also loaded successfully after the changes.

After simplifying signup on 3 October 2026, Chrome verified the running Neon-backed app: the Verify email tab is absent, registration immediately opens the home dashboard, and subsequent sign-in works with both a case-normalized email and username. The synthetic QA account was deleted. The sign-in screenshot was refreshed.

A service-cache regression test verifies that a reloaded account implementation receives a fresh cached service. This prevents stale exception classes from escaping interface error handling while developing. A separate interface test confirms incorrect credentials produce a normal message without crashing. Existing SQLite accounts still do not automatically migrate to Neon.

An isolated QA server and test database were used for actual Chrome browser checks. Registration, sign-in, purchase entry, Repair Champion/Turtle display, JSON download, deletion followed by JSON restoration, saved contrast preferences and persistence after refresh were verified. The 390-pixel mobile view with the sidebar collapsed had no horizontal document overflow. Desktop and mobile screenshots were inspected. Screenshot evidence is in `docs/screenshots/`. QA identities and the shop shown in screenshots are fictional test inputs.

Review found low-contrast primary-button text under the contrast override. The stylesheet now preserves white text on a dark green primary button and darkens captions. No user feedback is claimed: this was an implementation review.

The Turtle SVG is generated successfully through Python Turtle navigation. The optional desktop preview still depends on working Tk and remains unverified in the bundled runtime.

## Remaining checks

The pre-repository review on 3 October 2026 reran all 79 tests successfully in the project virtual environment and found no broken installed requirements. The new UI regression test deliberately supplies invalid email settings, verifies a safe warning without exposing the setting, signs in, saves a purchase, and confirms that email reset remains disabled. Email failure no longer prevents access to the shopping app. The test uses a disposable SQLite database; this review did not send real emails or modify live Neon accounts.

Git ignore rules were checked using temporary Git metadata without initializing a repository in this project. Private settings, databases, virtual environments, environment files and recovery-code downloads are excluded; example settings remain included. A targeted credential-pattern scan of eligible text files found no real credentials. Five matching database strings in setup tests were reviewed as synthetic fixtures. This is a targeted check, not an independent security audit.

Neon PostgreSQL was verified separately on 2 October 2026. Live checks passed for connection, schema creation, registration, login, two-account isolation, saved purchases across new database connections, stale-edit rejection and logout. Temporary QA accounts were deleted. The actual app's sign-in page rendered with hosted settings. This is additional live evidence, separate from the 79 automated tests.

Full keyboard and screen-reader accessibility, human usability feedback, Streamlit Cloud deployment/redeployment and provider backup restoration remain unverified. The narrow-screen screenshot is evidence of that viewport only, not a certification for every browser/device. A source-backed estimate remains approximate and is not independently validated carbon accounting.

Collect real feedback with `docs/usability-feedback.md`, record improvements, and smoke-test the public deployment and database restart/restore procedures before final submission.

## 2026 data and design update

On 5 October 2026, all 83 tests passed. Three new checks cover older-backup opt-in, immutable recalculation and confirmation before changing saved estimates. See [2026 update](2026-update.md) for source evidence and compatibility. Earlier browser evidence and PDF guides describe the prior release.
