"""Command-line demo: checks the bundled sample listings (or your own) and writes reports.

Usage:
    python run_demo.py                      # batch-check data/sample_listings.csv
    python run_demo.py --input my.csv       # your own CSV (needs a 'listing_text' column)
    python run_demo.py --text "MRP: Rs 50"  # check a single pasted listing
    python run_demo.py --llm                # use Claude if ANTHROPIC_API_KEY is set
"""
import argparse
import sys
from pathlib import Path

from lm_agents import (ComplianceOrchestrator, accuracy, flatten, get_llm,
                       read_listings, run_batch, write_csv, write_markdown)

ROOT = Path(__file__).resolve().parent


def main() -> int:
    try:
        sys.stdout.reconfigure(errors="replace")  # avoid Windows console encoding crashes
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Legal Metrology compliance checker")
    parser.add_argument("--input", default=str(ROOT / "data" / "sample_listings.csv"))
    parser.add_argument("--out", default=str(ROOT / "outputs"))
    parser.add_argument("--text", help="check one listing given as text")
    parser.add_argument("--llm", action="store_true", help="use Claude when ANTHROPIC_API_KEY is set")
    args = parser.parse_args()

    llm = get_llm() if args.llm else None
    if args.llm and llm is None:
        print("Note: no ANTHROPIC_API_KEY / anthropic package found - running offline.")
    orch = ComplianceOrchestrator(llm=llm)
    print("Mode:", orch.mode)

    if args.text:
        res = orch.check(text=args.text, listing_id="cli")
        print("\nStatus: %s | Score: %s\n" % (res["status"], res["score"]))
        print(res["explanation"])
        print("\nAgent trace:")
        for s in res["trace"]:
            print("  %d. [%s] %s: %s" % (s["step"], s["agent"], s["action"], s["observation"]))
        return 0

    try:
        rows = read_listings(args.input)
    except (OSError, ValueError) as exc:
        print("Could not read input file: %s" % exc)
        return 1
    results = run_batch(orch, rows)

    print("\n%-16s %-22s %5s  %s" % ("Listing", "Status", "Score", "Failed rules"))
    print("-" * 70)
    for r in flatten(results):
        print("%-16s %-22s %5s  %s" % (r["listing_id"], r["status"], r["score"], r["failed_rules"]))

    acc = accuracy(results)
    if acc is not None:
        print("\nAgreement with expected_status labels: %.1f%%" % (acc * 100))

    out = Path(args.out)
    csv_path = write_csv(results, out / "compliance_report.csv")
    md_path = write_markdown(results, out / "compliance_report.md")
    print("\nReports written to:\n  %s\n  %s" % (csv_path, md_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
