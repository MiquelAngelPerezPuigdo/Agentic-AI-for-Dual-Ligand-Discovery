#!/usr/bin/env python3
"""Check a local preparation manifest and/or the selected R2 layout."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    import csv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--r2-dosing", type=Path)
    args = parser.parse_args()
    if not args.preparation and not args.r2_dosing:
        parser.error("provide --preparation and/or --r2-dosing")
    if args.preparation:
        signature = json.loads((ROOT / "protocols/fixed-campaign/stock-preparation/recipe-signature.json").read_text())
        actual = json.loads(args.preparation.read_text())
        if any(actual.get(key) != value for key, value in signature.items()):
            raise ValueError("Local stock recipe/design differs from the published robot preparation. Reconcile before R2.")
        print("Local preparation matches the published stock recipe and first-round design.")
    if args.r2_dosing:
        def positions(path):
            with path.open(newline="", encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
            return [(r["sample_id"], r["well"], r["lc_well"]) for r in rows]
        expected = positions(ROOT / "protocols/fixed-campaign/round2-workup/well-map.csv")
        if positions(args.r2_dosing) != expected:
            raise ValueError("R2 well mapping differs: use the workup generated for the actual R2 design.")
        print("R2 reaction and LC positions match the published fixed workup.")


if __name__ == "__main__":
    main()
