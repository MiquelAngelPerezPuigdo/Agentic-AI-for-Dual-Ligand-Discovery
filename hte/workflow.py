from __future__ import annotations

import time
from pathlib import Path

from .analytics import analyze, observations, read_completed_inputs
from .design import make_design, validate_round1_coverage
from .inventory import candidates
from .io import digest, file_lock, object_digest, read_json, write_csv, write_json
from .planning import dosing_rows, required_validations, validate_dosing
from .protocols import export
from .scoring import score_candidates


def iterate(config, inventory, evidence, dosing_path, peaks_path, ready_path, calibration_path, output):
    if config.get("demo"):
        raise ValueError("Use the offline demo command for synthetic data")
    tables, hashes = read_completed_inputs(config, dosing_path, peaks_path, ready_path, calibration_path)
    dosing = tables["dosing"]
    if {r["round"] for r in dosing} != {"1"} or len(dosing) != config["design"]["round1_total"]:
        raise ValueError("Iteration requires the entire configured first round")
    validate_round1_coverage(config, inventory, dosing)
    validate_dosing(config, inventory, dosing)
    if config["design"].get("round2_controls") is None:
        raise ValueError("Specify round-two controls, or [] for ten new pairs")
    inputs = {"config": object_digest(config), "inventory": object_digest(inventory), "evidence": object_digest(evidence),
              **hashes}
    out = Path(output)/("iteration-"+object_digest(inputs)[:16])
    out.mkdir(parents=True, exist_ok=True)
    with file_lock(out/".iteration.lock"):
        return _iterate_locked(config, inventory, evidence, dosing, tables, inputs, out)


def _iterate_locked(config, inventory, evidence, dosing, tables, inputs, out):
    if (out/"complete.json").exists():
        # Repeated watcher events return the existing audited batch, without API calls or overwrites.
        completed = read_json(out/"complete.json")
        for name, expected in completed["output_sha256"].items():
            if not (out/name).exists() or digest(out/name) != expected:
                raise ValueError("Completed iteration output changed or disappeared: "+name)
        return out
    write_json(out/"inputs.json", inputs)
    write_json(out/"source_tables.json", tables)
    results, report = analyze(config, dosing, tables["peaks"], tables["calibration"], out/"analysis")
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
    if all(config["validation"].get(key) is True for key in required_validations(config)):
        try:
            export(config, inventory, next_design, out/"protocols", live=True, history=dosing)
            hardware = "Live protocols exported for local import"
        except ValueError as error:
            # Keep useful, audited CSVs even if the stricter release gate stops
            # protocol export. The robot is never started by this workflow.
            hardware = "CSV generated; live protocol export stopped: "+str(error)
    else:
        hardware = "CSV generated; hardware validation fields must be completed before live export"
    write_json(out/"complete.json", {"hardware_status": hardware, "next_sample_ids": [r["sample_id"] for r in next_design],
                                   "output_sha256": {path.relative_to(out).as_posix(): digest(path)
                                                     for path in sorted(out.rglob("*"))
                                                     if path.is_file() and path.name != "complete.json"
                                                     and not path.name.endswith(".lock")}})
    return out


def watch(config, inventory, evidence, inbox, dosing, calibration, output, once=False):
    with file_lock(Path(output)/".watcher.lock"):
        return _watch_locked(config, inventory, evidence, inbox, dosing, calibration, output, once)


def _watch_locked(config, inventory, evidence, inbox, dosing, calibration, output, once):
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
