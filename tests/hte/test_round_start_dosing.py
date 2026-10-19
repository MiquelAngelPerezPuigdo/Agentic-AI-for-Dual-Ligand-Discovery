"""Reject stale predose settings and insufficient retained SM/IS preparation."""
from pathlib import Path

import pytest

from hte.demo import synthetic_config
from hte.inventory import campaign_inventory
from hte.io import read_csv
from hte.planning import validate_config
from hte.preparation import build_stock_preparation

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("legacy", [{"round2_predosed": False},
                                   {"round2_predose_mode": "robot_before_round1"}])
def test_old_predose_settings_cannot_mix_with_round_start_dosing(legacy):
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    config["design"].update(legacy)
    with pytest.raises(ValueError, match="discard old predose protocols"):
        validate_config(config)


@pytest.mark.parametrize("nominal_ul,accepted", [(1991, True), (1990, False)])
def test_actual_sm_charge_must_cover_working_fill_and_both_source_residuals(nominal_ul, accepted):
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT/"hte_inputs/ligands.csv", config)
    design = read_csv(ROOT/"campaigns/hackathon2026/round1_design.csv")
    planned = build_stock_preparation(config, inventory, design)
    charges = [dict(stock_id=r["stock_id"], actual_mass_mg=r["planned_mass_mg"],
                    assay_fraction=r["assay_fraction"])
               for r in planned["stocks"] if r["stock_id"] != "IS_MASTER"]
    source = next(r for r in charges if r["stock_id"] == "substrate_stock")
    source.update(assay_fraction=.98,
                  actual_mass_mg=nominal_ul*1000*config["chemistry"]["substrate_molecular_weight_g_mol"]/1e6/.98)
    if not accepted:
        with pytest.raises(ValueError, match="Insufficient robot-preparation source"):
            build_stock_preparation(config, inventory, design, charges)
        return
    actual = build_stock_preparation(config, inventory, design, charges)
    source = next(r for r in actual["stocks"] if r["stock_id"] == "substrate_stock")
    assert source["prepare_ul"] == pytest.approx(nominal_ul)
    assert source["remaining_bulk_ul"] == pytest.approx(100)
    final = {tuple(r["location"]): r["volume_ul"] for r in actual["expected_final_liquids"]}
    assert final[("working4", "D2")] == 1890
