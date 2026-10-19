from __future__ import annotations

import math
from collections import defaultdict

from .io import finite, well_name, wells, reaction_wells


VALIDATIONS = ["chemistry_confirmed", "plate_adapter_seal_validated", "solvent_pipetting_validated",
               "heating_validated", "lc_plate_workflow_validated",
               "lc_calibration_validated", "local_app_simulation_passed",
               "injection_cycle_validated", "simultaneous_heating_capacity_validated"]

COMMON_WELLS = {"substrate_stock":"A1", "toluene":"A3", "workup":"A4", "LC_diluent":"A5",
                "internal_standard":"A8"}


def single_pipette(config):
    model = config["robot"]["single"]
    if model not in ("p20_single_gen2", "p300_single_gen2"):
        raise ValueError("Choose a p20 or p300 single GEN2")
    return ("p20", 20) if model == "p20_single_gen2" else ("p300_single", 300)


def pd_source_pool(config):
    pool = config["stock_preparation"].get("pd_source_pool")
    if not isinstance(pool, list) or not pool:
        raise ValueError("Specify the Pd working-tube source pool")
    sources = []
    for entry in pool:
        if (not isinstance(entry, dict) or type(entry.get("slot")) is not int or entry.get("slot") not in (1, 4)
                or entry.get("well") not in {f"{r}{col}" for r in "ABCD" for col in range(1, 7)}):
            raise ValueError("Pd source tubes must be valid positions in racks 1/4")
        sources.append((entry["slot"], entry["well"]))
    sm = config["stock_preparation"]
    if len(set(sources)) != len(sources) or (sm["substrate_source_slot"], sm["substrate_source_well"]) in sources:
        raise ValueError("Pd source tubes must be distinct and separate from combined SM/IS")
    return sources


def _pd_campaign(config):
    """Prepare Pd directly in its retained working tubes and route both rounds once."""
    stock, chemistry, pipetting = config["stock_preparation"], config["chemistry"], config["pipetting"]
    if stock.get("pd_preparation_mode") != "direct_retained_working_tubes":
        raise ValueError("Pd must be prepared directly in its retained 2 mL working tubes")
    addresses = pd_source_pool(config)
    total_mass = finite(stock["fixed_stock_mass_mg"]["Pd"], "fixed Pd stock mass", 0.000001)
    concentration = finite(config["liquids"]["pd_stock_mM"], "Pd stock concentration", 0.000001)
    assay_fractions = stock.get("assay_fractions", {})
    records = []
    for entry, (slot, well) in zip(stock["pd_source_pool"], addresses):
        stock_id = entry.get("stock_id")
        if not isinstance(stock_id, str) or not stock_id.startswith("Pd_"):
            raise ValueError("Each direct Pd source needs its own Pd_ stock_id")
        mass = finite(entry.get("planned_mass_mg"), stock_id + " planned mass", 0.000001)
        assay = finite(assay_fractions.get(stock_id, assay_fractions.get("Pd", 1)), stock_id + " assay", 0.000001, 1)
        volume = mass * assay / chemistry["pd_molecular_weight_g_mol"] / concentration * 1e6
        if volume > stock["tube_max_fill_ul"] + 1e-8:
            raise ValueError("Direct Pd source exceeds working-tube capacity: " + stock_id)
        records.append({"stock_id": stock_id, "reagent": "Pd", "source_slot": slot, "source_well": well,
                        "planned_mass_mg": mass, "assay_fraction": assay, "prepare_ul": volume,
                        "round1_consumption_ul": 0.0, "round2_consumption_ul": 0.0})
    if len({r["stock_id"] for r in records}) != len(records):
        raise ValueError("Direct Pd stock IDs must be distinct")
    if not math.isclose(sum(r["planned_mass_mg"] for r in records), total_mass, rel_tol=0, abs_tol=1e-8):
        raise ValueError("Direct Pd source masses must sum to the fixed campaign Pd mass")
    available = finite(stock["available_mass_mg"]["Pd"], "Pd campaign mass limit", 0.000001)
    if total_mass > available + 1e-8:
        raise ValueError("Direct Pd sources exceed the campaign mass limit; preserve the scope reserve")
    per_well = chemistry["substrate_molarity_M"] * chemistry["reaction_volume_ul"] * chemistry["pd_mol_percent"] / 100 / concentration * 1000
    _, capacity = single_pipette(config)
    strokes = math.ceil(per_well / (capacity - pipetting["air_gap_ul"] - pipetting["surplus_ul"]))
    per_stroke = per_well / strokes
    remaining = [r["prepare_ul"] for r in records]
    index, routes = 0, {}
    for round_number in (1, 2):
        previous = None  # A fresh tip is mandatory at the second-round boundary.
        routes[round_number] = []
        for _ in range(config["design"][f"round{round_number}_total"] * strokes):
            while index < len(records):
                withdrawal = per_stroke + (0 if pipetting["reuse_tips"] and previous == index else pipetting["surplus_ul"])
                if remaining[index] - withdrawal >= stock["tube_dead_ul"] - 1e-8:
                    break
                index += 1
            if index == len(records):
                raise ValueError("Direct Pd sources cannot cover the full campaign at the configured assay and tip usage; do not use the scope reserve")
            remaining[index] -= withdrawal
            records[index][f"round{round_number}_consumption_ul"] += withdrawal
            routes[round_number].append({"source_index": index, "volume_ul_per_channel": per_stroke,
                                         "aspirated_ul_per_channel": withdrawal})
            previous = index
    for record, residual in zip(records, remaining):
        record["full_campaign_consumption_ul"] = record["round1_consumption_ul"] + record["round2_consumption_ul"]
        record["full_campaign_required_ul"] = record["full_campaign_consumption_ul"] + stock["tube_dead_ul"]
        record["remaining_after_campaign_ul"] = residual
    return records, routes


def pd_source_recipes(config, round_number=1):
    """All individually weighed Pd working sources, including retained R2 balances."""
    if round_number not in (1, 2):
        raise ValueError("Pd source recipes require round 1 or 2")
    records, _ = _pd_campaign(config)
    for record in records:
        record["current_round_consumption_ul"] = record[f"round{round_number}_consumption_ul"]
        record["remaining_before_round_ul"] = record["prepare_ul"] - (record["round1_consumption_ul"] if round_number == 2 else 0)
        record["remaining_after_round_ul"] = record["remaining_before_round_ul"] - record["current_round_consumption_ul"]
    return records


def _route_pd(config, operations, round_number=1):
    """Apply the campaign-wide route, retaining rather than refilling sources for R2."""
    records, routes = _pd_campaign(config)
    requested = [op for op in operations if op["reagent"] == "Pd"]
    planned = routes[round_number]
    if len(requested) != len(planned):
        raise ValueError("Pd dosing operation count differs from the configured round")
    for operation, route in zip(requested, planned):
        if operation["channels"] != 1 or not math.isclose(operation["volume_ul_per_channel"], route["volume_ul_per_channel"], abs_tol=1e-8):
            raise ValueError("Pd working tubes require the planned single-channel doses")
        source = records[route["source_index"]]
        operation.update(source_slot=source["source_slot"], source_well=source["source_well"], stock_id=source["stock_id"])


def pd_material_budget(config, operations, reserve_round2=True):
    stock = config["stock_preparation"]
    round_number = 1 if reserve_round2 else 2
    records = pd_source_recipes(config, round_number)
    usage = defaultdict(float)
    for op in operations:
        if op["reagent"] == "Pd":
            usage[(op["source_slot"], op["source_well"])] += op["aspirated_ul_per_channel"]
    expected = {(r["source_slot"], r["source_well"]): r["current_round_consumption_ul"] for r in records}
    if any(not math.isclose(usage[key], value, abs_tol=1e-8) for key, value in expected.items()) or set(usage) - set(expected):
        raise ValueError("Pd operation consumption differs from the campaign-wide retained-source plan")
    sources = []
    for record in records:
        used = record["current_round_consumption_ul"]
        if not reserve_round2 and used == 0:
            continue
        sources.append({**record, "slot": record["source_slot"], "well": record["source_well"],
                        "load_ul": used + stock["tube_dead_ul"],
                        "consumption_ul": used})
    volume = sum(r["prepare_ul"] for r in records)
    required = sum(r["full_campaign_required_ul"] for r in records)
    return {"weigh_mg": stock["fixed_stock_mass_mg"]["Pd"],
            "scope_reserved_mg": stock.get("scope_reserved_mass_mg", {}).get("Pd", 0),
            "assay_fraction": sum(r["planned_mass_mg"] * r["assay_fraction"] for r in records) / stock["fixed_stock_mass_mg"]["Pd"],
            "stock_mM": config["liquids"]["pd_stock_mM"], "make_to_final_ul": volume,
            "preparation_mode": "direct_retained_working_tubes", "new_pd_mass_this_round_mg": stock["fixed_stock_mass_mg"]["Pd"] if reserve_round2 else 0,
            "current_round_deck_ul": sum(s["load_ul"] for s in sources),
            "round2_reserved_deck_ul": sum(r["round2_consumption_ul"] + stock["tube_dead_ul"] for r in records if r["round2_consumption_ul"] > 0) if reserve_round2 else 0,
            "full_campaign_deck_ul": required, "full_campaign_consumption_ul": sum(r["full_campaign_consumption_ul"] for r in records),
            "bulk_transfer_reserve_ul": 0, "unallocated_bulk_ul": 0,
            "excess_above_required_dead_volume_ul": volume - required,
            "source_loads": sources, "all_source_recipes": records,
            "instruction": "Weigh the Pd campaign charge directly into its four labeled 2 mL working tubes once. Robot adds solvent in place; retain all tubes unchanged for both rounds. No Pd bulk stock, aliquoting or refill; preserve the 10 mg scope reserve."}


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
    if config.get("automation", {}).get("enabled"):
        required.append("robot_stock_preparation_validated")
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
        raise ValueError("Reaction IS stock requires positive stock IS and zero workup IS")
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
    if config.get("schema_version") != 5:
        raise ValueError("Use campaign schema_version 5: robotic stock preparation, standards and per-round substrate dosing")
    if live_scope not in ("all", "first_reaction"):
        raise ValueError("Unknown live validation scope")
    reservoir_source_pools(config)
    stock = config["stock_preparation"]
    caps = config["design"].get("round2_ligand_caps", {})
    if not isinstance(caps, dict) or any(type(limit) is not int or limit < 0 for limit in caps.values()):
        raise ValueError("Round-two ligand caps must be nonnegative integers")
    if config["robot"].get("ligand_source_labware") != "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap":
        raise ValueError("This source layout requires the configured 2 mL Eppendorf working tubes")
    finite(stock["tube_max_fill_ul"], "2 mL working-tube fill limit", 1, 1950)
    finite(stock["tube_dead_ul"], "working-tube dead volume", 0)
    pd_source_pool(config)
    fixed = finite(stock.get("fixed_stock_mass_mg", {}).get("Pd"), "fixed Pd stock mass", 0.000001)
    if fixed > finite(stock.get("available_mass_mg", {}).get("Pd"), "Pd campaign mass limit", 0.000001):
        raise ValueError("Pd stock exceeds the campaign mass limit; do not use the scope reserve")
    finite(stock.get("bulk_transfer_reserve_ul"), "bulk transfer reserve", 0)
    finite(config["pipetting"]["aspirate_height_mm"], "stock tube aspiration height", 0.1, 39)
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
    finite(c["rpm"], "sealed reaction shaking", 200, 3000)
    finite(liquid["mix_rpm"], "uncapped reaction workup shaking (750 rpm maximum)", 200, 750)
    if (liquid.get("substrate_stock_solvent") != "toluene" or liquid.get("substrate_evaporation_required") is not False
            or liquid.get("substrate_stock_contains_internal_standard") is not True):
        raise ValueError("This campaign requires retained toluene stock containing SM and mesitylene; no evaporation")
    if liquid["internal_standard_addition_stage"] != "reaction_stock":
        raise ValueError("Combined SM/IS stock requires reaction-stage mesitylene")
    expected_ratio = finite(c["preloaded_internal_standard"]["mol_percent_relative_to_substrate"], "reaction IS mol%", 0.000001)/100
    if not math.isclose(finite(liquid["internal_standard_stock_mM"], "combined stock IS", 0.000001)/finite(liquid["substrate_stock_mM"], "combined stock SM", 0.000001), expected_ratio):
        raise ValueError("Combined SM/IS concentrations do not match the required IS loading")
    if config["timing"]["evaporation_total_minutes"] != 0:
        raise ValueError("No evaporation time belongs in the retained-toluene workflow")
    if (config["design"].get("substrate_dosing_stage") != "each_round_start"
            or any(key in config["design"] for key in ("round2_predosed", "round2_predose_mode"))):
        raise ValueError("Use substrate_dosing_stage=each_round_start; discard old predose protocols and regenerate")
    if not isinstance(config["robot"].get("reaction_multichannel"), bool):
        raise ValueError("Specify reaction_multichannel explicitly from the actual rack geometry")
    single, capacity = single_pipette(config)
    for name in ("reuse_tips",):
        if not isinstance(config["pipetting"].get(name), bool):
            raise ValueError(f"{name} must be true or false")
    for round_number in (1, 2):
        count = config["design"][f"round{round_number}_total"]
        if type(count) is not int or not 1 <= count <= len(reaction_wells(config)):
            raise ValueError("Round counts exceed the configured reaction rack capacity")
    for name in ("substrate_stock_mM", "ligand_stock_mM", "pd_stock_mM", "workup_ul", "aliquot_ul", "diluent_ul"):
        finite(liquid[name], name, 0.00001)
    for fraction_key, acid_key in (("quench_acetonitrile_fraction", "workup_formic_acid_percent"),
                                   ("lc_diluent_acetonitrile_fraction", "lc_diluent_formic_acid_percent")):
        acn = finite(liquid[fraction_key], fraction_key, 0, 1)
        acid = finite(liquid[acid_key], acid_key, 0, 10)
        if acn + acid / 10 > 1 + 1e-12:
            raise ValueError(f"{fraction_key} and 10% aqueous formic-acid stock require negative water; reduce the solvent fractions")
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
    for name in ("catalyst_mix_cycles", "catalyst_mix_every_transfers"):
        if type(p.get(name)) is not int or not 1 <= p[name] <= 20:
            raise ValueError(name+" must be an integer from 1 to 20")
    finite(p.get("catalyst_mix_max_ul"), "catalyst mixing volume", 1, 297)
    batch=config["robot"].get("lc_batch_size",24)
    if type(batch) is not int or batch<8 or batch>96 or batch%8:
        raise ValueError("LC preparation batches must contain a positive multiple of eight wells")
    if config["robot"].get("lc_single_plate_per_round") and batch < max(config["design"][f"round{r}_total"] for r in (1, 2)):
        raise ValueError("This campaign requires one LC plate per round; splitting R1 is disabled")
    finite(liquid["lc_mix_rpm"], "uncovered LC plate shaking (750 rpm maximum)", 200, 750)
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
        if config["timing"].get("enforce_deadline", True) and not timing["fits_planned_estimate"]:
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
        total_sm_volume = n_substrate / stocks["substrate_stock_mM"] * 1000
        v_sm = total_sm_volume
        preloaded_is, workup_is, final_is = internal_standard_amounts(config, n_substrate)
        if config["analytics"]["calibration_mode"] == "internal_standard" and final_is <= 0:
            raise ValueError("Combined substrate/IS dosing does not add IS to a reaction blank; define a separate validated blank preparation")
        # The same SM/IS aliquot supplies retained reaction solvent in both rounds.
        v_is = 0
        v_tol = c["reaction_volume_ul"] - total_sm_volume - v_a - v_b - v_pd
        if v_tol < -1e-8:
            raise ValueError("Stocks are too dilute to fit in the final reaction volume")
        if v_tol > 1e-8 and config.get("automation", {}).get("enabled"):
            raise ValueError("Automated stock preparation does not load a separate reaction toluene source; use the validated no-top-up stock concentrations or revise the preparation workflow before dosing")
        if v_sm > config["robot"]["reaction_working_volume_ul"]:
            raise ValueError("Substrate-stock dosing volume exceeds reaction working volume")
        row = {**d, "well": well, "substrate_umol": n_substrate, "pd_umol": n_pd,
               "ligand_a_umol": n_a, "ligand_b_umol": n_b, "sm_stock_ul": v_sm,
               "substrate_predosed_umol": 0,
               "substrate_predosed_ul": 0,
               "substrate_solvent_retained_ul": total_sm_volume,
               "substrate_solvent_evaporated_ul": 0,
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
    occupied = {(int(row["source_slot"]), row["source_well"]) for row in inventory.values()}
    if occupied.intersection(pd_source_pool(config)):
        raise ValueError("Pd working source overlaps a ligand tube")
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
    for op in operations:
        if op["reagent"] == "substrate_stock":
            op.update(source_slot=config["stock_preparation"]["substrate_source_slot"],
                      source_well=config["stock_preparation"]["substrate_source_well"])
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
    _route_pd(config, operations, int(rows[0]["round"]))
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
    # Source-only recirculation uses no extra stock. Clamp every mix to the liquid
    # available ABOVE dead volume, including the last transfers and p20 splits.
    remaining, count = defaultdict(float), defaultdict(int)
    for op in operations:
        if op["stage"] == "assembly" and op["reagent"] in {*inventory, "Pd"}:
            key = (op["reagent"], op["source_slot"], op["source_well"])
            remaining[key] += op["aspirated_ul_per_channel"]
    dead = config["stock_preparation"]["tube_dead_ul"]
    remaining = {key:value+dead if key[0] == "Pd" else math.ceil((value+dead)/10)*10 for key,value in remaining.items()}
    for op in operations:
        op["source_mix_cycles"], op["source_mix_ul"] = 0, 0
        key = (op["reagent"], op["source_slot"], op["source_well"])
        if key not in remaining:
            continue
        if not op["retained_tip_from_previous"] or count[key] % p["catalyst_mix_every_transfers"] == 0:
            op["source_mix_cycles"] = p["catalyst_mix_cycles"]
            op["source_mix_ul"] = min(p["catalyst_mix_max_ul"], capacities[op["pipette"]], remaining[key]-dead)
            if op["source_mix_ul"] <= 0:
                raise ValueError("No usable liquid available for catalyst source mixing")
        count[key] += 1
        remaining[key] -= op["aspirated_ul_per_channel"]
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
        capped_pairs = min(pair_count, config["design"].get("round2_ligand_caps", {}).get(key, pair_count))
        single_volume = n * max(c["ligand_a_mol_percent"],c["ligand_b_mol_percent"])/100/liquid["ligand_stock_mM"]*1000
        reference_volume = sum(n*(c["ligand_a_mol_percent"]+c["ligand_b_mol_percent"])/100/liquid["ligand_stock_mM"]*1000
                               for control in config["design"]["round2_controls"]
                               if reserve_wells and control["kind"] == "single" and control["ligand_a"] == key)
        usable=single_capacity-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]
        reserve = capped_pairs*(single_volume+math.ceil(single_volume/usable)*config["pipetting"]["surplus_ul"])+reference_volume
        if reference_volume: reserve += math.ceil(reference_volume/usable)*config["pipetting"]["surplus_ul"]
        dead = config["stock_preparation"]["tube_dead_ul"]
        prepare = math.ceil(((usage[key] + reserve) * margin + dead) / 100) * 100
        mass = corrected_mass(key, liquid["ligand_stock_mM"] * prepare * float(row["molecular_weight_g_mol"]) / 1e6)
        available = config["stock_preparation"].get("available_mass_mg", {}).get(key)
        if available is not None and mass > finite(available, key+" available mass", 0):
            raise ValueError(f"{key} stock preparation exceeds available mass: {mass:.3f} > {available} mg")
        records.append({"reagent": key, "name": row["name"], "solvent": "toluene",
                        "stock_mM": liquid["ligand_stock_mM"], "protocol_consumption_ul": usage[key],
                        "round2_reserve_ul": reserve, "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": mass,
                        "source_slot": row["source_slot"], "source_well": row["source_well"],
                        "on_deck_ul": prepare if key in config.get("automation",{}).get("direct_stock_ids",[]) and reserve_round2 else math.ceil((usage[key] + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["tube_max_fill_ul"],
                        "capacity_ok": usage[key] + dead <= config["stock_preparation"]["tube_max_fill_ul"]})
    # SM uses approximately 10% extra, rounded up to practical 0.5 mL preparations.
    # Working-tube dead volume and discarded surplus fit inside that budget.
    sm_per_well = n/liquid["substrate_stock_mM"]*1000
    sm_nominal = sum(op["volume_ul_per_channel"]*op["channels"] for op in operations if op["stage"] == "substrate")
    sm_reserve_nominal = reserve_wells*sm_per_well
    usable=single_capacity-config["pipetting"]["air_gap_ul"]-config["pipetting"]["surplus_ul"]
    reserve_tips=(1 if config["pipetting"]["reuse_tips"] else reserve_wells*math.ceil(sm_per_well/usable)) if reserve_wells else 0
    sm_reserve=sm_reserve_nominal+reserve_tips*config["pipetting"]["surplus_ul"]
    if sm_nominal or sm_reserve:
        sm_prepare = math.ceil((sm_nominal+sm_reserve_nominal)*finite(config["stock_preparation"]["substrate_margin_factor"], "SM preparation margin", 1)/500)*500
        sm_dead = config["stock_preparation"]["tube_dead_ul"]
        # Include R2's rounded deck minimum so no tiny SM refill is requested.
        retained_minimum=math.ceil((sm_reserve+sm_dead)/10)*10 if reserve_wells else sm_dead
        sm_load = math.ceil((usage["substrate_stock"]+retained_minimum)/10)*10
        if reserve_round2 and config.get("automation",{}).get("enabled"):
            bulk_required=sm_load+config["pipetting"]["surplus_ul"]+config["automation"]["bulk_dead_ul"]
            sm_prepare=max(sm_prepare,math.ceil(bulk_required/500)*500)
        if sm_load>config["stock_preparation"]["tube_max_fill_ul"]:
            raise ValueError("Retained SM/IS working tube cannot cover both rounds")
        records.append({"reagent":"substrate_stock", "name":"Combined SM + mesitylene; retained toluene",
            "solvent":"toluene", "stock_mM":liquid["substrate_stock_mM"],
            "protocol_consumption_ul":usage["substrate_stock"], "round2_reserve_ul":sm_reserve,
            "dead_ul":sm_dead,"prepare_ul":sm_prepare if reserve_round2 else 0,
            "mass_mg":corrected_mass("substrate_stock",liquid["substrate_stock_mM"]*sm_prepare*c["substrate_molecular_weight_g_mol"]/1e6),
            "source_slot":config["stock_preparation"]["substrate_source_slot"],
            "source_well":config["stock_preparation"]["substrate_source_well"],
            "on_deck_ul":sm_load,"source_capacity_ul":config["stock_preparation"]["tube_max_fill_ul"],
            "capacity_ok":sm_load <= config["stock_preparation"]["tube_max_fill_ul"]})
    pd_budget = pd_material_budget(config, operations, reserve_round2)
    for source in pd_budget["source_loads"]:
        slot, well, used, load = source["slot"], source["well"], source["consumption_ul"], source["load_ul"]
        records.append({"reagent":"Pd", "stock_id": source["stock_id"], "name":"Pd(COD)(DQ); direct retained working tube", "solvent":"toluene",
            "stock_mM":liquid["pd_stock_mM"], "protocol_consumption_ul":used,
            "round2_reserve_ul":source["round2_consumption_ul"] if reserve_round2 else 0,
            "dead_ul":config["stock_preparation"]["tube_dead_ul"],
            "prepare_ul":source["prepare_ul"] if reserve_round2 else 0,
            "mass_mg":source["planned_mass_mg"] if reserve_round2 else 0,
            "source_slot":slot, "source_well":well, "on_deck_ul":load,
            "source_capacity_ul":config["stock_preparation"]["tube_max_fill_ul"],
            "capacity_ok":load <= config["stock_preparation"]["tube_max_fill_ul"],
            "full_campaign_required_ul":source["full_campaign_required_ul"],
            "expected_retained_ul":source["remaining_before_round_ul"],
            "preparation_action":"Weigh directly in original 2 mL working tube; robot adds solvent in place" if reserve_round2 else "RETAIN original Pd tube and residual stock; NO refill or new weighing"})
    common = [("toluene", "toluene", None, "A3", c["reaction_volume_ul"]),
              ("workup", liquid["workup_composition"], "internal_standard_workup_mM", "A4", liquid["workup_ul"]),
              ("LC_diluent", liquid["lc_diluent_composition"], None, "A5", liquid["diluent_ul"])]
    for key, solvent, concentration, well, worst in common:
        if usage[key] == 0 and (not reserve_wells or key == "toluene"):
            continue
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
            prepare = math.ceil(((consumption+reserved)*margin+dead)/1000)*1000
            records.append({"reagent": key, "name": key, "solvent": solvent, "stock_mM": concentration_mM,
                        "protocol_consumption_ul": consumption, "round2_reserve_ul": reserved,
                        "dead_ul": dead, "prepare_ul": prepare,
                        "mass_mg": corrected_mass(key, concentration_mM * prepare * mw / 1e6) if mw else "",
                        "source_slot": 2, "source_well": source,
                        "on_deck_ul": math.ceil((consumption + dead)/10)*10,
                        "source_capacity_ul": config["stock_preparation"]["reservoir_max_fill_ul"],
                        "capacity_ok": consumption + dead <= config["stock_preparation"]["reservoir_max_fill_ul"]})
    for record in records:
        key = record["reagent"]
        record.setdefault("stock_id", key)
        record.setdefault("full_campaign_required_ul", "")
        record.setdefault("expected_retained_ul", "")
        volume = record["prepare_ul"]
        container = ("4 mL capped glass vial" if volume <= 3000 else "8 mL capped glass vial" if volume <= 6000
                     else "20 mL capped glass vial" if volume <= 16000 else "250 mL compatible solvent bottle")
        record["storage_container"] = config["stock_preparation"]["substrate_storage_container"] if key == "substrate_stock" else container
        record.setdefault("preparation_action", "Prepare bulk before campaign; refill R2 from reserves")
        if key == "Pd":
            record["storage_container"] = "Original 2 mL working tube; retained across both rounds"
        record["internal_standard_mM"] = liquid["internal_standard_stock_mM"] if key == "substrate_stock" else ""
        record["internal_standard_mass_mg"] = corrected_mass("internal_standard",liquid["internal_standard_stock_mM"]*volume*liquid["internal_standard_molecular_weight_g_mol"]/1e6) if key == "substrate_stock" else ""
        if config.get("automation",{}).get("enabled"):
            if key in ("workup","LC_diluent"):
                record.update(storage_container="Slot 2 reservoir; robot prepares from raw solvents during hold",
                              preparation_action="NO manual premixing; use the raw-solvent loading CSV")
            elif key == "substrate_stock":
                record.update(storage_container="Original 2 mL SM/IS working tube; filled once and retained across both rounds",
                              preparation_action="Robot prepares one campaign stock and fills the working tube once; cap between rounds, no R2 refill")
            elif key == "Pd" or key in config["automation"]["direct_stock_ids"]:
                record.update(storage_container="Original 2 mL working tube; retained across both rounds",
                              preparation_action="Weigh into working tube once; robot adds solvent and mixes; DO NOT replace for R2")
            else:
                record.update(storage_container="Compatible bulk source container in labeled preparation carrier",
                              preparation_action="Robot prepares from weighed charge and fills working tubes; R2 uses existing bulk ONLY")
            if not reserve_round2:
                record["mass_mg"]=0
                record["preparation_action"]="RETAIN original Pd tube and residual stock; NO refill or new weighing" if key == "Pd" else "NO new weighing: robot refills from original stock; retain direct stocks"
                if key=="substrate_stock":record["preparation_action"]="RETAIN original SM/IS working tube; dose 25 uL per EMPTY R2 vial, no stock refill"
    return records


def tip_budget(operations):
    count = defaultdict(int)
    for op in operations:
        stage = "dose" if op["stage"] in ("substrate", "assembly", "internal_standard") else "workup"
        if not op.get("retained_tip_from_previous"):
            count[f"{stage}_{op['pipette']}"] += op["channels"]
    return dict(count)


def catalyst_mixing_timing(config, operations):
    p = config["pipetting"]
    events, seconds, replaced = 0, 0, 0
    for op in operations:
        cycles = op.get("source_mix_cycles", 0)
        if not cycles:
            continue
        events += 1
        inverse_flow = 1/p[op["pipette"]+"_aspirate_ul_s"]+1/p[op["pipette"]+"_dispense_ul_s"]
        seconds += cycles*(op["source_mix_ul"]*inverse_flow+p["post_aspirate_seconds"]+p["post_dispense_seconds"])
        if not op["retained_tip_from_previous"]:
            replaced += min(cycles, p["prewet_cycles"])*op["aspirated_ul_per_channel"]*inverse_flow
    return {"source_mix_events":events, "mix_pumping_and_wait_minutes":seconds/60,
            "replaced_tip_conditioning_minutes":replaced/60,
            "net_added_programmed_minutes":(seconds-replaced)/60,
            "stock_consumed_by_mixing_ul":0, "physical_duration_measured":False,
            "instruction":"Include source mixing within measured dosing times. This subtotal excludes motion and initial robot stock preparation."}


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
            "individual_screw_cap_actions": 2*sample_count,
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
    if config.get("automation",{}).get("prepare_optional_pilot"):
        extra+=7;parallel+=7
    injections = sum(counts) + extra
    cycle = finite(t["injection_cycle_minutes"], "full injection cycle time", 0.00001)
    if not 0 <= parallel <= extra or parallel*cycle > config["chemistry"]["reaction_minutes"]:
        raise ValueError("Calibration overlap exceeds available first-reaction window")
    analysis = (injections-parallel) * cycle
    overhead = sum(finite(t[key], key, 0) for key in ["dosing_total_minutes", "evaporation_total_minutes",
                 "heat_ramp_total_minutes", "cooling_total_minutes", "workup_total_minutes",
                 "decision_minutes", "other_minutes"])
    overhead += finite(t.get("stock_preparation_total_minutes",0), "robot stock preparation allowance", 0)
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
        "deadline_enforced":t.get("enforce_deadline",True),
        "non_reaction_allocation_minutes":t["deadline_minutes"]-reaction,
        "interpretation": "Eight hours of reaction holds leave an approximately four-hour non-reaction allocation, including LC. This is a planning target; physical duration is recorded and the target is advisory unless enforce_deadline is enabled."
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
