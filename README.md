# ⚖️ Legal Metrology Compliance Agent

> **SIH 2025 · PS SIH25057**  
> An agentic AI system that automates Legal Metrology compliance auditing of e-commerce product listings, reducing manual inspection effort for regulators, platforms, and sellers.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🎯 What it does

Indian law (Legal Metrology (Packaged Commodities) Rules, 2011) requires every packaged product to declare:

| Field | Rule |
|---|---|
| Manufacturer / packer / importer name & address (with PIN) | R01 |
| Common / generic name of the commodity | R02 |
| Net quantity in standard units (g, kg, ml, L…) | R03–R04 |
| MRP (inclusive of all taxes) | R05–R06 |
| Month & year of manufacture / packing / import | R07 |
| Consumer care phone or e-mail | R08 |
| Country of origin | R09 |
| Selling price ≤ MRP | R10 |
| Expiry after manufacture date | R11 |

This tool checks product listings (text or label images) against all 11 rules and reports a **COMPLIANT / PARTIALLY COMPLIANT / NON-COMPLIANT** verdict with a 0–100 compliance score.

---

## 🏗️ Architecture — Multi-Agent Pipeline

```
Input (text / image)
        │
        ▼
  ┌─────────────┐
  │ Intake Agent │  ← Decides: text-only or vision needed?
  └──────┬──────┘
         │
         ▼
  ┌──────────────────┐
  │ Extraction Agent  │  ← Regex (offline) or Claude (vision+LLM)
  │  + Reflection     │  ← Retries with alternate method if fields missing
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Validation Agent  │  ← Deterministic rule engine (rules.py) — no LLM
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────────┐
  │ Explanation Agent     │  ← Plain-language fixes (offline template / Claude)
  └──────┬───────────────┘
         │
         ▼
   Compliance Report
   (verdict · score · violations · fix hints · agent trace)
```

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/legal-metrology-agent.git
cd legal-metrology-agent
```

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run (Offline — no API key needed)

```bash
streamlit run app.py
```

Open → **http://localhost:8501**

### 4. Run with Claude (optional — adds image reading & richer explanations)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

Or paste the key directly into the sidebar inside the app.

---

## 📂 Project Structure

```
legal_metrology_agent/
├── app.py                  # Streamlit dashboard (main entry point)
├── ui_components.py        # All CSS & HTML renderers
├── run_demo.py             # CLI demo (no Streamlit)
├── requirements.txt
├── .streamlit/
│   └── config.toml         # Theme
├── data/
│   └── sample_listings.csv # 28 labelled sample listings
├── lm_agents/
│   ├── __init__.py         # Public API + orchestrator
│   ├── agents.py           # Intake, Extraction, Validation, Explanation agents
│   ├── extractor.py        # Regex field extractor
│   ├── llm.py              # Anthropic Claude wrapper (lazy import)
│   ├── report.py           # Batch report helpers
│   └── rules.py            # Deterministic rule engine (11 rules)
└── tests/
    ├── test_pipeline.py
    └── test_ui.py
```

---

## ☁️ Deploy on Streamlit Cloud (free)

1. Push this repo to GitHub (public or private)
2. Go to → [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set **Main file: `app.py`**
4. *(Optional)* Add `ANTHROPIC_API_KEY` under **Settings → Secrets**
5. Click **Deploy** — live in ~2 minutes

---

## 🧪 Tests

```bash
pytest tests/ -v
```

11 tests covering the rule engine and UI renderers.

---

## 📋 Compliance Scoring

| Status | Condition |
|---|---|
| ✅ COMPLIANT | All 11 rules pass |
| 🟡 PARTIALLY COMPLIANT | Only major-severity rules fail |
| ❌ NON-COMPLIANT | At least one critical rule fails |

Score = weighted pass rate (critical rules weight 3×, major rules weight 1–2×).

---

## ⚠️ Disclaimer

Educational tool based on a simplified reading of the Legal Metrology (Packaged Commodities) Rules, 2011 and the 2017 e-commerce amendment. Always verify against the official text before relying on it for real compliance work.

---

## 📄 License

MIT © 2025
