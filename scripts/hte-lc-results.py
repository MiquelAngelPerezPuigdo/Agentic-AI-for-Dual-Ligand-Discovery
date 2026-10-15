#!/usr/bin/env python3
"""One local command after completed LC exports: next 22 pairs, or final analysis.

Run from the repository root. Keep the API key in anthropic.key. Each --exports
entry has its corresponding --injections entry in the same order. Use fresh output
directories. This script never connects to or starts a robot.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hte.analytics import analyze
from hte.ingestion import ingest_exports
from hte.inventory import campaign_inventory
from hte.io import read_csv, read_json
from hte.workflow import iterate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("next", "final"))
    parser.add_argument("--config", default="local_data/campaign.json")
    parser.add_argument("--inventory", default="hte_inputs/ligands.csv")
    parser.add_argument("--evidence", default="hte_inputs/literature.json")
    parser.add_argument("--dosing", required=True)
    parser.add_argument("--calibration", default="local_data/calibration.csv")
    parser.add_argument("--exports", nargs="+", required=True)
    parser.add_argument("--injections", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        config = read_json(args.config)
        inventory = campaign_inventory(args.inventory, config, confirmed=True)
        output = Path(args.output)
        peaks, ready = ingest_exports(config, args.exports, args.injections, args.dosing, output / "ingestion")
        if args.mode == "next":
            iteration = iterate(config, inventory, read_json(args.evidence), args.dosing,
                                peaks, ready, args.calibration, output / "decision")
            print("NEXT DOSING:", iteration / "next_dosing.csv")
            print(read_json(iteration / "complete.json")["hardware_status"])
            print("Expected: 22 new pairs + one L17 reference. Review deck loads and import/start the released Python locally.")
        else:
            _, report = analyze(config, read_csv(args.dosing), read_csv(peaks),
                                read_csv(args.calibration), output / "analysis")
            print("FINAL RESULTS:", output / "analysis/results.csv")
            if not report["batch_qc_pass"]:
                raise ValueError("Final analytical QC failed; inspect qc_report.json")
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f"HTE stopped: {error}\n")


if __name__ == "__main__":
    main()
