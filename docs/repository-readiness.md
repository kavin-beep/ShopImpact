# Repository readiness review

Reviewed 3 October 2026 before creating a repository. The core application is ready to put under version control. The repository has not been created or pushed as part of this review.

## Small improvements completed

- Invalid optional email settings show a safe warning instead of preventing sign-in. Purchase saving and recovery codes continue to work; unavailable email reset remains disabled.
- Gmail setup accurately describes optional verification and verified-address password resets. Signup still opens the home page immediately.
- The chart uses the consistent CO₂e label. How it works explains manufacturing, packaging, transport, and the role of spending in simple language.
- TOML, imported directly by setup tools, is explicitly pinned in requirements.txt.
- Ignore rules cover private environment files, database files, recovery-code downloads, purchase exports and disposable caches. The example settings, source data, artwork, tests, documentation and explanation PDFs remain available for the repository.

## Verification

All 79 automated tests passed in the project Python 3.12 virtual environment. The dependency check found no broken requirements. Tests cover purchase calculations and validation, import/export, account isolation, signup/login, recovery, conflicting saves, email actions, Insights and Streamlit UI interactions. The new email-configuration regression test signs in and saves a purchase despite invalid SMTP settings.

The supplied assessment brief was rechecked against docs/requirements.md. The required purchase fields, live calculations, monthly dashboard, badges, alternatives, Python data structures and conditional Turtle artwork are implemented. Existing screenshots and the 15-record synthetic test fixture are present. Turtle desktop preview and assessor acceptance of the SVG integration remain to be confirmed.

Private-file exclusions were verified using Git's own ignore handling with temporary metadata outside the project. No real credentials were found by the targeted scan of eligible text files. The connection strings in setup tests are deliberately synthetic; real database settings remain private. No live user data was changed during this review.

## Before public launch and final submission

1. Rotate the Neon database password previously shared in chat, then update private local and hosted settings. Do not put the replacement connection string in the repository or chat.
2. Create the repository using the required student naming convention, then add the real repository URL and arrange assessor access as specified by the brief.
3. Deploy app.py to Streamlit Cloud with private PostgreSQL settings. Verify two-account isolation, recovery, downloads and persistence after redeployment. Add the actual public URL to the README.
4. If enabling email, complete private Gmail setup and check inbox delivery and reset links from the deployed app. Recovery codes remain available without email.
5. Gather actual participant feedback using docs/usability-feedback.md; record changes and retest them. Complete keyboard and screen-reader checks and database backup restoration checks.
6. Complete the assessment submission PDF with the actual student name, registration number, school, course and project links. The ten-page explanation PDF is a learning guide, not that completed submission.

Public deployment, real feedback and final submission are pending. Passing automated tests alone does not establish those outcomes or guarantee an assessment grade.
