"""Four directly prepared Pd working stocks cover both rounds without refills."""
import copy
from pathlib import Path

import pytest

from hte.demo import synthetic_config
from hte.design import make_design
from hte.inventory import campaign_inventory, candidates
from hte.io import read_csv
from hte.planning import (catalyst_mixing_timing, dosing_rows, pd_material_budget,
                          stock_plan, transfer_operations, validate_config)
from hte.protocols import export

ROOT = Path(__file__).resolve().parents[2]


def campaign():
    c = synthetic_config(ROOT/"hte_inputs/campaign.json")
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", c)
    first = read_csv(ROOT/"campaigns/hackathon2026/round1_design.csv")
    tested = {r["pair_id"] for r in first}
    remaining = [p for p in candidates(inv) if p["pair_id"] not in tested]
    rank = [{"pair_id":p["pair_id"], "mean_score":50, "score_sd":0, "scoring_calls":5} for p in remaining]
    second = make_design(c, inv, remaining, rank, [], 2, history=first)
    return c, inv, first, second


@pytest.mark.parametrize("assay", [1, .98])
def test_same_ninety_mg_direct_stocks_cover_both_rounds_without_reweighing(assay):
    c, inv, first, second = campaign()
    c["stock_preparation"]["assay_fractions"]["Pd"] = assay
    plans, all_ops = [], []
    for design, reserve in ((first, True), (second, False)):
        rows = dosing_rows(c, inv, design)
        assert all(r["pd_umol"] == 3 and r["pd_ul"] == 75 and r["reaction_volume_ul"] == 250 for r in rows)
        ops = transfer_operations(c, inv, rows)
        all_ops += ops
        plans += [r for r in stock_plan(c, inv, ops, reserve) if r["reagent"] == "Pd"]
        budget = pd_material_budget(c, ops, reserve)
        assert budget["weigh_mg"] == 90 and budget["scope_reserved_mg"] == 10
        assert budget["make_to_final_ul"] == pytest.approx(90*assay/378.8/40*1e6)
        assert budget["full_campaign_consumption_ul"] == 5330
        assert budget["full_campaign_deck_ul"] == 5730
        assert budget["bulk_transfer_reserve_ul"] == 0 and budget["unallocated_bulk_ul"] == 0
        assert all(r["remaining_after_campaign_ul"] >= 100 for r in budget["all_source_recipes"])
    assert [r["on_deck_ul"] for r in plans] == [1451, 1451, 1001, 100, 551, 1376]
    assert [(int(r["source_slot"]), r["source_well"]) for r in plans] == [(4,"A3"),(4,"B3"),(4,"C3"),(4,"A4"),(4,"C3"),(4,"A4")]
    assert sum(r["mass_mg"] for r in plans) == 90
    assert [r["mass_mg"] for r in plans] == [22.8, 22.8, 22.8, 21.6, 0, 0]
    assert all("Original 2 mL working tube" in r["storage_container"] for r in plans)
    assert all("RETAIN" in r["preparation_action"] and "NO refill" in r["preparation_action"] for r in plans[4:])
    # 71 x 3 umol = 80.6844 mg active Pd reagent; source losses remain within 90 mg.
    assert sum(o["volume_ul_per_channel"] for o in all_ops if o["reagent"] == "Pd")*.04*378.8/1000 == pytest.approx(80.6844)


def test_insufficient_active_pd_or_mass_cannot_silently_take_scope_reserve():
    c, inv, first, _ = campaign()
    c["stock_preparation"]["assay_fractions"]["Pd"] = .95
    with pytest.raises(ValueError, match="do not use the scope reserve"):
        transfer_operations(c, inv, dosing_rows(c, inv, first))
    c["stock_preparation"]["available_mass_mg"]["Pd"] = 89
    with pytest.raises(ValueError, match="scope reserve"):
        validate_config(c)


@pytest.mark.parametrize("fault", ["duplicate", "substrate", "ligand", "too_few"])
def test_invalid_pd_sources_cannot_alias_other_material_or_overfill(fault):
    c, inv, first, _ = campaign()
    pool = c["stock_preparation"]["pd_source_pool"]
    if fault == "duplicate": pool.append(copy.deepcopy(pool[0]))
    if fault == "substrate": pool[0] = {"slot":4, "well":"D2"}
    if fault == "ligand": pool[0] = {"slot":1, "well":"A1"}
    if fault == "too_few": c["stock_preparation"]["pd_source_pool"] = pool[:1]
    with pytest.raises(ValueError):
        transfer_operations(c, inv, dosing_rows(c, inv, first))


@pytest.mark.parametrize("single,reuse", [("p300_single_gen2",True), ("p300_single_gen2",False), ("p20_single_gen2",True)])
def test_remixing_does_not_use_dead_volume_add_material_or_exceed_tip_capacity(single,reuse):
    c, inv, first, _ = campaign()
    c["robot"]["single"] = single
    c["pipetting"]["reuse_tips"] = reuse
    ops = transfer_operations(c, inv, dosing_rows(c, inv, first))
    stocks = stock_plan(c, inv, ops)
    remaining = {(r["reagent"],int(r["source_slot"]),r["source_well"]):r["on_deck_ul"] for r in stocks}
    mixes, periodic = 0, 0
    for o in ops:
        n, volume = o["source_mix_cycles"], o["source_mix_ul"]
        if n:
            mixes += 1
            periodic += o["retained_tip_from_previous"]
            assert o["stage"] == "assembly" and (o["reagent"] in inv or o["reagent"] == "Pd")
            key = (o["reagent"], o["source_slot"], o["source_well"])
            assert n == 2 and 0 < volume <= 100
            assert volume <= remaining[key]-100+1e-8
            assert volume+(1 if o["retained_tip_from_previous"] else 0) <= (20 if single.startswith("p20") else 300)
        key = (o["reagent"],o["source_slot"],o["source_well"])
        if key in remaining: remaining[key] -= o["aspirated_ul_per_channel"]*o["channels"]
    assert mixes > 0 and (periodic > 0 if reuse else periodic == 0)
    assert all(left >= 100-1e-8 for key,left in remaining.items() if key[0] in inv or key[0] == "Pd")
    assert catalyst_mixing_timing(c, ops)["stock_consumed_by_mixing_ul"] == 0


def test_actual_sdk_mix_commands_return_to_the_same_source_and_reconcile_time(tmp_path):
    from opentrons.simulate import simulate
    c, inv, first, _ = campaign()
    out = tmp_path/"r1"
    export(c, inv, first, out)
    ops = transfer_operations(c, inv, dosing_rows(c, inv, first))
    with (out/"dose_and_react.py").open() as stream: commands,_ = simulate(stream)
    mix_events = [i for i,cmd in enumerate(commands) if cmd["payload"].get("text", "").startswith("MIX OWN CATALYST SOURCE:")]
    expected = [o for o in ops if o["source_mix_cycles"]]
    assert len(mix_events) == len(expected)
    seconds = 0
    for start,op in zip(mix_events,expected):
        for cycle in range(2):
            aspirate, pause1, dispense, pause2 = [commands[start+1+4*cycle+j]["payload"] for j in range(4)]
            assert aspirate["volume"] == dispense["volume"] == op["source_mix_ul"]
            assert aspirate["location"] == dispense["location"]
            assert aspirate["location"].labware.as_well().well_name == op["source_well"]
            assert aspirate["location"].labware.first_parent() == str(op["source_slot"])
            assert "Air" not in aspirate["text"] and "Blow" not in dispense["text"]
            p = c["pipetting"]
            seconds += op["source_mix_ul"]*(1/p[op["pipette"]+"_aspirate_ul_s"]+1/p[op["pipette"]+"_dispense_ul_s"])
            seconds += pause1["seconds"]+pause2["seconds"]
    report = catalyst_mixing_timing(c, ops)
    assert report["mix_pumping_and_wait_minutes"] == pytest.approx(seconds/60)
    assert report["net_added_programmed_minutes"] > 0
    assert not report["physical_duration_measured"]
