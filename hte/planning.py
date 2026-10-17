from __future__ import annotations

import math
from collections import defaultdict

from .io import finite, well_name, wells, reaction_wells


VALIDATIONS = ["chemistry_confirmed", "plate_adapter_seal_validated", "solvent_pipetting_validated",
               "heating_validated", "lc_plate_workflow_validated",
               "lc_calibration_validated", "local_app_simulation_passed", "round2_predose_storage_validated",
               "injection_cycle_validated", "simultaneous_heating_capacity_validated",
               "substrate_evaporation_validated"]

COMMON_WELLS = {"substrate_stock":"A1", "Pd":"A2", "toluene":"A3", "workup":"A4", "LC_diluent":"A5",
                "internal_standard":"A8"}


def single_pipette(config):
    model = config["robot"]["single"]
    if model not in ("p20_single_gen2", "p300_single_gen2"):
        raise ValueError("Choose a p20 or p300 single GEN2")
    return ("p20", 20) if model == "p20_single_gen2" else ("p300_single", 300)


def reservoir_source_pools(config):
    overrides = config["stock_preparation"].get("reservoir_source_pools", {})
    if set(overrides)-set(COMMON_WELLS):
        raise ValueError("Unknown reservoir source-pool reagent")
    pools = {key:overrides.get(key,[well]) for key,well in COMMON_WELLS.items()}
    seen = set()
    for key, pool in pools.items():
        if not isinstance(pool,list) or not pool:
            raise ValueError("Each reservoir source pool needs a nonempty channel list")
        for well in pool:
            if well not in [f"A{i}" for i in range(1,13)] or well in seen:
                raise ValueError("Reservoir source pools need distinct valid channels")
            seen.add(well)
    return pools


def required_validations(config):
    required = [*VALIDATIONS]
    if config["pipetting"].get("reuse_tips"):
        required.append("noncontact_tip_reuse_validated")
    if config["liquids"].get("internal_standard_addition_stage") == "reaction_stock":
        required.append("pre_reaction_internal_standard_validated")
    if config["timing"].get("staged_lc_overlap_minutes",0):
        required.append("staged_lc_timing_confirmed")
    return required


def internal_standard_amounts(config, substrate_umol):
    liquid = config["liquids"]
    stage = liquid["internal_standard_addition_stage"]
    stock_mM = finite(liquid.get("internal_standard_stock_mM", 0), "substrate-stock IS concentration", 0)
    workup_mM = finite(liquid["internal_standard_workup_mM"], "workup IS concentration", 0)
    if stage not in ("reaction_stock", "workup"):
        raise ValueError("Internal standard addition stage must be reaction_stock or workup")
    if stage == "reaction_stock" and (stock_mM <= 0 or workup_mM != 0):
        raise ValueError("Separate reaction IS stock requires positive stock IS and zero workup IS")
    if stage == "workup" and (stock_mM != 0 or workup_mM <= 0):
        raise ValueError("Workup IS requires zero substrate-stock IS and positive workup IS")
    preloaded = (substrate_umol*finite(config["chemistry"]["preloaded_internal_standard"]["mol_percent_relative_to_substrate"],
                                    "internal standard mol%", 0)/100 if stage == "reaction_stock" else 0)
    workup = workup_mM*liquid["workup_ul"]/1000
    extract_ul = config["chemistry"]["reaction_volume_ul"]+liquid["workup_ul"]
    final_uM = (preloaded+workup)*1e6/extract_ul*liquid["aliquot_ul"]/(liquid["aliquot_ul"]+liquid["diluent_ul"])
    return preloaded, workup, final_uM


def analytical_summary(config):
    c,l = config["chemistry"],config["liquids"]
    extract=c["reaction_volume_ul"]+l["workup_ul"]
    final=l["aliquot_ul"]+l["diluent_ul"]
    fraction=l["aliquot_ul"]/final
    acid_extract=l["workup_formic_acid_percent"]*l["workup_ul"]/extract
    return {"substrate_umol":c["substrate_molarity_M"]*c["reaction_volume_ul"],
            "extract_ul":extract,"dilution_factor":final/l["aliquot_ul"],
            "maximum_analyte_uM":c["substrate_molarity_M"]*c["reaction_volume_ul"]*1e6/extract*fraction,
            "internal_standard_final_uM":internal_standard_amounts(config,c["substrate_molarity_M"]*c["reaction_volume_ul"])[2],
            "extract_formic_acid_percent":acid_extract,
            "final_formic_acid_percent":acid_extract*fraction+l["lc_diluent_formic_acid_percent"]*(1-fraction),
            "final_toluene_percent":100*c["reaction_volume_ul"]/extract*fraction,
            "nominal_vial_headspace_ul":2000-extract}


def validate_config(config, live=False, live_scope="all"):
    if config.get("schema_version") != 2:
        raise ValueError("Use campaign schema_version 2: separate mesitylene stock, evaporated DCM and explicit reaction/LC well maps")
    if live_scope not in ("all", "first_reaction"):
        raise ValueError("Unknown live validation scope")
    reservoir_source_pools(config)
    stock = config["stock_preparation"]
    dead = finite(stock["reservoir_dead_ul"], "reservoir dead volume", 0)
    capacity = finite(stock["reservoir_max_fill_ul"], "reservoir fill limit", dead+1)
    if capacity > config["robot"].get("reservoir_working_volume_ul", capacity):
        raise ValueError("Reservoir fill limit exceeds the configured labware working volume")
    c, liquid = config["chemistry"], config["liquids"]
    for name in ("substrate_molarity_M", "reaction_volume_ul", "ligand_a_mol_percent",
                 "ligand_b_mol_percent", "pd_mol_percent", "reaction_minutes"):
        finite(c[name], name, 0.00001)
    finite(c["temperature_C"], "temperature", 37, 95)
    finite(c.get("thermal_equilibration_minutes", 0), "thermal equilibration", 0)
    for name, value in (("reaction shaking", c["rpm"]), ("workup shaking", liquid["mix_rpm"])):
        finite(value, name, 200, 3000)
    if liquid.get("substrate_stock_solvent") != "DCM" or liquid.get("substrate_evaporation_required") is not True:
        raise ValueError("This campaign requires DCM substrate dosing followed by complete evaporation before assembly")
    if config["design"].get("round2_predose_mode") != "manual_offdeck":
        raise ValueError("One reaction block requires manual off-deck round-two substrate predosing")
    if not isinstance(config["robot"].get("reaction_multichannel"), bool):
        raise ValueError("Specify reaction_multichannel explicitly from the actual rack geometry")
    single, capacity = single_pipette(config)
    for name in ("reuse_tips",):
        if not isinstance(config["pipetting"].get(name), bool):
            raise ValueError(f"{name} must be true or false")
    if not isinstance(config["design"].get("round2_predosed"), bool):
        raise ValueError("round2_predosed must be true or false")
    for round_number in (1, 2):
        count = config["design"][f"round{round_number}_total"]
        if type(count) is not int or not 1 <= count <= len(reaction_wells(config)):
            raise ValueError("Round counts exceed the configured reaction rack capacity")
    for name in ("substrate_stock_mM", "ligand_stock_mM", "pd_stock_mM", "workup_ul", "aliquot_ul", "diluent_ul"):
        finite(liquid[name], name, 0.00001)
    for name in ("aspirate_height_mm", "dispense_above_top_mm", "surplus_ul", "air_gap_ul"):
        finite(config["pipetting"][name], name, 0.1)
    if config["pipetting"]["aspirate_height_mm"] <= 1:
        raise ValueError("Aspiration requires bottom clearance greater than 1 mm per HTEL guidance")
    if config["pipetting"]["surplus_ul"]+config["pipetting"]["air_gap_ul"] >= capacity:
        raise ValueError("Air gap plus surplus leaves no single-channel transfer capacity")
    for name in (single+"_aspirate_ul_s", single+"_dispense_ul_s", "p300_aspirate_ul_s", "p300_dispense_ul_s", "minimum_"+single+"_ul"):
        finite(config["pipetting"][name], name, 0.000001)
    for name in ("workup_aspirate_ul_s", "workup_dispense_ul_s"):
        finite(config["pipetting"][name], name, 0.000001)
    for name in ("post_aspirate_seconds", "post_dispense_seconds"):
        finite(config["pipetting"][name], name, 0)
    if type(config["pipetting"]["prewet_cycles"]) is not int or not 0 <= config["pipetting"]["prewet_cycles"] <= 5:
        raise ValueError("Choose 0-5 prewet cycles")
    p = config["pipetting"]
    batch=config["robot"].get("lc_batch_size",24)
    if type(batch) is not int or batch<8 or batch>96 or batch%8:
        raise ValueError("LC preparation batches must contain a positive multiple of eight wells")
    if config["robot"].get("lc_single_plate_per_round") and batch < max(config["design"][f"round{r}_total"] for r in (1, 2)):
        raise ValueError("This campaign requires one LC plate per round; splitting R1 is disabled")
    finite(liquid["lc_mix_rpm"], "uncovered LC plate shaking", 200, 3000)
    finite(liquid["lc_mix_minutes"], "LC plate mixing time", 0.01)
    finite(liquid["lc_max_module_temperature_C"], "maximum LC module temperature", 20, 40)
    if type(p["sample_prewet_cycles"]) is not int or not 0 <= p["sample_prewet_cycles"] <= 5:
        raise ValueError("Choose 0-5 sample prewet cycles")
    finite(p["sample_aspirate_height_mm"], "sample aspiration height", 0.1)
    if p["sample_aspirate_height_mm"] <= 1:
        raise ValueError("Sample aspiration requires bottom clearance greater than 1 mm")
    finite(p["sample_flow_rate_multiplier"], "sample flow-rate multiplier", 0.000001, 1)
    finite(p["sample_air_gap_rate"], "sample air-gap rate", 0.000001, 1)
    finite(p["sample_pause_seconds"], "sample aspiration/dispense pause", 0)
    # Fresh sample tips retain a surplus on every split transfer. There must
    # remain enough extract to keep the tip immersed on the final aspiration.
    # Partial columns use the configured single-channel pipette.
    partial_capacity = capacity-p["air_gap_ul"]-p["surplus_ul"]
    withdrawals = liquid["aliquot_ul"]+math.ceil(liquid["aliquot_ul"]/partial_capacity)*p["surplus_ul"]
    extract_volume = c["reaction_volume_ul"]+liquid["workup_ul"]
    if withdrawals >= extract_volume:
        raise ValueError("Sample transfer plus discarded surplus exhausts the extract; reduce the aliquot")
    n0 = c["substrate_molarity_M"]*c["reaction_volume_ul"]
    preloaded_is, _, final_is = internal_standard_amounts(config, n0)
    if config["analytics"]["calibration_mode"] == "internal_standard" and abs(final_is-config["analytics"]["internal_standard_final_uM"]) > 1e-6:
        raise ValueError("Configured final IS concentration differs from the dosing/workup/dilution amounts")
    if liquid.get("internal_standard_addition_stage") == "reaction_stock":
        standard = c.get("preloaded_internal_standard", {})
        if standard.get("identity") != config["analytics"]["internal_standard"] or standard.get("addition_stage") != "reaction_stock":
            raise ValueError("Record the separate reaction internal standard in the chemistry context for LLM scoring")
        if abs(finite(standard.get("mol_percent_relative_to_substrate"), "preloaded IS mol%", 0)-preloaded_is/n0*100) > 1e-6:
            raise ValueError("Chemistry context and internal-standard loading differ")
    if live and config["pipetting"].get("reuse_tips") and not config["validation"].get("noncontact_tip_reuse_validated"):
        raise ValueError("Validate source-dedicated noncontact tip reuse before live export")
    if config["robot"]["heater_slot"] != 10:
        raise ValueError("This deck is designed for heater-shaker slot 10")
    if config["robot"]["p300"] != "p300_multi_gen2":
        raise ValueError("This protocol requires a p300 eight-channel GEN2")
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
        needed = required_validations(config)
        if live_scope == "first_reaction":
            needed = [name for name in needed if name != "lc_calibration_validated"]
        missing = [name for name in needed if config["validation"].get(name) is not True]
        if missing:
            raise ValueError("Bench decisions/validation required: " + ", ".join(missing))
        for key in ("reaction_labware", "lc_labware", "heater_adapter"):
            if not config["robot"].get(key) and not config["robot"].get(key.replace("_labware", "_definition_path")):
                raise ValueError(f"Exact Opentrons load name required: {key}")
        if not c.get("pd_identity"):
            raise ValueError("Pd identity must be specified")
        if not config["analytics"].get("method_id"):
            raise ValueError("Configure LC method before starting the first reaction")
        if live_scope == "all":
            from .analytics import validate_analytics_settings
            validate_analytics_settings(config)
        if any(str(config["analytics"].get(key)).upper().startswith("SYNTHETIC") for key in ("method_id", "channel")):
            raise ValueError("Synthetic LC settings cannot release live protocols")
        timing = schedule(config)
        if not timing["fits_planned_estimate"]:
            raise ValueError(f"Configured timing allowances exceed the competition deadline: {timing['planned_total_minutes']:g} > {timing['deadline_minutes']:g} min; replace allowances with the timed local plan")
    return config


def dosing_rows(config, inventory, design):
    validate_config(config)
    from .inventory import pair_id
    from .design import validate_design
    validate_design(config, inventory, design)
    if not design or len({int(d["round"]) for d in design}) != 1:
        raise ValueError("A dosing design must contain one nonempty round")
    round_number = int(design[0]["round"])
    if round_number not in (1, 2) or len(design) != config["design"][f"round{round_number}_total"]:
        raise ValueError("Dosing design count differs from the configured round")
    if round_number == 2 and config["design"].get("round2_predosed"):
        if {well_name(d["well"]) for d in design} != set(reaction_wells(config)[:len(design)]):
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
        total_sm_volume = n_substrate / stocks["substrate_stock_mM"] * 1000
        v_sm = 0 if predosed else total_sm_volume
        preloaded_is, workup_is, final_is = internal_standard_amounts(config, n_substrate)
        if config["analytics"]["calibration_mode"] == "internal_standard" and final_is <= 0:
            raise ValueError("Combined substrate/IS dosing does not add IS to a reaction blank; define a separate validated blank preparation")
        # All substrate DCM is removed; mesitylene is added only afterwards in toluene.
        v_is = preloaded_is/stocks["internal_standard_stock_mM"]*1000 if preloaded_is else 0
        v_tol = c["reaction_volume_ul"] - v_is - v_a - v_b - v_pd
        if v_tol < -1e-8:
            raise ValueError("Stocks are too dilute to fit in the final reaction volume")
        if v_sm > config["robot"]["reaction_working_volume_ul"]:
            raise ValueError("Substrate-stock dosing volume exceeds reaction working volume")
        row = {**d, "well": well, "substrate_umol": n_substrate, "pd_umol": n_pd,
               "ligand_a_umol": n_a, "ligand_b_umol": n_b, "sm_stock_ul": v_sm,
               "substrate_predosed_umol": n_substrate if predosed else 0,
               "substrate_predosed_ul": total_sm_volume if predosed else 0,
               "substrate_solvent_retained_ul": 0,
               "substrate_solvent_evaporated_ul": total_sm_volume,
               "internal_standard_stock_ul": v_is,
               "internal_standard_total_umol": preloaded_is+workup_is,
               "internal_standard_added_umol": preloaded_is,
               "internal_standard_predosed_umol": 0,
               "internal_standard_workup_umol": workup_is,
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


def validate_dosing(config, inventory, rows):
    """Reject stale or edited numerical doses before quantification or feedback."""
    expected = dosing_rows(config, inventory, rows)
    numeric_fields = ("substrate_umol", "pd_umol", "ligand_a_umol", "ligand_b_umol", "sm_stock_ul",
                      "substrate_solvent_retained_ul", "substrate_solvent_evaporated_ul", "internal_standard_stock_ul",
                      "substrate_predosed_umol", "substrate_predosed_ul", "internal_standard_total_umol", "internal_standard_added_umol",
                      "internal_standard_predosed_umol", "internal_standard_workup_umol", "internal_standard_final_uM",
                      "ligand_a_ul", "ligand_b_ul", "pd_ul", "toluene_ul", "reaction_volume_ul",
                      "temperature_C", "reaction_minutes", "workup_ul", "aliquot_ul", "diluent_ul")
    for actual, calculated in zip(rows, expected):
        for field in numeric_fields:
            if field not in actual or not math.isclose(finite(actual[field], field), calculated[field],
                                                     rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(f"Dosing value differs from the campaign: {actual['sample_id']} {field}")
    return expected


def transfer_operations(config, inventory, rows):
    """Expand all transfers, including surplus discarded with tips; multi volumes are PER CHANNEL."""
    operations = []
    p = config["pipetting"]
    single, capacity = single_pipette(config)
    capacities = {single: capacity - p["air_gap_ul"] - p["surplus_ul"],
                  "p300": 300 - p["air_gap_ul"] - p["surplus_ul"]}

    def add(stage, reagent, slot, source, target_slot, targets, volume, multi=False):
        if volume <= 1e-9:
            return
        pipette = "p300" if multi else single
        count = math.ceil(volume / capacities[pipette])
        part = volume / count
        minimum = 20 if multi else p["minimum_"+single+"_ul"]
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
            if target_slot == 3 and not config["robot"]["reaction_multichannel"]:
                break
            column = [f"{r}{col}" for r in "ABCDEFGH"]
            if all(w in remaining for w in column):
                values = [remaining[w] for w in column]
                if min(values) >= 20 and max(values)-min(values) < 1e-8:
                    add(stage, reagent, 2, source, target_slot, column, values[0], multi=True)
                    for w in column:
                        del remaining[w]
        for w, volume in remaining.items():
            add(stage, reagent, 2, source, target_slot, [w], volume)

    common("substrate", "substrate_stock", "A1", {r["well"]: r["sm_stock_ul"] for r in rows})
    common("internal_standard", "internal_standard", "A8", {r["well"]: r["internal_standard_stock_ul"] for r in rows})
    for ligand in inventory:
        for r in rows:
            volume = sum(r[f"ligand_{side}_ul"] for side in ("a", "b") if r[f"ligand_{side}"] == ligand)
            add("assembly", ligand, int(inventory[ligand]["source_slot"]), inventory[ligand]["source_well"],
                3, [r["well"]], volume)
    common("assembly", "toluene", "A3", {r["well"]: r["toluene_ul"] for r in rows})
    common("assembly", "Pd", "A2", {r["well"]: r["pd_ul"] for r in rows})
    common("workup", "workup", "A4", {r["well"]: r["workup_ul"] for r in rows})
    lc_volumes = {r["lc_well"]: r["diluent_ul"] for r in rows}
    if config["robot"].get("pad_lc_diluent_columns"):
        for row in rows:
            for letter in "ABCDEFGH":
                lc_volumes.setdefault(letter+row["lc_well"][1:], row["diluent_ul"])
    common("dilution", "LC_diluent", "A5", lc_volumes, target_slot=6)
    remaining = {r["well"]: r for r in rows}
    for col in range(1, 13):
        if not config["robot"]["reaction_multichannel"]:
            break
        column = [f"{r}{col}" for r in "ABCDEFGH"]
        if all(w in remaining for w in column):
            volumes = [remaining[w]["aliquot_ul"] for w in column]
            if min(volumes) >= 20 and max(volumes)-min(volumes) < 1e-8:
                add("sampling", "reaction_samples", 3, column[0], 6, column, volumes[0], multi=True)
                for w in column:
                    del remaining[w]
    for r in remaining.values():
        add("sampling", r["sample_id"], 3, r["well"], 6, [r["lc_well"]], r["aliquot_ul"])
    # Allocate complete aspirations to reservoir channels before assigning reused tips.
    # Worst-case fresh surplus makes this conservative when a tip is retained.
    pools = reservoir_source_pools(config)
    limit = config["stock_preparation"]["reservoir_max_fill_ul"]-config["stock_preparation"]["reservoir_dead_ul"]
    spent = defaultdict(float)
    index = defaultdict(int)
    for op in operations:
        if op["source_slot"] != 2:
            continue
        key = op["reagent"]
        withdrawal = op["aspirated_ul_per_channel"]*op["channels"]
        pool = pools[key]
        while index[key] < len(pool) and spent[(key,pool[index[key]])]+withdrawal > limit:
            index[key] += 1
        if index[key] >= len(pool):
            raise ValueError(f"Reservoir source capacity exceeded for {key}; add a validated source channel")
        op["source_well"] = pool[index[key]]
        spent[(key,op["source_well"])] += withdrawal
    for op in operations:
        if op["stage"] in ("dilution","sampling"):
            op["lc_batch"] = wells().index(op["destination_wells"][0])//config["robot"]["lc_batch_size"]+1
    for i, op in enumerate(operations):
        previous = operations[i-1] if i else None
        following = operations[i+1] if i+1 < len(operations) else None
        def same(other):
            return bool(other and config["pipetting"].get("reuse_tips") and op["source_slot"] != 3
                        and op.get("lc_batch") == other.get("lc_batch")
                        and all(op[k] == other[k] for k in ["stage", "reagent", "source_slot", "source_well", "pipette"]))
        op["retained_tip_from_previous"] = same(previous)
        op["retain_tip_for_next"] = same(following)
        if op["retained_tip_from_previous"]:
            op["aspirated_ul_per_channel"] -= p["surplus_ul"]
    return operations


def stock_plan(config, inventory, operations, reserve_round2=True):
    usage = defaultdict(float)
    source_usage = defaultdict(float)
    for op in operations:
        if op["source_slot"] != 3:
            usage[op["reagent"]] += op["aspirated_ul_per_channel"] * op["channels"]
            source_usage[(op["reagent"],op["source_well"])] += op["aspirated_ul_per_channel"] * op["channels"]
    c, liquid = config["chemistry"], config["liquids"]
    _, single_capacity = single_pipette(config)
    margin = finite(config["stock_preparation"]["margin_factor"], "stock margin", 1)
    reserve_wells = config["design"]["round2_total"] if reserve_round2 else 0
    n = c["substrate_molarity_M"] * c["reaction_volume_ul"]
    # Only distinct pair experiments and the explicitly configured references are allowed.
    pair_count = min(reserve_wells-len(config["design"]["round2_controls"]), len(inventory)-1) if reserve_wells else 0
    records = []
    def corrected_mass(key, pure_mass):
        assay = finite(config["stock_preparation"].get("assay_fractions", {}).get(key, 1), key+" assay fraction", 0.000001, 1)
        return pure_mass/assay
    for key, row in inventory.items():
        single_volume = n * max(c["ligand_a_mol_percent"],c["ligand_b_mol_percent"])/100/liquid["ligand_stock_mM"]*1000
        reference_volume = sum(n*(c["ligand_a_mol_percent"]+c["ligand_b_mol_percent"])/100/liquid["ligand_stock_mM"]*1000
                               for control in config["design"]["round2_controls"]
                               if reserve_wells and control["kind"] == "single" and control["ligand_a"] == key)
        usable=single_capacity-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]
        reserve = pair_count*(single_volume+math.ceil(single_volume/usable)*config["pipetting"]["surplus_ul"])+reference_volume
        if reference_volume: reserve += math.ceil(reference_volume/usable)*config["pipetting"]["surplus_ul"]
        dead = config["stock_preparation"]["tube_dead_ul"]
        prepare = math.ceil(((usage[key] + reserve) * margin + dead) / 10) * 10
        records.append({"reagent": key, "name": row["name"], "solvent": "toluene",
                        "stock_mM": liquid["ligand_stock_mM"], "protocol_consumption_ul": usage[key],
                        "round2_reserve_ul": reserve, "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": corrected_mass(key, liquid["ligand_stock_mM"] * prepare * float(row["molecular_weight_g_mol"]) / 1e6),
                        "source_slot": row["source_slot"], "source_well": row["source_well"],
                        "on_deck_ul": math.ceil((usage[key] + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["tube_max_fill_ul"],
                        "capacity_ok": usage[key] + dead <= config["stock_preparation"]["tube_max_fill_ul"]})
    common = [("substrate_stock", liquid["substrate_stock_solvent"], "substrate_stock_mM", "A1", n/liquid["substrate_stock_mM"]*1000),
              ("internal_standard", liquid["internal_standard_stock_solvent"], "internal_standard_stock_mM", "A8",
               internal_standard_amounts(config,n)[0]/liquid["internal_standard_stock_mM"]*1000),
              ("Pd", "toluene", "pd_stock_mM", "A2", n*c["pd_mol_percent"]/100/liquid["pd_stock_mM"]*1000),
              ("toluene", "toluene", None, "A3", c["reaction_volume_ul"]),
              ("workup", liquid["workup_composition"], "internal_standard_workup_mM", "A4", liquid["workup_ul"]),
              ("LC_diluent", liquid["lc_diluent_composition"], None, "A5", liquid["diluent_ul"])]
    for key, solvent, concentration, well, worst in common:
        # Conservatively allow single-channel splitting and surplus for every reserve well.
        count = math.ceil(worst / (single_capacity-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]))
        reserve = reserve_wells * (worst + count * config["pipetting"]["surplus_ul"])
        dead = config["stock_preparation"]["reservoir_dead_ul"]
        concentration_mM = liquid[concentration] if concentration else ""
        mw = c.get("pd_molecular_weight_g_mol") if key == "Pd" else c.get("substrate_molecular_weight_g_mol") if key == "substrate_stock" else liquid["internal_standard_molecular_weight_g_mol"] if key in ("workup","internal_standard") else None
        pool = reservoir_source_pools(config)[key]
        used = [well for well in pool if source_usage[(key,well)] > 0] or pool[:1]
        for i, source in enumerate(used):
            consumption = source_usage[(key,source)]
            reserved = reserve if i == 0 else 0
            prepare = math.ceil(((consumption+reserved)*margin+dead)/10)*10
            if key == "substrate_stock":
                prepare = max(prepare,finite(config["stock_preparation"].get("substrate_min_prepare_ul",0),"minimum substrate stock preparation",0))
            if key == "internal_standard":
                prepare = max(prepare,finite(config["stock_preparation"].get("internal_standard_min_prepare_ul",0),"minimum IS stock preparation",0))
            records.append({"reagent": key, "name": key, "solvent": solvent, "stock_mM": concentration_mM,
                        "protocol_consumption_ul": consumption, "round2_reserve_ul": reserved,
                        "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": corrected_mass(key, concentration_mM * prepare * mw / 1e6) if mw else "",
                        "source_slot": 2, "source_well": source,
                        "on_deck_ul": math.ceil((consumption + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["reservoir_max_fill_ul"],
                        "capacity_ok": consumption + dead <= config["stock_preparation"]["reservoir_max_fill_ul"]})
    for record in records:
        record["storage_container"] = config["stock_preparation"].get("substrate_storage_container", "") if record["reagent"] == "substrate_stock" else "Capped compatible glass stock vial; ordinary plastic source-tube rack"
        if record["reagent"] == "internal_standard":
            record["name"] = config["analytics"]["internal_standard"] + " internal standard; add AFTER DCM evaporation"
    return records


def tip_budget(operations):
    count = defaultdict(int)
    for op in operations:
        stage = "dose" if op["stage"] in ("substrate", "assembly", "internal_standard") else "workup"
        if not op.get("retained_tip_from_previous"):
            count[f"{stage}_{op['pipette']}"] += op["channels"]
    return dict(count)


def workup_timing(config, operations):
    """Calculate pumping/waits from emitted transfers, excluding unmeasured motion and staff time.

    Eight-channel flow is per channel: simultaneous channels do not multiply elapsed time.
    The calculation follows RUNTIME's prewet, air-gap and settling commands exactly.
    """
    p = config["pipetting"]
    stages = {name: {"transfers": 0, "tip_pickups": 0, "pump_seconds": 0.0,
                     "programmed_wait_seconds": 0.0} for name in ("workup", "dilution", "sampling")}
    for op in operations:
        if op["stage"] not in stages:
            continue
        sampling = op["stage"] == "sampling"
        fresh = not op["retained_tip_from_previous"]
        if sampling:
            aspirate = p[op["pipette"]+"_aspirate_ul_s"]*p["sample_flow_rate_multiplier"]
            dispense = p[op["pipette"]+"_dispense_ul_s"]*p["sample_flow_rate_multiplier"]
            aspiration_wait = dispense_wait = p["sample_pause_seconds"]
            cycles = p["sample_prewet_cycles"] if fresh else 0
        else:
            aspirate, dispense = p["workup_aspirate_ul_s"], p["workup_dispense_ul_s"]
            aspiration_wait, dispense_wait = p["post_aspirate_seconds"], p["post_dispense_seconds"]
            cycles = p["prewet_cycles"] if fresh else 0
        air_flow = aspirate*(p["sample_air_gap_rate"] if sampling else 1)
        pump = (op["aspirated_ul_per_channel"]/aspirate
                + (op["volume_ul_per_channel"]+p["air_gap_ul"])/dispense
                + p["air_gap_ul"]/air_flow
                + cycles*op["aspirated_ul_per_channel"]*(1/aspirate+1/dispense))
        wait = (aspiration_wait+dispense_wait)*(1+cycles if sampling else 1)
        row = stages[op["stage"]]
        row["transfers"] += 1
        row["tip_pickups"] += int(fresh)
        row["pump_seconds"] += pump
        row["programmed_wait_seconds"] += wait
    samples = [op for op in operations if op["stage"] == "sampling"]
    sample_count = len({(op["lc_batch"], well) for op in samples for well in op["destination_wells"]})
    lc_plates = len({op["lc_batch"] for op in samples})
    for row in stages.values():
        row["calculated_minutes"] = (row["pump_seconds"]+row["programmed_wait_seconds"])/60
    liquid_minutes = sum(row["calculated_minutes"] for row in stages.values())
    shaking = 2+lc_plates*config["liquids"]["lc_mix_minutes"] if samples else 0
    return {"sample_count": sample_count, "lc_plates": lc_plates, "stages": stages,
            "pump_and_programmed_wait_minutes": liquid_minutes, "shaking_minutes": shaking,
            "calculated_subtotal_minutes": liquid_minutes+shaking,
            "tip_pickup_events": sum(row["tip_pickups"] for row in stages.values()),
            "individual_screw_cap_actions": 4*sample_count,
            "manual_workup_block_and_lc_moves": 2+2*lc_plates if samples else 0,
            "physical_run_measured": False,
            "excluded": ["gantry travel and vertical motion", "tip pickup/drop motion and rack changes",
                         "module ramp/latch time and residual cooling", "all staff pauses, screw caps, plate moves/sealing and LC loading"],
            "interpretation": "Calculated pumping, programmed waits and shaking only; not a measured complete workup duration. Do not replace the full handling allowance with this subtotal."}


def schedule(config):
    t = config["timing"]
    counts = [config["design"]["round1_total"], config["design"]["round2_total"]]
    reaction = 2 * config["chemistry"]["reaction_minutes"]
    extra = t["additional_injections"]
    parallel = t.get("calibration_injections_during_round1_reaction", 0)
    if type(extra) is not int or type(parallel) is not int or extra < 0:
        raise ValueError("Injection counts must be nonnegative integers")
    injections = sum(counts) + extra
    cycle = finite(t["injection_cycle_minutes"], "full injection cycle time", 0.00001)
    if not 0 <= parallel <= t["additional_injections"] or parallel*cycle > config["chemistry"]["reaction_minutes"]:
        raise ValueError("Calibration overlap exceeds available first-reaction window")
    analysis = (injections-parallel) * cycle
    overhead = sum(finite(t[key], key, 0) for key in ["dosing_total_minutes", "evaporation_total_minutes",
                 "heat_ramp_total_minutes", "cooling_total_minutes", "workup_total_minutes",
                 "decision_minutes", "other_minutes"])
    if t["heat_ramp_total_minutes"] < 2*config["chemistry"].get("thermal_equilibration_minutes", 0):
        raise ValueError("Heating overhead omits the configured equilibration for both rounds")
    finite(t["deadline_minutes"], "competition deadline", 0.00001)
    total = reaction + analysis + overhead
    overlap=finite(t.get("staged_lc_overlap_minutes",0),"staged LC overlap",0)
    batch=config["robot"].get("lc_batch_size",24)
    allocation=t.get("staged_lc_overlap_minutes_by_round",{"1":overlap,"2":0})
    if abs(sum(allocation.values())-overlap)>1e-6:
        raise ValueError("Staged LC timing allocations do not sum to the planned overlap")
    for index,count in enumerate(counts,1):
        hidden=finite(allocation[str(index)],"LC overlap allocation",0)
        available=((count-1)//batch)*batch*cycle
        if hidden>available:
            raise ValueError("Staged LC overlap exceeds its preceding injection windows")
    lc_plates = [math.ceil(count/batch) for count in counts]
    minimum_shaking = 2*2 + sum(lc_plates)*config["liquids"]["lc_mix_minutes"]
    if t["workup_total_minutes"] < minimum_shaking:
        raise ValueError("Workup budget omits reaction-extract and LC-plate shaking holds")
    planned=total-overlap
    operating_budget = {
        "target_total_minutes": t["deadline_minutes"],
        "reaction_minutes": reaction,
        "lc_minutes_outside_reaction_holds": analysis,
        "handling_decision_and_contingency_cap_minutes": t["deadline_minutes"]-reaction-analysis,
        "calibration_minutes_parallel_to_round1_hold": parallel*cycle,
        "fixed_tasks_fit_window": reaction+analysis <= t["deadline_minutes"],
        "status": "Target allocation; complete physical timing has not been validated",
        "interpretation": "Remaining time is a cap for ALL dosing, evaporation, heating/cooling, workups, manual handling, decisions, final analysis and contingency. It is not an estimate of those tasks or evidence that they fit."
    }
    return {"reaction_minutes": reaction, "lc_minutes": analysis, "overhead_minutes": overhead,
            "injections": injections, "minimum_reaction_plus_lc_minutes": reaction + analysis,
            "calibration_minutes_hidden_in_reaction": parallel*cycle,
            "serial_total_minutes": total, "deadline_minutes": t["deadline_minutes"],
            "staged_lc_overlap_minutes":overlap,"planned_total_minutes":planned,
            "remaining_minutes": t["deadline_minutes"]-planned,
            "fits_serial_estimate": total <= t["deadline_minutes"],
            "fits_planned_estimate":planned<=t["deadline_minutes"],
            "lc_plates_by_round":lc_plates,"manual_lc_plate_moves":2*sum(lc_plates),
            "minimum_workup_shaking_minutes":minimum_shaking,
            "operating_budget":operating_budget,
            "scenario_status":"Unmeasured handling-allowance scenario; not a validated completion-time forecast",
            "assumptions": "Full injection cycle. All R1 measurements required before decision. One LC plate per round gives no within-round preparation/injection overlap. The target budget does not replace measured handling allowances. Workup includes both extract and LC shaking, moves and manual caps."}


def schedule_scenarios(config, cycles=(1.7, 2, 3, 5, 6)):
    """Method durations are provisional full-cycle scenarios until HTE measures overhead."""
    import copy
    scenarios = []
    for cycle in cycles:
        scenario = copy.deepcopy(config)
        scenario["timing"]["injection_cycle_minutes"] = cycle
        scenarios.append({"assumed_full_cycle_minutes": cycle, **schedule(scenario)})
    return scenarios
