from __future__ import annotations

import json
import time
from pathlib import Path

from .analytics import analyze, observations, validate_completion
from .design import make_design
from .inventory import candidates
from .io import digest, object_digest, read_csv, read_json, write_csv, write_json
from .planning import dosing_rows
from .protocols import export
from .scoring import score_candidates


def iterate(config, inventory, evidence, dosing_path, peaks_path, ready_path, calibration_path, output):
    if config.get("demo"):
        raise ValueError("Use the offline demo command for synthetic data")
    validate_completion(ready_path, peaks_path, dosing_path, config)
    dosing = read_csv(dosing_path)
    if {r["round"] for r in dosing} != {"1"} or len(dosing) != config["design"]["round1_total"]:
        raise ValueError("Iteration requires the entire configured first round")
    if config["design"].get("round2_controls") is None:
        raise ValueError("Specify round-two controls, or [] for ten new pairs")
    inputs = {"config": object_digest(config), "inventory": object_digest(inventory), "evidence": object_digest(evidence),
              "dosing": digest(dosing_path), "peaks": digest(peaks_path), "ready": digest(ready_path), "calibration": digest(calibration_path)}
    out = Path(output)/("iteration-"+object_digest(inputs)[:16])
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/"inputs.json", inputs)
    if (out/"complete.json").exists():
        # Repeated watcher events return the existing audited batch, without API calls or overwrites.
        completed = read_json(out/"complete.json")
        for name, expected in completed["output_sha256"].items():
            if not (out/name).exists() or digest(out/name) != expected:
                raise ValueError("Completed iteration output changed or disappeared: "+name)
        return out
    results, report = analyze(config, dosing, read_csv(peaks_path), read_csv(calibration_path), out/"analysis")
    if not report["batch_qc_pass"]:
        raise ValueError(f"Batch LC QC failed; inspect {out/'analysis/qc_report.json'}")
    feedback = observations(results)
    tested = {r["pair_id"] for r in dosing if r["kind"] == "pair"}
    remaining = [c for c in candidates(inventory) if c["pair_id"] not in tested]
    ranking = score_candidates(config, inventory, remaining, evidence, feedback, out/"scoring")
    next_design = make_design(config, inventory, remaining, ranking, [], 2, history=dosing)
    # The next-dose CSV is useful before a final hardware review. Live protocols need validated hardware.
    write_csv(out/"next_design.csv", next_design)
    write_csv(out/"next_dosing.csv", dosing_rows(config, inventory, next_design))
    if all(config["validation"].values()):
        export(config, inventory, next_design, out/"protocols", live=True)
        hardware = "Live protocols exported for local import"
    else:
        hardware = "CSV generated; hardware validation fields must be completed before live export"
    write_json(out/"complete.json", {"hardware_status": hardware, "next_sample_ids": [r["sample_id"] for r in next_design],
                                   "output_sha256": {name: digest(out/name) for name in ("next_design.csv", "next_dosing.csv")}})
    return out


def watch(config, inventory, evidence, inbox, dosing, calibration, output, once=False):
    inbox = Path(inbox)
    inbox.mkdir(parents=True, exist_ok=True)
    state_path = Path(output)/"watcher_state.json"
    state = read_json(state_path) if state_path.exists() else {}
    print("Watching local LC inbox. Publish peaks.csv and peaks.ready.json only after complete export.", flush=True)
    while True:
        for ready in sorted(inbox.glob("*.ready.json")):
            peaks = ready.with_name(ready.name.replace(".ready.json", ".csv"))
            if not peaks.exists():
                continue
            # Include all inputs so a repaired export/calibration/config can be reconsidered.
            key = object_digest({"ready": digest(ready), "peaks": digest(peaks), "dosing": digest(dosing),
                                 "calibration": digest(calibration), "config": config, "inventory": inventory, "evidence": evidence})
            if key in state:
                continue
            try:
                out = iterate(config, inventory, evidence, dosing, peaks, ready, calibration, output)
                state[key] = {"status": "complete", "output": str(out)}
                print(f"Generated next batch: {out}", flush=True)
            except Exception as error:
                # A failed event is recorded once. No endless paid API retry loop.
                state[key] = {"status": "failed", "error": str(error)}
                print(f"Event stopped: {error}", flush=True)
            write_json(state_path, state)
        if once:
            return state
        time.sleep(3)
