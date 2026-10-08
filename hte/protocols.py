from __future__ import annotations

from pathlib import Path

from .io import atomic_text, digest, write_csv, write_json
from .planning import dosing_rows, stock_plan, tip_budget, transfer_operations, validate_config


RUNTIME = '''
import time
from opentrons import protocol_api

metadata = {"protocolName": "Dual-ligand HTE",
            "author": "HTE campaign generator", "description": "Local operation. Load source volumes from deck_loads.csv."}
requirements = {"robotType": "OT-2", "apiLevel": "2.18"}

def run(protocol: protocol_api.ProtocolContext):
    if DEMO and not protocol.is_simulating():
        raise RuntimeError("DEMONSTRATION ONLY: bench inputs have not been finalized")
    hs = protocol.load_module("heaterShakerModuleV1", 10)
    adapter = hs.load_adapter(CONFIG["robot"]["heater_adapter"])
    plate = (protocol.load_labware_from_definition(DEFINITIONS["reaction"], 3, "Glass vial reaction block")
             if "reaction" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["reaction_labware"], 3, "Reaction plate"))
    has_predose = any(op["stage"] == "round2_predose" for op in OPERATIONS)
    if STAGE == "dose_and_react" and has_predose:
        lc = (protocol.load_labware_from_definition(DEFINITIONS["reaction"], 6, "Round-two substrate block")
              if "reaction" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["reaction_labware"], 6, "Round-two substrate block"))
    else:
        lc = (protocol.load_labware_from_definition(DEFINITIONS["lc"], 6, "LC dilution plate")
              if "lc" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["lc_labware"], 6, "LC dilution plate"))
    racks = {slot: protocol.load_labware("opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", slot)
             for slot in [1, 4]}
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tips300 = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in [8, 9]]
    single = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=tips300)
    pipettes = {"p20": single, "p300": multi}
    labware = {1: racks[1], 4: racks[4], 2: reservoir, 3: plate, 6: lc}
    p = CONFIG["pipetting"]
    for pipette in [single, multi]:
        pipette.flow_rate.aspirate = p["p20_aspirate_ul_s"] if pipette is single else p["p300_aspirate_ul_s"]
        pipette.flow_rate.dispense = p["p20_dispense_ul_s"] if pipette is single else p["p300_dispense_ul_s"]

    def transfer(op):
        pipette = pipettes[op["pipette"]]
        fresh = not pipette.has_tip
        if fresh:
            try:
                pipette.pick_up_tip()
            except protocol_api.labware.OutOfTipsError:
                protocol.pause("Replace ALL empty tip racks for " + op["pipette"] + " in the same slots, then resume.")
                pipette.reset_tipracks()
                pipette.pick_up_tip()
        source = labware[op["source_slot"]][op["source_well"]]
        target = labware[op["destination_slot"]][op["destination_wells"][0]]
        protocol.comment(op["reagent"] + ": " + str(op["volume_ul_per_channel"]) + " uL per channel into " + ",".join(op["destination_wells"]))
        if fresh and op["source_slot"] != 3:
            for _ in range(p["prewet_cycles"]):
                pipette.aspirate(op["aspirated_ul_per_channel"], source.bottom(p["aspirate_height_mm"]))
                pipette.dispense(op["aspirated_ul_per_channel"], source.bottom(p["aspirate_height_mm"]))
        pipette.aspirate(op["aspirated_ul_per_channel"], source.bottom(p["aspirate_height_mm"]))
        protocol.delay(seconds=p["post_aspirate_seconds"])
        pipette.air_gap(p["air_gap_ul"])
        pipette.dispense(op["volume_ul_per_channel"] + p["air_gap_ul"],
                         target.top(p["dispense_above_top_mm"]))
        protocol.delay(seconds=p["post_dispense_seconds"])
        # Retained reverse-pipetting surplus is discarded. No touching, mixing, or return to source.
        if not op["retain_tip_for_next"]:
            pipette.drop_tip()

    def transfer_stage(stage):
        for op in OPERATIONS:
            if op["stage"] == stage:
                transfer(op)

    def onto_heater():
        hs.open_labware_latch()
        protocol.move_labware(plate, adapter, use_gripper=False)
        hs.close_labware_latch()

    def off_heater():
        hs.deactivate_shaker()
        hs.deactivate_heater()
        hs.open_labware_latch()
        protocol.move_labware(plate, 3, use_gripper=False)

    protocol.pause("Verify exact plate definitions, offsets, source volumes in deck_loads.csv, and fresh tips. Slots 7 and 11 must be empty. Remove source-tube caps only for dosing. Resume locally.")
    if STAGE == "dose_and_react":
        if any(op["stage"] == "substrate" for op in OPERATIONS):
            transfer_stage("substrate")
            protocol.pause("Cover unused volatile stock sources during dry-down using HTE-validated covers. Substrate/DCM A1 will be needed again for round-two predosing. Covers must be removed before any later aspiration. Resume to evaporate the first reaction block.")
            onto_heater()
            hs.set_and_wait_for_temperature(CONFIG["evaporation"]["temperature_C"])
            hs.set_and_wait_for_shake_speed(CONFIG["evaporation"]["rpm"])
            protocol.delay(minutes=CONFIG["evaporation"]["minutes"])
            hs.deactivate_shaker()
            hs.deactivate_heater()
            protocol.pause("HTE: verify DCM dry-down endpoint under the approved ventilation SOP. Wait for safe handling temperature before moving. Uncover ligand, toluene and Pd sources for assembly; preserve unused volatile sources under validated covers. Resume only when dry, cooled and required sources accessible. The timer does not prove dryness.")
            off_heater()
        else:
            protocol.pause("Round two: use the ten substrate wells predosed by round one. Verify sample mapping, 5 umol substrate per well, and complete ambient DCM evaporation before adding catalysts. Do not add substrate again.")
        transfer_stage("assembly")
        protocol.pause("Seal every reaction well using the validated toluene-compatible 95 C seal. Check seal and clamp before resuming. Retain source stocks capped. Prepare assay standards while reactions run.")
        onto_heater()
        try:
            hs.set_and_wait_for_temperature(CONFIG["chemistry"]["temperature_C"])
            hs.set_and_wait_for_shake_speed(CONFIG["chemistry"]["rpm"])
            if CONFIG["chemistry"].get("thermal_equilibration_minutes", 0):
                protocol.delay(minutes=CONFIG["chemistry"]["thermal_equilibration_minutes"])
            hold_start = time.monotonic()
            if has_predose:
                protocol.pause("Before round-two substrate predosing: confirm A1 substrate stock concentration/load remains valid and remove every cover obstructing reservoir aspiration. Other stocks can remain capped. Resume promptly; this pause is part of the reaction hold.")
                transfer_stage("round2_predose")
                protocol.pause("Round-two substrate dosing complete in slot 6. Cap/remove unused stock sources. Remove the second block for ambient DCM evaporation under the HTE ventilated setup; no second heater step. Resume promptly. Run calibration standards on LC during this first reaction hold.")
            elapsed = 0 if protocol.is_simulating() else (time.monotonic()-hold_start)/60
            if elapsed >= CONFIG["chemistry"]["reaction_minutes"]:
                raise RuntimeError("Reaction hold exceeded during predosing/pause. Stop and record the actual hold time.")
            protocol.delay(minutes=CONFIG["chemistry"]["reaction_minutes"]-elapsed)
        finally:
            hs.deactivate_shaker()
            hs.deactivate_heater()
        protocol.pause("Reaction hold complete. At the next manual-move prompt, use the HTE-validated thermal handling SOP to move the sealed block off the heater to slot 3 for cooling. If that SOP requires a cool module, wait for white status first. Keep sealed until cooled to the validated opening temperature.")
        off_heater()
        protocol.comment("Start workup protocol with the cooled reaction plate in slot 3. Preserve all sample IDs and well positions.")
    else:
        protocol.pause("Reaction plate must be cooled and in slot 3. Open seal under HTE SOP. Confirm homogeneous extraction method and workup reagent, including the approved internal standard when used.")
        transfer_stage("workup")
        onto_heater()
        hs.set_and_wait_for_shake_speed(CONFIG["liquids"]["mix_rpm"])
        protocol.delay(minutes=2)
        off_heater()
        protocol.pause("Inspect extraction for phase separation, precipitates and recovery. Do not resume sampling if the validated homogeneous matrix is not achieved.")
        transfer_stage("dilution")
        transfer_stage("sampling")
        protocol.pause("Seal LC plate and shake 2 minutes with the HTE-validated LC plate/adapter method. Submit only after mixing and transfer to the autosampler. Use lc_sequence.csv to retain well/sample mapping.")
'''


def export(config, inventory, design, output, live=False):
    validate_config(config, live=live)
    definitions = {}
    from .io import read_json
    for kind in ("reaction", "lc"):
        definition = config["robot"].get(kind+"_definition_path")
        if definition:
            definitions[kind] = read_json(definition)
        elif not config["robot"].get(kind+"_labware"):
            raise ValueError(f"Supply the exact {kind} library name or custom definition JSON")
    if not config["robot"].get("heater_adapter"):
        raise ValueError("Supply the exact heater adapter before exporting a simulation")
    rows = dosing_rows(config, inventory, design)
    ops = transfer_operations(config, inventory, rows)
    stocks = stock_plan(config, inventory, ops, reserve_round2=int(rows[0]["round"]) == 1)
    if any(not r["capacity_ok"] for r in stocks):
        raise ValueError("Deck source capacity exceeded: " + ", ".join(r["reagent"] for r in stocks if not r["capacity_ok"]))
    if live:
        used = {r["ligand_a"] for r in rows} | {r["ligand_b"] for r in rows}
        bad = [key for key in used if key and inventory[key]["identity_confirmed"] != "true"]
        if bad:
            raise ValueError("Ligand identities unresolved: " + ", ".join(bad))
    output = Path(output)
    if (output/"export_manifest.json").exists():
        raise ValueError("Protocol export already exists; use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "dosing.csv", rows)
    write_csv(output / "stock_preparation.csv", stocks)
    # Different source loads for dose vs workup. Common reservoir stock bottles stay off deck.
    deck = []
    for stage, members in [("dose_and_react", {"substrate", "assembly", "round2_predose"}), ("workup", {"workup", "dilution"})]:
        from collections import defaultdict
        use = defaultdict(float)
        for op in ops:
            if op["stage"] in members:
                use[op["reagent"]] += op["aspirated_ul_per_channel"] * op["channels"]
        for r in stocks:
            if r["reagent"] in use:
                deck.append({"protocol": stage, "reagent": r["reagent"], "source_slot": r["source_slot"],
                             "source_well": r["source_well"], "load_ul": math_ceil10(use[r["reagent"]] + r["dead_ul"]),
                             "stock_mM": r["stock_mM"], "solvent": r["solvent"]})
    write_csv(output / "deck_loads.csv", deck)
    write_json(output / "operations.json", ops)
    write_json(output / "tip_budget.json", tip_budget(ops))
    write_csv(output / "lc_sequence.csv", [{"sample_id": r["sample_id"], "well": r["well"], "round": r["round"]} for r in rows])
    if any(op["stage"] == "round2_predose" for op in ops):
        from .io import wells
        n0 = config["chemistry"]["substrate_molarity_M"]*config["chemistry"]["reaction_volume_ul"]
        write_csv(output/"round2_predose.csv", [{"round": 2, "sample_id": f"R2-{i:03d}", "well": well,
                  "substrate_umol": n0, "sm_DCM_ul": n0/config["liquids"]["substrate_stock_mM"]*1000,
                  "evaporation": "ambient during round-one hold; verify dryness before catalysts"}
                  for i, well in enumerate(wells()[:config["design"]["round2_total"]], 1)])
    for stage in ("dose_and_react", "workup"):
        prefix = "# Generated, self-contained. Keep this file with its dosing and deck-load CSVs.\n"
        prefix += f"STAGE = {stage!r}\nDEMO = {not live!r}\nCONFIG = {config!r}\nOPERATIONS = {ops!r}\nDEFINITIONS = {definitions!r}\n"
        protocol_name = f"Dual-ligand HTE R{rows[0]['round']} {stage}"
        runtime = RUNTIME.replace('"protocolName": "Dual-ligand HTE"', '"protocolName": '+repr(protocol_name))
        atomic_text(output / f"{stage}.py", prefix + runtime)
    write_json(output / "export_manifest.json", {
        "live": live, "sample_ids": [r["sample_id"] for r in rows],
        "files": {name: digest(output/name) for name in ["dosing.csv", "deck_loads.csv", "dose_and_react.py", "workup.py"]}})
    return rows


def math_ceil10(value):
    import math
    return math.ceil(value/10)*10
