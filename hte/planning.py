from __future__ import annotations

import math
from collections import defaultdict

from .io import finite, well_name, wells


VALIDATIONS = ["chemistry_confirmed", "plate_adapter_seal_validated", "solvent_pipetting_validated",
               "heating_and_evaporation_validated", "homogeneous_sampling_validated",
               "lc_calibration_validated", "local_app_simulation_passed", "round2_ambient_evaporation_validated"]


def required_validations(config):
    required = [*VALIDATIONS]
    if config["pipetting"].get("reuse_tips"):
        required.append("noncontact_tip_reuse_validated")
    if config["liquids"].get("naphthalene_addition_stage") == "substrate_stock":
        required.append("pre_reaction_internal_standard_validated")
    return required


def internal_standard_amounts(config, substrate_umol):
    liquid = config["liquids"]
    stage = liquid.get("naphthalene_addition_stage", "workup")
    stock_mM = finite(liquid.get("naphthalene_substrate_stock_mM", 0), "substrate-stock IS concentration", 0)
    workup_mM = finite(liquid["naphthalene_workup_mM"], "workup IS concentration", 0)
    if stage not in ("substrate_stock", "workup"):
        raise ValueError("Naphthalene addition stage must be substrate_stock or workup")
    if stage == "substrate_stock" and (stock_mM <= 0 or workup_mM != 0):
        raise ValueError("Combined substrate/IS stock requires positive stock IS and zero workup IS")
    if stage == "workup" and (stock_mM != 0 or workup_mM <= 0):
        raise ValueError("Workup IS requires zero substrate-stock IS and positive workup IS")
    preloaded = substrate_umol*stock_mM/liquid["substrate_stock_mM"]
    workup = workup_mM*liquid["workup_ul"]/1000
    extract_ul = config["chemistry"]["reaction_volume_ul"]+liquid["workup_ul"]
    final_uM = (preloaded+workup)*1e6/extract_ul*liquid["aliquot_ul"]/(liquid["aliquot_ul"]+liquid["diluent_ul"])
    return preloaded, workup, final_uM


def validate_config(config, live=False):
    c, liquid = config["chemistry"], config["liquids"]
    for name in ("substrate_molarity_M", "reaction_volume_ul", "ligand_a_mol_percent",
                 "ligand_b_mol_percent", "pd_mol_percent", "reaction_minutes"):
        finite(c[name], name, 0.00001)
    finite(c["temperature_C"], "temperature", 37, 95)
    for name in ("substrate_stock_mM", "ligand_stock_mM", "pd_stock_mM", "workup_ul", "aliquot_ul", "diluent_ul"):
        finite(liquid[name], name, 0.00001)
    for name in ("aspirate_height_mm", "dispense_above_top_mm", "surplus_ul", "air_gap_ul"):
        finite(config["pipetting"][name], name, 0.1)
    if config["pipetting"]["surplus_ul"]+config["pipetting"]["air_gap_ul"] >= 20:
        raise ValueError("Air gap plus surplus leaves no p20 transfer capacity")
    for name in ("p20_aspirate_ul_s", "p20_dispense_ul_s", "p300_aspirate_ul_s", "p300_dispense_ul_s", "minimum_p20_ul"):
        finite(config["pipetting"][name], name, 0.000001)
    for name in ("post_aspirate_seconds", "post_dispense_seconds"):
        finite(config["pipetting"][name], name, 0)
    if not isinstance(config["pipetting"]["prewet_cycles"], int) or not 0 <= config["pipetting"]["prewet_cycles"] <= 5:
        raise ValueError("Choose 0-5 prewet cycles")
    n0 = c["substrate_molarity_M"]*c["reaction_volume_ul"]
    preloaded_is, _, final_is = internal_standard_amounts(config, n0)
    if config["analytics"]["calibration_mode"] == "internal_standard" and abs(final_is-config["analytics"]["internal_standard_final_uM"]) > 1e-6:
        raise ValueError("Configured final IS concentration differs from the dosing/workup/dilution amounts")
    if liquid.get("naphthalene_addition_stage") == "substrate_stock":
        standard = c.get("preloaded_internal_standard", {})
        if standard.get("identity") != "naphthalene" or standard.get("addition_stage") != "substrate_stock":
            raise ValueError("Record the preloaded naphthalene in the chemistry context for LLM scoring")
        if abs(finite(standard.get("mol_percent_relative_to_substrate"), "preloaded IS mol%", 0)-preloaded_is/n0*100) > 1e-6:
            raise ValueError("Chemistry context and combined-stock naphthalene loading differ")
    if live and config["pipetting"].get("reuse_tips") and not config["validation"].get("noncontact_tip_reuse_validated"):
        raise ValueError("Validate source-dedicated noncontact tip reuse before live export")
    if config["robot"]["heater_slot"] != 10:
        raise ValueError("This deck is designed for heater-shaker slot 10")
    if config["robot"]["p20"] != "p20_single_gen2" or config["robot"]["p300"] != "p300_multi_gen2":
        raise ValueError("This protocol requires a p20 single GEN2 and p300 eight-channel GEN2")
    volume = c["reaction_volume_ul"] + liquid["workup_ul"]
    if volume > config["robot"]["reaction_working_volume_ul"]:
        raise ValueError("Extraction exceeds reaction plate working volume")
    if liquid["aliquot_ul"] + liquid["diluent_ul"] > config["robot"]["lc_working_volume_ul"]:
        raise ValueError("Diluted sample exceeds LC plate working volume")
    if liquid["aliquot_ul"] >= volume:
        raise ValueError("Aliquot must be smaller than extract volume")
    if live:
        if config.get("demo"):
            raise ValueError("Demo protocol cannot be exported for live use")
        missing = [name for name in required_validations(config) if config["validation"].get(name) is not True]
        if missing:
            raise ValueError("Bench decisions/validation required: " + ", ".join(missing))
        for key in ("reaction_labware", "lc_labware", "heater_adapter"):
            if not config["robot"].get(key) and not config["robot"].get(key.replace("_labware", "_definition_path")):
                raise ValueError(f"Exact Opentrons load name required: {key}")
        if not c.get("pd_identity"):
            raise ValueError("Pd identity must be specified")
    return config


def dosing_rows(config, inventory, design):
    validate_config(config)
    from .inventory import pair_id
    if not design or len({int(d["round"]) for d in design}) != 1:
        raise ValueError("A dosing design must contain one nonempty round")
    round_number = int(design[0]["round"])
    if round_number not in (1, 2) or len(design) != config["design"][f"round{round_number}_total"]:
        raise ValueError("Dosing design count differs from the configured round")
    if round_number == 2 and config["design"].get("round2_predosed"):
        if {well_name(d["well"]) for d in design} != set(wells()[:len(design)]):
            raise ValueError("Round-two wells do not match the substrate predose manifest")
    c, stocks = config["chemistry"], config["liquids"]
    n = c["substrate_molarity_M"] * c["reaction_volume_ul"]  # M * uL = umol
    seen_samples, seen_wells = set(), set()
    rows = []
    for d in design:
        well = well_name(d["well"])
        if well in seen_wells or d["sample_id"] in seen_samples or not d["sample_id"]:
            raise ValueError("Duplicate well/sample ID")
        seen_samples.add(d["sample_id"])
        seen_wells.add(well)
        kind = d["kind"]
        if kind not in ("pair", "single", "no_ligand", "no_pd", "blank"):
            raise ValueError("Unknown reaction kind")
        a, b = d["ligand_a"], d["ligand_b"]
        if kind in ("pair", "no_pd") and (not a or not b or a == b):
            raise ValueError("Pair and no-Pd controls require two different ligands")
        if kind in ("pair", "no_pd") and d["pair_id"] != pair_id(a, b):
            raise ValueError("Pair ID differs from ligand identities")
        if kind == "single" and (not a or b):
            raise ValueError("Single control requires only ligand A")
        if kind in ("blank", "no_ligand") and (a or b):
            raise ValueError("Blank/no-ligand controls must not specify ligands")
        if any(key and key not in inventory for key in (a, b)):
            raise ValueError("Unknown ligand in dosing design")
        n_substrate = 0 if kind == "blank" else n
        n_pd = 0 if kind in ("blank", "no_pd") else n * c["pd_mol_percent"] / 100
        n_a = n * (c["ligand_a_mol_percent"] + c["ligand_b_mol_percent"] if kind == "single"
                   else c["ligand_a_mol_percent"]) / 100 if a else 0
        n_b = n * c["ligand_b_mol_percent"] / 100 if b else 0
        v_a = n_a / stocks["ligand_stock_mM"] * 1000
        v_b = n_b / stocks["ligand_stock_mM"] * 1000
        v_pd = n_pd / stocks["pd_stock_mM"] * 1000
        predosed = int(d["round"]) == 2 and config["design"].get("round2_predosed", False)
        v_sm = 0 if predosed else n_substrate / stocks["substrate_stock_mM"] * 1000
        preloaded_is, workup_is, final_is = internal_standard_amounts(config, n_substrate)
        if config["analytics"]["calibration_mode"] == "internal_standard" and final_is <= 0:
            raise ValueError("Combined substrate/IS dosing does not add IS to a reaction blank; define a separate validated blank preparation")
        v_tol = c["reaction_volume_ul"] - v_a - v_b - v_pd
        if v_tol < -1e-8:
            raise ValueError("Stocks are too dilute to fit in the final reaction volume")
        if v_sm > config["robot"]["reaction_working_volume_ul"]:
            raise ValueError("DCM dosing volume exceeds reaction working volume")
        row = {**d, "well": well, "substrate_umol": n_substrate, "pd_umol": n_pd,
               "ligand_a_umol": n_a, "ligand_b_umol": n_b, "sm_DCM_ul": v_sm,
               "substrate_predosed_umol": n_substrate if predosed else 0,
               "naphthalene_total_umol": preloaded_is+workup_is,
               "naphthalene_added_with_substrate_umol": 0 if predosed else preloaded_is,
               "naphthalene_predosed_umol": preloaded_is if predosed else 0,
               "naphthalene_workup_umol": workup_is,
               "internal_standard_final_uM": final_is,
               "ligand_a_ul": v_a, "ligand_b_ul": v_b, "pd_ul": v_pd,
               "toluene_ul": max(0, v_tol), "reaction_volume_ul": c["reaction_volume_ul"],
               "temperature_C": c["temperature_C"], "reaction_minutes": c["reaction_minutes"],
               "workup_ul": stocks["workup_ul"], "aliquot_ul": stocks["aliquot_ul"],
               "diluent_ul": stocks["diluent_ul"]}
        rows.append(row)
    if round_number == 1:
        from .design import validate_round1_coverage
        validate_round1_coverage(config, inventory, design)
    return rows


def transfer_operations(config, inventory, rows):
    """Expand all transfers, including surplus discarded with tips; multi volumes are PER CHANNEL."""
    operations = []
    p = config["pipetting"]
    capacities = {"p20": 20 - p["air_gap_ul"] - p["surplus_ul"],
                  "p300": 300 - p["air_gap_ul"] - p["surplus_ul"]}

    def add(stage, reagent, slot, source, target_slot, targets, volume, multi=False):
        if volume <= 1e-9:
            return
        pipette = "p300" if multi else "p20"
        count = math.ceil(volume / capacities[pipette])
        part = volume / count
        minimum = 20 if multi else p["minimum_p20_ul"]
        if part < minimum:
            raise ValueError(f"{reagent}: {part:.3f} uL below validated pipette minimum {minimum}")
        for _ in range(count):
            operations.append({"stage": stage, "reagent": reagent, "source_slot": slot,
                               "source_well": source, "destination_slot": target_slot,
                               "destination_wells": targets, "volume_ul_per_channel": part,
                               "aspirated_ul_per_channel": part + p["surplus_ul"],
                               "pipette": pipette, "channels": 8 if multi else 1})

    def common(stage, reagent, source, volumes, target_slot=3):
        remaining = dict(volumes)
        for col in range(1, 13):
            column = [f"{r}{col}" for r in "ABCDEFGH"]
            if all(w in remaining for w in column):
                values = [remaining[w] for w in column]
                if min(values) >= 20 and max(values)-min(values) < 1e-8:
                    add(stage, reagent, 2, source, target_slot, column, values[0], multi=True)
                    for w in column:
                        del remaining[w]
        for w, volume in remaining.items():
            add(stage, reagent, 2, source, target_slot, [w], volume)

    common("substrate", "substrate_DCM", "A1", {r["well"]: r["sm_DCM_ul"] for r in rows})
    if int(rows[0]["round"]) == 1 and config["design"].get("round2_predosed"):
        n0 = config["chemistry"]["substrate_molarity_M"]*config["chemistry"]["reaction_volume_ul"]
        volume = n0/config["liquids"]["substrate_stock_mM"]*1000
        common("round2_predose", "substrate_DCM", "A1",
               {w: volume for w in wells()[:config["design"]["round2_total"]]}, target_slot=6)
    for ligand in inventory:
        for r in rows:
            volume = sum(r[f"ligand_{side}_ul"] for side in ("a", "b") if r[f"ligand_{side}"] == ligand)
            add("assembly", ligand, int(inventory[ligand]["source_slot"]), inventory[ligand]["source_well"],
                3, [r["well"]], volume)
    common("assembly", "toluene", "A3", {r["well"]: r["toluene_ul"] for r in rows})
    common("assembly", "Pd", "A2", {r["well"]: r["pd_ul"] for r in rows})
    common("workup", "workup", "A4", {r["well"]: r["workup_ul"] for r in rows})
    common("dilution", "LC_diluent", "A5", {r["well"]: r["diluent_ul"] for r in rows}, target_slot=6)
    remaining = {r["well"]: r for r in rows}
    for col in range(1, 13):
        column = [f"{r}{col}" for r in "ABCDEFGH"]
        if all(w in remaining for w in column):
            volumes = [remaining[w]["aliquot_ul"] for w in column]
            if min(volumes) >= 20 and max(volumes)-min(volumes) < 1e-8:
                add("sampling", "reaction_samples", 3, column[0], 6, column, volumes[0], multi=True)
                for w in column:
                    del remaining[w]
    for r in remaining.values():
        add("sampling", r["sample_id"], 3, r["well"], 6, [r["well"]], r["aliquot_ul"])
    for i, op in enumerate(operations):
        previous = operations[i-1] if i else None
        following = operations[i+1] if i+1 < len(operations) else None
        def same(other):
            return bool(other and config["pipetting"].get("reuse_tips") and op["source_slot"] != 3
                        and all(op[k] == other[k] for k in ["stage", "reagent", "source_slot", "source_well", "pipette"]))
        op["retained_tip_from_previous"] = same(previous)
        op["retain_tip_for_next"] = same(following)
        if op["retained_tip_from_previous"]:
            op["aspirated_ul_per_channel"] -= p["surplus_ul"]
    return operations


def stock_plan(config, inventory, operations, reserve_round2=True):
    usage = defaultdict(float)
    for op in operations:
        if op["source_slot"] != 3:
            usage[op["reagent"]] += op["aspirated_ul_per_channel"] * op["channels"]
    c, liquid = config["chemistry"], config["liquids"]
    margin = finite(config["stock_preparation"]["margin_factor"], "stock margin", 1)
    reserve_wells = config["design"]["round2_total"] if reserve_round2 else 0
    n = c["substrate_molarity_M"] * c["reaction_volume_ul"]
    # Any ligand could be used as a 12 mol% single in every round-two well.
    worst_ligand = n * (c["ligand_a_mol_percent"] + c["ligand_b_mol_percent"]) / 100 / liquid["ligand_stock_mM"] * 1000
    records = []
    def corrected_mass(key, pure_mass):
        assay = finite(config["stock_preparation"].get("assay_fractions", {}).get(key, 1), key+" assay fraction", 0.000001, 1)
        return pure_mass/assay
    for key, row in inventory.items():
        part_count = math.ceil(worst_ligand / (20-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]))
        reserve = reserve_wells * (worst_ligand + part_count * config["pipetting"]["surplus_ul"])
        dead = config["stock_preparation"]["tube_dead_ul"]
        prepare = math.ceil(((usage[key] + reserve) * margin + dead) / 10) * 10
        records.append({"reagent": key, "name": row["name"], "solvent": "toluene",
                        "stock_mM": liquid["ligand_stock_mM"], "round1_consumption_ul": usage[key],
                        "round2_reserve_ul": reserve, "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": corrected_mass(key, liquid["ligand_stock_mM"] * prepare * float(row["molecular_weight_g_mol"]) / 1e6),
                        "source_slot": row["source_slot"], "source_well": row["source_well"],
                        "on_deck_ul": math.ceil((usage[key] + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["tube_max_fill_ul"],
                        "capacity_ok": usage[key] + dead <= config["stock_preparation"]["tube_max_fill_ul"]})
    common = [("substrate_DCM", "DCM", "substrate_stock_mM", "A1", n/liquid["substrate_stock_mM"]*1000),
              ("Pd", "toluene", "pd_stock_mM", "A2", n*c["pd_mol_percent"]/100/liquid["pd_stock_mM"]*1000),
              ("toluene", "toluene", None, "A3", c["reaction_volume_ul"]),
              ("workup", liquid["workup_composition"], "naphthalene_workup_mM", "A4", liquid["workup_ul"]),
              ("LC_diluent", liquid["lc_diluent_composition"], None, "A5", liquid["diluent_ul"])]
    for key, solvent, concentration, well, worst in common:
        # Conservatively allow single-channel splitting and surplus for every reserve well.
        count = math.ceil(worst / (20-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]))
        reserve = reserve_wells * (worst + count * config["pipetting"]["surplus_ul"])
        if key == "substrate_DCM" and config["design"].get("round2_predosed"):
            reserve = 0  # Round-two substrate is already included in round-one operations.
        dead = config["stock_preparation"]["reservoir_dead_ul"]
        prepare = math.ceil(((usage[key] + reserve) * margin + dead) / 10) * 10
        if key == "substrate_DCM":
            prepare = max(prepare, finite(config["stock_preparation"].get("substrate_min_prepare_ul", 0),
                                          "minimum substrate stock preparation", 0))
        concentration_mM = liquid[concentration] if concentration else ""
        mw = c.get("pd_molecular_weight_g_mol") if key == "Pd" else c.get("substrate_molecular_weight_g_mol") if key == "substrate_DCM" else liquid["naphthalene_molecular_weight_g_mol"] if key == "workup" else None
        records.append({"reagent": key, "name": key, "solvent": solvent, "stock_mM": concentration_mM,
                        "round1_consumption_ul": usage[key], "round2_reserve_ul": reserve,
                        "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": corrected_mass(key, concentration_mM * prepare * mw / 1e6) if mw else "",
                        "source_slot": 2, "source_well": well,
                        "on_deck_ul": math.ceil((usage[key] + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["reservoir_max_fill_ul"],
                        "capacity_ok": usage[key] + dead <= config["stock_preparation"]["reservoir_max_fill_ul"]})
    # The mixture is one reservoir source; report its second solute separately.
    for record in records:
        mixed = record["reagent"] == "substrate_DCM" and liquid.get("naphthalene_addition_stage") == "substrate_stock"
        record["naphthalene_stock_mM"] = liquid.get("naphthalene_substrate_stock_mM", 0) if mixed else ""
        record["naphthalene_mass_mg"] = corrected_mass("naphthalene", liquid["naphthalene_substrate_stock_mM"]*
            record["prepare_ul"]*liquid["naphthalene_molecular_weight_g_mol"]/1e6) if mixed else ""
        record["storage_container"] = config["stock_preparation"].get("substrate_storage_container", "") if mixed else ""
        if mixed:
            record["name"] = "Starting material + naphthalene internal standard"
    return records


def tip_budget(operations):
    count = defaultdict(int)
    for op in operations:
        stage = "dose" if op["stage"] in ("substrate", "assembly", "round2_predose") else "workup"
        if not op.get("retained_tip_from_previous"):
            count[f"{stage}_{op['pipette']}"] += op["channels"]
    return dict(count)


def schedule(config):
    t = config["timing"]
    counts = [config["design"]["round1_total"], config["design"]["round2_total"]]
    reaction = 2 * config["chemistry"]["reaction_minutes"]
    injections = sum(counts) + t["additional_injections"]
    cycle = finite(t["injection_cycle_minutes"], "full injection cycle time", 2)
    parallel = int(t.get("calibration_injections_during_round1_reaction", 0))
    if not 0 <= parallel <= t["additional_injections"] or parallel*cycle > config["chemistry"]["reaction_minutes"]:
        raise ValueError("Calibration overlap exceeds available first-reaction window")
    analysis = (injections-parallel) * cycle
    overhead = sum(finite(t[key], key, 0) for key in ["dosing_total_minutes", "evaporation_total_minutes",
                 "heat_ramp_total_minutes", "cooling_total_minutes", "workup_total_minutes",
                 "decision_minutes", "other_minutes"])
    total = reaction + analysis + overhead
    return {"reaction_minutes": reaction, "lc_minutes": analysis, "overhead_minutes": overhead,
            "injections": injections, "minimum_reaction_plus_lc_minutes": reaction + analysis,
            "calibration_minutes_hidden_in_reaction": parallel*cycle,
            "serial_total_minutes": total, "deadline_minutes": t["deadline_minutes"],
            "remaining_minutes": t["deadline_minutes"]-total,
            "fits_serial_estimate": total <= t["deadline_minutes"],
            "assumptions": "Full cycle time, serial round-one analysis before round-two decision; no unvalidated overlap."}
