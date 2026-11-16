import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lm_agents import ComplianceOrchestrator, accuracy, read_listings, run_batch
from lm_agents.extractor import extract_regex
from lm_agents.rules import parse_month_year, parse_money, parse_quantity, validate, summarize

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 16)

GOOD = """Product: Toothpaste
Common Name: Toothpaste
Net Quantity: 150 g
MRP: Rs. 95 (inclusive of all taxes)
Selling Price: Rs. 90
Manufactured by: Dantaa Care Ltd, MG Road, Pune - 411001
Mfg Date: 08/2026
Consumer Care: 1800-123-4567
Country of Origin: India"""


def test_parsers():
    assert parse_money("Rs. 1,299.50 /-") == 1299.5
    assert parse_money("N/A") is None
    assert parse_quantity("2 x 100 g")["count"] == 2
    assert parse_quantity("500gms")["unit"] == "gms"
    assert parse_quantity("big pack") is None
    assert parse_month_year("08/2026") == (2026, 8)
    assert parse_month_year("Sept 2025") == (2025, 9)
    assert parse_month_year("15-03-2026") == (2026, 3)
    assert parse_month_year("13/2026") is None


def test_compliant_listing():
    res = ComplianceOrchestrator(today=TODAY).check(text=GOOD)
    assert res["status"] == "COMPLIANT" and res["score"] == 100


def test_missing_mrp_is_non_compliant():
    res = ComplianceOrchestrator(today=TODAY).check(text=GOOD.replace("MRP: Rs. 95 (inclusive of all taxes)\n", ""))
    assert res["status"] == "NON-COMPLIANT"
    assert any(r["rule_id"] == "R05" and r["status"] == "FAIL" for r in res["results"])


def test_bad_unit_is_partial():
    res = ComplianceOrchestrator(today=TODAY).check(text=GOOD.replace("150 g", "150 gms"))
    assert res["status"] == "PARTIALLY COMPLIANT"


def test_selling_above_mrp():
    res = ComplianceOrchestrator(today=TODAY).check(text=GOOD.replace("Rs. 90", "Rs. 120"))
    assert res["status"] == "NON-COMPLIANT"


def test_no_input_and_image_without_llm_do_not_crash():
    orch = ComplianceOrchestrator(today=TODAY)
    assert orch.check(text="")["status"] == "ERROR"
    assert orch.check(image_bytes=b"x")["status"] == "ERROR"


def test_garbage_text_does_not_crash():
    res = ComplianceOrchestrator(today=TODAY).check(text="\x00??## lorem ipsum")
    assert res["status"] == "NON-COMPLIANT"


class FailingLLM:
    def complete(self, *a, **k):
        raise RuntimeError("network down")


def test_llm_failure_falls_back_to_offline():
    res = ComplianceOrchestrator(llm=FailingLLM(), today=TODAY).check(text=GOOD)
    assert res["status"] == "COMPLIANT"
    assert any("Falling back" in s["observation"] for s in res["trace"])


class FakeLLM:
    def complete(self, system, content, max_tokens=0):
        if "ONLY one JSON" in system:
            return ('{"generic_name":"Toothpaste","manufacturer":"X Ltd, Pune - 411001",'
                    '"net_quantity":"150 g","mrp":"95","mfg_date":"08/2026",'
                    '"consumer_care":"1800-123-4567","country_of_origin":"India","mrp_incl_tax":true}')
        return "Looks fine."


def test_llm_path_with_fake_client():
    res = ComplianceOrchestrator(llm=FakeLLM(), today=TODAY).check(text="anything")
    assert res["status"] == "COMPLIANT"


def test_reflection_recovers_missing_field():
    class PartialLLM(FakeLLM):
        def complete(self, system, content, max_tokens=0):
            out = super().complete(system, content, max_tokens)
            return out.replace('"country_of_origin":"India",', "")
    res = ComplianceOrchestrator(llm=PartialLLM(), today=TODAY).check(text=GOOD)
    assert res["fields"]["country_of_origin"] == "India"
    assert any(s["action"] == "reflect" for s in res["trace"])


def test_sample_dataset_matches_labels():
    rows = read_listings(ROOT / "data" / "sample_listings.csv")
    results = run_batch(ComplianceOrchestrator(today=TODAY), rows)
    assert len(results) >= 20
    assert accuracy(results) == 1.0
