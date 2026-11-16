"""Deterministic rule engine for Legal Metrology (Packaged Commodities) declarations.

This module is the "tool" that the Validation Agent calls. It contains NO LLM
calls, so compliance decisions are always reproducible and auditable.

Educational simplification of the Legal Metrology (Packaged Commodities)
Rules, 2011 and the 2017 e-commerce amendment. Always verify against the
official text before relying on it for real compliance work.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

FIELD_KEYS = [
    "product_name",
    "generic_name",
    "manufacturer",
    "net_quantity",
    "mrp",
    "selling_price",
    "mfg_date",
    "expiry",
    "consumer_care",
    "country_of_origin",
]

# Fields that every packaged commodity listing must declare.
MANDATORY_FIELDS = [
    "generic_name",
    "manufacturer",
    "net_quantity",
    "mrp",
    "mfg_date",
    "consumer_care",
    "country_of_origin",
]

STANDARD_UNITS = {"g", "kg", "mg", "ml", "mL", "l", "L", "cl", "cm", "mm", "m", "N"}

UNIT_ALIASES = {
    "gm": "g", "gms": "g", "gram": "g", "grams": "g", "gr": "g",
    "kgs": "kg", "kilogram": "kg", "kilograms": "kg", "kilo": "kg",
    "ltr": "L", "ltrs": "L", "lt": "L", "litre": "L", "litres": "L",
    "liter": "L", "liters": "L",
    "mls": "ml", "millilitre": "ml", "millilitres": "ml",
    "pcs": "N (number)", "pc": "N (number)", "pieces": "N (number)",
    "piece": "N (number)", "nos": "N (number)", "no": "N (number)",
}

MISSING_TOKENS = {
    "", "na", "n/a", "nil", "none", "null", "not available", "not mentioned",
    "not provided", "not applicable", "not specified", "-", "--",
}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

REF = "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)"


def is_missing(value: object) -> bool:
    """True if the value is None or a placeholder such as 'N/A'."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_TOKENS


def parse_money(value: object) -> Optional[float]:
    """Pull the first number out of a price string like 'Rs. 1,299.00 /-'."""
    if is_missing(value):
        return None
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", str(value))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_quantity(value: object) -> Optional[Dict[str, object]]:
    """Parse '500 g', '1L', '2 x 100 g'. Returns None if it cannot be parsed."""
    if is_missing(value):
        return None
    text = str(value).strip().replace(",", "")
    m = re.match(
        r"(?:(\d+)\s*[xX\u00d7*]\s*)?(\d+(?:\.\d+)?)\s*([A-Za-z]+)(?![A-Za-z])\.?", text
    )
    if not m:
        return None
    try:
        amount = float(m.group(2))
    except ValueError:
        return None
    return {
        "count": int(m.group(1)) if m.group(1) else 1,
        "amount": amount,
        "unit": m.group(3),
    }


def parse_month_year(value: object) -> Optional[Tuple[int, int]]:
    """Parse many date styles to (year, month); None if invalid."""
    if is_missing(value):
        return None
    s = str(value).strip().lower()
    year = month = None
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        month, year = int(m.group(2)), int(m.group(3))
    if year is None:
        m = re.fullmatch(r"(\d{1,2})[/\-.](\d{4})", s)
        if m:
            month, year = int(m.group(1)), int(m.group(2))
    if year is None:
        m = re.fullmatch(r"(\d{4})[/\-.](\d{1,2})(?:[/\-.]\d{1,2})?", s)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
    if year is None:
        m = re.fullmatch(r"(?:\d{1,2}[\s\-]+)?([a-z]{3,9})[\s,.\-/]*(\d{4})", s)
        if m:
            name = m.group(1)
            key = name[:4] if name[:4] in MONTHS else name[:3]
            if key in MONTHS:
                month, year = MONTHS[key], int(m.group(2))
    if year is None or month is None:
        return None
    if not (1 <= month <= 12 and 1990 <= year <= 2100):
        return None
    return year, month


@dataclass
class RuleResult:
    rule_id: str
    name: str
    status: str  # PASS | FAIL | SKIP
    severity: str  # critical | major
    weight: int
    message: str
    fix: str
    legal_ref: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


_PHONE = re.compile(
    r"(?:\+?91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}\b|1800[\s\-]?\d{3}[\s\-]?\d{3,4}|\b0\d{2,4}[\s\-]?\d{6,8}\b"
)
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_PIN = re.compile(r"(?<!\d)\d{3}\s?\d{3}(?!\d)")


def validate(fields: Dict[str, object], today: Optional[date] = None) -> List[RuleResult]:
    """Run every rule against the extracted fields and return RuleResults."""
    today = today or date.today()
    out: List[RuleResult] = []

    def add(rule_id, name, status, severity, weight, message, fix=""):
        out.append(RuleResult(rule_id, name, status, severity, weight, message, fix, REF))

    # R01 manufacturer / packer / importer with address
    mfr = fields.get("manufacturer")
    if is_missing(mfr):
        add("R01", "Manufacturer / packer / importer name & address", "FAIL", "critical", 3,
            "Name and address of the manufacturer, packer or importer is missing.",
            "Add the full name and postal address of the manufacturer/packer/importer.")
    elif not _PIN.search(str(mfr)):
        add("R01", "Manufacturer / packer / importer name & address", "FAIL", "critical", 3,
            "Manufacturer details are present but the address has no 6-digit PIN code.",
            "Provide the complete address including the PIN code.")
    else:
        add("R01", "Manufacturer / packer / importer name & address", "PASS", "critical", 3,
            "Manufacturer name and address declared.")

    # R02 generic name
    if is_missing(fields.get("generic_name")):
        add("R02", "Common or generic name of the commodity", "FAIL", "major", 1,
            "Common/generic name of the commodity is missing.",
            "Declare the common or generic name (e.g. 'Basmati Rice', 'Toothpaste').")
    else:
        add("R02", "Common or generic name of the commodity", "PASS", "major", 1,
            "Generic name declared.")

    # R03 / R04 net quantity
    qty = parse_quantity(fields.get("net_quantity"))
    if qty is None or float(qty["amount"]) <= 0:
        raw = fields.get("net_quantity")
        msg = ("Net quantity is missing." if is_missing(raw)
               else "Net quantity '%s' could not be read as a value with a unit." % raw)
        add("R03", "Net quantity declared", "FAIL", "critical", 3, msg,
            "Declare net quantity as a number with a standard unit, e.g. '500 g' or '1 L'.")
        add("R04", "Net quantity uses a standard unit", "SKIP", "major", 2,
            "Skipped because net quantity could not be read.")
    else:
        add("R03", "Net quantity declared", "PASS", "critical", 3,
            "Net quantity declared: %s %s." % (qty["amount"], qty["unit"]))
        unit = str(qty["unit"])
        if unit in STANDARD_UNITS:
            add("R04", "Net quantity uses a standard unit", "PASS", "major", 2,
                "Unit '%s' is a standard unit." % unit)
        else:
            suggestion = UNIT_ALIASES.get(unit.lower())
            hint = ("Use '%s' instead of '%s'." % (suggestion, unit) if suggestion
                    else "Use a standard unit: g, kg, mg, ml, L, cm, m or N (number).")
            add("R04", "Net quantity uses a standard unit", "FAIL", "major", 2,
                "Unit '%s' is not a standard metric unit symbol." % unit, hint)

    # R05 / R06 MRP
    mrp = parse_money(fields.get("mrp"))
    if mrp is None or mrp <= 0:
        add("R05", "Maximum Retail Price (MRP) declared", "FAIL", "critical", 3,
            "MRP is missing or not a valid amount.",
            "Declare 'MRP Rs. <amount> (inclusive of all taxes)'.")
    else:
        add("R05", "Maximum Retail Price (MRP) declared", "PASS", "critical", 3,
            "MRP declared: Rs. %.2f." % mrp)
    if mrp is None:
        add("R06", "MRP stated as inclusive of all taxes", "SKIP", "major", 2,
            "Skipped because MRP is missing.")
    elif fields.get("mrp_incl_tax"):
        add("R06", "MRP stated as inclusive of all taxes", "PASS", "major", 2,
            "MRP is declared as inclusive of all taxes.")
    else:
        add("R06", "MRP stated as inclusive of all taxes", "FAIL", "major", 2,
            "MRP is not declared as inclusive of all taxes.",
            "Add the words 'inclusive of all taxes' next to the MRP.")

    # R07 month & year of manufacture / pack / import
    my = parse_month_year(fields.get("mfg_date"))
    if my is None:
        raw = fields.get("mfg_date")
        msg = ("Month and year of manufacture/packing/import is missing." if is_missing(raw)
               else "Date '%s' could not be read as a valid month and year." % raw)
        add("R07", "Month & year of manufacture / pack / import", "FAIL", "major", 2, msg,
            "Declare the month and year, e.g. '08/2026'.")
    elif (my[0], my[1]) > (today.year, today.month):
        add("R07", "Month & year of manufacture / pack / import", "FAIL", "major", 2,
            "Manufacturing date %02d/%d is in the future." % (my[1], my[0]),
            "Correct the manufacturing/packing month and year.")
    else:
        add("R07", "Month & year of manufacture / pack / import", "PASS", "major", 2,
            "Manufacture/pack date declared: %02d/%d." % (my[1], my[0]))

    # R08 consumer care
    cc = fields.get("consumer_care")
    if is_missing(cc):
        add("R08", "Consumer care details", "FAIL", "major", 2,
            "Consumer care details are missing.",
            "Add a consumer-care phone number or e-mail address.")
    elif _PHONE.search(str(cc)) or _EMAIL.search(str(cc)):
        add("R08", "Consumer care details", "PASS", "major", 2,
            "Consumer care contact declared.")
    else:
        add("R08", "Consumer care details", "FAIL", "major", 2,
            "Consumer care entry has no valid phone number or e-mail.",
            "Provide a valid phone number or e-mail address.")

    # R09 country of origin
    if is_missing(fields.get("country_of_origin")):
        add("R09", "Country of origin", "FAIL", "major", 2,
            "Country of origin is missing.",
            "Declare the country of origin (e.g. 'India').")
    else:
        add("R09", "Country of origin", "PASS", "major", 2,
            "Country of origin declared: %s." % fields.get("country_of_origin"))

    # R10 selling price must not exceed MRP
    sp = parse_money(fields.get("selling_price"))
    if sp is None or mrp is None:
        add("R10", "Selling price does not exceed MRP", "SKIP", "critical", 3,
            "Skipped because selling price or MRP is not available.")
    elif sp > mrp + 1e-9:
        add("R10", "Selling price does not exceed MRP", "FAIL", "critical", 3,
            "Selling price Rs. %.2f is above the declared MRP Rs. %.2f." % (sp, mrp),
            "Reduce the selling price to at most the MRP.")
    else:
        add("R10", "Selling price does not exceed MRP", "PASS", "critical", 3,
            "Selling price Rs. %.2f is within MRP Rs. %.2f." % (sp, mrp))

    # R11 expiry after manufacture
    exp = parse_month_year(fields.get("expiry"))
    if exp is None or my is None:
        add("R11", "Expiry date is after manufacture date", "SKIP", "major", 1,
            "Skipped because expiry or manufacture date is not available.")
    elif exp < my:
        add("R11", "Expiry date is after manufacture date", "FAIL", "major", 1,
            "Expiry %02d/%d is earlier than manufacture %02d/%d." % (exp[1], exp[0], my[1], my[0]),
            "Correct the expiry or manufacture date.")
    else:
        add("R11", "Expiry date is after manufacture date", "PASS", "major", 1,
            "Expiry date is consistent with manufacture date.")

    return out


def summarize(results: List[RuleResult]) -> Tuple[str, int]:
    """Return (overall status, score 0-100)."""
    scored = [r for r in results if r.status != "SKIP"]
    total = sum(r.weight for r in scored) or 1
    passed = sum(r.weight for r in scored if r.status == "PASS")
    score = int(round(100.0 * passed / total))
    fails = [r for r in scored if r.status == "FAIL"]
    if not fails:
        return "COMPLIANT", score
    if any(r.severity == "critical" for r in fails):
        return "NON-COMPLIANT", score
    return "PARTIALLY COMPLIANT", score
