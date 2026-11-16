"""Legal Metrology Compliance Agent - Streamlit interface.

Run with:  streamlit run app.py
"""
import json
from collections import Counter
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

import ui_components as ui
from lm_agents import (ComplianceOrchestrator, accuracy, flatten, get_llm,
                       markdown_report, parse_listings_bytes, read_listings, run_batch)
from lm_agents.rules import validate

ROOT = Path(__file__).resolve().parent
SAMPLE_CSV = ROOT / "data" / "sample_listings.csv"
FALLBACK_TEXT = """Product: Herbal Toothpaste
Common Name: Toothpaste
Net Quantity: 150 gms
MRP: Rs. 95
Selling Price: Rs. 99
Manufactured by: Dantaa Care Ltd, 45 MG Road, Pune, Maharashtra
Mfg Date: 08/2026
Country of Origin: India"""

st.set_page_config(page_title="Legal Metrology Compliance Agent", page_icon="⚖️", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)


@st.cache_data
def load_examples():
    """Pick one example of each outcome from the bundled sample data."""
    try:
        rows = read_listings(SAMPLE_CSV)
    except Exception:
        return {"Listing with serious issues": FALLBACK_TEXT}
    wanted = [("COMPLIANT", "Compliant listing"),
              ("PARTIALLY COMPLIANT", "Listing with minor issues"),
              ("NON-COMPLIANT", "Listing with serious issues")]
    picked = {}
    for status, label in wanted:
        for row in rows:
            if row.get("expected_status") == status:
                picked[label] = row["listing_text"]
                break
    return picked or {"Listing with serious issues": FALLBACK_TEXT}


EXAMPLES = load_examples()
PICK = "Choose an example"
if "listing_text" not in st.session_state:
    st.session_state["listing_text"] = EXAMPLES.get("Listing with serious issues", FALLBACK_TEXT)


def apply_example():
    choice = st.session_state.get("example_choice")
    if choice in EXAMPLES:
        st.session_state["listing_text"] = EXAMPLES[choice]


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    # Styled sidebar logo/header
    st.markdown("""
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">⚖️</div>
      <div class="sidebar-logo-name">LM Checker</div>
      <div class="sidebar-logo-tag">LEGAL METROLOGY · SIH 2025</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-title">⚙️ Settings</p>', unsafe_allow_html=True)
    mode = st.radio("How should the agents read listings?",
                    ["Offline", "With Claude"],
                    help="Offline needs no account. With Claude adds label-image reading and "
                         "richer explanations, and falls back to offline if anything fails.")
    api_key = ""
    if mode == "With Claude":
        api_key = st.text_input("Anthropic API key", type="password",
                                help="Leave empty if ANTHROPIC_API_KEY is already set on this computer.")

llm = get_llm(api_key or None) if mode == "With Claude" else None
orchestrator = ComplianceOrchestrator(llm=llm)

with st.sidebar:
    if mode == "With Claude" and llm is None:
        st.warning("No working API key found, so listings are being checked offline.")
    st.markdown('<span class="modepill">%s</span>' % escape(orchestrator.mode), unsafe_allow_html=True)
    st.markdown('<p class="hint" style="margin-top:.8rem">Educational tool based on a simplified reading '
                'of the Legal Metrology (Packaged Commodities) Rules, 2011.</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------- shared renderers
def render_result(res, key):
    st.markdown(ui.verdict(res), unsafe_allow_html=True)
    if res["status"] == "ERROR":
        return
    t_fix, t_details, t_checks, t_trace, t_report = st.tabs(
        ["🔧 What to fix", "📋 Declared details", "☑️ All checks", "🕐 Agent steps", "📄 Report"])
    with t_fix:
        st.markdown(ui.issues(res["results"]), unsafe_allow_html=True)
    with t_details:
        st.markdown('<p class="hint">What the agents found written on the listing.</p>', unsafe_allow_html=True)
        st.markdown(ui.fields_table(res["fields"]), unsafe_allow_html=True)
    with t_checks:
        st.markdown(ui.checks_table(res["results"]), unsafe_allow_html=True)
    with t_trace:
        st.markdown('<p class="hint">Each agent logs what it did, so you can see how the verdict was reached.</p>',
                    unsafe_allow_html=True)
        st.markdown(ui.timeline(res["trace"]), unsafe_allow_html=True)
    with t_report:
        st.markdown(ui.explanation_panel(str(res["explanation"])), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ Download report (text)", str(res["explanation"]).encode("utf-8"),
                           file_name="%s_report.txt" % res["listing_id"], mime="text/plain",
                           key="dl_txt_" + key)
        c2.download_button("⬇️ Download full result (JSON)",
                           json.dumps(res, indent=2, default=str).encode("utf-8"),
                           file_name="%s_result.json" % res["listing_id"], mime="application/json",
                           key="dl_json_" + key)


# ---------------------------------------------------------------- page
st.markdown(ui.header(
    "Legal Metrology Compliance Agent",
    "Check whether an online product listing carries the declarations Indian law requires: "
    "maker's address, net quantity, MRP, manufacture date, consumer care and country of origin."),
    unsafe_allow_html=True)

tab_single, tab_batch, tab_about = st.tabs(["🔍 Check Listing", "📊 Audit Batch", "ℹ️ How It Works"])

# ---- single listing
with tab_single:
    left, right = st.columns([5, 7], gap="large")
    with left:
        st.markdown('<p class="section-title">📝 Listing text</p>', unsafe_allow_html=True)
        st.selectbox("Start from an example", [PICK] + list(EXAMPLES), key="example_choice",
                     on_change=apply_example)
        st.text_area("Paste the product listing or label text", key="listing_text", height=300)
        with st.expander("📷 Add a photo of the label (needs Claude)"):
            upload = st.file_uploader("Label image", type=["png", "jpg", "jpeg", "webp"],
                                      label_visibility="collapsed")
            if upload is not None and llm is None:
                st.info("Reading images needs the With Claude option and an API key. "
                        "Switch it on in the sidebar, or paste the label text instead.")
        run_single = st.button("▶ Run check", type="primary", key="run_single")
        if run_single:
            image_bytes, media = None, "image/png"
            if upload is not None:
                image_bytes, media = upload.getvalue(), (upload.type or "image/png")
            with st.spinner("The agents are reading the listing..."):
                st.session_state["single"] = orchestrator.check(
                    text=st.session_state.get("listing_text", ""), image_bytes=image_bytes,
                    media_type=media, listing_id="listing")
    with right:
        st.markdown('<p class="section-title">📊 Result</p>', unsafe_allow_html=True)
        single = st.session_state.get("single")
        if single is None:
            st.markdown(ui.empty_state("No result yet",
                                       "Paste a listing, or pick an example, then choose Run check."),
                        unsafe_allow_html=True)
        else:
            render_result(single, "single")

# ---- batch audit
with tab_batch:
    st.markdown('<p class="section-title">📦 Audit many listings</p>', unsafe_allow_html=True)
    st.markdown('<p class="hint">Check a whole catalogue at once and see which problems come up most.</p>',
                unsafe_allow_html=True)
    source = st.radio("Listings to check", ["Sample dataset (28 listings)", "Upload my own CSV"],
                      horizontal=True)
    csv_file = None
    if source.startswith("Upload"):
        csv_file = st.file_uploader("CSV file", type=["csv"], key="batch_csv")
        st.markdown('<p class="hint">The file needs a <b>listing_text</b> column. '
                    'Optional columns: listing_id, title, expected_status.</p>', unsafe_allow_html=True)

    if st.button("▶ Run audit", type="primary", key="run_batch"):
        rows = None
        try:
            if source.startswith("Upload"):
                if csv_file is None:
                    st.warning("Choose a CSV file first.")
                else:
                    rows = parse_listings_bytes(csv_file.getvalue())
            else:
                rows = read_listings(SAMPLE_CSV)
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("Could not read the listings: %s" % exc)
        if rows:
            bar = st.progress(0.0, text="Checking listings...")
            results = run_batch(orchestrator, rows,
                                lambda i, n: bar.progress(i / n, text="Checked %d of %d" % (i, n)))
            bar.empty()
            st.session_state["batch"] = results

    batch = st.session_state.get("batch")
    if batch:
        status_counts = Counter(r["status"] for r in batch)
        avg = sum(int(r["score"]) for r in batch) / len(batch)
        st.markdown(ui.stats_strip([
            (len(batch), "Listings checked", "#17212B"),
            (status_counts.get("COMPLIANT", 0), "Compliant", ui.PALETTE["COMPLIANT"][0]),
            (status_counts.get("PARTIALLY COMPLIANT", 0), "Partly compliant", ui.PALETTE["PARTIALLY COMPLIANT"][0]),
            (status_counts.get("NON-COMPLIANT", 0), "Non-compliant", ui.PALETTE["NON-COMPLIANT"][0]),
            ("%.0f" % avg, "Average score", "#0D6E75"),
        ]), unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<p class="section-title">📊 Outcome mix</p>', unsafe_allow_html=True)
            st.markdown(ui.distribution(status_counts), unsafe_allow_html=True)
        with c2:
            st.markdown('<p class="section-title">⚠️ Most common problems</p>', unsafe_allow_html=True)
            fail_names = Counter(x["name"] for r in batch for x in r["results"] if x["status"] == "FAIL")
            st.markdown(ui.hbars(fail_names.most_common(5)), unsafe_allow_html=True)

        st.markdown('<p class="section-title">📋 Listings</p>', unsafe_allow_html=True)
        present = [s for s in ("COMPLIANT", "PARTIALLY COMPLIANT", "NON-COMPLIANT", "ERROR") if s in status_counts]
        chosen = st.multiselect("Show", present, default=present,
                                format_func=lambda s: ui.STATUS_LABEL[s])
        shown = [r for r in batch if r["status"] in chosen]
        flat = pd.DataFrame(flatten(shown))
        if not flat.empty:
            flat["status"] = flat["status"].map(lambda s: ui.STATUS_LABEL.get(s, s))
            flat = flat.rename(columns={"listing_id": "Listing", "title": "Product", "status": "Verdict",
                                        "score": "Score", "failed_rules": "Failed checks",
                                        "expected_status": "Expected"})
            if (flat["Expected"] == "").all():
                flat = flat.drop(columns=["Expected"])
            st.dataframe(flat, hide_index=True,
                         column_config={"Score": st.column_config.ProgressColumn(
                             "Score", min_value=0, max_value=100, format="%d")})
        else:
            st.info("No listings match the selected verdicts.")

        acc = accuracy(batch)
        if acc is not None:
            st.markdown('<p class="hint">Agreement with the expected_status labels in the file: <b>%.0f%%</b></p>'
                        % (acc * 100), unsafe_allow_html=True)

        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button("⬇️ Download table (CSV)",
                           pd.DataFrame(flatten(batch)).to_csv(index=False).encode("utf-8"),
                           file_name="compliance_report.csv", mime="text/csv", key="dl_batch_csv")
        d2.download_button("⬇️ Download report (Markdown)", markdown_report(batch).encode("utf-8"),
                           file_name="compliance_report.md", mime="text/markdown", key="dl_batch_md")

        if shown:
            st.markdown('<p class="section-title">🔎 Look at one listing</p>', unsafe_allow_html=True)
            ids = [r["listing_id"] for r in shown]
            pick = st.selectbox("Listing", ids, label_visibility="collapsed")
            render_result(next(r for r in shown if r["listing_id"] == pick), "batch")
    else:
        st.markdown(ui.empty_state("No audit yet", "Choose a source above, then select Run audit."),
                    unsafe_allow_html=True)

# ---- how it works
with tab_about:
    st.markdown('<p class="section-title">🔗 Four agents, one verdict</p>', unsafe_allow_html=True)
    st.markdown(ui.pipeline_steps(), unsafe_allow_html=True)
    st.markdown('<p class="hint">The legal checks are plain code rather than an AI guess, so the same listing '
                'always gets the same verdict. The AI is used only where language skills help: reading messy '
                'text and images, and explaining the result.</p>', unsafe_allow_html=True)

    st.markdown('<p class="section-title" style="margin-top:1.4rem">📜 What gets checked</p>', unsafe_allow_html=True)
    rule_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (escape(r.rule_id), escape(r.name), ui.SEVERITY_LABEL.get(r.severity, r.severity))
        for r in validate({}))
    st.markdown(ui.H('<table class="tbl"><tr><th>Code</th><th>Check</th><th>If it fails</th></tr>%s</table>'
                     % rule_rows), unsafe_allow_html=True)
    st.markdown('<p class="hint" style="margin-top:.8rem">A listing is <b>non-compliant</b> if any critical check '
                'fails, <b>partly compliant</b> if only major checks fail, and <b>compliant</b> if none fail. '
                'The score weights critical checks more heavily.</p>', unsafe_allow_html=True)
