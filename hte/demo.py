"""Synthetic offline acceptance exercise. No scientific predictions or paid API calls."""
from pathlib import Path

from .analytics import analyze, complete_export, validate_completion
from .design import consensus_select, make_design, pair_features
from .inventory import candidates, load_inventory
from .io import new_output, read_json, write_csv, write_json
from .planning import schedule
from .protocols import export


def fixtures(config, dosing):
    cal = []
    for name in ("substrate", "product"):
        for concentration in (0, 100, 500, 1000, 2500, 5000, 6000):
            cal.append({"analyte": name, "concentration_uM": concentration, "area": concentration*10,
                        "internal_standard_area": 10000, "internal_standard_concentration_uM": 50,
                        "method_id": "SYNTHETIC_2MIN", "channel": "SYNTHETIC_UV"})
    peaks = []
    for i, dose in enumerate(dosing):
        fraction = 0.2 if dose["kind"] == "single" else (i % 17)/20
        for name, concentration in (("product", fraction*5000), ("substrate", (1-fraction)*5000),
                                    ("internal_standard", 1000)):
            peaks.append({"sample_id": dose["sample_id"], "retention_time_min": config["analytics"]["references"][name]["retention_time_min"],
                          "area": concentration*10, "channel": "SYNTHETIC_UV", "method_id": "SYNTHETIC_2MIN", "qc_flag": "ok"})
    return cal, peaks


def run(output, inventory_path, config_path="hte_inputs/campaign.json"):
    out = new_output(output)
    config = read_json(config_path)
    config["demo"] = True
    config["design"]["require_lm_embeddings"] = False
    config["design"]["exploration_backend"] = "SYNTHETIC_fingerprint_fixture"
    config["robot"].update(reaction_labware="biorad_96_wellplate_200ul_pcr",
                           heater_adapter="opentrons_96_pcr_adapter")
    config["analytics"].update(method_id="SYNTHETIC_2MIN", channel="SYNTHETIC_UV",
        references={name: {"retention_time_min": rt, "window_min": 0.05}
                    for name, rt in [("substrate", 0.4), ("product", 0.9), ("internal_standard", 1.5)]},
        quantification_limit_uM={"substrate": 10, "product": 10}, missing_analyte_policy="censor")
    write_json(out/"campaign.json", config)
    inventory = load_inventory(inventory_path, confirmed=True)
    pairs = candidates(inventory)
    # Deterministic arbitrary scores are fixture data, not an LLM ranking.
    ranking = [{"pair_id": c["pair_id"], "mean_score": (i*37 % 101), "score_sd": 1, "scoring_calls": 5}
               for i, c in enumerate(pairs)]
    write_csv(out/"SYNTHETIC_ranking.csv", ranking)
    selection, trace = consensus_select(pairs, ranking, pair_features(inventory, pairs), 65)
    write_csv(out/"selection.csv", trace)
    design1 = make_design(config, inventory, pairs, ranking, selection, 1)
    write_csv(out/"round1_design.csv", design1)
    dose1 = export(config, inventory, design1, out/"round1")
    cal, peaks = fixtures(config, dose1)
    write_csv(out/"calibration.csv", cal)
    write_csv(out/"round1_peaks.csv", peaks)
    complete_export(config, out/"round1_peaks.csv", out/"round1/dosing.csv", out/"round1_peaks.ready.json")
    validate_completion(out/"round1_peaks.ready.json", out/"round1_peaks.csv", out/"round1/dosing.csv", config)
    results, report = analyze(config, dose1, peaks, cal, out/"analysis1")
    tested = {d["pair_id"] for d in design1 if d["kind"] == "pair"}
    remaining = [c for c in pairs if c["pair_id"] not in tested]
    ranking2 = [r for r in ranking if r["pair_id"] not in tested]
    design2 = make_design(config, inventory, remaining, ranking2, [], 2, history=design1)
    write_csv(out/"round2_design.csv", design2)
    dose2 = export(config, inventory, design2, out/"round2")
    _, peaks2 = fixtures(config, dose2)
    write_csv(out/"round2_peaks.csv", peaks2)
    complete_export(config, out/"round2_peaks.csv", out/"round2/dosing.csv", out/"round2_peaks.ready.json")
    _, report2 = analyze(config, dose2, peaks2, cal, out/"analysis2")
    write_json(out/"demo_report.json", {"synthetic_only": True, "api_calls": 0, "robot_execution_allowed": False,
        "round1_pairs": len(tested), "round1_reference_wells": 1, "round2_pairs": len(design2),
        "round1_qc_pass": report["batch_qc_pass"], "round2_qc_pass": report2["batch_qc_pass"],
        "no_pair_repeats": not tested.intersection(d["pair_id"] for d in design2),
        "round2_substrate_redosed": any(d["sm_DCM_ul"] != 0 for d in dose2), "schedule": schedule(config)})
    return out/"demo_report.json"
