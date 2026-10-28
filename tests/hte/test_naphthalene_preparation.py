"""Mass, solvent and release contracts for robot-prepared solid naphthalene."""
import copy
from pathlib import Path

import pytest

from hte.demo import synthetic_config
from hte.inventory import campaign_inventory
from hte.io import read_csv
from hte.preparation import (ANALYTICAL, Plan, build_stock_preparation,
                             calibration_recipes, export_stock_preparation, matrix)

ROOT = Path(__file__).resolve().parents[2]
IS_LOCATION = ("working1", "C2")


@pytest.fixture
def campaign():
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config)
    design = read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv")
    return config, inventory, design


def charges(plan, mass=60, assay=1):
    return [dict(stock_id=row["stock_id"],
                 actual_mass_mg=mass if row["stock_id"] == "IS_SOURCE" else row["planned_mass_mg"],
                 assay_fraction=assay if row["stock_id"] == "IS_SOURCE" else row["assay_fraction"])
            for row in plan["stocks"] if row["stock_id"] != "IS_MASTER"]


@pytest.mark.parametrize("mass,assay", [(60, 1), (60, .99), (59.7, .985)])
def test_weighed_source_and_both_uses_preserve_concentrations(campaign, mass, assay):
    config, inventory, design = campaign
    planned = build_stock_preparation(config, inventory, design)
    plan = build_stock_preparation(config, inventory, design, charges(planned, mass, assay))
    stocks = {row["stock_id"]: row for row in plan["stocks"]}
    source = stocks["IS_SOURCE"]
    assert source["prepare_ul"] == pytest.approx(mass * assay / 128.17 / 500 * 1e6)
    assert source["prepare_ul"] < 1950
    assert source["kind"] == "direct" and "carrier_id" not in source
    transfers = [step for step in plan["steps"] if step["type"] == "transfer"
                 and tuple(step["source"]) == IS_LOCATION]
    assert [step["volume_ul"] for step in transfers] == pytest.approx([500, 32])
    assert all(step["label"] == "naphthalene stock" for step in transfers)
    final = {tuple(row["location"]): row["volume_ul"] for row in plan["expected_final_liquids"]}
    assert final[IS_LOCATION] == pytest.approx(source["prepare_ul"] - 534)
    assert final[IS_LOCATION] >= 100
    assert 500 * 500 / stocks["substrate_stock"]["prepare_ul"] == pytest.approx(100)
    assert 32 * 500 / stocks["IS_MASTER"]["prepare_ul"] == pytest.approx(2)
    assert final[("analytical", ANALYTICAL["IS_WORK"])] == pytest.approx(1000)
    assert not any(tuple(row["location"]) == IS_LOCATION for row in plan["initial_liquids"])
    assert not any("naphthalene" in row["reagent"].lower() for row in plan["raw_loads"])
    mix_index = next(i for i, step in enumerate(plan["steps"])
                     if step["type"] == "mix" and tuple(step["location"]) == IS_LOCATION)
    observe_index = next(i for i, step in enumerate(plan["steps"])
                         if step["type"] == "pause" and "fully dissolved" in step["message"])
    first_use_index = next(i for i, step in enumerate(plan["steps"])
                          if step["type"] == "transfer" and tuple(step["source"]) == IS_LOCATION)
    assert mix_index < observe_index < first_use_index


def test_analytical_is_master_counts_stock_carrier_toluene_exactly(campaign):
    config, inventory, design = campaign
    plan = build_stock_preparation(config, inventory, design)
    master = next(row for row in plan["stocks"] if row["stock_id"] == "IS_MASTER")
    location = [master["carrier_id"], master["source_well"]]
    additions = [step for step in plan["steps"]
                 if step["type"] == "transfer" and step["target"] == location]
    volumes = {step["label"]: step["volume_ul"] for step in additions}
    assert volumes == pytest.approx({"naphthalene stock": 32, "toluene": 64 / 3,
                                    "ACN": 4016, "10% aqueous FA stock": 80,
                                    "water": 11552 / 3})
    assert sum(volumes.values()) == pytest.approx(8000)
    assert (volumes["naphthalene stock"] + volumes["toluene"]) / 8000 == pytest.approx(1 / 150)
    assert volumes["ACN"] / 8000 == pytest.approx(.502)
    assert volumes["10% aqueous FA stock"] * .1 / 8000 == pytest.approx(.001)
    mixes = [step for step in plan["steps"] if step["type"] == "mix" and step["location"] == location]
    assert len(mixes) == 1 and mixes[0]["channels"] == 1
    work = [step for step in plan["steps"] if step["type"] == "transfer"
            and step["target"] == ["analytical", ANALYTICAL["IS_WORK"]]]
    assert len(work) == 1 and work[0]["volume_ul"] == 1000 and work[0]["source"] == location
    for row in calibration_recipes(config):
        assert row["is_ul"] * 2 == pytest.approx(200 / 3)
        assert row["internal_standard_identity"] == "naphthalene"
        assert row["internal_standard_cas"] == "91-20-3"


@pytest.mark.parametrize("mass,assay,match", [(130, 1, "container capacity"),
                                           (30, 1, "Insufficient robot-preparation source"),
                                           (60, .5, "Insufficient robot-preparation source")])
def test_source_cannot_overfill_or_run_below_dead_volume(campaign, mass, assay, match):
    config, inventory, design = campaign
    planned = build_stock_preparation(config, inventory, design)
    with pytest.raises(ValueError, match=match):
        build_stock_preparation(config, inventory, design, charges(planned, mass, assay))


def test_loading_files_request_one_solid_is_charge_and_an_empty_master(campaign, tmp_path):
    config, inventory, design = campaign
    folder = export_stock_preparation(config, inventory, design, tmp_path / "preparation")
    template = read_csv(folder / "weighed_charges_template.csv")
    assert sum(row["stock_id"] == "IS_SOURCE" for row in template) == 1
    assert not any(row["stock_id"] == "IS_MASTER" for row in template)
    loading = {row["stock_id"]: row for row in read_csv(folder / "bulk_carriers.csv")}
    assert loading["IS_SOURCE"]["carrier_id"] == "WORKING RACK"
    assert loading["IS_SOURCE"]["slot"] == "1" and loading["IS_SOURCE"]["well"] == "C2"
    assert float(loading["IS_SOURCE"]["preloaded_mass_mg"]) == 60
    assert float(loading["IS_MASTER"]["preloaded_mass_mg"]) == 0
    assert loading["IS_MASTER"]["preload_action"].startswith("EMPTY:")
    assert loading["substrate_stock"]["preload_action"].startswith("Weigh SM ONLY;")
    source = (folder / "prepare_stocks.py").read_text()
    assert "weighed SOLID naphthalene" in source
    assert "neat mesitylene" not in source


@pytest.mark.parametrize("credit", [-1, float("nan"), float("inf"), 60])
def test_invalid_or_excess_carrier_credit_is_rejected_before_transfers(campaign, credit):
    config, *_ = campaign
    plan = Plan(config, large=True)
    target = ["BULK-TEST", "A1"]
    plan.initial_liquid(target, 100)
    with pytest.raises(ValueError):
        matrix(plan, target, 8000, {}, ["working4", "D3"], toluene_credit_ul=credit)
    assert not plan.steps


def test_carrier_credit_requires_delivered_liquid(campaign):
    config, *_ = campaign
    plan = Plan(config, large=True)
    with pytest.raises(ValueError, match="already delivered"):
        matrix(plan, ["BULK-TEST", "A1"], 8000, {}, ["working4", "D3"], toluene_credit_ul=32)
    assert not plan.steps


def test_source_configuration_cannot_reuse_neat_liquid_or_occupied_slot(campaign):
    config, inventory, design = campaign
    stale = copy.deepcopy(config)
    stale["automation"]["neat_is_density_g_ml"] = .864
    with pytest.raises(ValueError, match="obsolete neat-liquid"):
        build_stock_preparation(stale, inventory, design)
    occupied = copy.deepcopy(config)
    occupied["automation"]["internal_standard_source"].update(slot=4, well="D2")
    with pytest.raises(ValueError, match="overlaps"):
        build_stock_preparation(occupied, inventory, design)


@pytest.mark.parametrize("optional_pilot", [False, True])
def test_independent_component_ledger_reaches_every_final_calibration_well(campaign, optional_pilot):
    """Propagate solvent volumes and solid µmol through actual draws, including waste."""
    from collections import defaultdict
    from hte.preparation import build_hold_preparation
    from hte.planning import dosing_rows, transfer_operations

    config, inventory, design = campaign
    config["automation"]["prepare_optional_pilot"] = optional_pilot
    plan = build_stock_preparation(config, inventory, design)
    ledger = {}

    def contents(location):
        return ledger.setdefault(tuple(location), {"volume": 0.0, "amounts": defaultdict(float)})

    for row in plan["stocks"]:
        if row["stock_id"] == "IS_MASTER":
            continue  # Derived from the measured source; no manually supplied chemical.
        location = (["working" + str(row["source_slot"]), row["source_well"]]
                    if row["kind"] == "direct" else [row["carrier_id"], row["source_well"]])
        chemical = ("SM" if row["reagent"] == "substrate_stock" else
                    "P" if row["reagent"] == "product_standard" else
                    "IS" if row["reagent"] == "internal_standard" else row["reagent"])
        contents(location)["amounts"][chemical] += row["actual_mass_mg"] * row["assay_fraction"] / row["mw"] * 1000

    def execute(report):
        # Each phase explicitly loads a new raw reservoir, including its empty H1.
        for location in list(ledger):
            if location[0] == "raw":
                del ledger[location]
        raw = {("raw", row["well"]): row["reagent"] for row in report["raw_loads"]}
        for row in report["initial_liquids"]:
            location = tuple(row["location"])
            if location in raw:
                ledger[location] = {"volume": row["volume_ul"],
                                    "amounts": defaultdict(float, {raw[location]: row["volume_ul"]})}
            else:
                assert contents(location)["volume"] == pytest.approx(row["volume_ul"])
        for step in report["steps"]:
            if step["type"] != "transfer":
                continue
            source, target = contents(step["source"]), contents(step["target"])
            delivered = step["volume_ul"] * step["channels"]
            withdrawn = delivered + config["pipetting"]["surplus_ul"] * step["channels"]
            assert source["volume"] >= withdrawn
            for chemical, amount in list(source["amounts"].items()):
                per_ul = amount / source["volume"]
                target["amounts"][chemical] += delivered * per_ul
                source["amounts"][chemical] -= withdrawn * per_ul
            target["volume"] += delivered
            source["volume"] -= withdrawn
        for row in report["expected_final_liquids"]:
            assert contents(row["location"])["volume"] == pytest.approx(row["volume_ul"])

    execute(plan)
    combined = contents(["working4", "D2"])
    assert combined["amounts"]["SM"] / combined["volume"] * 1000 == pytest.approx(1000)
    assert combined["amounts"]["IS"] / combined["volume"] * 1000 == pytest.approx(100)
    operations = transfer_operations(config, inventory, dosing_rows(config, inventory, design))
    hold = build_hold_preparation(config, operations, 1, plan)
    execute(hold)
    recipes = hold["calibration_recipes"] + hold["pilot_recipes"]
    assert len(recipes) == (21 if optional_pilot else 14)
    for row in recipes:
        sample = contents(["cal_plate", row["well"]])
        assert sample["volume"] == pytest.approx(1000)
        assert sample["amounts"]["IS"] / sample["volume"] * 1e6 == pytest.approx(200 / 3)
        expected_sm = (row["concentration_uM"] if row["analyte"] == "substrate" else 0) if "analyte" in row else row["substrate_uM"]
        expected_p = (row["concentration_uM"] if row["analyte"] == "product" else 0) if "analyte" in row else row["product_uM"]
        assert sample["amounts"]["SM"] / sample["volume"] * 1e6 == pytest.approx(expected_sm)
        assert sample["amounts"]["P"] / sample["volume"] * 1e6 == pytest.approx(expected_p)
        for solvent, fraction in (("toluene", 1 / 150), ("ACN", .502), ("FA", .001),
                                  ("water", 1 - 1 / 150 - .502 - .001)):
            assert sample["amounts"][solvent] / sample["volume"] == pytest.approx(fraction)
