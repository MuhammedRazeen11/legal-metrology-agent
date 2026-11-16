"""Field extraction tools: an offline regex extractor and an optional LLM extractor."""
from __future__ import annotations

import re
from typing import Dict, Optional

from .rules import FIELD_KEYS, is_missing

LABELS = {
    "product_name": ["product name", "product", "title", "item", "name"],
    "generic_name": ["generic name", "common name", "common or generic name", "commodity"],
    "manufacturer": [
        "manufacturer", "manufactured by", "marketed by", "packed by", "packer",
        "packed & marketed by", "importer", "imported by",
        "manufacturer / packer / importer", "manufacturer name & address",
    ],
    "net_quantity": [
        "net quantity", "net qty", "net wt", "net weight", "net content",
        "net contents", "quantity", "net volume",
    ],
    "mrp": ["mrp", "m.r.p", "maximum retail price"],
    "selling_price": ["selling price", "price", "sale price", "our price", "offer price"],
    "mfg_date": [
        "mfg date", "manufacturing date", "date of manufacture", "manufactured on",
        "packed on", "pkd", "pkd date", "month and year of manufacture",
        "date of import", "mfg", "packing date",
    ],
    "expiry": ["expiry", "expiry date", "best before", "use by", "exp", "exp date"],
    "consumer_care": [
        "consumer care", "customer care", "consumer care details", "contact",
        "helpline", "customer support", "for complaints",
    ],
    "country_of_origin": ["country of origin", "origin", "made in"],
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


_LABEL_MAP = {_norm(s): key for key, syns in LABELS.items() for s in syns}
_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 &/.\-()]{1,60}?)\s*[:=]\s*(.+?)\s*$")


def empty_fields() -> Dict[str, object]:
    fields: Dict[str, object] = {k: None for k in FIELD_KEYS}
    fields["mrp_incl_tax"] = False
    return fields


def extract_regex(text: str) -> Dict[str, object]:
    """Offline extractor: 'Label: value' lines first, then regex fallbacks."""
    fields = empty_fields()
    text = text or ""

    for line in re.split(r"\r?\n|\s\|\s", text):
        m = _LINE.match(line)
        if not m:
            continue
        key = _LABEL_MAP.get(_norm(m.group(1)))
        value = m.group(2).strip()
        if key and fields[key] is None and not is_missing(value):
            fields[key] = value

    flags = re.IGNORECASE

    def fallback(key: str, pattern: str, group: int = 1) -> None:
        if fields[key] is None:
            m = re.search(pattern, text, flags)
            if m and not is_missing(m.group(group)):
                fields[key] = m.group(group).strip(" ,.;-")

    fallback("mrp", r"(?:\bmrp\b|m\.r\.p\.?|maximum retail price)\s*[:\-]?\s*(?:rs\.?|inr|\u20b9)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
    fallback("net_quantity", r"net\s*(?:qty|quantity|wt|weight|content[s]?|volume)\.?\s*[:\-]?\s*(\d[\d.,]*\s*[A-Za-z]+)")
    fallback("country_of_origin", r"(?:country of origin|made in)\s*[:\-]?\s*([A-Za-z][A-Za-z ]{1,30})")
    fallback("mfg_date", r"(?:mfg\.?|manufactured|pkd\.?|packed)\s*(?:date|on)?\s*[:\-]\s*([0-9A-Za-z/\-. ]{4,16})")
    fallback("manufacturer", r"(?:manufactured|marketed|packed|imported)(?:\s*(?:&|and)\s*(?:marketed|packed))?\s*by\s*[:\-]?\s*([^\n]+)")

    if fields["consumer_care"] is None:
        m = re.search(
            r"(?:\+?91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}\b|1800[\s\-]?\d{3}[\s\-]?\d{3,4}|[\w.+\-]+@[\w\-]+\.[\w.\-]+",
            text,
        )
        if m:
            fields["consumer_care"] = m.group(0)

    fields["mrp_incl_tax"] = bool(
        re.search(r"incl\w*\.?\s*(?:of\s*)?(?:all\s*)?taxes", text, flags)
    )
    return fields


LLM_SYSTEM = (
    "You extract Legal Metrology declarations from e-commerce product listings or "
    "product label images. Reply with ONLY one JSON object with these keys: "
    "product_name, generic_name, manufacturer (name AND address), net_quantity "
    "(value and unit as written), mrp (as written), selling_price (as written), "
    "mfg_date (month/year of manufacture, packing or import), expiry, consumer_care "
    "(phone or e-mail), country_of_origin, mrp_incl_tax (true only if the text says the "
    "MRP is inclusive of all taxes). Use null for anything not present. Never guess "
    "or invent values."
)


def _extract_json(text: str) -> Optional[dict]:
    import json

    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[start:i + 1])
                        if isinstance(data, dict):
                            return data
                    except ValueError:
                        break
                    break
        start = text.find("{", start + 1)
    return None


def extract_llm(llm, text: Optional[str] = None, image_bytes: Optional[bytes] = None,
                media_type: str = "image/png") -> Dict[str, object]:
    """LLM extractor. Raises on any failure so the caller can fall back."""
    import base64

    content = []
    if image_bytes:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        })
    content.append({"type": "text", "text": "Listing / label content:\n" + (text or "(see image)")})
    raw = llm.complete(LLM_SYSTEM, content, max_tokens=900)
    data = _extract_json(raw)
    if data is None:
        raise ValueError("LLM did not return valid JSON")
    fields = empty_fields()
    for key in FIELD_KEYS:
        value = data.get(key)
        if value is not None and not is_missing(value):
            fields[key] = str(value).strip()
    fields["mrp_incl_tax"] = bool(data.get("mrp_incl_tax"))
    return fields
