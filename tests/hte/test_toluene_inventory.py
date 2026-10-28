"""Finite RockPhos, economical combined SM/IS, and worst-case working-source checks."""
from pathlib import Path

import pytest

from hte.analytical_stocks import preparation
from hte.demo import synthetic_config
from hte.design import make_design, validate_design
from hte.inventory import campaign_inventory, candidates
from hte.io import read_csv, read_json
from hte.planning import dosing_rows, stock_plan, transfer_operations
from hte.protocols import export

ROOT = Path(__file__).resolve().parents[2]


def inputs():
    c = synthetic_config(ROOT/"hte_inputs/campaign.json")
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", c)
    first = read_csv(ROOT/"campaigns/hackathon2026/round1_design.csv")
    tested = {r["pair_id"] for r in first}
    remaining = [p for p in candidates(inv) if p["pair_id"] not in tested]
    return c, inv, first, remaining


def preferred_second(c, inv, first, remaining, ligand):
    rank = [{"pair_id":p["pair_id"],"mean_score":100 if ligand in (p["ligand_a"],p["ligand_b"]) else 0,
             "score_sd":0,"scoring_calls":5} for p in remaining]
    return make_design(c, inv, remaining, rank, [], 2, history=first)


def test_rockphos_cap_is_hard_even_when_it_has_all_the_highest_scores():
    c, inv, first, remaining = inputs()
    second = preferred_second(c, inv, first, remaining, "L03")
    assert len(second)==23 and sum("L03" in (r["ligand_a"],r["ligand_b"]) for r in second)==4
    unused = next(p for p in remaining if "L03" in (p["ligand_a"],p["ligand_b"]) and p["pair_id"] not in {r["pair_id"] for r in second})
    target = next(r for r in second if r["kind"]=="pair" and "L03" not in (r["ligand_a"],r["ligand_b"]))
    target.update(unused)
    with pytest.raises(ValueError, match="ligand cap exceeded"):
        validate_design(c, inv, second, first)


def test_rockphos_stock_including_fifty_percent_margin_stays_below_ten_mg():
    c, inv, first, _ = inputs()
    c["stock_preparation"]["assay_fractions"]["L03"] = 0.97
    rows = dosing_rows(c, inv, first)
    stock = next(r for r in stock_plan(c, inv, transfer_operations(c,inv,rows)) if r["reagent"]=="L03")
    assert stock["prepare_ul"]==800 and stock["round2_reserve_ul"]==304
    assert stock["mass_mg"]==pytest.approx(7.499296/0.97) and stock["mass_mg"]<10
    c["stock_preparation"]["available_mass_mg"]["L03"] = 7
    with pytest.raises(ValueError, match="available mass"):
        stock_plan(c,inv,transfer_operations(c,inv,rows))


def test_combined_stock_has_practical_rounded_margin_and_covers_source_losses():
    c, inv, first, _ = inputs()
    rows=dosing_rows(c,inv,first);ops=transfer_operations(c,inv,rows)
    stock=next(r for r in stock_plan(c,inv,ops) if r["reagent"]=="substrate_stock")
    assert stock["prepare_ul"]==2500
    assert stock["mass_mg"]==pytest.approx(402.9)
    assert stock["internal_standard_mass_mg"]==pytest.approx(32.0425)
    assert stock["on_deck_ul"] + c["automation"]["bulk_dead_ul"] + c["pipetting"]["surplus_ul"] <= stock["prepare_ul"]
    assert stock["protocol_consumption_ul"] == 48*25+1
    assert stock["round2_reserve_ul"] >= 23*25+1
    assert stock["on_deck_ul"] == 1890
    assert (stock["source_slot"],stock["source_well"])==(4,"D2")
    assert not any(o["stage"]=="internal_standard" or o["reagent"]=="toluene" for o in ops)
    for row in rows:
        assert row["sm_stock_ul"]==25 and row["internal_standard_total_umol"]==2.5
        assert row["ligand_a_ul"]==row["ligand_b_ul"]==75 and row["toluene_ul"]==0


def test_worst_case_twenty_two_l17_pairs_and_reference_fit_two_ml_tube(tmp_path):
    from opentrons.simulate import simulate
    c,inv,first,remaining=inputs()
    second=preferred_second(c,inv,first,remaining,"L17")
    assert sum("L17" in (r["ligand_a"],r["ligand_b"]) for r in second)==23
    out=tmp_path/"r2";export(c,inv,second,out,history=dosing_rows(c,inv,first))
    load=next(r for r in read_csv(out/"deck_loads.csv") if r["reagent"]=="L17")
    assert float(load["load_ul"])==1910 and float(load["load_ul"])<1950
    with (out/"dose_and_react.py").open() as stream: commands,_=simulate(stream)
    text=[r["payload"].get("text","") for r in commands]
    assert not any("Evaporate" in t or "DCM" in t for t in text)
    sm=[i for i,t in enumerate(text) if t.startswith("substrate_stock:")]
    catalyst=[i for i,t in enumerate(text) if t.startswith("Pd:") or any(t.startswith(ligand+":") for ligand in inv)]
    assert len(sm)==23 and max(sm)<min(catalyst)
    assert not any(t.startswith("internal_standard:") for t in text)


def test_small_analytical_masters_have_independent_weighings_and_cover_optional_pilots():
    c,*_=inputs();rows=preparation(c)
    # At 10 mM, a practical >=5 mg charge rounds to 4 mL SM or 6 mL product.
    expected = {"substrate": (4000, 6.4464), "product": (6000, 5.8254)}
    for analyte in ("substrate","product"):
        masters=[r for r in rows if r["analyte"]==analyte and r["stock_mM"]==10]
        assert len(masters)==2
        assert {r["role"] for r in masters} == {"fit", "independent_check_and_optional_pilot"}
        assert all(r["prepare_ul"] == expected[analyte][0] for r in masters)
        assert all(r["mass_mg"] == pytest.approx(expected[analyte][1]) for r in masters)
        assert all(r["prepare_ul"] >= r["required_master_ul"]*1.1 for r in masters)
        assert sum(r["mass_mg"] for r in masters)<13
    c["stock_preparation"]["analytical_minimum_weigh_mg"] = 10
    larger = [r for r in preparation(c) if r["stock_mM"]==10]
    assert all(r["mass_mg"] >= 10 and "Axygen bulk reservoir" in r["storage_container"] for r in larger)
