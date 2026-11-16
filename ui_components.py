"""Styling and HTML renderers for the Streamlit interface.

Design: Professional SIH-grade Legal Metrology dashboard.
Dark teal/navy branding, card-based layout, animated scores, rich CSS.
All user-provided text is HTML-escaped before it is rendered.
"""
from html import escape
from typing import Dict, Iterable, List, Tuple

PALETTE = {
    "COMPLIANT": ("#1E7B4F", "#E8F4EE"),
    "PARTIALLY COMPLIANT": ("#A8610A", "#FBF1E3"),
    "NON-COMPLIANT": ("#B42318", "#FBEAE8"),
    "ERROR": ("#5B6773", "#EAEEF2"),
}
STATUS_LABEL = {
    "COMPLIANT": "Compliant",
    "PARTIALLY COMPLIANT": "Partly compliant",
    "NON-COMPLIANT": "Non-compliant",
    "ERROR": "Could not check",
}
SEVERITY_LABEL = {"critical": "Critical", "major": "Major"}
FIELD_LABELS = [
    ("product_name", "Product"),
    ("generic_name", "Common name"),
    ("manufacturer", "Manufacturer, packer or importer"),
    ("net_quantity", "Net quantity"),
    ("mrp", "MRP"),
    ("selling_price", "Selling price"),
    ("mfg_date", "Made or packed on"),
    ("expiry", "Expiry"),
    ("consumer_care", "Consumer care"),
    ("country_of_origin", "Country of origin"),
]

CSS = """
<style>
/* ── Design Tokens ─────────────────────────────────────────────── */
:root {
  --teal:        #0D6E75;
  --teal-dark:   #094F55;
  --teal-light:  #E0F2F4;
  --navy:        #0C2D48;
  --ink:         #1A2733;
  --muted:       #5B6E7E;
  --line:        #D4DCE5;
  --panel:       #FFFFFF;
  --bg:          #F0F4F8;
  --pass:        #1E7B4F;
  --pass-bg:     #E8F4EE;
  --warn:        #A8610A;
  --warn-bg:     #FBF1E3;
  --fail:        #B42318;
  --fail-bg:     #FBEAE8;
  --shadow-sm:   0 1px 4px rgba(0,0,0,.07), 0 2px 8px rgba(0,0,0,.05);
  --shadow-md:   0 4px 16px rgba(0,0,0,.10), 0 1px 4px rgba(0,0,0,.06);
  --radius:      10px;
  --radius-sm:   6px;
}

/* ── Base App ──────────────────────────────────────────────────── */
.stApp {
  font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--ink);
  background: var(--bg);
}
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1200px; }
footer, #MainMenu { visibility: hidden; }

/* ── App Header Banner ─────────────────────────────────────────── */
.app-banner {
  background: linear-gradient(135deg, #094F55 0%, #0D6E75 45%, #12818A 75%, #0C4A6E 100%);
  border-radius: var(--radius);
  padding: 2rem 2.4rem 1.8rem 2.4rem;
  margin-bottom: 1.6rem;
  display: flex;
  align-items: center;
  gap: 1.6rem;
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}
.app-banner::before {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    -55deg,
    rgba(255,255,255,.025) 0px, rgba(255,255,255,.025) 1px,
    transparent 1px, transparent 28px
  );
}
.app-banner-icon {
  font-size: 3.2rem;
  line-height: 1;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,.35));
  flex-shrink: 0;
}
.app-banner-text { flex: 1; position: relative; }
.app-title {
  font-size: 1.9rem;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: -.01em;
  margin: 0 0 .3rem 0;
  line-height: 1.1;
  text-shadow: 0 2px 8px rgba(0,0,0,.3);
}
.app-sub {
  color: rgba(255,255,255,.8);
  font-size: .97rem;
  margin: 0;
  max-width: 52rem;
  line-height: 1.55;
}
.app-badge {
  position: absolute;
  top: 1rem;
  right: 1.2rem;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 999px;
  padding: .28rem .9rem;
  font-size: .78rem;
  font-weight: 700;
  color: rgba(255,255,255,.9);
  letter-spacing: .06em;
  text-transform: uppercase;
}

/* ── Section / Utility ─────────────────────────────────────────── */
.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink);
  margin: .2rem 0 .7rem 0;
  display: flex;
  align-items: center;
  gap: .4rem;
}
.section-title::after {
  content: "";
  flex: 1;
  height: 2px;
  background: linear-gradient(90deg, var(--line) 0%, transparent 100%);
  margin-left: .5rem;
  border-radius: 2px;
}
.hint { color: var(--muted); font-size: .92rem; line-height: 1.55; margin: .2rem 0; }
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.2rem 1.4rem;
  box-shadow: var(--shadow-sm);
}
.pre { white-space: pre-wrap; line-height: 1.6; font-size: .93rem; }
.modepill {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  padding: .3rem .9rem;
  border-radius: 999px;
  font-size: .82rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--teal-light), #cce9ec);
  color: var(--teal-dark);
  border: 1px solid rgba(13,110,117,.25);
  box-shadow: inset 0 1px 2px rgba(255,255,255,.8);
}
.modepill::before { content: "●"; font-size: .55rem; }

/* ── Empty State ───────────────────────────────────────────────── */
.empty {
  background: var(--panel);
  border: 2px dashed #C2CDD7;
  border-radius: var(--radius);
  padding: 3rem 2rem;
  text-align: center;
  color: var(--muted);
  box-shadow: var(--shadow-sm);
}
.empty-icon {
  font-size: 3rem;
  margin-bottom: .8rem;
  opacity: .6;
  display: block;
}
.empty b {
  display: block;
  color: var(--ink);
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: .4rem;
}
.empty p { margin: 0; font-size: .95rem; }

/* ── Verdict Card ──────────────────────────────────────────────── */
.verdict {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.5rem 1.6rem 1.3rem 1.6rem;
  margin-bottom: 1.1rem;
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}
.verdict::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  border-radius: var(--radius) var(--radius) 0 0;
}
.verdict-top { display: flex; align-items: flex-start; gap: 1.4rem; flex-wrap: wrap; }
.verdict-badge {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  padding: .5rem 1.1rem;
  border-radius: var(--radius-sm);
  font-weight: 800;
  font-size: 1.1rem;
  letter-spacing: .03em;
  border: 2px solid;
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
  flex-shrink: 0;
}
.verdict-meta { color: var(--muted); font-size: .95rem; line-height: 1.65; flex: 1; }
.verdict-meta b { color: var(--ink); }

/* Score gauge */
.score-wrap { margin-top: 1.2rem; }
.score-top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: .4rem; }
.score-num {
  font-size: 2.6rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
}
.score-of { color: var(--muted); font-size: .92rem; }
.score-pct { font-size: .88rem; font-weight: 700; }
/* animated progress bar */
.bar-outer {
  height: 14px;
  background: #E6ECF2;
  border-radius: 999px;
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.12);
}
.bar-inner {
  height: 100%;
  border-radius: 999px;
  transition: width 1s cubic-bezier(.4,0,.2,1);
  position: relative;
}
.bar-inner::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,.35) 50%, transparent 100%);
  border-radius: 999px;
}
/* tick marks */
.bar-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: .3rem;
  font-size: .73rem;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  padding: 0 .1rem;
}
.bar-pin { position: relative; }
.bar-pin::before {
  content: "▼";
  position: absolute;
  top: -16px;
  left: 0;
  transform: translateX(-50%);
  font-size: .6rem;
  color: var(--ink);
}

/* ── Issues / Violations ───────────────────────────────────────── */
.allgood {
  background: var(--pass-bg);
  border: 1.5px solid #9FCFB5;
  border-left: 5px solid var(--pass);
  border-radius: var(--radius-sm);
  padding: 1rem 1.2rem;
  color: #145038;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: .6rem;
}
.issue {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 5px solid var(--fail);
  border-radius: var(--radius-sm);
  padding: 1rem 1.1rem;
  margin-bottom: .75rem;
  box-shadow: var(--shadow-sm);
  transition: box-shadow .2s;
}
.issue:hover { box-shadow: var(--shadow-md); }
.issue.major { border-left-color: var(--warn); }
.issue-head { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; margin-bottom: .35rem; }
.issue-icon { font-size: 1.1rem; }
.issue-name { font-weight: 700; font-size: 1rem; color: var(--ink); }
.sev {
  font-size: .75rem;
  font-weight: 700;
  padding: .18rem .65rem;
  border-radius: 999px;
  letter-spacing: .04em;
  text-transform: uppercase;
}
.sev.critical { background: var(--fail-bg); color: var(--fail); border: 1px solid #F5BEBB; }
.sev.major    { background: var(--warn-bg); color: var(--warn); border: 1px solid #F0CCA0; }
.issue-msg { line-height: 1.6; color: var(--ink); font-size: .95rem; }
.issue-fix {
  margin-top: .5rem;
  padding: .5rem .8rem;
  background: #F7F9FB;
  border-radius: 4px;
  color: var(--muted);
  font-size: .91rem;
  line-height: 1.55;
  border-left: 3px solid var(--line);
}
.issue-fix b { color: var(--teal); }

/* ── Checks Table ──────────────────────────────────────────────── */
table.tbl {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
table.tbl td, table.tbl th {
  padding: .6rem .9rem;
  border-bottom: 1px solid #EDF0F4;
  text-align: left;
  vertical-align: top;
  font-size: .93rem;
}
table.tbl th {
  background: linear-gradient(180deg, #EEF3F7 0%, #E8EFF5 100%);
  font-weight: 700;
  font-size: .83rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .05em;
}
table.tbl tr:last-child td { border-bottom: none; }
table.tbl tbody tr:hover td { background: #F7FAFC; transition: background .15s; }
table.tbl td.k { width: 36%; color: var(--muted); font-size: .91rem; }
.na { color: var(--fail); font-style: italic; font-size: .9rem; }
.mark {
  display: inline-flex;
  width: 1.5rem;
  height: 1.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 800;
  font-size: .82rem;
  color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.mark.PASS { background: linear-gradient(135deg, #22A06B, #1E7B4F); }
.mark.FAIL { background: linear-gradient(135deg, #E0392A, #B42318); }
.mark.SKIP { background: linear-gradient(135deg, #8FA3B1, #6B7F8E); }

/* ── Fields Table Icons ────────────────────────────────────────── */
.field-icon { margin-right: .4rem; opacity: .75; }

/* ── Agent Timeline ────────────────────────────────────────────── */
.trace { padding: .3rem 0; }
.trace-item {
  display: flex;
  gap: 1rem;
  position: relative;
  padding-bottom: 1.1rem;
}
.trace-item:not(:last-child)::before {
  content: "";
  position: absolute;
  left: 1.15rem;
  top: 2.1rem;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, var(--teal-light) 0%, #E0ECF0 100%);
}
.trace-avatar {
  flex-shrink: 0;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: .78rem;
  color: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.2);
  position: relative;
  z-index: 1;
}
.trace-body { flex: 1; padding-top: .2rem; }
.trace-agent { font-weight: 700; font-size: .95rem; color: var(--ink); }
.trace-act {
  font-size: .82rem;
  color: var(--muted);
  margin-left: .4rem;
  background: #EEF3F7;
  padding: .08rem .5rem;
  border-radius: 999px;
  font-weight: 600;
}
.trace-obs {
  margin-top: .35rem;
  line-height: 1.6;
  font-size: .91rem;
  color: #3A4D5C;
  background: #F7FAFC;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: .55rem .8rem;
}

/* ── Stats Strip / KPI ─────────────────────────────────────────── */
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: .8rem;
  margin-bottom: 1.2rem;
}
.stat {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.1rem .9rem 1.1rem;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  transition: transform .18s, box-shadow .18s;
}
.stat:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat::after {
  content: "";
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 3px;
  border-radius: 0 0 var(--radius) var(--radius);
}
.stat-icon { font-size: 1.4rem; margin-bottom: .3rem; display: block; }
.stat-n {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
}
.stat-l { color: var(--muted); font-size: .84rem; margin-top: .15rem; font-weight: 500; }

/* ── Distribution Bar ──────────────────────────────────────────── */
.dist {
  display: flex;
  height: 18px;
  border-radius: 999px;
  overflow: hidden;
  background: #E0E8EF;
  margin: .6rem 0 .7rem 0;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.1);
}
.dist > div { transition: width .6s ease; }
.legend { display: flex; gap: 1.2rem; flex-wrap: wrap; font-size: .88rem; color: var(--muted); }
.legend-dot {
  display: inline-block;
  width: .7rem;
  height: .7rem;
  border-radius: 50%;
  margin-right: .35rem;
  vertical-align: middle;
}

/* ── Horizontal Bars ───────────────────────────────────────────── */
.hbar-row {
  display: grid;
  grid-template-columns: minmax(130px, 38%) 1fr 2.5rem;
  align-items: center;
  gap: .8rem;
  margin: .5rem 0;
  font-size: .92rem;
}
.hbar-label { color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hbar-track {
  background: #E0E8EF;
  height: 11px;
  border-radius: 999px;
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(0,0,0,.08);
}
.hbar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--teal) 0%, #12818A 100%);
  border-radius: 999px;
  transition: width .5s ease;
}
.hbar-n { text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); font-weight: 600; font-size: .88rem; }

/* ── Pipeline / Flow ───────────────────────────────────────────── */
.flow {
  display: flex;
  gap: 0;
  margin: .8rem 0 1.2rem 0;
  overflow-x: auto;
  padding-bottom: .4rem;
}
.flow-step {
  flex: 1 1 160px;
  min-width: 150px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.1rem 1rem 1rem 1rem;
  position: relative;
  box-shadow: var(--shadow-sm);
  transition: transform .18s, box-shadow .18s;
}
.flow-step:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.flow-step:not(:last-child)::after {
  content: "→";
  position: absolute;
  right: -1.05rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.3rem;
  color: var(--teal);
  font-weight: 700;
  z-index: 2;
  background: var(--bg);
  border-radius: 50%;
  width: 1.8rem;
  height: 1.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--teal-light);
  box-shadow: var(--shadow-sm);
}
.flow-step:not(:last-child) { margin-right: 1.5rem; }
.flow-num {
  display: inline-flex;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--teal) 0%, var(--teal-dark) 100%);
  color: #fff;
  align-items: center;
  justify-content: center;
  font-size: .78rem;
  font-weight: 800;
  margin-bottom: .55rem;
  box-shadow: 0 2px 6px rgba(13,110,117,.4);
}
.flow-step b { font-size: 1rem; font-weight: 700; display: block; color: var(--ink); margin-bottom: .25rem; }
.flow-step p { margin: 0; color: var(--muted); font-size: .88rem; line-height: 1.55; }

/* ── Explanation Panel ─────────────────────────────────────────── */
.expl-panel {
  background: #F7FAFC;
  border: 1px solid var(--line);
  border-left: 4px solid var(--teal);
  border-radius: var(--radius-sm);
  padding: 1.1rem 1.3rem;
  box-shadow: var(--shadow-sm);
}

/* ── Sidebar styles ────────────────────────────────────────────── */
.sidebar-logo {
  background: linear-gradient(135deg, var(--teal-dark) 0%, var(--teal) 100%);
  border-radius: var(--radius);
  padding: 1rem 1rem .9rem 1rem;
  margin-bottom: 1rem;
  text-align: center;
  box-shadow: var(--shadow-sm);
}
.sidebar-logo-icon { font-size: 2rem; }
.sidebar-logo-name {
  font-weight: 800;
  font-size: 1.15rem;
  color: #fff;
  letter-spacing: -.01em;
  margin-top: .2rem;
}
.sidebar-logo-tag { font-size: .75rem; color: rgba(255,255,255,.65); letter-spacing: .05em; margin-top: .1rem; }
</style>
"""


def H(markup: str) -> str:
    """Collapse indentation/blank lines so Streamlit's markdown never treats HTML as code."""
    return "\n".join(line.strip() for line in markup.strip().splitlines() if line.strip())


def header(title: str, subtitle: str) -> str:
    return H("""
    <div class="app-banner">
      <div class="app-banner-icon">⚖️</div>
      <div class="app-banner-text">
        <p class="app-title">%s</p>
        <p class="app-sub">%s</p>
      </div>
      <div class="app-badge">SIH 2025</div>
    </div>
    """ % (escape(title), escape(subtitle)))


def empty_state(title: str, text: str) -> str:
    return H("""
    <div class="empty">
      <span class="empty-icon">📋</span>
      <b>%s</b>
      <p>%s</p>
    </div>
    """ % (escape(title), escape(text)))


def _counts(results: List[Dict[str, object]]) -> Tuple[int, int, int]:
    return (sum(1 for r in results if r["status"] == "PASS"),
            sum(1 for r in results if r["status"] == "FAIL"),
            sum(1 for r in results if r["status"] == "SKIP"))


def verdict(res: Dict[str, object]) -> str:
    color, bg_color = PALETTE.get(res["status"], PALETTE["ERROR"])
    label = STATUS_LABEL.get(res["status"], res["status"])
    score = max(0, min(100, int(res["score"])))

    # Icon per status
    status_icon = {
        "COMPLIANT": "✅",
        "PARTIALLY COMPLIANT": "⚠️",
        "NON-COMPLIANT": "❌",
        "ERROR": "⚠️",
    }.get(res["status"], "❓")

    if res["status"] == "ERROR":
        meta = "<b>The check did not run.</b><br>%s" % escape(str(res["explanation"]))
        return H("""
        <div class="verdict" style="border-top:4px solid %(c)s;">
          <div class="verdict-top">
            <span class="verdict-badge" style="color:%(c)s;border-color:%(c)s;background:%(bg)s;">
              %(icon)s %(label)s
            </span>
            <div class="verdict-meta">%(meta)s</div>
          </div>
        </div>
        """ % {"c": color, "bg": bg_color, "icon": status_icon,
               "label": escape(label), "meta": meta})

    passed, failed, skipped = _counts(res["results"])
    issues_text = "No issues found 🎉" if failed == 0 else "%d issue%s to fix" % (failed, "" if failed == 1 else "s")
    meta = "<b>%s</b><br>%d checks passed · %d skipped<br>Checked in <b>%s</b> mode" % (
        issues_text, passed, skipped, escape(str(res["mode"])))

    # animated bar uses inline style with JS-free transition (triggered by browser render)
    bar_gradient = {
        "COMPLIANT": "linear-gradient(90deg, #22A06B 0%, #1E7B4F 100%)",
        "PARTIALLY COMPLIANT": "linear-gradient(90deg, #E8A940 0%, #A8610A 100%)",
        "NON-COMPLIANT": "linear-gradient(90deg, #E0392A 0%, #B42318 100%)",
    }.get(res["status"], "linear-gradient(90deg, #8A96A3, #5B6773)")

    return H("""
    <div class="verdict" style="border-top:4px solid %(c)s;">
      <div class="verdict-top">
        <span class="verdict-badge" style="color:%(c)s;border-color:%(c)s;background:%(bg)s;">
          %(icon)s&nbsp;%(label)s
        </span>
        <div class="verdict-meta">%(meta)s</div>
      </div>
      <div class="score-wrap">
        <div class="score-top">
          <div>
            <span class="score-num" style="color:%(c)s;">%(s)d</span>
            <span class="score-of">&nbsp;/ 100 compliance score</span>
          </div>
          <span class="score-pct" style="color:%(c)s;">%(s)d%%</span>
        </div>
        <div class="bar-outer">
          <div class="bar-inner" style="width:%(s)d%%;background:%(grad)s;"></div>
        </div>
        <div class="bar-ticks">
          <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
        </div>
      </div>
    </div>
    """ % {"c": color, "bg": bg_color, "icon": status_icon,
           "label": escape(label), "meta": meta, "s": score, "grad": bar_gradient})


def issues(results: List[Dict[str, object]]) -> str:
    fails = [r for r in results if r["status"] == "FAIL"]
    if not fails:
        return H('<div class="allgood">✅&nbsp;&nbsp;Every declaration checked is present and valid. Nothing to fix!</div>')
    out = []
    for r in fails:
        sev = r["severity"]
        icon = "🔴" if sev == "critical" else "🟡"
        out.append("""
        <div class="issue %(sev)s">
          <div class="issue-head">
            <span class="issue-icon">%(icon)s</span>
            <span class="issue-name">%(name)s</span>
            <span class="sev %(sev)s">%(sevlabel)s</span>
          </div>
          <div class="issue-msg">%(msg)s</div>
          <div class="issue-fix"><b>💡 How to fix:</b>&nbsp;%(fix)s</div>
        </div>
        """ % {
            "sev": sev,
            "icon": icon,
            "name": escape(r["name"]),
            "sevlabel": SEVERITY_LABEL.get(sev, sev),
            "msg": escape(r["message"]),
            "fix": escape(r["fix"]),
        })
    return H("".join(out))


def checks_table(results: List[Dict[str, object]]) -> str:
    glyph = {"PASS": "✓", "FAIL": "✗", "SKIP": "–"}
    rows = []
    for r in results:
        rows.append(
            "<tr><td style=\"width:2.6rem\"><span class=\"mark %s\">%s</span></td>"
            "<td><b>%s</b></td><td>%s</td></tr>"
            % (r["status"], glyph[r["status"]], escape(r["name"]), escape(r["message"]))
        )
    return H(
        '<table class="tbl"><tr><th></th><th>Check</th><th>Result</th></tr>%s</table>'
        % "".join(rows)
    )


def fields_table(fields: Dict[str, object]) -> str:
    field_icons = {
        "product_name": "📦",
        "generic_name": "🏷️",
        "manufacturer": "🏭",
        "net_quantity": "⚖️",
        "mrp": "💰",
        "selling_price": "🛒",
        "mfg_date": "📅",
        "expiry": "⏳",
        "consumer_care": "📞",
        "country_of_origin": "🌐",
    }
    rows = []
    for key, label in FIELD_LABELS:
        value = fields.get(key)
        shown = '<span class="na">Not declared</span>' if value in (None, "") else escape(str(value))
        icon = field_icons.get(key, "•")
        rows.append(
            "<tr><td class=\"k\"><span class=\"field-icon\">%s</span>%s</td><td>%s</td></tr>"
            % (icon, escape(label), shown)
        )
    tax = "Yes" if fields.get("mrp_incl_tax") else '<span class="na">Not stated</span>'
    rows.append("<tr><td class=\"k\"><span class=\"field-icon\">🧾</span>MRP inclusive of all taxes</td><td>%s</td></tr>" % tax)
    return H('<table class="tbl">%s</table>' % "".join(rows))


def timeline(trace: List[Dict[str, object]]) -> str:
    # Assign avatar colors by agent name
    avatar_colors = [
        "#0D6E75", "#1E7B4F", "#7C3AED", "#B45309", "#1D4ED8",
        "#9D174D", "#065F46", "#92400E",
    ]
    agent_color_map: Dict[str, str] = {}
    color_idx = 0

    items = []
    for s in trace:
        agent_name = str(s["agent"])
        if agent_name not in agent_color_map:
            agent_color_map[agent_name] = avatar_colors[color_idx % len(avatar_colors)]
            color_idx += 1
        initials = "".join(w[0].upper() for w in agent_name.split()[:2]) or "A"
        av_color = agent_color_map[agent_name]
        items.append("""
        <div class="trace-item">
          <div class="trace-avatar" style="background:%(av)s;">%(ini)s</div>
          <div class="trace-body">
            <span class="trace-agent">%(agent)s</span>
            <span class="trace-act">%(act)s</span>
            <div class="trace-obs">%(obs)s</div>
          </div>
        </div>
        """ % {
            "av": av_color,
            "ini": escape(initials),
            "agent": escape(agent_name),
            "act": escape(str(s["action"])),
            "obs": escape(str(s["observation"])),
        })
    return H('<div class="trace">%s</div>' % "".join(items))


def explanation_panel(text: str) -> str:
    return H('<div class="expl-panel pre">%s</div>' % escape(text))


def stats_strip(items: Iterable[Tuple[str, str, str]]) -> str:
    stat_icons = ["📊", "✅", "🟡", "❌", "🏆"]
    cells = []
    for idx, (n, label, color) in enumerate(items):
        icon = stat_icons[idx] if idx < len(stat_icons) else "📌"
        cells.append("""
        <div class="stat" style="border-top:3px solid %(c)s;">
          <span class="stat-icon">%(icon)s</span>
          <div class="stat-n" style="color:%(c)s;">%(n)s</div>
          <div class="stat-l">%(label)s</div>
        </div>
        """ % {"c": color, "icon": icon, "n": escape(str(n)), "label": escape(label)})
    return H('<div class="stats">%s</div>' % "".join(cells))


def distribution(counts: Dict[str, int]) -> str:
    total = sum(counts.values()) or 1
    segs, legend = [], []
    for status in ("COMPLIANT", "PARTIALLY COMPLIANT", "NON-COMPLIANT", "ERROR"):
        n = counts.get(status, 0)
        if not n:
            continue
        color = PALETTE[status][0]
        pct = 100.0 * n / total
        segs.append(
            '<div style="width:%.2f%%;background:%s;" title="%s: %d (%.0f%%)">'
            '</div>' % (pct, color, STATUS_LABEL[status], n, pct)
        )
        legend.append(
            '<span><span class="legend-dot" style="background:%s;"></span>%s: <b>%d</b></span>'
            % (color, STATUS_LABEL[status], n)
        )
    return H(
        '<div class="dist">%s</div><div class="legend">%s</div>'
        % ("".join(segs), "".join(legend))
    )


def hbars(items: List[Tuple[str, int]]) -> str:
    if not items:
        return H('<div class="hint">No rule failures in this batch. 🎉</div>')
    top = max(n for _, n in items) or 1
    rows = []
    for label, n in items:
        pct = 100.0 * n / top
        rows.append("""
        <div class="hbar-row">
          <span class="hbar-label" title="%(label)s">%(label)s</span>
          <div class="hbar-track"><div class="hbar-fill" style="width:%(pct).1f%%"></div></div>
          <span class="hbar-n">%(n)d</span>
        </div>
        """ % {"label": escape(label), "pct": pct, "n": n})
    return H("".join(rows))


def pipeline_steps() -> str:
    steps = [
        ("🔍", "Intake", "Looks at what you gave it — text or a label image — and plans the steps ahead."),
        ("📄", "Extraction", "Reads out the declared details. If something is missing it tries a second method."),
        ("✅", "Validation", "Checks every detail against the rules with plain code, so results are repeatable."),
        ("📝", "Explanation", "Writes what is wrong and how to fix it in plain, actionable language."),
    ]
    step_html = []
    for idx, (icon, title, desc) in enumerate(steps, 1):
        step_html.append("""
        <div class="flow-step">
          <div class="flow-num">%(idx)d</div>
          <b>%(icon)s %(title)s</b>
          <p>%(desc)s</p>
        </div>
        """ % {"idx": idx, "icon": icon, "title": escape(title), "desc": escape(desc)})
    return H('<div class="flow">%s</div>' % "".join(step_html))
