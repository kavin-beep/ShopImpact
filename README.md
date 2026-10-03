# ShopImpact Conscious Shopping Dashboard

ShopImpact is a Python and Streamlit shopping tracker with separate accounts, saved purchase histories, monthly goals and estimates based on published emissions data. It implements Scenario 1 of the Year 1 Python Programming assessment.

## Run in VS Code

Open this entire SA PYTHON folder and run these commands in its PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --no-cache-dir
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

On another computer, install Python 3.12 and first run `py -3.12 -m venv .venv`. VS Code tasks and the Run ShopImpact debug configuration are included. Debugging requires Microsoft's Python and Python Debugger extensions.

Open the URL printed in the terminal, normally http://localhost:8501. Create your own account, save the recovery code privately, and sign in. Accounts start empty; no demo purchases are loaded. Closing or refreshing the page signs you out but does not delete saved purchases. Sessions expire after 12 hours.

## Features

- Registration with email, email-or-username/password sign-in, sign-out and recovery-code password reset.
- Existing accounts can add or change their sign-in email after confirming their current password.
- Private purchase histories and settings saved across restarts.
- Product type, brand/shop, price and date input with instant estimate preview.
- Month/year dashboard with spending, estimated kg CO2e, charts and goals.
- Polished green-and-cream interface, split sign-in page, responsive cards and readable contrast settings.
- Six-month Insights with logged spending/impact trends, average purchases, goal balance and previous-calendar-month comparison.
- Eco Saver, Low Impact Shopper and Repair Champion achievements.
- Conditional Turtle artwork, rotating tips and high contrast.
- Category alternatives, named reuse/repair options with official links, and price-based comparison with visible assumptions.
- Search, month/category filters, date/price/impact sorting, filtered CSV downloads, editing, deletion and JSON backup/restore.
- Confirmed account deletion and protection against conflicting edits in multiple tabs.

## Data and calculations

The original invented factors have been replaced by US EPA Supply Chain GHG Emission Factors v1.3.0, in kg CO2e per 2022 USD. INR reference factors use the World Bank's 2022 annual-average exchange rate. Values, source rows, category mappings and source URLs are included in `data/emission_sources.json` and `data/product_catalog.json`.

These are **rough reference estimates**. US sector averages, broad category mappings, a fixed historical exchange rate and unadjusted current prices are not a validated India-specific product footprint. New and reused versions use the same underlying factor; no unsupported reuse discount is invented. Read [methodology](docs/methodology.md).

## Files and integration

| File | Responsibility |
| --- | --- |
| app.py | Shopping interface, dashboard, goals, editing and backups |
| account_ui.py | Account screens and authenticated save flow |
| accounts.py | Argon2id passwords, sessions, recovery and database storage |
| logic.py | Decimal calculations, purchase dictionaries, monthly summaries, badge rules |
| insights.py | Six-month trends, goal balance and filtered history views |
| ui.py | Shared visual styling and sign-in branding |
| storage.py | Validated JSON import/export and spreadsheet-safe CSV |
| data/ | Product catalog, published source evidence and tips |
| tools/draw_rewards.py | Turtle leaf generation and optional desktop preview |
| tests/ | Disposable account/UI tests and synthetic purchase fixtures |
| docs/ | Design, methodology, test evidence, deployment and assessment checklist |

## Storage and privacy

Without hosted settings, accounts are stored in `personal_data/shopimpact.db`, excluded from Git. This workspace is now configured to use Neon PostgreSQL through private settings. Local SQLite accounts are not automatically migrated; export purchases before switching and restore them into a hosted account if needed. Each account has isolated purchases and settings. Passwords use salted Argon2id hashes; session and recovery tokens are stored as hashes. Five failed login/recovery attempts block that identifier for 15 minutes. Recovery rotates the code and revokes previous sessions. The database administrator can access purchase data; it is not end-to-end encrypted.

Purchases save automatically on successful add/edit/delete/restore. Goals and appearance save through their labelled button. Purchase JSON backups exclude credentials, sessions and settings. Imports support 1,000 records and 2 MB. Legacy illustrative backups require an explicit migration checkbox and have estimates recalculated. Downloaded backups remain on your computer after account deletion.

New registrations require a unique email address. Existing accounts keep their usernames, passwords and purchases after additive migrations. Add an email in the sidebar's **Account email** panel. Email matching ignores case; username and email sign-in share the account's failed-attempt counter.

Creating an account automatically signs the user in and opens the home dashboard. The sign-in page contains Sign in, Create account and Recover account tabs. The recovery code can be saved from an expandable panel on the home page.

Email verification and password-reset links are implemented. Gmail delivery is awaiting private sender setup; use the [Gmail setup guide](docs/email-setup.md). Verification is optional for dashboard access and available from the sidebar's Account email panel; a verified address is required for email password-reset links. Links expire, can be used once and are invalidated by relevant account changes. Resetting a password signs out existing sessions and replaces the recovery code. Google OAuth sign-in is not implemented.

## Turtle

```powershell
.\.venv\Scripts\python.exe tools/draw_rewards.py
.\.venv\Scripts\python.exe tools/draw_rewards.py --preview
```

The default command uses `turtle.TNavigator` with an SVG pen adapter. The optional preview uses `turtle.Turtle` and requires working Tk. The app displays the generated SVG when a qualifying choice exists; it is not a live browser Turtle animation. Desktop preview remains unverified in the bundled runtime. Confirm assessment acceptance of the SVG integration.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

79 automated tests pass (3 October 2026), covering calculations, factor provenance, account isolation, persistence, recovery, rate limiting, concurrent saves, trends, filtering and interface workflows. Tests use disposable databases and do not write to real accounts. The 15-purchase synthetic fixture exists only for testing. See [test evidence](docs/testing.md).

## Deployment and assessment

The [repository readiness review](docs/repository-readiness.md) records the final checks and remaining launch/submission work. Invalid optional email settings now leave sign-in, shopping and recovery-code access available; email reset buttons remain disabled until valid settings are provided.

The [ten-page code and data guide](output/pdf/ShopImpact_10_Page_Explanation.pdf) is included for learning and review. Its test count describes the earlier 78-test snapshot; the current suite includes one additional regression test. It is separate from the final assessment submission document.

See [deployment instructions](docs/deployment.md). Neon PostgreSQL was connected and verified on 2 October 2026: registration, login, account isolation, purchase persistence across new connections, conflicting-save protection and logout passed. Temporary QA accounts were deleted, and the actual app's sign-in page loaded with hosted settings. Public Streamlit Cloud deployment, redeployment persistence and provider backup restoration remain pending.

Start hosted database setup with the [Neon walkthrough](docs/neon-setup.md) and private terminal helper.

Public app URL: pending deployment.

GitHub repository: [kavin-beep/ShopImpact](https://github.com/kavin-beep/ShopImpact).

Real participant feedback, assessor access and the final submission PDF remain pending. See [requirements](docs/requirements.md) and [feedback template](docs/usability-feedback.md). Screenshots use an isolated QA account and fictional input, not a preloaded demo workspace.

## References

- [EPA dataset](https://catalog.data.gov/dataset/supply-chain-greenhouse-gas-emission-factors-v1-3-by-naics-6)
- [World Bank 2022 INR exchange rate](https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF?date=2022&format=json)
- [Streamlit database guidance](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data)
- [Python Turtle](https://docs.python.org/3/library/turtle.html)
- [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

## Screenshots

![Account sign-in](docs/screenshots/sign-in.png)

![Monthly dashboard](docs/screenshots/dashboard.png)

![Six-month insights](docs/screenshots/insights.png)

![Chart and Turtle reward](docs/screenshots/rewards.png)
