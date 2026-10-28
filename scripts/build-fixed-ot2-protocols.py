#!/usr/bin/env python3
"""Publish fixed-movement OT-2 files; LC interpretation remains locally gated."""
from __future__ import annotations

import ast
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.design import make_design
from hte.inventory import campaign_inventory, candidates
from hte.io import read_csv, read_json, write_csv, write_json
from hte.planning import dosing_rows, transfer_operations
from hte.preparation import export_stock_preparation
from hte.protocols import export

DEST = ROOT / "protocols" / "fixed-campaign"
PREFLIGHT = (
    "HTE PRE-FLIGHT: The project owner confirmed the planned setup. Before running, "
    "the local operator must confirm the actual deck, labware definitions and offsets, "
    "source recovery and solvent compatibility, safe shaker mounting and containment, "
    "and the setup files for this run. Stop if any differ. Analytical method, LC peak "
    "separation and calibration must be established from real standards; they are "
    "not certified by this protocol. Resume only when the local setup is suitable."
)


def fixed_r2_design(config, inventory, history, reverse=False):
    pairs = candidates(inventory)
    ranking = [dict(pair_id=p["pair_id"], mean_score=100 - 99 * i / len(pairs), score_sd=0)
               for i, p in enumerate(reversed(pairs) if reverse else pairs)]
    return make_design(config, inventory, pairs, ranking, [], 2, history=history)


def workup_ops(config, inventory, design):
    rows = dosing_rows(config, inventory, design)
    return [op for op in transfer_operations(config, inventory, rows)
            if op["stage"] in {"workup", "dilution", "sampling"}]


def make_executable(source, *, workup_only=False):
    text = source.read_text()
    tree = ast.parse(text)
    assignments = {t.id: n for n in tree.body if isinstance(n, ast.Assign)
                   for t in n.targets if isinstance(t, ast.Name)}
    demo = assignments["DEMO"]
    if ast.literal_eval(demo.value) is not True or demo.lineno != demo.end_lineno:
        raise ValueError("Expected a guarded simulation export")
    lines = text.splitlines(keepends=True)
    # Stock preparation places several assignments on a single line.
    line = lines[demo.lineno - 1]
    old = "DEMO=True" if "DEMO=True" in line else "DEMO = True"
    if line.count(old) != 1:
        raise ValueError("Unexpected preview guard representation")
    lines[demo.lineno - 1] = line.replace(old, old.replace("True", "False"), 1)
    if workup_only:
        operations = assignments["OPERATIONS"]
        values = ast.literal_eval(operations.value)
        values = [op for op in values if op["stage"] in {"workup", "dilution", "sampling"}]
        if operations.lineno != operations.end_lineno:
            raise ValueError("Unexpected operation layout")
        lines[operations.lineno - 1] = "OPERATIONS = " + repr(values) + "\n"
        hold = assignments["HOLD_PLAN"]
        lines[hold.lineno - 1] = "HOLD_PLAN = {}\n"
    text = "".join(lines)
    signature = "def run(protocol: protocol_api.ProtocolContext):\n"
    if text.count(signature) != 1:
        raise ValueError("Unexpected generated protocol entry point")
    return ("# PREPLANNED EXECUTABLE: local operator preflight required; no LC calibration claimed.\n"
            + text.replace(signature, signature + "    protocol.pause(" + repr(PREFLIGHT) + ")\n", 1))


def main():
    config = read_json(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config, confirmed=True)
    first = read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv")
    second = fixed_r2_design(config, inventory, first)
    alternate = fixed_r2_design(config, inventory, first, reverse=True)
    if workup_ops(config, inventory, second) != workup_ops(config, inventory, alternate):
        raise ValueError("R2 workup movements are not independent of selected ligands")
    if DEST.exists():
        raise ValueError(f"Remove existing generated folder before rebuilding: {DEST}")
    with tempfile.TemporaryDirectory(prefix="hte-fixed-") as temp:
        temp = Path(temp)
        stock = export_stock_preparation(config, inventory, first, temp / "stock")
        r1 = temp / "r1"
        export(config, inventory, first, r1)
        r2 = temp / "r2"
        export(config, inventory, second, r2, history=dosing_rows(config, inventory, first), stage="workup")
        (DEST / "stock-preparation").mkdir(parents=True)
        (DEST / "round1").mkdir()
        (DEST / "round2-workup").mkdir()
        for source, dest, only in [(stock / "prepare_stocks.py", DEST / "stock-preparation/prepare_stocks.py", False),
                                    (r1 / "dose_and_react.py", DEST / "round1/dose_and_react.py", False),
                                    (r1 / "workup.py", DEST / "round1/workup.py", False),
                                    (r2 / "workup.py", DEST / "round2-workup/workup.py", True)]:
            dest.write_text(make_executable(source, workup_only=only))
        for name in ("bulk_carriers.csv", "raw_reagents_to_load.csv"):
            shutil.copyfile(stock / name, DEST / "stock-preparation" / name)
        manifest = read_json(stock / "preparation_manifest.json")
        write_json(DEST / "stock-preparation/recipe-signature.json",
                   {key: manifest[key] for key in ("recipe_digest", "inventory_digest", "design_signature")})
        for name in ("dosing.csv", "deck_loads.csv", "raw_reagents_to_load.csv", "calibration_preparation.csv",
                     "calibration_injection_map.csv", "lc_batch01_injections.csv", "lc_sequence.csv"):
            shutil.copyfile(r1 / name, DEST / "round1" / name)
        write_csv(DEST / "round2-workup/well-map.csv",
                  [{k: row[k] for k in ("sample_id", "well", "lc_well")} for row in second])
    print(DEST)


if __name__ == "__main__":
    main()
