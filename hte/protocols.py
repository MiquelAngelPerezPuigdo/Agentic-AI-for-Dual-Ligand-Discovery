from __future__ import annotations

from pathlib import Path

from .io import atomic_text, digest, new_output, object_digest, write_csv, write_json
from .planning import dosing_rows, stock_plan, tip_budget, transfer_operations, validate_config, validate_dosing


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
    single_key = "p20" if CONFIG["robot"]["single"] == "p20_single_gen2" else "p300_single"
    single_tiprack = "opentrons_96_tiprack_20ul" if single_key == "p20" else "opentrons_96_tiprack_300ul"
    tips_single = protocol.load_labware(single_tiprack, 5)
    tips300 = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in [8, 9]]
    single = protocol.load_instrument(CONFIG["robot"]["single"], "left", tip_racks=[tips_single])
    multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=tips300)
    pipettes = {single_key: single, "p300": multi}
    labware = {1: racks[1], 4: racks[4], 2: reservoir, 3: plate, 6: lc}
    p = CONFIG["pipetting"]
    for pipette in [single, multi]:
        pipette.flow_rate.aspirate = p[single_key+"_aspirate_ul_s"] if pipette is single else p["p300_aspirate_ul_s"]
        pipette.flow_rate.dispense = p[single_key+"_dispense_ul_s"] if pipette is single else p["p300_dispense_ul_s"]

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
        sampling = op["stage"] == "sampling"
        multiplier = p["sample_flow_rate_multiplier"] if sampling else 1
        pipette.flow_rate.aspirate = p[op["pipette"]+"_aspirate_ul_s"] * multiplier
        pipette.flow_rate.dispense = p[op["pipette"]+"_dispense_ul_s"] * multiplier
        source_height = p["sample_aspirate_height_mm"] if sampling else p["aspirate_height_mm"]
        source_location = source.bottom(source_height)
        aspirate_pause = p["sample_pause_seconds"] if sampling else p["post_aspirate_seconds"]
        dispense_pause = p["sample_pause_seconds"] if sampling else p["post_dispense_seconds"]
        protocol.comment(op["reagent"] + ": " + str(op["volume_ul_per_channel"]) + " uL per channel into " + ",".join(op["destination_wells"]))
        cycles = p["sample_prewet_cycles"] if sampling else p["prewet_cycles"]
        if fresh and (sampling or op["source_slot"] != 3):
            # Condition only in this source, before visiting a destination.
            # Sample channels return to their own reaction well; no air gaps or blowouts here.
            for _ in range(cycles):
                pipette.aspirate(op["aspirated_ul_per_channel"], source_location)
                if sampling:
                    protocol.delay(seconds=aspirate_pause)
                pipette.dispense(op["aspirated_ul_per_channel"], source_location)
                if sampling:
                    protocol.delay(seconds=dispense_pause)
        pipette.aspirate(op["aspirated_ul_per_channel"], source_location)
        protocol.delay(seconds=aspirate_pause)
        # API 2.18 has no air_gap(rate=...). Temporarily change its aspiration flow.
        liquid_aspirate_flow = pipette.flow_rate.aspirate
        if sampling:
            pipette.flow_rate.aspirate = liquid_aspirate_flow * p["sample_air_gap_rate"]
        pipette.air_gap(p["air_gap_ul"])
        pipette.flow_rate.aspirate = liquid_aspirate_flow
        pipette.dispense(op["volume_ul_per_channel"] + p["air_gap_ul"],
                         target.top(p["dispense_above_top_mm"]))
        protocol.delay(seconds=dispense_pause)
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
        else:
            protocol.pause("Round two: use the ten capped wells predosed by round one. Verify sample mapping and substrate/IS amounts in round2_predose.csv, retained toluene volume and approved storage interval. Uncap only for dosing. Do not evaporate or add substrate/IS again; the retained stock solvent counts in the final reaction volume.")
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
                protocol.pause("Round-two substrate dosing complete in slot 6. Cap every predosed vial promptly with the validated closure and label the mapping; retain the stock toluene and store under the approved conditions. Cap/remove unused sources. Do not evaporate. Resume promptly. Run calibration standards on LC during this first reaction hold.")
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
        is_instruction = ("Naphthalene was added with substrate; use IS-free workup and LC diluent."
                          if CONFIG["liquids"].get("naphthalene_addition_stage") == "substrate_stock"
                          else "Use the configured naphthalene concentration in the workup reagent.")
        protocol.pause("Reaction plate must be cooled and in slot 3. Open seal under HTE SOP. Confirm homogeneous extraction method and workup composition. " + is_instruction)
        transfer_stage("workup")
        onto_heater()
        hs.set_and_wait_for_shake_speed(CONFIG["liquids"]["mix_rpm"])
        protocol.delay(minutes=2)
        off_heater()
        protocol.pause("Inspect extraction: one homogeneous phase, no precipitate, no aspiration-path bubbles. Use the validated mixing-to-sampling interval; remix under the approved method if delayed. Do not sample one phase or assume pipette prewetting dissolves solids. Confirm sample-specific bottom clearance and immersion at the lowest remaining volume.")
        transfer_stage("dilution")
        transfer_stage("sampling")
        protocol.pause("Seal LC plate and shake 2 minutes with the HTE-validated LC plate/adapter method. Let bubbles clear for the validated interval; check seal, autosampler needle height and minimum remaining sample volume. Submit only after mixing. Use lc_sequence.csv for well/sample mapping. If a transfer was uncertain, quarantine its LC well and prepare a fresh documented dilution; never top it up or restart the whole workup.")
'''


def validate_definition_geometry(config, definitions, rows):
    """Reject incompatible well maps and multichannel pitch before making protocols."""
    from .io import finite, wells
    for kind, definition in definitions.items():
        needed = {row["well"] for row in rows}
        if kind == "reaction" and config["design"].get("round2_predosed"):
            needed.update(wells()[:config["design"]["round2_total"]])
        defined = definition.get("wells", {})
        if not needed.issubset(defined):
            raise ValueError(f"{kind} definition lacks campaign well addresses; 24-vial racks require a different protocol and heating plan")
        volume = (config["chemistry"]["reaction_volume_ul"]+config["liquids"]["workup_ul"]
                  if kind == "reaction" else config["liquids"]["aliquot_ul"]+config["liquids"]["diluent_ul"])
        for key in needed:
            if finite(defined[key]["totalLiquidVolume"], "well capacity", 0) < volume:
                raise ValueError(f"{kind} well {key} capacity is less than the planned liquid volume")
        for col in range(1, 13):
            column = [f"{r}{col}" for r in "ABCDEFGH"]
            if not set(column).issubset(needed):
                continue
            first = defined[column[0]]
            for i, key in enumerate(column[1:], 1):
                well = defined[key]
                if (abs(well["x"]-first["x"]) > 0.2 or abs(well["y"]-(first["y"]-9*i)) > 0.2
                        or abs(well["z"]-first["z"]) > 0.2):
                    raise ValueError(f"{kind} definition is incompatible with 9 mm eight-channel geometry")


def export(config, inventory, design, output, live=False, history=None, stage="all"):
    if stage not in ("all", "dose_and_react", "workup"):
        raise ValueError("Unknown export stage")
    # Calibration runs during R1. Only the first reaction may start before it.
    scope = "first_reaction" if stage == "dose_and_react" and design and str(design[0]["round"]) == "1" else "all"
    validate_config(config, live=live, live_scope=scope)
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
    validate_definition_geometry(config, definitions, rows)
    if int(rows[0]["round"]) == 2:
        if live and not history:
            raise ValueError("Live round-two export requires the first-round dosing history to exclude repeats and verify predoses")
        if history:
            from .design import validate_design
            validate_dosing(config, inventory, history)
            validate_design(config, inventory, design, history)
    ops = transfer_operations(config, inventory, rows)
    stocks = stock_plan(config, inventory, ops, reserve_round2=int(rows[0]["round"]) == 1)
    if any(not r["capacity_ok"] for r in stocks):
        raise ValueError("Deck source capacity exceeded: " + ", ".join(r["reagent"] for r in stocks if not r["capacity_ok"]))
    if live:
        used = {r["ligand_a"] for r in rows} | {r["ligand_b"] for r in rows}
        bad = [key for key in used if key and inventory[key]["identity_confirmed"] != "true"]
        if bad:
            raise ValueError("Ligand identities unresolved: " + ", ".join(bad))
    output = new_output(output)
    write_csv(output / "dosing.csv", rows)
    write_csv(output / "stock_preparation.csv", stocks)
    # Different source loads for dose vs workup. Common reservoir stock bottles stay off deck.
    deck = []
    for deck_stage, members in [("dose_and_react", {"substrate", "assembly", "round2_predose"}), ("workup", {"workup", "dilution"})]:
        from collections import defaultdict
        use = defaultdict(float)
        for op in ops:
            if op["stage"] in members:
                use[(op["reagent"],op["source_slot"],op["source_well"])] += op["aspirated_ul_per_channel"] * op["channels"]
        for r in stocks:
            address = (r["reagent"],r["source_slot"],r["source_well"])
            if address in use:
                deck.append({"protocol": deck_stage, "reagent": r["reagent"], "source_slot": r["source_slot"],
                             "source_well": r["source_well"], "load_ul": math_ceil10(use[address] + r["dead_ul"]),
                             "stock_mM": r["stock_mM"], "naphthalene_stock_mM": r["naphthalene_stock_mM"],
                             "solvent": r["solvent"]})
    write_csv(output / "deck_loads.csv", deck)
    write_json(output / "operations.json", ops)
    write_json(output / "tip_budget.json", tip_budget(ops))
    write_csv(output / "lc_sequence.csv", [{"sample_id": r["sample_id"], "well": r["well"], "round": r["round"]} for r in rows])
    if any(op["stage"] == "round2_predose" for op in ops):
        from .io import wells
        n0 = config["chemistry"]["substrate_molarity_M"]*config["chemistry"]["reaction_volume_ul"]
        write_csv(output/"round2_predose.csv", [{"round": 2, "sample_id": f"R2-{i:03d}", "well": well,
                  "substrate_umol": n0, "sm_stock_ul": n0/config["liquids"]["substrate_stock_mM"]*1000,
                  "naphthalene_predosed_umol": n0*config["liquids"].get("naphthalene_substrate_stock_mM", 0)/config["liquids"]["substrate_stock_mM"],
                  "storage": "Cap promptly; retain 25 uL stock toluene (or configured dose); no evaporation; verify retained volume before catalysts"}
                  for i, well in enumerate(wells()[:config["design"]["round2_total"]], 1)])
    stages = ("dose_and_react", "workup") if stage == "all" else (stage,)
    for protocol_stage in stages:
        prefix = "# Generated, self-contained. Keep this file with its dosing and deck-load CSVs.\n"
        prefix += f"STAGE = {protocol_stage!r}\nDEMO = {not live!r}\nCONFIG = {config!r}\nOPERATIONS = {ops!r}\nDEFINITIONS = {definitions!r}\n"
        protocol_name = f"Dual-ligand HTE R{rows[0]['round']} {protocol_stage}"
        runtime = RUNTIME.replace('"protocolName": "Dual-ligand HTE"', '"protocolName": '+repr(protocol_name))
        atomic_text(output / f"{protocol_stage}.py", prefix + runtime)
    write_json(output / "export_manifest.json", {
        "live": live, "released_stages": list(stages), "validation_scope": scope,
        "sample_ids": [r["sample_id"] for r in rows],
        "config_digest": object_digest(config), "inventory_digest": object_digest(inventory),
        "design_digest": object_digest(design), "history_digest": object_digest(history) if history else None,
        "files": {path.name: digest(path) for path in sorted(output.iterdir()) if path.is_file()}})
    return rows


def math_ceil10(value):
    import math
    return math.ceil(value/10)*10
