"""ShopImpact: run with python -m streamlit run app.py."""
import json
import importlib
from pathlib import Path
from datetime import date
import streamlit as st
import logic as shopping_rules
import storage as backup_storage

# Community Cloud may rerun app.py while retaining imported modules from the
# previous deployment. Refresh the rules and backup bindings as one version.
source_version = json.loads((Path(__file__).resolve().parent / "data/emission_sources.json").read_text(encoding="utf-8"))["methodology"]
if shopping_rules.VERSION != source_version:
    importlib.reload(shopping_rules)
if backup_storage.VERSION != shopping_rules.VERSION:
    importlib.reload(backup_storage)

from logic import ROOT, CATALOG, SOURCE, VERSION, impact, make_purchase, month_records, summary, badges, update_purchase, recalculate_purchases
from storage import export_json, export_csv, import_json
from account_ui import require_account, save_account, sign_out, EMAIL_REQUEST_MESSAGE
from email_delivery import queue_email_action, queue_notice
from accounts import AccountError
from sqlalchemy.exc import SQLAlchemyError
from ui import apply_styles
from insights import monthly_trend, month_insights, filter_purchases

st.set_page_config(page_title="ShopImpact | Conscious shopping", page_icon="🌿", layout="wide")
apply_styles()
service, account, mailer = require_account()
if "tip_index" not in st.session_state:
    st.session_state.tip_index = 0
settings = account["settings"]
records = account["purchases"]
key = "personal"

with st.sidebar:
    st.title("🌿 ShopImpact")
    st.caption("Small choices. Thoughtful habits.")
    st.write(f"Signed in as **{account['username']}**")
    with st.expander("Account email"):
        if account.get("email"):
            st.caption(f"Sign-in email: {account['email']}")
            st.caption("Verified" if account.get("email_verified") else "Email not verified yet")
            if mailer and not account.get("email_verified") and st.button("Send verification email"):
                queue_email_action(service, mailer, account["email"], "verify")
                st.success(EMAIL_REQUEST_MESSAGE)
        else:
            st.write("Add an email to sign in with it next time.")
        with st.form("account_email", clear_on_submit=True):
            email = st.text_input("Sign-in email", max_chars=254, placeholder="name@example.com")
            email_password = st.text_input("Current password", type="password", max_chars=128)
            if st.form_submit_button("Save sign-in email"):
                try:
                    old_email = account.get("email")
                    account["email"] = service.set_email(st.session_state.auth_token, email, email_password)
                    account.update(service.load(st.session_state.auth_token))
                    if mailer and old_email != account["email"]:
                        queue_email_action(service, mailer, account["email"], "verify")
                        if old_email:
                            queue_notice(mailer, old_email, "ShopImpact email address changed",
                                         "Your ShopImpact sign-in email was changed after password confirmation. If you did not make this change, use your recovery code to secure your account.")
                    st.success("Email saved. You can sign in immediately; verify it from your inbox to enable email password resets." if mailer else "Email saved. You can sign in with your email or username.")
                except AccountError as error:
                    st.error(str(error))
                except SQLAlchemyError:
                    st.error("Your email could not be saved. Please try again.")
    if st.button("Sign out"):
        sign_out(service)
    if st.button("Reload saved data", help="Load the latest saved data after changes in another tab."):
        st.session_state.pop("account_data", None)
        for widget in ["contrast", "budget", "carbon_goal"]:
            st.session_state.pop(widget, None)
        st.rerun()
    st.divider()
    with st.form("goals"):
        st.subheader("Your monthly goals")
        high_contrast = st.checkbox("High contrast", value=settings["contrast"], key="contrast")
        budget = st.number_input("Spending goal (INR)", min_value=100.0, value=float(settings["budget"]), step=100.0, key="budget")
        carbon_goal = st.slider("Estimated CO₂e goal (kg)", 10, 1000, int(settings["carbon_goal"]), step=10, key="carbon_goal")
        if st.form_submit_button("Save goals & appearance"):
            if save_account(service, account, settings={"budget": budget, "carbon_goal": carbon_goal, "contrast": high_contrast}):
                settings = account["settings"]
                st.success("Preferences saved.")
    st.caption("Goals help you reflect. They do not change the fixed badge rules.")
    st.info("Purchases save to your account. Sign in again after a refresh to continue. Download a backup whenever you want a separate copy.")

apply_styles(high_contrast)

st.markdown('''<section class="si-hero">
<span class="si-chip">2026 refresh</span><span class="si-chip">Private shopping journal</span>
<h1>A little more mindful, every month.</h1>
<p>Know where your money goes. Explore your estimated impact. Find a thoughtful next step.</p>
</section>''', unsafe_allow_html=True)
if st.session_state.get("account_created"):
    st.success("Your account is ready. Welcome to ShopImpact!")
    with st.expander("Save your account recovery code"):
        st.write("Keep this code privately. It lets you recover your account if you forget your password.")
        st.code(st.session_state.recovery_code)
        st.download_button("Download recovery code", st.session_state.recovery_code,
                           "shopimpact-recovery-code.txt", "text/plain")
        if st.button("I saved my recovery code"):
            st.session_state.pop("account_created", None)
            st.session_state.pop("recovery_code", None)
            st.rerun()
st.write("Track your shopping, explore alternatives, and celebrate your progress.")
st.caption("INR · USEEIO v1.4 reference factors · Sources reviewed 5 October 2026. Rough US-sector estimates, not product measurements.")
older_estimates = sum(p.get("methodology") != VERSION for p in records)
if older_estimates:
    st.info(f"{older_estimates} purchases retain their earlier reference estimates. New or edited entries use the updated data. Recalculate your history in How it works to compare all entries on the same basis.")

if st.session_state.get("personal"):
    with st.expander("Save entries from your previous session"):
        st.write("Your earlier session entries can be saved to this account. Estimates will be recalculated using the new sourced factors.")
        if st.button("Import my earlier session entries"):
            old = [make_purchase(p["product_type"], p["price"], p["brand"], p["purchase_date"], p["id"]) for p in st.session_state.personal]
            existing = {p["id"] for p in records}
            merged = records + [p for p in old if p["id"] not in existing]
            if save_account(service, account, purchases=merged):
                del st.session_state["personal"]
                st.rerun()

entry, insights, history, about = st.tabs(["Dashboard & add purchase", "Insights", "Purchase history & backups", "How it works"])
with entry:
    months = sorted({date.today().strftime("%Y-%m")} | {p["purchase_date"][:7] for p in records}, reverse=True)
    if "next_dashboard_month" in st.session_state:
        st.session_state.month = st.session_state.pop("next_dashboard_month")
    if st.session_state.get("month") not in months:
        st.session_state.pop("month", None)
    heading, period = st.columns([3, 1])
    heading.subheader("Monthly overview")
    month = period.selectbox("Dashboard month", months, key="month")
    monthly = month_records(records, month)
    totals = summary(monthly)
    a, b, c = st.columns(3)
    a.metric("Monthly spend", f"INR {totals['spend']:,.2f}")
    b.metric("Estimated CO₂e", f"{totals['co2']:,.2f} kg")
    c.metric("Reuse & repair choices", f"{totals['lower']} / {totals['count']}")

    st.divider()
    if st.session_state.pop("purchase_saved", False):
        st.success("Purchase saved. Your overview and history are up to date.")
    st.subheader("Add a purchase")
    c1, c2, c3, c4 = st.columns([1.7, 1.4, 1.9, 1.5])
    category = c1.selectbox("Product type", list(CATALOG), key="new_category")
    price = c2.number_input("Price (INR)", min_value=0.0, max_value=10000000.0, value=500.0, step=50.0, key="new_price")
    brand = c3.text_input("Brand or shop", max_chars=80, placeholder="e.g. Local reuse shop", key="new_brand")
    purchased_on = c4.date_input("Purchase date", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2100, 12, 31), key="new_date")
    st.caption(f"Live preview: {impact(price, category):,.2f} estimated kg CO₂e · reference factor {float(CATALOG[category]['multiplier']):.6f} per INR")
    if st.button("Add purchase", type="primary", key="add"):
        try:
            if len(records) >= 1000:
                raise ValueError("This workspace supports 1,000 purchases. Export a backup before starting a new one.")
            updated = records + [make_purchase(category, price, brand, purchased_on)]
            if save_account(service, account, purchases=updated):
                records = updated
                st.session_state.tip_index += 1
                st.session_state.purchase_saved = True
                st.session_state.next_dashboard_month = purchased_on.strftime("%Y-%m")
                st.rerun()
        except ValueError as error:
            st.error(str(error))

    main, rewards = st.columns([2, 1])
    with main:
        st.subheader("Your month at a glance")
        chart_measure = st.radio("Chart measure", ["Estimated CO₂e", "Spending"], horizontal=True)
        if monthly:
            field = "estimated_co2" if chart_measure == "Estimated CO₂e" else "price"
            grouped = {}
            for purchase in monthly:
                product = purchase["product_type"]
                grouped[product] = grouped.get(product, 0) + float(purchase[field])
            st.bar_chart({"Product type": list(grouped), "Estimated kg CO₂e" if field == "estimated_co2" else "INR": list(grouped.values())}, x="Product type", color="#28644F")
        else:
            st.info("Add your first purchase to start your monthly dashboard.")
        for label, used, goal in [("Spending", float(totals["spend"]), budget), ("Estimated CO₂e", float(totals["co2"]), carbon_goal)]:
            st.progress(min(used / goal, 1.0), text=f"{label}: {used:,.2f} of {goal:,.2f} ({used / goal:.0%})")
            if used > goal:
                st.caption(f"{label} is above your chosen goal. You can use the comparison tool to reflect on future choices.")
    with rewards:
        st.subheader("Your achievements")
        earned = badges(monthly)
        for badge in earned:
            st.success(f"🏅 {badge}")
        if totals["lower"]:
            artwork = ROOT / "assets/turtle/leaf.svg"
            if artwork.exists():
                st.image(str(artwork), caption="A Turtle leaf for a reuse, repair or reusable choice.", width=220)
            else:
                st.info("Run tools/draw_rewards.py to generate the Turtle leaf.")
        if not earned:
            st.write("Your next achievement starts with a thoughtful choice.")
        with st.expander("See badge rules"):
            st.write("Eco Saver: at least 3 purchases and a monthly estimated footprint of 50 kg CO₂e or less.")
            st.write("Low Impact Shopper: at least 3 reuse, repair or reusable choices, making up at least 60% of the month. This rewards habits, not verified emissions savings.")
            st.write("Repair Champion: at least one repair-service purchase this month.")
        tips = json.loads((ROOT / "data/eco_tips.json").read_text(encoding="utf-8"))
        st.subheader("A small idea")
        if st.button("Another tip"):
            st.session_state.tip_index += 1
        st.write(tips[st.session_state.tip_index % len(tips)])

    st.subheader("Explore alternatives")
    st.write(f"Ideas for {category.lower()}:")
    for alternative in CATALOG[category]["alternatives"]:
        st.write(f"• {alternative}")
    st.caption(CATALOG[category]["mapping_note"])
    with st.expander("Brand and service options to explore"):
        links = json.loads((ROOT / "data/alternative_links.json").read_text(encoding="utf-8"))
        for option in links[category]:
            st.markdown(f"[{option['name']}]({option['url']}) — {option['note']}")
        st.caption("Official pages checked 2 October 2026. These document reuse, repair or reusable-product options, not independent ethical certification or verified emissions savings. Check local availability and terms.")
    with st.expander("Compare a different choice", expanded=False):
        target = st.selectbox("Compare with", list(CATALOG), index=list(CATALOG).index(CATALOG[category]["compare_with"]))
        alternative_price = st.number_input("Alternative price (INR)", min_value=0.0, max_value=10000000.0, value=500.0)
        original, alternative = impact(price, category), impact(alternative_price, target)
        x, y = st.columns(2)
        x.metric("Current choice (estimated kg CO₂e)", f"{original:,.2f}")
        y.metric("Alternative (estimated kg CO₂e)", f"{alternative:,.2f}", delta=f"{alternative - original:+,.2f}", delta_color="inverse")
        st.caption("Reference-model comparison only. A lower price can lower this estimate without lowering physical emissions. Reuse benefits are not quantified by this model.")

with insights:
    st.subheader("See the bigger picture")
    st.write("Explore six months of your recorded shopping and reflect on your goals.")
    insight_month = st.selectbox("Insights month", months, key="insight_month")
    detail = month_insights(records, insight_month, settings["budget"])
    average, balance, change = st.columns(3)
    average.metric("Average purchase", f"INR {detail['average']:,.2f}" if detail["average"] is not None else "No entries")
    balance.metric("Above spending goal" if detail["remaining"] < 0 else "Spending goal remaining", f"INR {abs(detail['remaining']):,.2f}")
    change.metric("Change from previous month", f"INR {detail['spend_change']:+,.2f}" if detail["spend_change"] is not None else "No prior entries")
    st.caption("Compared with the previous calendar month, using logged entries only. Empty months mean no entries, not verified zero spending. Goals use your current saved preferences; these are not forecasts.")
    trend = monthly_trend(records, insight_month)
    measure = st.radio("Trend measure", ["Spending (INR)", "Estimated CO₂e (kg)"], horizontal=True)
    field = "spend" if measure == "Spending (INR)" else "co2"
    st.line_chart({"Month": [row["month"] for row in trend], measure: [float(row[field]) for row in trend]}, x="Month", color="#28644F")
    if detail["top_category"]:
        st.info(f"Largest spending category: {detail['top_category']} · INR {detail['top_spend']:,.2f}")
    else:
        st.info("No purchases logged for this month. Add entries to reveal your patterns.")
    with st.expander("View the monthly numbers"):
        st.dataframe([{"Month": row["month"], "Entries": row["count"], "Spending (INR)": float(row["spend"]), "Estimated CO₂e (kg)": float(row["co2"])} for row in trend], hide_index=True, width="stretch")

with history:
    st.subheader("Your purchase history")
    if records:
        query = st.text_input("Search purchases", placeholder="Brand, shop, category or date")
        f1, f2, f3 = st.columns(3)
        history_month = f1.selectbox("Filter month", ["All months"] + sorted({p["purchase_date"][:7] for p in records}, reverse=True))
        history_category = f2.selectbox("Filter category", ["All categories"] + list(CATALOG))
        order = f3.selectbox("Sort purchases", ["Newest first", "Oldest first", "Highest price", "Highest estimated impact"])
        filtered = filter_purchases(records, query, None if history_month == "All months" else history_month,
                                    None if history_category == "All categories" else history_category, order)
        if filtered:
            filtered_totals = summary(filtered)
            st.caption(f"Showing {len(filtered)} of {len(records)} purchases · INR {filtered_totals['spend']:,.2f} · {filtered_totals['co2']:,.2f} estimated kg CO₂e")
            st.dataframe([{"Date": p["purchase_date"], "Product type": p["product_type"], "Brand / shop": p["brand"],
                           "Price (INR)": float(p["price"]), "Estimated CO₂e (kg)": float(p["estimated_co2"])} for p in filtered], hide_index=True, width="stretch")
            st.download_button("Download filtered CSV", export_csv(filtered), "shopimpact-filtered.csv", "text/csv")
            lookup = {p["id"]: p for p in filtered}
            selected = st.selectbox("Choose a purchase to edit", list(lookup), format_func=lambda i: f"{lookup[i]['purchase_date']} · {lookup[i]['brand']} · INR {lookup[i]['price']} · {i[:8]}")
            record = lookup[selected]
            with st.form(f"edit_{key}_{selected}"):
                edit_type = st.selectbox("Edit product type", list(CATALOG), index=list(CATALOG).index(record["product_type"]))
                edit_price = st.number_input("Edit price (INR)", min_value=0.0, max_value=10000000.0, value=float(record["price"]))
                edit_brand = st.text_input("Edit brand or shop", value=record["brand"], max_chars=80)
                edit_date = st.date_input("Edit date", value=date.fromisoformat(record["purchase_date"]), min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))
                if st.form_submit_button("Save changes"):
                    try:
                        replacement = make_purchase(edit_type, edit_price, edit_brand, edit_date, selected)
                        if save_account(service, account, purchases=update_purchase(records, replacement)):
                            st.rerun()
                    except ValueError as error:
                        st.error(str(error))
            confirm_delete = st.checkbox("Confirm deletion of this purchase", key=f"confirm_{key}_{selected}")
            if st.button("Delete selected purchase", disabled=not confirm_delete):
                if save_account(service, account, purchases=[p for p in records if p["id"] != selected]):
                    st.rerun()
        else:
            st.info("No purchases match these filters. Try a different month, category or search.")
    else:
        st.info("No purchases yet. Add one on the dashboard.")
    st.subheader("Keep a copy")
    st.caption("JSON restores your entries. CSV is a spreadsheet-friendly report. Neither includes your goal settings.")
    d1, d2 = st.columns(2)
    d1.download_button("Download JSON backup", export_json(records), f"shopimpact-{key}.json", "application/json")
    d2.download_button("Download CSV report", export_csv(records), f"shopimpact-{key}.csv", "text/csv")
    uploaded = st.file_uploader("Restore a ShopImpact JSON backup", type=["json"], key=f"upload_{key}")
    confirm_restore = st.checkbox("Replace this workspace with the backup", key=f"restore_confirm_{key}")
    legacy = st.checkbox("Allow an older backup and recalculate its estimates", help="Earlier reference or illustrative estimates will be replaced with the current sourced factors.")
    if st.button("Restore backup", disabled=uploaded is None or not confirm_restore):
        try:
            restored = import_json(uploaded.getvalue(), allow_legacy=legacy)
            if save_account(service, account, purchases=restored):
                st.rerun()
        except ValueError as error:
            st.error(str(error))

with about:
    st.subheader("An honest estimate, a helpful habit")
    st.write("Making, packaging and delivering products can release greenhouse gases. CO₂e means carbon dioxide equivalent: a common measure of their combined warming effect. ShopImpact uses the product category and price as clues to estimate that impact; spending itself does not directly create emissions.")
    st.write("ShopImpact uses price × category multiplier to estimate spending-related greenhouse gas emissions. The updated factors come from USEEIO Supply Chain GHG Emission Factors v1.4.0, published by the Cornerstone Sustainability Data Initiative in October 2025, including supply-chain margins and IPCC AR6 warming potentials.")
    st.write("The base currency is INR. A higher price can increase this estimate without changing physical emissions. Free items return zero in this model; that does not mean they have zero environmental impact.")
    st.write(f"The reference conversion is {SOURCE['fx_inr_per_usd']} INR per USD, the World Bank's annual average for {SOURCE['fx_year']}, matching the factors' 2024 dollar price basis. It is not a live exchange rate. Current prices are not inflation-adjusted; US sector averages may differ substantially from Indian products. Treat results as rough estimates, not certified carbon accounting.")
    with st.expander("Data freshness and reference years"):
        st.write("Reviewed 5 October 2026. A 2026 refresh means the latest verified source release available at review, not measured 2026 product emissions.")
        st.write(f"Factor release: v1.4.0 · Published {SOURCE['published']} · Dollar price basis: 2024 · Warming method: {SOURCE['gwp']}.")
        latest_fx = SOURCE["latest_available_annual_fx"]
        st.write(f"Latest available World Bank annual rate at review: {latest_fx['year']} · {latest_fx['inr_per_usd']} INR/USD. This is shown for context; calculations use the matching 2024 rate. No full-year 2026 rate is available yet.")
        st.caption("Data is a checked snapshot, not a live feed. Previous source files are archived for reproducibility.")
    st.write("Badges reflect your logged choices, not a certification of sustainability. Reused and new versions use the same category factor; no unsupported reuse discount is applied. Brand links document reuse, repair or reusable-product options, not independent certification or endorsements.")
    st.dataframe([{"Category": name, "Reference kg CO₂e per INR": float(info["multiplier"]), "EPA NAICS": info["source_code"], "Mapping limitations": info["mapping_note"]} for name, info in CATALOG.items()], hide_index=True)
    st.markdown("[Published USEEIO dataset](https://zenodo.org/records/17202747) · [World Bank reference exchange rate](https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF?date=2024&format=json)")
    if older_estimates:
        with st.expander("Update my saved estimates"):
            st.write("Download a JSON backup first. Recalculation preserves purchase IDs, dates, brands and prices, and updates estimates and methodology. Badges and totals may change. Your goals stay the same.")
            approve_recalculation = st.checkbox("Use the updated reference data for all my purchases", key="approve_recalculation")
            if st.button("Recalculate saved estimates", disabled=not approve_recalculation):
                try:
                    if save_account(service, account, purchases=recalculate_purchases(records)):
                        st.rerun()
                except ValueError as error:
                    st.error(str(error))
    st.write("Purchases and preferences are saved separately for each account. Passwords are protected with Argon2id hashing. The database administrator can access purchase data; it is not end-to-end encrypted. Sign out on a shared computer. Sessions expire after 12 hours and a page refresh requires another sign-in.")
    st.write("Dates may include planned purchases. Your dashboard groups all entries by their selected purchase month and year.")
    st.caption("Built with Python, Streamlit, datetime, lists, dictionaries, and genuine Turtle-generated artwork.")
    with st.expander("Delete my account and purchases"):
        st.write("Download a backup first if you want to keep your purchase history. This permanently deletes your account and its data.")
        with st.form("delete_account"):
            password = st.text_input("Confirm your password", type="password", max_chars=128)
            confirmed = st.checkbox("I understand my account and purchases will be deleted")
            if st.form_submit_button("Permanently delete my account") and confirmed:
                try:
                    service.delete_account(st.session_state.auth_token, password)
                    st.session_state.clear()
                    st.rerun()
                except AccountError as error:
                    st.error(str(error))
                except SQLAlchemyError:
                    st.error("Account deletion failed. Please try again.")
