# Design and user needs

Students, young adults and families may want to understand purchases without specialist knowledge. Their main needs are quick entry, understandable totals, suggestions they can act on and encouragement without guilt. The first design uses an earthy green and cream palette, visible labels, whitespace, and a separate explanation of the model's limitations.

## Current layout

The sign-in page pairs a dark green introduction panel with labelled account forms. On narrow screens the panels stack. The dashboard uses a quieter cream background, white metric cards, rounded controls and consistent heading sizes. Captions keep their intended text colour without Streamlit's default opacity reduction. A shared stylesheet supports the same appearance across account and shopping pages.

```text
+----------------------+--------------------------------------------------+
| ShopImpact           | Title and reference estimate notice              |
| Account / sign out   | Dashboard | Insights | History | How it works     |
| High contrast        |                                                  |
|                      | Month selection                                  |
| Monthly goals        | Spending total | CO2 estimate | Lower choices    |
| Spending             |                                                  |
| Estimated CO2e       | Product type | Price | Brand | Date              |
|                      | Live impact preview                [Add purchase]|
| Backup reminder      | Category chart             | Achievements      |
|                      | Goal progress              | Turtle leaf       |
|                      |                            | Rotating tip      |
|                      | Alternatives and comparison                      |
+----------------------+--------------------------------------------------+
```

Insights shows six calendar months ending at a chosen month, average purchase, remaining or exceeded spending goal, previous-month change and largest spending category. Missing entries are described explicitly and are not treated as proof of zero spending or emissions.

History combines search, month and category filters with date/price/impact sorting. Filtered results have their own totals and CSV download. The edit selector follows the displayed results; a zero-result view hides edit/delete controls while full backups remain available. Editing, explicit delete confirmation and confirmed JSON restoration remain supported. The explanation tab describes assumptions and privacy. Browser review confirmed stacked inputs at a 390-pixel viewport with the sidebar collapsed; no horizontal document overflow was detected in that view.

## Design choices

Use text labels with badge symbols so meaning is not conveyed by colour alone. Keep the most important totals above the chart. Present alternatives as options, without guilt or unsupported brand endorsements. Require sign-in before showing purchase data. Keep each account separate and show that entries save automatically. Recovery codes and explicit deletion support account ownership. Synthetic test entries never populate live accounts.

High contrast was reviewed in Chrome and primary-button text was corrected. Full keyboard navigation, zoom and screen-reader assessment remain pending; a contrast toggle alone is not an accessibility certification.

## Feedback to collect

Ask real participants to add a purchase, find a monthly total, edit a mistake, compare two choices, and save/restore a backup. Record their observations and permission-appropriate notes. No user research or usability feedback has been conducted yet.
