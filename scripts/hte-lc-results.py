#!/usr/bin/env python3
"""One local command after completed LC exports: next 22 pairs, or final analysis.

Run from the repository root. Keep the API key in anthropic.key. Each --exports
entry has its corresponding --injections entry in the same order. Repeat the same
command/output to resume unchanged inputs without buying accepted scores again.
Use a fresh output directory for deliberately changed inputs. This script never
connects to or starts a robot.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hte.analytics import analyze, read_completed_inputs
from hte.ingestion import ingest_exports
from hte.inventory import campaign_inventory
from hte.io import digest, file_lock, object_digest, read_csv, read_json, write_json
from hte.planning import validate_dosing
from hte.transfer import snapshot_settings
from hte.workflow import iterate


def source_inputs(args):
    """Fingerprint exact, ordered inputs before reading any effective settings."""
    files = [("config", args.config), ("inventory", args.inventory),
             ("dosing", args.dosing), ("calibration", args.calibration)]
    if args.mode == "next":
        files.append(("evidence", args.evidence))
    files.extend(("export", path) for path in args.exports)
    files.extend(("injections", path) for path in args.injections)
    return {"mode": args.mode, "files": [
        {"role": role, "path": str(Path(path).resolve()), "sha256": digest(path)}
        for role, path in files]}


def prepared_inputs(args, output, config, inventory, evidence, sources):
    """Reuse verified preparation, retaining the original paid-scoring path.

    The caller holds .helper.lock throughout the complete command. A committed
    input manifest is written before iterate can create or purchase any score.
    """
    manifest = output / "helper_inputs.json"
    if manifest.exists():
        saved = read_json(manifest)
        if saved["sources"] != sources:
            raise ValueError("Inputs changed since this run. Preserve its scoring records; "
                             "use a new output directory only for an intentional new decision")
        files = {path.relative_to(output).as_posix(): path
                 for folder in (output / "inputs", output / "ingestion")
                 for path in folder.rglob("*") if path.is_file()}
        if set(files) != set(saved["prepared_sha256"]) or any(
                digest(files[name]) != expected
                for name, expected in saved["prepared_sha256"].items()):
            raise ValueError("Archived helper input changed or disappeared; restore the verified "
                             "snapshot before resuming this run")
        print("RESUMING VERIFIED RUN:", output, flush=True)
    else:
        existing = {path.name for path in output.iterdir()} - {".helper.lock"}
        if existing:
            raise ValueError("Output has no completed helper input manifest. Preserve it and "
                             "inspect any existing scoring records before choosing a new directory")
        write_json(output / "helper_started.json", {"sources": sources,
                   "status": "preparing_inputs_no_scoring_started"})
        snapshot_settings(Path(__file__).resolve().parents[1], output / "inputs",
                          config, inventory, evidence, args.calibration)
        ingest_exports(config, args.exports, args.injections, args.dosing, output / "ingestion")
        if source_inputs(args) != sources:
            raise ValueError("Inputs changed during helper preparation; no scoring was started")
        files = {path.relative_to(output).as_posix(): digest(path)
                 for folder in (output / "inputs", output / "ingestion")
                 for path in folder.rglob("*") if path.is_file()}
        write_json(manifest, {"schema_version": 1, "sources": sources, "prepared_sha256": files})
    return (output / "ingestion/peaks.csv", output / "ingestion/peaks.ready.json",
            output / "inputs/calibration.csv", output / "ingestion/sources/dosing.csv")


def process(args, config, inventory, evidence, sources):
    output = Path(args.output)
    with file_lock(output / ".helper.lock"):
        peaks, ready, calibration, dosing = prepared_inputs(
            args, output, config, inventory, evidence, sources)
        if args.mode == "next":
            iteration = iterate(config, inventory, evidence, dosing,
                                peaks, ready, calibration, output / "decision")
            print("NEXT DOSING:", iteration / "next_dosing.csv")
            print(read_json(iteration / "complete.json")["hardware_status"])
            if (iteration / "protocols/dose_and_react.py").exists():
                if (iteration/"protocols/refill_stocks.py").exists():
                    print("RUN R2 AUTOMATIC STOCK REFILL FIRST:",iteration/"protocols/refill_stocks.py")
                print("R2 PROTOCOL:", iteration / "protocols/dose_and_react.py")
                print("R2 DECK LOADS:", iteration / "protocols/deck_loads.csv")
            print("Expected: 22 new pairs + one L17 reference. Review deck loads and import/start the released Python locally.")
        else:
            tables, hashes = read_completed_inputs(config, dosing, peaks, ready, calibration)
            validate_dosing(config, inventory, tables["dosing"])
            _, report = analyze(config, tables["dosing"], tables["peaks"],
                                tables["calibration"], output / "analysis")
            write_json(output / "analysis/inputs.json", {
                "config": object_digest(config), "inventory": object_digest(inventory), **hashes})
            print("FINAL RESULTS:", output / "analysis/results.csv")
            if not report["batch_qc_pass"]:
                raise ValueError("Final analytical QC failed; inspect qc_report.json")
            print("RETURN PACKAGE: python scripts/hte-return-package.py (after copying instrument logs/raw files and notes into local_data)")


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
        sources = source_inputs(args)
        config = read_json(args.config)
        inventory = campaign_inventory(args.inventory, config, confirmed=True)
        doses = read_csv(args.dosing)
        validate_dosing(config, inventory, doses)
        expected_round = 1 if args.mode == "next" else 2
        if (len(doses) != config["design"][f"round{expected_round}_total"]
                or {str(row["round"]) for row in doses} != {str(expected_round)}):
            raise ValueError(f"{args.mode} requires the complete round-{expected_round} dosing table")
        evidence = read_json(args.evidence) if args.mode == "next" else None
        if source_inputs(args) != sources:
            raise ValueError("Inputs changed while reading helper settings; no scoring was started")
        process(args, config, inventory, evidence, sources)
    except (ValueError, KeyError, FileNotFoundError, ImportError) as error:
        parser.exit(2, f"HTE stopped: {error}\n")


if __name__ == "__main__":
    main()
