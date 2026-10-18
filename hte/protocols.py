from __future__ import annotations

from pathlib import Path

from .io import atomic_text, digest, new_output, object_digest, write_csv, write_json, wells
from .planning import (catalyst_mixing_timing, dosing_rows, pd_material_budget, stock_plan,
                       tip_budget, transfer_operations, validate_config, validate_dosing, workup_timing)


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
    lc = (protocol.load_labware_from_definition(DEFINITIONS["lc"], 6, "CALIBRATION" if STAGE=="dose_and_react" and ROUND==1 else "R"+str(ROUND)+"-LC01")
          if "lc" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["lc_labware"], 6, "R"+str(ROUND)+"-LC01"))
    racks = {slot: protocol.load_labware(CONFIG["robot"]["ligand_source_labware"], slot)
             for slot in [1, 4]}
    reservoir = (protocol.load_labware_from_definition(DEFINITIONS["reservoir"], 2, "Common liquid sources")
                 if "reservoir" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["reservoir_labware"], 2))
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
        if op["stage"] in ("workup", "dilution"):
            pipette.flow_rate.aspirate = p["workup_aspirate_ul_s"]
            pipette.flow_rate.dispense = p["workup_dispense_ul_s"]
        source_height = p["sample_aspirate_height_mm"] if sampling else p["aspirate_height_mm"]
        source_location = source.bottom(source_height)
        aspirate_pause = p["sample_pause_seconds"] if sampling else p["post_aspirate_seconds"]
        dispense_pause = p["sample_pause_seconds"] if sampling else p["post_dispense_seconds"]
        protocol.comment(op["reagent"] + ": " + str(op["volume_ul_per_channel"]) + " uL per channel into " + ",".join(op["destination_wells"]))
        mix_cycles = op.get("source_mix_cycles", 0)
        if mix_cycles:
            protocol.comment("MIX OWN CATALYST SOURCE: " + op["reagent"] + ", " + str(mix_cycles) + " cycles of " + str(op["source_mix_ul"]) + " uL, submerged at bottom clearance; no air gap/blowout.")
            for _ in range(mix_cycles):
                pipette.aspirate(op["source_mix_ul"], source_location)
                protocol.delay(seconds=p["post_aspirate_seconds"])
                pipette.dispense(op["source_mix_ul"], source_location)
                protocol.delay(seconds=p["post_dispense_seconds"])
        cycles = p["sample_prewet_cycles"] if sampling else p["prewet_cycles"]
        if mix_cycles and not sampling:
            cycles = max(0, cycles-mix_cycles)
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

    def transfer_stage(stage, batch=None):
        for op in OPERATIONS:
            if op["stage"] == stage and (batch is None or op.get("lc_batch")==batch):
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

    def load_lc_plate(label):
        return (protocol.load_labware_from_definition(DEFINITIONS["lc"], 6, label)
                if "lc" in DEFINITIONS else protocol.load_labware(CONFIG["robot"]["lc_labware"], 6, label))

    def wait_for_cool_module():
        # Module temperature does not establish the temperature inside the vials.
        hs.deactivate_heater()
        if not protocol.is_simulating():
            while hs.current_temperature is None or hs.current_temperature > CONFIG["liquids"]["lc_max_module_temperature_C"]:
                protocol.pause("Wait until the heater-shaker has cooled to at most " + str(CONFIG["liquids"]["lc_max_module_temperature_C"]) + " C before workup or LC mixing. Heater is OFF; then resume. Separately confirm the sealed reaction vials have cooled before opening.")

    def shake_and_release_lc(batch):
        # The reaction block stays in slot 3. No pipetting occurs on the module.
        # off_heater() already stopped shaking before opening the latch.
        wait_for_cool_module()
        protocol.pause("LC plate R"+str(ROUND)+"-LC"+str(batch).zfill(2)+" is complete. RECAP the sampled reaction vials. Leave the LC plate UNCOVERED for shaking. At the next manual move, take only this LC plate from slot 6 to the cooled flat adapter in slot 10; preserve A1 orientation. No manual sample pipetting or HPLC-vial transfers.")
        hs.open_labware_latch()
        protocol.move_labware(lc, adapter, use_gripper=False)
        hs.close_labware_latch()
        try:
            hs.set_and_wait_for_shake_speed(CONFIG["liquids"]["lc_mix_rpm"])
            protocol.delay(minutes=CONFIG["liquids"]["lc_mix_minutes"])
        finally:
            hs.deactivate_shaker()
            hs.deactivate_heater()
        hs.open_labware_latch()
        protocol.move_labware(lc, protocol_api.OFF_DECK, use_gripper=False)
        protocol.pause("LC plate R"+str(ROUND)+"-LC"+str(batch).zfill(2)+": move DIRECTLY from the shaker to the HPLC handoff. Apply the confirmed autosampler-compatible pierceable seal, check orientation/carrier and needle depth, and inject only the sample wells in lc_sequence.csv. Do not inject padding wells. Start this plate's sequence before resuming. Keep plate ID and actual injection mapping. No optimization until ALL first-round measurements finish.")

    protocol.pause("Verify exact plate definitions, offsets, source volumes in deck_loads.csv, and fresh tips. Slots 7 and 11 must be empty. Keep caps identified and clean. For workup, keep reaction vials CAPPED until the explicit cooled-opening pause. Resume locally.")
    if STAGE == "dose_and_react":
        protocol.pause("BEFORE DOSING: use the ROBOT-PREPARED working sources, at their exact CSV addresses. No hand aliquoting. Keep the 10 mg Pd scope reserve untouched. Open required source caps; let bubbles clear. Source racks stay off the heater-shaker. Pause for aggregates, persistent bubbles, blocked tips or air uptake.")
        if any(op["stage"] == "substrate" for op in OPERATIONS):
            protocol.pause("FIRST load the SAME reaction block with the 23 NEW, labeled R2 vials, UNCAPPED, following round2_predose.csv. The robot will predose SM/IS now, before the first reaction. No catalyst yet.")
            transfer_stage("round2_predose")
            protocol.pause("CAP the 23 robot-predosed R2 vials and store them labeled until R2. Replace them with 48 NEW EMPTY R1 vials in the SAME block. Remove all 48 caps before resuming. No hand pipetting; retain toluene in R2 vials.")
            protocol.pause("Confirm the 48 first-round reaction vials are empty and correctly loaded. REMOVE ALL reaction-vial screw caps and open the required sources before pipetting.")
            transfer_stage("substrate")
            protocol.comment("Combined stock supplies SM AND mesitylene in 25 uL retained toluene. No evaporation and no separate IS dose.")
        else:
            protocol.pause("Round two: CONFIRM the 48 first-round vials were archived after sampling and the 23 NEW, labeled predosed vials are fitted into the SAME block following round2_predose.csv. If this changeover was already completed during R1 LC, do not repeat it. Each NEW vial must contain 25 uL combined stock: 25 umol SM AND 2.5 umol mesitylene in retained toluene; NO catalyst yet. REMOVE ALL 23 reaction-vial screw caps and open required sources BEFORE resuming pipetting. Check orientation and any required dummy vials. No SM or IS redosing.")
        transfer_stage("internal_standard")
        transfer_stage("assembly")
        protocol.pause("TIGHTEN every occupied vial screw cap BY HAND before heating/shaking. Use HTEL's compatible septum screw caps and mounting procedure for 95 C. Check no vial remains open. Cap remaining source stocks. No stir bars. Resume for the module's heat/shake cycle.")
        onto_heater()
        hold_timer = None
        try:
            hs.set_and_wait_for_temperature(CONFIG["chemistry"]["temperature_C"])
            hs.set_and_wait_for_shake_speed(CONFIG["chemistry"]["rpm"])
            if CONFIG["chemistry"].get("thermal_equilibration_minutes", 0):
                protocol.delay(minutes=CONFIG["chemistry"]["thermal_equilibration_minutes"])
            hold_timer = ReactionHoldTimer(protocol, CONFIG["chemistry"]["reaction_minutes"]*60,
                CONFIG["chemistry"].get("max_hold_overrun_seconds", 60))
            protocol.comment("Start the independent operator reaction timer now. Python cannot stop heating while the App is paused. Respond to preparation prompts promptly; at the four-hour endpoint stop the run/module if a prompt remains blocked and record the deviation.")
            if HOLD_PLAN:
                execute_liquid_plan(protocol,HOLD_PLAN,{"working1":racks[1],"working4":racks[4],"reservoir":reservoir,"cal_plate":lc},single,multi,check_deadline=hold_timer.check)
            protocol.delay(seconds=hold_timer.remaining())
            hold_timer.finish()
        finally:
            hs.deactivate_shaker()
            hs.deactivate_heater()
            if hold_timer is not None: hold_timer.record("module_shutdown")
        protocol.pause("Reaction hold complete. At the next manual-move prompt, use HTEL's approved thermal handling procedure to move the sealed block off the heater to slot 3. Keep sealed until cooled to the approved opening temperature and record cooling time.")
        off_heater()
        protocol.comment("Start workup with the cooled block in slot 3. Keep reaction-vial and LC-well mappings distinct. Archive first-round vials after sampling before changing to round two.")
    else:
        wait_for_cool_module()
        protocol.pause("Separately CONFIRM the sealed reaction vials have cooled to HTEL's approved opening temperature in slot 3, then UNSCREW/REMOVE all occupied reaction-vial caps under HTEL SOP and open workup sources. Mesitylene is already in each reaction: workup and LC diluent contain NO added internal standard. Confirm the approved extraction composition before proceeding.")
        transfer_stage("workup")
        protocol.pause("SCREW every vial cap back on BY HAND before vigorous shaking. Check tightness and mounting. Do not shake open vials at high rpm.")
        onto_heater()
        try:
            hs.set_and_wait_for_shake_speed(CONFIG["liquids"]["mix_rpm"])
            protocol.delay(minutes=2)
        finally:
            hs.deactivate_shaker()
            hs.deactivate_heater()
        off_heater()
        protocol.pause("After vigorous shaking, keep ALL reaction vials screw-capped until their sampling batch. Let bubbles clear briefly. No stir bars are present.")
        protocol.pause("Sample promptly after vigorous mixing and bubble settling. If distinct layers, solids in the aspiration path or bubbles are obvious, pause for review; do not choose a layer or assume repeated aspiration dissolves solids. Keep the tip above the bottom and below the liquid surface.")
        batches=sorted({op["lc_batch"] for op in OPERATIONS if op["stage"]=="sampling"})
        for batch in batches:
            if batch != batches[0]:
                protocol.pause("Load a NEW empty LC autosampler plate in slot 6 for R"+str(ROUND)+"-LC"+str(batch).zfill(2)+". Keep the preceding plate at HPLC; do not reuse it. Use the exact wells in lc_sequence.csv, which retain their campaign column numbers.")
                lc = load_lc_plate("R"+str(ROUND)+"-LC"+str(batch).zfill(2))
                labware[6] = lc
            active=[op["source_well"] for op in OPERATIONS if op["stage"]=="sampling" and op["lc_batch"]==batch]
            active=list(dict.fromkeys(active))
            protocol.pause("Label the LC plate R"+str(ROUND)+"-LC"+str(batch).zfill(2)+". Sampling batch "+str(batch)+": let visible bubbles settle after the automated extract shake, then UNSCREW/REMOVE the caps ONLY from "+", ".join(active)+". Keep all other reaction vials capped. Confirm caps lie below the 45 mm labware clearance envelope. Resume only with these aspiration targets open.")
            transfer_stage("dilution",batch)
            transfer_stage("sampling",batch)
            shake_and_release_lc(batch)
        protocol.comment("All final LC plates prepared and shaken automatically. Retain reaction-vial archives and LC plates, and record actual plate/well identities and sequence start times.")
'''


def validate_definition_geometry(config, definitions, rows):
    """Reject incompatible well maps and multichannel pitch before making protocols."""
    from .io import finite, reaction_wells
    for kind, definition in definitions.items():
        if kind == "reservoir":
            from .planning import reservoir_source_pools
            needed = {w for pool in reservoir_source_pools(config).values() for w in pool}
            if not needed.issubset(definition["wells"]):
                raise ValueError("Reservoir definition lacks source channels")
            if any(definition["wells"][w]["totalLiquidVolume"] < config["stock_preparation"]["reservoir_max_fill_ul"] for w in needed):
                raise ValueError("Reservoir definition capacity is less than the configured fill limit")
            if "centerMultichannelOnWells" not in definition.get("parameters", {}).get("quirks", []):
                raise ValueError("Reservoir requires centerMultichannelOnWells for eight-channel diluent aspiration")
            for well in needed:
                geometry = definition["wells"][well]
                if geometry.get("shape") != "rectangular" or geometry.get("yDimension", 0) < 63:
                    raise ValueError("Reservoir channels must span all eight tips (at least 63 mm along Y)")
                if config["pipetting"]["aspirate_height_mm"] >= geometry["depth"]:
                    raise ValueError("Reservoir aspiration height is outside the source channel")
            continue
        needed = {row["lc_well"] if kind == "lc" else row["well"] for row in rows}
        if kind == "lc" and config["robot"].get("pad_lc_diluent_columns"):
            needed = {f"{r}{well[1:]}" for well in needed for r in "ABCDEFGH"}
        defined = definition.get("wells", {})
        if not needed.issubset(defined):
            raise ValueError(f"{kind} definition lacks campaign well addresses; supply the matching rack geometry")
        volume = (config["chemistry"]["reaction_volume_ul"]+config["liquids"]["workup_ul"]
                  if kind == "reaction" else config["liquids"]["aliquot_ul"]+config["liquids"]["diluent_ul"])
        for key in needed:
            if finite(defined[key]["totalLiquidVolume"], "well capacity", 0) < volume:
                raise ValueError(f"{kind} well {key} capacity is less than the planned liquid volume")
            if kind == "reaction" and config["pipetting"]["sample_aspirate_height_mm"] >= defined[key]["depth"]:
                raise ValueError("Reaction sampling height is outside the vial")
        if kind == "lc" and "centerMultichannelOnWells" in definition.get("parameters", {}).get("quirks", []):
            raise ValueError("LC plate must use individual well centers, not reservoir multichannel centering")
        for col in range(1, 13):
            if kind == "reaction" and not config["robot"]["reaction_multichannel"]:
                break
            column = [f"{r}{col}" for r in "ABCDEFGH"]
            if not set(column).issubset(needed):
                continue
            first = defined[column[0]]
            for i, key in enumerate(column[1:], 1):
                well = defined[key]
                if (abs(well["x"]-first["x"]) > 0.2 or abs(well["y"]-(first["y"]-9*i)) > 0.2
                        or abs(well["z"]-first["z"]) > 0.2):
                    raise ValueError(f"{kind} definition is incompatible with 9 mm eight-channel geometry")


def export(config, inventory, design, output, live=False, history=None, stage="all",preparation_path=None):
    if stage not in ("all", "dose_and_react", "workup"):
        raise ValueError("Unknown export stage")
    # Calibration runs during R1. Only the first reaction may start before it.
    scope = "first_reaction" if stage == "dose_and_react" and design and str(design[0]["round"]) == "1" else "all"
    validate_config(config, live=live, live_scope=scope)
    definitions = {}
    from .io import read_json
    for kind in ("reaction", "lc", "reservoir"):
        definition = config["robot"].get(kind+"_definition_path")
        if definition:
            definitions[kind] = read_json(definition)
        elif not config["robot"].get(kind+"_labware"):
            raise ValueError(f"Supply the exact {kind} library name or custom definition JSON")
    if not config["robot"].get("heater_adapter"):
        raise ValueError("Supply the exact heater adapter before exporting a simulation")
    rows = dosing_rows(config, inventory, design)
    source = (config["stock_preparation"]["substrate_source_slot"], config["stock_preparation"]["substrate_source_well"])
    if source in {(int(r["source_slot"]), r["source_well"]) for r in inventory.values()}:
        raise ValueError("Combined SM/IS source overlaps a ligand tube")
    if source[0] not in (1, 4) or source[1] not in {f"{r}{col}" for r in "ABCD" for col in range(1, 7)}:
        raise ValueError("Combined SM/IS source is absent from the source racks")
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
    from .preparation import (build_hold_preparation,build_refill,build_stock_preparation,
        definitions as prep_definitions,LIQUID_RUNTIME,load_preparation,refill_source,validate_source_reach)
    explicit_preparation=preparation_path
    preparation_path=preparation_path or config.get("automation",{}).get("preparation_manifest_path")
    if preparation_path and not Path(preparation_path).exists() and not live and not explicit_preparation:preparation_path=None
    prep=load_preparation(config,inventory,preparation_path,live=live) if preparation_path else None
    if prep and int(rows[0]["round"])==1:
        from .preparation import design_signature
        if prep["design_signature"]!=design_signature(design):raise ValueError("Stock preparation differs from this first-round design")
    if live and not prep:raise ValueError("Run robot stock preparation from actual weights and supply --preparation or automation.preparation_manifest_path")
    if prep is None and int(rows[0]["round"])==1:prep=build_stock_preparation(config,inventory,design)
    hold=build_hold_preparation(config,ops,int(rows[0]["round"]),prep)
    refill=build_refill(config,inventory,design,history,prep) if int(rows[0]["round"])==2 and history and prep else None
    if live:
        validate_source_reach(config,hold)
        if refill: validate_source_reach(config,refill)
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
    if int(rows[0]["round"])==1:
        from .analytical_stocks import preparation
        write_csv(output / "analytical_stock_preparation.csv", preparation(config))
    # Different source loads for dose vs robot-prepared workup fluids.
    deck = []
    for deck_stage, members in [("dose_and_react", {"substrate", "round2_predose", "internal_standard", "assembly"}), ("workup", {"workup", "dilution"})]:
        from collections import defaultdict
        use = defaultdict(float)
        for op in ops:
            if op["stage"] in members:
                use[(op["reagent"],op["source_slot"],op["source_well"])] += op["aspirated_ul_per_channel"] * op["channels"]
        for r in stocks:
            address = (r["reagent"],int(r["source_slot"]),r["source_well"])
            if address in use:
                deck.append({"protocol": deck_stage, "reagent": r["reagent"], "source_slot": r["source_slot"],
                             "source_well": r["source_well"], "load_ul": max(math_ceil10(use[address] + r["dead_ul"]),r["on_deck_ul"]) if deck_stage=="dose_and_react" else math_ceil10(use[address]+r["dead_ul"]),
                             "stock_mM": r["stock_mM"],
                             "solvent": r["solvent"]})
    write_csv(output / "deck_loads.csv", deck)
    write_json(output / "operations.json", ops)
    write_json(output/"hold_preparation_plan.json",hold)
    if preparation_path:write_json(output/"source_preparation_manifest.json",prep)
    if hold["pilot_recipes"]:
        write_csv(output/"pilot_preparation.csv",hold["pilot_recipes"])
        write_csv(output/"pilot_injection_map.csv",[dict(inj_no=i,sample_id=r["sample_id"],method_id=config["analytics"].get("method_id") or "",lc_plate_id=r["plate_id"],well=r["well"]) for i,r in enumerate(hold["pilot_recipes"],1)])
    if hold["calibration_recipes"]:
        write_csv(output/"calibration_preparation.csv",hold["calibration_recipes"])
        write_csv(output/"calibration_injection_map.csv",[
            dict(inj_no=i,sample_id=r["sample_id"],method_id=config["analytics"]["method_id"] or "",lc_plate_id="CALIBRATION",well=r["well"])
            for i,r in enumerate(hold["calibration_recipes"],1)])
    write_csv(output/"raw_reagents_to_load.csv",hold["raw_loads"])
    if refill:
        write_json(output/"refill_plan.json",refill)
        atomic_text(output/"refill_stocks.py",refill_source(config,refill,live))
    write_json(output / "pd_material_budget.json", pd_material_budget(config, ops, reserve_round2=int(rows[0]["round"]) == 1))
    write_json(output / "catalyst_mixing_timing.json", catalyst_mixing_timing(config, ops))
    write_json(output / "tip_budget.json", tip_budget(ops))
    write_json(output / "workup_timing.json", workup_timing(config, ops))
    sequence=[{"sample_id":r["sample_id"],"well":r["lc_well"],"reaction_well":r["well"],
               "lc_plate_id":f"R{r['round']}-LC{wells().index(r['lc_well'])//config['robot']['lc_batch_size']+1:02d}",
               "lc_batch":wells().index(r["lc_well"])//config["robot"]["lc_batch_size"]+1,"round":r["round"]} for r in rows]
    write_csv(output / "lc_sequence.csv",sequence)
    plate_rows=[]
    for batch in sorted({r["lc_batch"] for r in sequence}):
        members=[r for r in sequence if r["lc_batch"]==batch]
        plate_rows.append({"lc_plate_id":members[0]["lc_plate_id"],"lc_batch":batch,
                           "sample_count":len(members),"sample_wells":",".join(r["well"] for r in members),
                           "final_ul_per_sample":config["liquids"]["aliquot_ul"]+config["liquids"]["diluent_ul"],
                           "route":"slot 6 -> heater-shaker slot 10 -> HPLC (OFF_DECK)",
                           "uncovered_shake_rpm":config["liquids"]["lc_mix_rpm"],
                           "shake_minutes":config["liquids"]["lc_mix_minutes"],"heater":"OFF",
                           "seal":"After shaking, before HPLC: confirmed pierceable autosampler seal"})
        write_csv(output/f"lc_batch{batch:02d}_injections.csv",[
            {"inj_no":i,"sample_id":r["sample_id"],"method_id":config["analytics"]["method_id"] or "",
             "lc_plate_id":r["lc_plate_id"],"well":r["well"],
             "vial_position":"","injection_name":"","type":""}
            for i,r in enumerate([r for r in sequence if r["lc_batch"]==batch],1)])
    write_csv(output/"lc_plates.csv",plate_rows)
    occupied={r["lc_well"] for r in rows}
    padding=sorted({w for op in ops if op["stage"]=="dilution" for w in op["destination_wells"]}-occupied)
    write_csv(output/"lc_padding_wells.csv",[{"lc_plate_id":f"R{rows[0]['round']}-LC{wells().index(w)//config['robot']['lc_batch_size']+1:02d}","well":w,"contents":"Diluent only; NO sample; DO NOT INJECT"} for w in padding],fields=["lc_plate_id","well","contents"])
    if int(rows[0]["round"]) == 1 and config["design"]["round2_predosed"]:
        from .io import reaction_wells
        n0 = config["chemistry"]["substrate_molarity_M"]*config["chemistry"]["reaction_volume_ul"]
        write_csv(output/"round2_predose.csv", [{"round": 2, "sample_id": f"R2-{i:03d}", "well": well,
                  "lc_well": wells()[i-1], "substrate_umol": n0,
                  "sm_stock_ul": n0/config["liquids"]["substrate_stock_mM"]*1000,
                  "internal_standard_predosed_umol": n0*config["chemistry"]["preloaded_internal_standard"]["mol_percent_relative_to_substrate"]/100,
                  "substrate_solvent_retained_ul": n0/config["liquids"]["substrate_stock_mM"]*1000,
                  "storage": "ROBOT PREDOSE before R1 in the SAME block. Staff CAP, label and store these 23 vials, then replace with 48 empty R1 vials. No manual pipetting. Retain toluene; no SM/IS redose."}
                  for i, well in enumerate(reaction_wells(config)[:config["design"]["round2_total"]], 1)])
    stages = ("dose_and_react", "workup") if stage == "all" else (stage,)
    for protocol_stage in stages:
        prefix = "# Generated, self-contained. Keep this file with its dosing and deck-load CSVs.\n"
        prefix += f"STAGE = {protocol_stage!r}\nROUND = {int(rows[0]['round'])!r}\nDEMO = {not live!r}\nCONFIG = {config!r}\nOPERATIONS = {ops!r}\nDEFINITIONS = {definitions!r}\nHOLD_PLAN = {hold!r}\nPREP_DEFINITIONS = {prep_definitions(config)!r}\n"
        protocol_name = f"Dual-ligand HTE R{rows[0]['round']} {protocol_stage}"
        runtime = RUNTIME.replace('"protocolName": "Dual-ligand HTE"', '"protocolName": '+repr(protocol_name))
        atomic_text(output / f"{protocol_stage}.py", prefix + 'from opentrons import protocol_api\n'+LIQUID_RUNTIME+runtime)
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
