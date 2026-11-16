import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ui_components as ui
from lm_agents import ComplianceOrchestrator


def test_user_text_is_escaped_in_html():
    evil = "<script>alert(1)</script>"
    res = ComplianceOrchestrator().check(text="Product: %s\nMRP: Rs 10" % evil)
    html = ui.fields_table(res["fields"]) + ui.issues(res["results"]) + ui.checks_table(res["results"])
    assert "<script>" not in html


def test_verdict_renders_for_every_status():
    orch = ComplianceOrchestrator()
    for text in ["", "Product: x", "Product: x\nMRP: Rs 5"]:
        assert "verdict" in ui.verdict(orch.check(text=text))


def test_app_runs_end_to_end():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    [b for b in at.button if b.label == "Run check"][0].click().run()
    assert not at.exception
    [b for b in at.button if b.label == "Run audit"][0].click().run()
    assert not at.exception
