# Generated, self-contained. Keep this file with its dosing and deck-load CSVs.
STAGE = 'workup'
DEMO = True
CONFIG = {'demo': True, 'chemistry': {'substrate': 'pyridine-2-sulfonyl fluoride / PyFluor', 'substrate_smiles': 'FS(C1=NC=CC=C1)(=O)=O', 'product': '2-fluoropyridine', 'product_smiles': 'FC1=NC=CC=C1', 'substrate_molecular_weight_g_mol': 161.16, 'substrate_molarity_M': 0.1, 'reaction_volume_ul': 250, 'ligand_a_mol_percent': 6, 'ligand_b_mol_percent': 6, 'pd_mol_percent': 12, 'pd_identity': 'Pd(COD)(DQ), CAS 86228-59-3, one Pd atom per complex', 'pd_molecular_weight_g_mol': 378.8, 'temperature_C': 95, 'reaction_minutes': 240, 'thermal_equilibration_minutes': 0, 'rpm': 500, 'atmosphere': 'air; ligand stocks prepared in glovebox', 'preloaded_internal_standard': {'identity': 'naphthalene', 'smiles': 'c1ccc2ccccc2c1', 'mol_percent_relative_to_substrate': 1, 'addition_stage': 'substrate_stock'}, 'additives': [], 'scale_status': 'Provisional 250 uL scale for larger glass vials; 1 M substrate in toluene reported soluble by user; exact vial geometry/heating and 20/40 mM catalyst stocks pending HTEL validation'}, 'design': {'round1_total': 60, 'round2_total': 10, 'round1_controls': [{'kind': 'single', 'ligand_a': 'L17', 'ligand_b': '', 'pair_id': ''}], 'round2_controls': [], 'objective': 'calibrated product yield; conversion retained as diagnostic', 'consensus_weight_llm': 0.5, 'require_all_ligands_in_round1_pairs': True, 'minimum_llm_percentile': 0.25, 'exploration_backend': 'SYNTHETIC_fingerprint_fixture', 'require_lm_embeddings': False, 'seed': 20261009, 'round2_predosed': True, 'excluded_ligands': [{'ligand_id': 'L07', 'cas': '224311-55-1', 'reason': 'AdJohnPhos delivery delayed; excluded per user, 59 pairs + 1 reference then 10 pairs'}]}, 'liquids': {'substrate_stock_mM': 1000, 'ligand_stock_mM': 20, 'pd_stock_mM': 40, 'workup_ul': 250, 'aliquot_ul': 20, 'diluent_ul': 180, 'workup_composition': '1:1 water/acetonitrile, 1% v/v formic acid; NO naphthalene', 'mix_rpm': 500, 'naphthalene_addition_stage': 'substrate_stock', 'naphthalene_substrate_stock_mM': 10, 'naphthalene_workup_mM': 0, 'naphthalene_molecular_weight_g_mol': 128.17, 'lc_diluent_composition': '1:1 water/acetonitrile, 1% v/v formic acid; NO naphthalene', 'substrate_stock_solvent': 'toluene'}, 'robot': {'p300': 'p300_multi_gen2', 'heater_slot': 10, 'reaction_labware': 'nest_96_wellplate_2ml_deep', 'reaction_definition_path': None, 'reaction_working_volume_ul': 1000, 'lc_labware': 'nest_96_wellplate_2ml_deep', 'lc_definition_path': None, 'lc_working_volume_ul': 2000, 'heater_adapter': 'opentrons_96_deep_well_adapter', 'reservoir_working_volume_ul': 11900, 'single': 'p300_single_gen2', 'pipette_setup_status': 'Proposed p300 single + p300 multi for 25-250 uL transfers; confirm installed mounts with HTE'}, 'pipetting': {'aspirate_height_mm': 1.5, 'dispense_above_top_mm': 2, 'surplus_ul': 1, 'air_gap_ul': 2, 'minimum_p20_ul': 2, 'prewet_cycles': 2, 'post_aspirate_seconds': 0.5, 'post_dispense_seconds': 0.5, 'p20_aspirate_ul_s': 4, 'p20_dispense_ul_s': 8, 'p300_aspirate_ul_s': 15, 'p300_dispense_ul_s': 30, 'reuse_tips': True, 'sample_prewet_cycles': 2, 'sample_aspirate_height_mm': 1.5, 'sample_flow_rate_multiplier': 0.5, 'sample_air_gap_rate': 0.1, 'sample_pause_seconds': 1, 'minimum_p300_single_ul': 20, 'p300_single_aspirate_ul_s': 15, 'p300_single_dispense_ul_s': 30}, 'stock_preparation': {'assay_fractions': {}, 'margin_factor': 1.5, 'tube_dead_ul': 100, 'reservoir_dead_ul': 1500, 'tube_max_fill_ul': 1400, 'reservoir_max_fill_ul': 11900, 'substrate_min_prepare_ul': 5000, 'substrate_storage_container': '10 mL glass vial with a toluene-compatible PTFE-faced closure; capped off-deck reserve', 'reservoir_source_pools': {'workup': ['A4', 'A6'], 'LC_diluent': ['A5', 'A7']}}, 'llm': {'model': 'claude-opus-4-8', 'repeats': 5, 'seed': 20261009, 'batch_size': 435, 'max_output_tokens': 10000, 'workers': 2, 'timeout_seconds': 240, 'budget_usd': 20, 'input_usd_per_million': 5, 'output_usd_per_million': 25, 'prompt_cache': {'enabled': True, 'ttl': '1h', 'read_multiplier': 0.1, 'write_5m_multiplier': 1.25, 'write_1h_multiplier': 2.0}, 'data_sharing_confirmed': True}, 'analytics': {'instrument_public_listing': 'HTEL confirmed Thermo Vanquish Horizon / ISQ-EM; quantitative UV channel to be selected with authentic standards', 'software_public_listing': 'HTEL confirmed Chromeleon and supplied a wide integrated-peak CSV; method ID absent from export', 'method_id': 'SYNTHETIC_2MIN', 'channel': 'SYNTHETIC_UV', 'calibration_mode': 'internal_standard', 'internal_standard': 'naphthalene', 'internal_standard_final_uM': 50, 'internal_standard_area_tolerance_fraction': 0.3, 'minimum_calibration_r2': 0.995, 'calibration_check_tolerance_fraction': 0.15, 'calibration_requirements': {'minimum_nonzero_levels': 5, 'require_zero_blank': True, 'minimum_independent_checks': 1}, 'quantification_limit_uM': {'substrate': 10, 'product': 10}, 'negative_concentration_tolerance_uM': 1, 'yield_tolerance_percent': 5, 'mass_balance_tolerance_fraction': 0.1, 'blank_max_product_umol': 0.01, 'maximum_rejected_fraction': 0, 'references': {'substrate': {'retention_time_min': 0.4, 'window_min': 0.05}, 'product': {'retention_time_min': 0.9, 'window_min': 0.05}, 'internal_standard': {'retention_time_min': 1.5, 'window_min': 0.05}}, 'column_mapping': None, 'export_sheet': None, 'missing_analyte_policy': 'censor', 'export_format': 'htel_chromeleon_wide', 'example_wavelengths_nm': {'UV_VIS_1': 253, 'UV_VIS_2': 270, 'UV_VIS_3': 300, 'UV_VIS_4': 370}, 'requested_method_duration_minutes': 1.7}, 'timing': {'deadline_minutes': 720, 'injection_cycle_minutes': 1.7, 'additional_injections': 14, 'calibration_injections_during_round1_reaction': 14, 'dosing_total_minutes': 30, 'evaporation_total_minutes': 0, 'heat_ramp_total_minutes': 12, 'cooling_total_minutes': 12, 'workup_total_minutes': 20, 'decision_minutes': 8, 'other_minutes': 5, 'cycle_status': 'User requests HTEL existing 1.7-minute method; injection-to-injection cycle and analyte separation remain unvalidated'}, 'validation': {'chemistry_confirmed': False, 'plate_adapter_seal_validated': False, 'solvent_pipetting_validated': False, 'homogeneous_sampling_validated': False, 'lc_calibration_validated': False, 'local_app_simulation_passed': False, 'noncontact_tip_reuse_validated': False, 'pre_reaction_internal_standard_validated': False, 'injection_cycle_validated': False, 'simultaneous_heating_capacity_validated': False, 'heating_validated': False, 'round2_predose_storage_validated': False}}
OPERATIONS = [{'stage': 'assembly', 'reagent': 'L02', 'source_slot': 1, 'source_well': 'B1', 'destination_slot': 3, 'destination_wells': ['G1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'L02', 'source_slot': 1, 'source_well': 'B1', 'destination_slot': 3, 'destination_wells': ['B2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L03', 'source_slot': 1, 'source_well': 'C1', 'destination_slot': 3, 'destination_wells': ['E1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'L03', 'source_slot': 1, 'source_well': 'C1', 'destination_slot': 3, 'destination_wells': ['H1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L04', 'source_slot': 1, 'source_well': 'D1', 'destination_slot': 3, 'destination_wells': ['F1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L08', 'source_slot': 1, 'source_well': 'D2', 'destination_slot': 3, 'destination_wells': ['D1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'L08', 'source_slot': 1, 'source_well': 'D2', 'destination_slot': 3, 'destination_wells': ['E1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L09', 'source_slot': 1, 'source_well': 'A3', 'destination_slot': 3, 'destination_wells': ['C1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L11', 'source_slot': 1, 'source_well': 'C3', 'destination_slot': 3, 'destination_wells': ['B1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L13', 'source_slot': 1, 'source_well': 'A4', 'destination_slot': 3, 'destination_wells': ['B2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L16', 'source_slot': 1, 'source_well': 'D4', 'destination_slot': 3, 'destination_wells': ['H1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L18', 'source_slot': 1, 'source_well': 'B5', 'destination_slot': 3, 'destination_wells': ['A1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L19', 'source_slot': 1, 'source_well': 'C5', 'destination_slot': 3, 'destination_wells': ['C1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L21', 'source_slot': 1, 'source_well': 'A6', 'destination_slot': 3, 'destination_wells': ['A2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L24', 'source_slot': 1, 'source_well': 'D6', 'destination_slot': 3, 'destination_wells': ['G1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'L24', 'source_slot': 1, 'source_well': 'D6', 'destination_slot': 3, 'destination_wells': ['A2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L27', 'source_slot': 4, 'source_well': 'C1', 'destination_slot': 3, 'destination_wells': ['A1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'L27', 'source_slot': 4, 'source_well': 'C1', 'destination_slot': 3, 'destination_wells': ['B1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L30', 'source_slot': 4, 'source_well': 'B2', 'destination_slot': 3, 'destination_wells': ['D1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'L31', 'source_slot': 4, 'source_well': 'C2', 'destination_slot': 3, 'destination_wells': ['F1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'Pd', 'source_slot': 2, 'source_well': 'A2', 'destination_slot': 3, 'destination_wells': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300', 'channels': 8, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'assembly', 'reagent': 'Pd', 'source_slot': 2, 'source_well': 'A2', 'destination_slot': 3, 'destination_wells': ['A2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 76.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'assembly', 'reagent': 'Pd', 'source_slot': 2, 'source_well': 'A2', 'destination_slot': 3, 'destination_wells': ['B2'], 'volume_ul_per_channel': 75.0, 'aspirated_ul_per_channel': 75.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'workup', 'reagent': 'workup', 'source_slot': 2, 'source_well': 'A4', 'destination_slot': 3, 'destination_wells': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'], 'volume_ul_per_channel': 250.0, 'aspirated_ul_per_channel': 251.0, 'pipette': 'p300', 'channels': 8, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'workup', 'reagent': 'workup', 'source_slot': 2, 'source_well': 'A4', 'destination_slot': 3, 'destination_wells': ['A2'], 'volume_ul_per_channel': 250.0, 'aspirated_ul_per_channel': 251.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'workup', 'reagent': 'workup', 'source_slot': 2, 'source_well': 'A4', 'destination_slot': 3, 'destination_wells': ['B2'], 'volume_ul_per_channel': 250.0, 'aspirated_ul_per_channel': 250.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'dilution', 'reagent': 'LC_diluent', 'source_slot': 2, 'source_well': 'A5', 'destination_slot': 6, 'destination_wells': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'], 'volume_ul_per_channel': 180.0, 'aspirated_ul_per_channel': 181.0, 'pipette': 'p300', 'channels': 8, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'dilution', 'reagent': 'LC_diluent', 'source_slot': 2, 'source_well': 'A5', 'destination_slot': 6, 'destination_wells': ['A2'], 'volume_ul_per_channel': 180.0, 'aspirated_ul_per_channel': 181.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': True}, {'stage': 'dilution', 'reagent': 'LC_diluent', 'source_slot': 2, 'source_well': 'A5', 'destination_slot': 6, 'destination_wells': ['B2'], 'volume_ul_per_channel': 180.0, 'aspirated_ul_per_channel': 180.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': True, 'retain_tip_for_next': False}, {'stage': 'sampling', 'reagent': 'reaction_samples', 'source_slot': 3, 'source_well': 'A1', 'destination_slot': 6, 'destination_wells': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'], 'volume_ul_per_channel': 20.0, 'aspirated_ul_per_channel': 21.0, 'pipette': 'p300', 'channels': 8, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'sampling', 'reagent': 'R2-009', 'source_slot': 3, 'source_well': 'A2', 'destination_slot': 6, 'destination_wells': ['A2'], 'volume_ul_per_channel': 20.0, 'aspirated_ul_per_channel': 21.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}, {'stage': 'sampling', 'reagent': 'R2-010', 'source_slot': 3, 'source_well': 'B2', 'destination_slot': 6, 'destination_wells': ['B2'], 'volume_ul_per_channel': 20.0, 'aspirated_ul_per_channel': 21.0, 'pipette': 'p300_single', 'channels': 1, 'retained_tip_from_previous': False, 'retain_tip_for_next': False}]
DEFINITIONS = {}

import time
from opentrons import protocol_api

metadata = {"protocolName": 'Dual-ligand HTE R2 workup',
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
