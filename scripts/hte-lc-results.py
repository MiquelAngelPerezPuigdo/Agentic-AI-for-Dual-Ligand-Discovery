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

from hte.analytics import analyze, read_completed_inputs
from hte.ingestion import ingest_exports
from hte.inventory import campaign_inventory
from hte.io import object_digest, read_csv, read_json, write_json
from hte.planning import validate_dosing
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
        doses = read_csv(args.dosing)
        validate_dosing(config, inventory, doses)
        expected_round = 1 if args.mode == "next" else 2
        if (len(doses) != config["design"][f"round{expected_round}_total"]
                or {str(row["round"]) for row in doses} != {str(expected_round)}):
            raise ValueError(f"{args.mode} requires the complete round-{expected_round} dosing table")
        output = Path(args.output)
        peaks, ready = ingest_exports(config, args.exports, args.injections, args.dosing, output / "ingestion")
        if args.mode == "next":
            iteration = iterate(config, inventory, read_json(args.evidence), args.dosing,
                                peaks, ready, args.calibration, output / "decision")
            print("NEXT DOSING:", iteration / "next_dosing.csv")
            print(read_json(iteration / "complete.json")["hardware_status"])
            print("Expected: 22 new pairs + one L17 reference. Review deck loads and import/start the released Python locally.")
        else:
            tables, hashes = read_completed_inputs(config, args.dosing, peaks, ready, args.calibration)
            validate_dosing(config, inventory, tables["dosing"])
            _, report = analyze(config, tables["dosing"], tables["peaks"],
                                tables["calibration"], output / "analysis")
            write_json(output / "analysis/inputs.json", {
                "config": object_digest(config), "inventory": object_digest(inventory), **hashes})
            print("FINAL RESULTS:", output / "analysis/results.csv")
            if not report["batch_qc_pass"]:
                raise ValueError("Final analytical QC failed; inspect qc_report.json")
    except (ValueError, KeyError, FileNotFoundError, ImportError) as error:
        parser.exit(2, f"HTE stopped: {error}\n")


if __name__ == "__main__":
    main()
