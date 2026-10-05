# Assessment requirements status

Current on 3 October 2026. The rubric totals 60 marks: planning 10, Python logic 15, interface 15, testing/creativity 10, GitHub/documentation 10. Distinguished is the highest named tier; no grade is guaranteed.

| Requirement | Evidence and current status |
| --- | --- |
| User needs, sketches, palette and feature planning | docs/design.md contains initial planning and wireframes |
| Product type, price, brand and date | Implemented and exercised in interface/browser checks |
| Price times multiplier calculation | Implemented; published EPA source rows and historical currency conversion recorded |
| Monthly spending and estimated CO2 dashboard | Implemented; month/year logic tested; desktop dashboard inspected |
| Badges and rules | Implemented and boundary-tested |
| Alternatives for each product type | Three shopping approaches per category plus named options with official source links; no unsupported ethical certification |
| Turtle footprint, leaf or badge | Turtle-generated SVG displayed conditionally; source included; desktop preview and assessor interpretation remain to be confirmed |
| Lists, dictionaries, control structures, datetime and modular code | Implemented in logic, storage, accounts and interface modules |
| Interactive UI and live updates | Working local app; add/edit/delete and saved preferences tested |
| 10–15 varied purchases for testing | 15 labelled synthetic records in tests; none preloaded for real users |
| Creative additions | Private accounts, permanent saving, recovery, goals, search, comparison, backups, tips, contrast and deletion |
| Email account features | Email/password login working; verification and reset links implemented and tested, awaiting private Gmail setup and actual inbox delivery |
| Thorough testing | 83 automated tests pass; actual browser review and screenshots recorded |
| Genuine usability feedback and refinement | Feedback template prepared; real participant feedback still required |
| app.py and requirements.txt | Present; dependencies installed and checked |
| Detailed README | Overview, features, integration, run/deployment steps and screenshot evidence present; public links pending |
| GitHub repository, naming and assessor access | Pending actual repository and student details |
| Streamlit Cloud deployment | Public app deployed and sign-in page checked; live URL in README. Local Neon checks passed previously; full cloud account workflows, redeployment and backup restoration checks remain pending |
| Submission PDF | Pending real student name, registration number, school, repository and live links |

The real app has no demo workspace. Synthetic data belongs only in tests and in the separate browser QA database. Local accounts use SQLite; public mode requires PostgreSQL. Do not mark public deployment complete based on a local server or an example secrets file.
