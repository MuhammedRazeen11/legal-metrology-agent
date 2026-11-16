"""Batch processing and report writers (CSV + Markdown)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Dict, List, Optional


def _parse_rows(fh) -> List[Dict[str, str]]:
    reader = csv.DictReader(fh)
    if not reader.fieldnames or "listing_text" not in reader.fieldnames:
        raise ValueError("The CSV needs a column named 'listing_text'.")
    rows = []
    for i, row in enumerate(reader, 1):
        row = {k: (v or "") for k, v in row.items() if k is not None}
        if not row.get("listing_id"):
            row["listing_id"] = "L%03d" % i
        rows.append(row)
    if not rows:
        raise ValueError("The CSV has no rows to check.")
    return rows


def read_listings(path) -> List[Dict[str, str]]:
    """Read a CSV with a 'listing_text' column (and optional listing_id, title, expected_status)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return _parse_rows(fh)


def parse_listings_bytes(data: bytes) -> List[Dict[str, str]]:
    """Same as read_listings, for uploaded file contents."""
    import io

    return _parse_rows(io.StringIO(data.decode("utf-8-sig", errors="replace"), newline=""))


def run_batch(orchestrator, rows: List[Dict[str, str]],
              progress: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, object]]:
    results = []
    for i, row in enumerate(rows, 1):
        res = orchestrator.check(text=row.get("listing_text", ""), listing_id=row["listing_id"])
        res["title"] = row.get("title", "")
        res["expected_status"] = row.get("expected_status", "")
        results.append(res)
        if progress:
            progress(i, len(rows))
    return results


def flatten(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = []
    for r in results:
        failed = [x["rule_id"] for x in r["results"] if x["status"] == "FAIL"]
        rows.append({
            "listing_id": r["listing_id"],
            "title": r.get("title", ""),
            "status": r["status"],
            "score": r["score"],
            "failed_rules": ";".join(failed),
            "expected_status": r.get("expected_status", ""),
        })
    return rows


def write_csv(results, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = flatten(results)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["listing_id", "title", "status", "score", "failed_rules", "expected_status"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def markdown_report(results) -> str:
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines = ["# Legal Metrology Compliance Report", "",
             "Listings checked: %d" % len(results), ""]
    for status, n in sorted(counts.items()):
        lines.append("- %s: %d" % (status, n))
    lines.append("")
    for r in results:
        lines.append("## %s - %s (score %s)" % (r["listing_id"], r["status"], r["score"]))
        if r.get("title"):
            lines.append("*%s*" % r["title"])
        lines.append("")
        lines.append(str(r["explanation"]))
        lines.append("")
    return "\n".join(lines)


def write_markdown(results, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_report(results), encoding="utf-8")
    return path


def accuracy(results) -> Optional[float]:
    labelled = [r for r in results if r.get("expected_status")]
    if not labelled:
        return None
    ok = sum(1 for r in labelled if r["status"] == r["expected_status"])
    return ok / len(labelled)
