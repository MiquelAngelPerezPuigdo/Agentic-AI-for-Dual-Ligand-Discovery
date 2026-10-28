#!/usr/bin/env python3
"""Interactive local guide for the HTE campaign. Never connects to the robot."""
from __future__ import annotations

import copy
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hte.io import digest, finite, read_csv, read_json, write_json
from hte.planning import required_validations
from hte.analytics import validate_analytics_settings


CHECKS = {
    "chemistry_confirmed": "Reaction chemistry and reagent identities confirmed",
    "plate_adapter_seal_validated": "Reaction block, caps, mounting and seal confirmed",
    "solvent_pipetting_validated": "Solvents, tips, source recovery and delivery checked",
    "heating_validated": "Reaction heating, temperatures and cooling checked",
    "lc_plate_workflow_validated": "LC plate, shaker, seals and autosampler checked",
    "lc_calibration_validated": "Real LC calibration and chromatograms reviewed",
    "local_app_simulation_passed": "Generated protocols simulated in the local Opentrons App",
    "injection_cycle_validated": "Actual LC injection-to-injection cycle confirmed",
    "simultaneous_heating_capacity_validated": "Concurrent heating and preparation setup checked",
    "robot_stock_preparation_validated": "Stock reservoirs, tubes, mixing and solvent compatibility checked",
    "noncontact_tip_reuse_validated": "Noncontact tip reuse checked",
    "pre_reaction_internal_standard_validated": "Naphthalene stability in the reaction checked",
    "staged_lc_timing_confirmed": "Staged LC timing checked",
}


class Guide:
    def __init__(self, root=ROOT, ask=input, say=print):
        self.root = Path(root).resolve()
        self.ask, self.say = ask, say
        self.config = self.root / "local_data/campaign.json"

    def path(self, relative):
        return self.root / relative

    def setup(self):
        local = self.path("local_data")
        local.mkdir(parents=True, exist_ok=True)
        for source, dest in (("hte_inputs/campaign.json", "local_data/campaign.json"),
                             ("hte_inputs/calibration_template.csv", "local_data/calibration-plan.csv")):
            target = self.path(dest)
            if not target.exists():
                # Exclusive creation: never replace existing settings or records.
                with self.path(source).open("rb") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                self.say("Created", dest)
        key = self.path("anthropic.key")
        if not key.exists():
            # Create an empty template without reading or displaying credentials.
            fd = os.open(key, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with self.path("anthropic.key.example").open("rb") as src, os.fdopen(fd, "wb") as dst:
                shutil.copyfileobj(src, dst)
            self.say("Created anthropic.key. Replace its placeholder locally before step 8.")

    def status(self):
        config = read_json(self.config)
        self.say("\nCAMPAIGN: 48 pairs in R1; 22 pairs + one reference in R2.")
        self.say("LC method:", config["analytics"].get("method_id") or "not set")
        self.say("Quantitative UV channel:", config["analytics"].get("channel") or "not set")
        self.say("LC cycle (minutes):", config["timing"]["injection_cycle_minutes"])
        self.say("Axygen bulk residual (µL):", config["automation"]["bulk_dead_ul"], "-- check on the actual reservoir")
        missing = [name for name in required_validations(config) if config["validation"].get(name) is not True]
        self.say("Local checks still to confirm:", len(missing))
        for name in missing:
            self.say("  -", CHECKS.get(name, name))
        self.say("Calibration:", "present" if self.path("local_data/calibration.csv").is_file() else "not yet available")
        self.say("Claude key: use anthropic.key (or ANTHROPIC_API_KEY); confirm it is filled before step 8.")
        self.say("Bench sheet: docs/HTE-staff-checklist.pdf | Weighing map: docs/weighing-list.md")

    def run(self, *args):
        sys.stdout.flush()
        result = subprocess.run([sys.executable, *map(str, args)], cwd=self.root, check=False)
        if result.returncode:
            self.say("Stopped. Read the message above; nothing was started on the robot.")
            return False
        return True

    def cli(self, *args):
        return self.run("-m", "hte.cli", "--config", "local_data/campaign.json", *args)

    def fresh(self, relative):
        if self.path(relative).exists():
            self.say("Already exists:", relative, "-- preserved. Review it before making a replacement.")
            return False
        return True

    def settings(self):
        if self.path("output/r1-decision").exists() and not self.decisions():
            self.say("R2 decision has started. Settings are locked here to protect its resumable input record.")
            return
        if self.decisions():
            self.say("The R2 decision is complete; changes here apply only to subsequent protocol export.")
        original = read_json(self.config)
        config = copy.deepcopy(original)
        analytics = config["analytics"]
        self.say("Enter real lab settings only. Press Enter to keep the existing value.")
        method = self.ask(f"LC method ID [{analytics.get('method_id') or 'unset'}]: ").strip()
        channel = self.ask(f"UV channel 1-4 or UV_VIS_1..4 [{analytics.get('channel') or 'unset'}]: ").strip().upper()
        if method:
            analytics["method_id"] = method
        if channel:
            channel = "UV_VIS_" + channel if channel in ("1", "2", "3", "4") else channel
            if channel not in {f"UV_VIS_{i}" for i in range(1, 5)}:
                raise ValueError("Choose UV channel 1, 2, 3 or 4")
            analytics["channel"] = channel
        sheet = self.ask(f"XLSX worksheet name, if used [{analytics.get('export_sheet') or 'unset'}]: ").strip()
        if sheet:
            analytics["export_sheet"] = sheet
        cycle = self.ask(f"Measured full LC cycle in minutes [{config['timing']['injection_cycle_minutes']}]: ").strip()
        if cycle:
            config["timing"]["injection_cycle_minutes"] = finite(cycle, "LC cycle", 0.000001)
        residual = self.ask(f"Measured conservative Axygen residual in µL [{config['automation']['bulk_dead_ul']}]: ").strip()
        if residual:
            config["automation"]["bulk_dead_ul"] = finite(residual, "Axygen bulk residual", 100, 2000)
        if (config["automation"]["bulk_dead_ul"] != original["automation"]["bulk_dead_ul"]
                and self.path("local_data/stock-prep/preparation_manifest.json").exists()):
            raise ValueError("Stock preparation is already recorded. Preserve it and consult the operator before changing its source residual")
        if self.ask("Enter measured LC retention times, windows and LOQs now? [y/N]: ").strip().lower() == "y":
            references = {}
            for key, label in (("substrate", "starting material"), ("product", "product"), ("internal_standard", "naphthalene")):
                rt = finite(self.ask(f"{label} retention time (minutes): "), label + " RT", 0)
                window = finite(self.ask(f"{label} matching half-window (minutes): "), label + " window", 0.000001)
                references[key] = {"retention_time_min": rt, "window_min": window}
            loq = {key: finite(self.ask(f"{label} quantification limit (µM): "), label + " LOQ", 0.000001)
                   for key, label in (("substrate", "starting material"), ("product", "product"))}
            analytics.update(references=references, quantification_limit_uM=loq)
            validate_analytics_settings(config)
        if analytics != original["analytics"] and self.path("local_data/calibration.csv").exists():
            raise ValueError("LC settings cannot be changed here after calibration exists; preserve the records and consult the analytical operator")
        if self.ask("Review unconfirmed physical checks now? [y/N]: ").strip().lower() == "y":
            self.say("Only answer yes for work actually checked by the lab. Enter leaves a check pending.")
            for key in required_validations(config):
                if config["validation"].get(key) is True:
                    continue
                if key == "lc_calibration_validated" and not self.path("local_data/calibration.csv").is_file():
                    self.say("  Calibration check remains pending until calibration.csv has been created.")
                    continue
                if self.ask("Confirmed: " + CHECKS.get(key, key) + "? [y/N]: ").strip().lower() == "y":
                    config["validation"][key] = True
        if config != original:
            write_json(self.config, config)
            self.say("Saved local_data/campaign.json.")
        else:
            self.say("No settings changed.")

    def prepare(self, live=False):
        out = "local_data/stock-prep" if live else "output/prep-preview"
        if self.fresh(out) and self.cli("prepare-stocks", "--output", out, *(["--live"] if live else [])):
            self.say("Loading maps:", out + "/bulk_carriers.csv and raw_reagents_to_load.csv")
            self.say("Protocol:", out + "/prepare_stocks.py", "(import and start locally in the Opentrons App)")
        if not live and self.fresh("output/r1-preview"):
            if self.cli("export", "--design", "campaigns/hackathon2026/round1_design.csv", "--output", "output/r1-preview"):
                self.say("R1 previews: output/r1-preview/dose_and_react.py and workup.py")
        if not live:
            self.say("Previews cannot run on hardware. Simulate them and complete the local checks first.")

    def r1(self, stage):
        out = "output/r1-dose" if stage == "dose_and_react" else "output/r1-workup"
        if not self.fresh(out):
            return
        if self.cli("export", "--design", "campaigns/hackathon2026/round1_design.csv",
                    "--output", out, "--live", "--stage", stage):
            self.say("Protocol:", out + "/" + stage + ".py")
            if stage == "dose_and_react":
                self.say("Use 48 EMPTY reaction vials. Calibration injection map:", out + "/calibration_injection_map.csv")
            else:
                self.say("Reaction injection map:", out + "/lc_batch01_injections.csv")

    def input_file(self, label, default=None, optional=False):
        hint = f" [{default}]" if default else ""
        raw = self.ask(label + hint + ": ").strip().strip("\"'")
        if not raw:
            raw = default or ""
        if not raw and optional:
            return None
        path = Path(raw).expanduser()
        path = path if path.is_absolute() else self.root / path
        if not path.is_file():
            raise ValueError(f"File not found: {path}")
        return str(path)

    def calibration(self):
        if not self.fresh("local_data/calibration.csv"):
            return
        self.say("Copy and complete the calibration map from output/r1-dose/calibration_injection_map.csv.")
        export = self.input_file("Completed calibration LC export", "local_data/calibration-vendor.csv")
        mapping = self.input_file("Completed calibration injection map", "local_data/calibration-map.csv")
        review = self.input_file("Reviewed blank-absence CSV, if needed (Enter to skip)", optional=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        folder = self.path("output/guide-calibration-" + stamp)
        folder.mkdir(parents=True)
        peaks = folder / "peaks.csv"
        if not self.cli("normalize", export, "--injections", mapping, "--output", peaks):
            return
        args = ["calibration-from-peaks", "--peaks", peaks, "--plan", "local_data/calibration-plan.csv", "--output", "local_data/calibration.csv"]
        if review:
            args += ["--reviewed-absences", review]
        if self.cli(*args):
            self.say("Calibration saved to local_data/calibration.csv. Review actual chromatograms, then confirm the LC calibration check in option 2.")

    def input_pairs(self, round_number):
        self.say("For each completed LC export, give its own reviewed injection map.")
        exports, mappings = [], []
        while True:
            exports.append(self.input_file(f"Round {round_number} LC export"))
            mappings.append(self.input_file("Matching injection map"))
            if self.ask("Another LC export for this round? [y/N]: ").strip().lower() != "y":
                return exports, mappings

    def decisions(self):
        base = self.path("output/r1-decision/decision")
        return sorted(p.parent for p in base.glob("iteration-*/complete.json") if (p.parent / "next_design.csv").is_file()) if base.exists() else []

    def decision(self):
        found = self.decisions()
        if not found:
            raise ValueError("No completed R2 decision found; finish option 7 first")
        if len(found) != 1:
            raise ValueError("More than one completed R2 decision exists; use the expert instructions to choose the correct one")
        decision = found[0]
        record = read_json(decision / "complete.json")
        for name, expected in record["output_sha256"].items():
            path = (decision / name).resolve()
            if not path.is_relative_to(decision.resolve()) or not path.is_file() or digest(path) != expected:
                raise ValueError("Completed R2 decision file changed or disappeared: " + name)
        return decision

    def next_round(self):
        if not self.path("output/r1-dose/dosing.csv").is_file():
            raise ValueError("R1 dosing table missing: generate R1 dosing first")
        if not self.path("local_data/calibration.csv").is_file():
            raise ValueError("Calibration missing: complete option 5 first")
        self.say("This step processes all 48 R1 results and may make paid Claude calls. Retrying uses the same output.")
        exports, mappings = self.input_pairs(1)
        if self.run("scripts/hte-lc-results.py", "next", "--dosing", "output/r1-dose/dosing.csv",
                    "--exports", *exports, "--injections", *mappings, "--output", "output/r1-decision"):
            self.say("Next: use the printed R2 files. If live export was blocked, resolve the reason and choose option 8.")

    def r2_protocols(self):
        decision = self.decision()
        existing = decision / "protocols/dose_and_react.py"
        if existing.exists():
            self.say("R2 protocols already exist:", existing.parent)
            self.say("Run refill_stocks.py first, then dose_and_react.py; run workup.py after reaction/cooling.")
            self.say("Review the LC sequence and injection maps in that same folder.")
            return
        if not self.fresh("output/r2-live"):
            return
        if self.cli("export", "--design", decision / "next_design.csv", "--history", "output/r1-dose/dosing.csv", "--live", "--output", "output/r2-live"):
            self.say("R2: output/r2-live/refill_stocks.py, then dose_and_react.py, then workup.py after cooling.")
            self.say("Review output/r2-live/lc_sequence.csv and lc_batch01_injections.csv for the actual LC sequence.")

    def final(self):
        decision = self.decision()
        if not self.fresh("output/r2-final"):
            return
        dosing = decision / "next_dosing.csv"
        if not dosing.is_file():
            raise ValueError("R2 dosing CSV not found; generate R2 protocols first")
        for exported in (self.path("output/r2-live/dosing.csv"), decision / "protocols/dosing.csv"):
            if exported.is_file() and read_csv(exported) != read_csv(dosing):
                raise ValueError("R2 live dosing table differs from the completed decision; inspect the run before analysis")
        exports, mappings = self.input_pairs(2)
        if self.run("scripts/hte-lc-results.py", "final", "--dosing", dosing, "--exports", *exports,
                    "--injections", *mappings, "--output", "output/r2-final"):
            self.say("Final results: output/r2-final/analysis/results.csv")

    def practice(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        out = "output/guide-practice-" + stamp
        self.say("Synthetic rehearsal: no paid calls and no robot execution.")
        if self.run("-m", "hte.cli", "rehearse-loop", "--output", out):
            self.say("Practice report:", out + "/rehearsal_report.json")

    def menu(self):
        self.setup()
        actions = {"1": self.status, "2": self.settings, "3": self.prepare, "4": lambda: self.prepare(True),
                   "5": lambda: self.r1("dose_and_react"), "6": self.calibration,
                   "7": lambda: self.r1("workup"), "8": self.next_round, "9": self.r2_protocols,
                   "10": self.final, "11": lambda: self.run("scripts/hte-return-package.py"), "12": self.practice}
        self.say("\nHTE CAMPAIGN GUIDE — local workstation only")
        self.status()
        while True:
            self.say("\n1 Status   2 LC settings/checks   3 Stock preview   4 Live stock protocol")
            self.say("5 R1 dosing   6 Calibration   7 R1 workup   8 R1 results / choose R2")
            self.say("9 R2 protocols   10 Final results   11 Return package   12 Practice   0 Exit")
            choice = self.ask("Choose a step: ").strip()
            if choice in ("0", "q", "quit"):
                return
            try:
                if choice not in actions:
                    self.say("Choose one of the listed numbers.")
                    continue
                actions[choice]()
            except (ValueError, KeyError, FileNotFoundError, OSError) as exc:
                self.say("Stopped:", exc)
                self.say("No robot was started. See docs/HTE-START-HERE.md for the matching step.")


if __name__ == "__main__":
    try:
        Guide().menu()
    except (KeyboardInterrupt, EOFError):
        print("\nGuide closed. Saved files remain in place.")
