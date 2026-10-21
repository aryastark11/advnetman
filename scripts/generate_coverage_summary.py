#!/usr/bin/env python3
"""
Generates a markdown summary table from coverage.json for GitHub Step Summary and local reporting.
"""

import os
import sys
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate markdown coverage summary")
    parser.add_argument("--input", default="build/coverage/coverage.json", help="Path to coverage.json")
    parser.add_argument("--output", default="build/coverage_summary.md", help="Path to output markdown")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: coverage file {args.input} not found.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        cov = json.load(f)

    totals = cov.get("totals", {})
    pct = totals.get("percent_covered", 0.0)
    stmts = totals.get("num_statements", 0)
    missing = totals.get("missing_lines", 0)

    md = f"# 🧪 NSoT GUI Unit Tests & Code Coverage Summary\n\n"
    md += f"**Total Code Coverage**: `{pct:.1f}%` | **Total Statements**: `{stmts}` | **Missed Statements**: `{missing}`\n\n"
    md += "| Module | Statements | Missing | Coverage |\n"
    md += "| :--- | :--- | :--- | :--- |\n"

    for file_path, data in sorted(cov.get("files", {}).items()):
        fname = os.path.basename(file_path)
        summary = data.get("summary", {})
        fpct = summary.get("percent_covered", 0.0)
        fstmts = summary.get("num_statements", 0)
        fmiss = summary.get("missing_lines", 0)
        badge = "🟢" if fpct >= 80 else ("🟡" if fpct >= 50 else "🔴")
        md += f"| `{fname}` | {fstmts} | {fmiss} | {badge} **{fpct:.1f}%** |\n"

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out:
        out.write(md)

    print(f"[✓] Coverage summary markdown generated at: {args.output}")
    print(f"    Total Coverage: {pct:.1f}% ({stmts - missing}/{stmts} statements)")

if __name__ == "__main__":
    main()
