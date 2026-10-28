"""Independent campaign conservation checks for Pd prepared in retained small tubes."""
import copy
from collections import Counter
from pathlib import Path

import pytest

from hte.demo import synthetic_config
from hte.design import make_design
from hte.inventory import campaign_inventory, candidates
from hte.io import read_csv
from hte.planning import dosing_rows, transfer_operations
from hte.preparation import build_refill, build_stock_preparation


ROOT = Path(__file__).resolve().parents[2]
PD_LOCATIONS = {("working4", well) for well in ("A3", "B3", "C3", "A4")}


@pytest.fixture
def pd_campaign():
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config)
    first = read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv")
    tested = {row["pair_id"] for row in first}
    remaining = [pair for pair in candidates(inventory) if pair["pair_id"] not in tested]
    scores = [dict(pair_id=pair["pair_id"], mean_score=50, score_sd=0, scoring_calls=5)
              for pair in remaining]
    second = make_design(config, inventory, remaining, scores, [], 2, history=first)
    return config, inventory, first, second


def weighed_charges(preparation, assay=0.98):
    return [dict(stock_id=row["stock_id"], actual_mass_mg=row["planned_mass_mg"],
                 assay_fraction=assay if row["reagent"] == "Pd" else row["assay_fraction"])
            for row in preparation["stocks"] if row["stock_id"] != "IS_MASTER"]


def test_four_pd_sources_are_prepared_in_place_without_a_bulk_transfer(pd_campaign):
    config, inventory, first, _ = pd_campaign
    plan = build_stock_preparation(config, inventory, first)
    records = [row for row in plan["stocks"] if row["reagent"] == "Pd"]
    assert len(records) == 4
    assert sum(row["planned_mass_mg"] for row in records) == pytest.approx(90)
    assert sorted(row["planned_mass_mg"] for row in records) == [21.6, 22.8, 22.8, 22.8]
    assert all(row["kind"] == "direct" for row in records)
    assert all(not row.get("carrier_id", "").startswith("BULK") for row in records)
    pd_additions = [step for step in plan["steps"] if step["type"] == "transfer"
                    and tuple(step["target"]) in PD_LOCATIONS]
    assert {tuple(step["target"]) for step in pd_additions} == PD_LOCATIONS
    assert all(step["source"][0] == "raw" and step["label"] == "toluene"
               for step in pd_additions)
    assert all(row["prepare_ul"] <= 1950 for row in records)


@pytest.mark.parametrize("assay", [1.0, 0.98, 0.97])
def test_each_retained_pd_tube_covers_both_rounds_and_keeps_100_ul(pd_campaign, assay):
    config, inventory, first, second = pd_campaign
    config["stock_preparation"]["assay_fractions"]["Pd"] = assay
    planned = build_stock_preparation(config, inventory, first)
    preparation = build_stock_preparation(config, inventory, first, weighed_charges(planned, assay))
    remaining = {tuple(row["location"]): row["volume_ul"]
                 for row in preparation["expected_final_liquids"]
                 if tuple(row["location"]) in PD_LOCATIONS}
    assert len(remaining) == 4
    assert sum(remaining.values()) == pytest.approx(90 * assay / 378.8 / 40 * 1e6)
    expected_counts = [Counter({"A3": 18, "B3": 18, "C3": 12}),
                       Counter({"C3": 6, "A4": 17})]
    nominal_delivered, actual_withdrawn = 0, 0
    all_doses = []
    for design, expected in zip((first, second), expected_counts):
        doses = dosing_rows(config, inventory, design)
        all_doses.append(doses)
        pd_ops = [op for op in transfer_operations(config, inventory, doses) if op["reagent"] == "Pd"]
        assert Counter(op["source_well"] for op in pd_ops) == expected
        for op in pd_ops:
            assert op["source_slot"] == 4
            assert op["volume_ul_per_channel"] == 75
            location = ("working4", op["source_well"])
            # Every operation, including source mixing, must leave its planned dead volume.
            if op["source_mix_cycles"]:
                assert op["source_mix_ul"] <= remaining[location] - 100 + 1e-7
            remaining[location] -= op["aspirated_ul_per_channel"]
            assert remaining[location] >= 100 - 1e-7
            nominal_delivered += op["volume_ul_per_channel"]
            actual_withdrawn += op["aspirated_ul_per_channel"]
    assert nominal_delivered == 71 * 75
    assert actual_withdrawn == 5330  # Five source-dedicated tips, each retaining 1 µL.
    refill = build_refill(config, inventory, second, all_doses[0], preparation)
    assert not any(step["type"] == "transfer" and tuple(step["target"]) in PD_LOCATIONS
                   for step in refill["steps"])


def test_actual_small_underweighing_is_accepted_without_inventing_material(pd_campaign):
    config, inventory, first, _ = pd_campaign
    planned = build_stock_preparation(config, inventory, first)
    charges = weighed_charges(planned)
    pd_ids = {row["stock_id"] for row in planned["stocks"] if row["reagent"] == "Pd"}
    for row in charges:
        if row["stock_id"] in pd_ids:
            row["actual_mass_mg"] -= 0.05
    actual = build_stock_preparation(config, inventory, first, charges)
    records = [row for row in actual["stocks"] if row["reagent"] == "Pd"]
    assert sum(row["mass_mg_used"] for row in records) == pytest.approx(89.8)
    assert sum(row["prepare_ul"] for row in records) == pytest.approx(89.8 * 0.98 / 378.8 / 40 * 1e6)


def test_aggregate_or_individual_pd_deficits_cannot_be_hidden(pd_campaign):
    config, inventory, first, _ = pd_campaign
    planned = build_stock_preparation(config, inventory, first)
    pd_records = [row for row in planned["stocks"] if row["reagent"] == "Pd"]
    charges = weighed_charges(planned)
    pd_ids = {row["stock_id"] for row in pd_records}
    excessive = copy.deepcopy(charges)
    next(row for row in excessive if row["stock_id"] in pd_ids)["actual_mass_mg"] += 0.1
    with pytest.raises(ValueError):
        build_stock_preparation(config, inventory, first, excessive)
    deficient = copy.deepcopy(charges)
    first_source = next(row["stock_id"] for row in pd_records if row["planned_mass_mg"] == 22.8)
    next(row for row in deficient if row["stock_id"] == first_source)["actual_mass_mg"] = 22.4
    with pytest.raises(ValueError):
        build_stock_preparation(config, inventory, first, deficient)
