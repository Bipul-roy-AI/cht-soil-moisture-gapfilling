"""Audit the *recorded* CHT daily SMAP series; do not infer why a day is missing.

Usage: python scripts/audit_availability.py
No Earth Engine login or third-party Python packages are required.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path


def audit(path: Path) -> tuple[dict, list[dict]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not {"date", "SMAP_SM"}.issubset(rows[0]):
        raise ValueError("Expected a nonempty CSV with date and SMAP_SM columns")

    observations = []
    for row in rows:
        day = date.fromisoformat(row["date"])
        raw = row["SMAP_SM"].strip()
        # Reject non-finite strings that would otherwise be counted as observed.
        if raw:
            from math import isfinite

            if not isfinite(float(raw)):
                raise ValueError(f"Non-finite SMAP_SM on {day}")
        observations.append((day, bool(raw)))

    observations.sort()
    dates = [day for day, _ in observations]
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate dates in the SMAP export")
    expected = (dates[-1] - dates[0]).days + 1
    if expected != len(dates):
        raise ValueError("The CSV must enumerate every calendar day in its period")

    monthly = defaultdict(lambda: {"days": 0, "valid": 0, "missing": 0})
    max_run = run = 0
    transitions = {"valid_to_missing": 0, "missing_to_valid": 0}
    for i, (day, valid) in enumerate(observations):
        item = monthly[day.strftime("%Y-%m")]
        item["days"] += 1
        item["valid" if valid else "missing"] += 1
        run = 0 if valid else run + 1
        max_run = max(max_run, run)
        if i and observations[i - 1][1] != valid:
            key = "valid_to_missing" if not valid else "missing_to_valid"
            transitions[key] += 1

    n = len(rows)
    missing = sum(not valid for _, valid in observations)
    summary = {
        "source": path.name,
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "total_days": n,
        "valid_days": n - missing,
        "missing_days": missing,
        "missing_fraction": round(missing / n, 6),
        "longest_missing_run_days": max_run,
        "transitions": transitions,
        "interpretation": "Availability of recorded regional daily means only; cause and pixelwise coverage not determined.",
    }
    table = [
        {"month": month, **monthly[month],
         "missing_fraction": round(monthly[month]["missing"] / monthly[month]["days"], 6)}
        for month in sorted(monthly)
    ]
    return summary, table


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project / "data/smap_daily_means.csv")
    parser.add_argument("--output-dir", type=Path, default=project / "results")
    args = parser.parse_args()
    summary, monthly = audit(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "availability_audit.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "availability_monthly.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(monthly[0]))
        writer.writeheader()
        writer.writerows(monthly)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
