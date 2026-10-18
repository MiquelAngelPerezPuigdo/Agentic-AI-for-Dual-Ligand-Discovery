"""Exercise preparation, dilution and refill as liquid operations, without real chemistry."""
import copy
from pathlib import Path

import pytest

from hte.demo import synthetic_config
from hte.design import make_design
from hte.inventory import campaign_inventory,candidates
from hte.io import read_csv,read_json
from hte.planning import dosing_rows,transfer_operations,validate_config
from hte.preparation import (ANALYTICAL,Plan,build_hold_preparation,build_refill,
    build_stock_preparation,calibration_recipes,export_stock_preparation,load_preparation)
from hte.protocols import export

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    directory=tmp_path_factory.mktemp("robot-prep")
    c=synthetic_config(ROOT/"hte_inputs/campaign.json")
    inv=campaign_inventory(ROOT/"hte_inputs/ligands.csv",c)
    first=read_csv(ROOT/"campaigns/hackathon2026/round1_design.csv")
    prep_dir=export_stock_preparation(c,inv,first,directory/"preparation")
    c["automation"]["preparation_manifest_path"]=str(prep_dir/"preparation_manifest.json")
    tested={r["pair_id"] for r in first};remaining=[p for p in candidates(inv) if p["pair_id"] not in tested]
    ranking=[dict(pair_id=p["pair_id"],mean_score=100 if "L17" in (p["ligand_a"],p["ligand_b"]) else 50,score_sd=0,scoring_calls=5) for p in remaining]
    second=make_design(c,inv,remaining,ranking,[],2,history=first)
    r1=dosing_rows(c,inv,first)
    export(c,inv,first,directory/"r1")
    export(c,inv,second,directory/"r2",history=r1)
    return directory,c,inv,first,second,r1


def test_preparation_preserves_all_volume_and_finite_reagent_budgets(setup):
    directory,c,inv,first,_,_=setup
    plan=read_json(directory/"preparation/preparation_manifest.json")
    initial=sum(r["volume_ul"] for r in plan["initial_liquids"])
    final=sum(r["volume_ul"] for r in plan["expected_final_liquids"])
    assert initial-final==pytest.approx(plan["discarded_surplus_ul"])
    stocks={r["stock_id"]:r for r in plan["stocks"]}
    assert stocks["Pd"]["actual_mass_mg"]==90 and stocks["L03"]["actual_mass_mg"]<10
    assert stocks["substrate_stock"]["prepare_ul"]==pytest.approx(2000)
    assert stocks["L03"]["kind"]=="direct"
    assert "solute displacement" in plan["concentration_basis"]
    assert not plan["actual_weighed_charges_supplied"] and not plan["physical_run_completed"]
    assert len([s for s in plan["steps"] if s["type"]=="transfer" and s["label"]=="neat mesitylene"])==2


def test_every_calibration_well_has_the_expected_analyte_and_constant_is(setup):
    directory,c,inv,first,_,_=setup
    plan=read_json(directory/"r1/hold_preparation_plan.json")
    final={tuple(r["location"]):r["volume_ul"] for r in plan["expected_final_liquids"]}
    recipes=calibration_recipes(c)
    assert len(recipes)==14 and len({r["well"] for r in recipes})==14
    for row in recipes:
        assert final[("cal_plate",row["well"])]==pytest.approx(1000)
        assert row["analyte_ul"]*row["stock_mM"]==pytest.approx(row["concentration_uM"])
        assert row["is_ul"]*2==pytest.approx(200/3)
        assert row["analyte_ul"]==0 or row["analyte_ul"]>=20
    for well in c['automation']['calibration_matrix_wells']:
        additions=[s for s in plan['steps'] if s['type']=='transfer' and s['target']==['reservoir',well]]
        assert sum(s['volume_ul'] for s in additions)==pytest.approx(9000)
        assert sum(s['volume_ul'] for s in additions if s['label']=='ACN')/9000==pytest.approx(.502)
        assert sum(s['volume_ul'] for s in additions if s['label']=='toluene')/9000==pytest.approx(1/150)
        assert sum(s['volume_ul']*.1 for s in additions if s['label']=='10% aqueous FA stock')/9000==pytest.approx(.001)
    assert sum(r["role"]=="check" for r in recipes)==2
    assert all(s["location"][0]!="cal_plate" or s["channels"]==1 for s in plan["steps"] if s["type"]=="mix")


def test_workup_fluids_are_built_from_raw_solvents_with_correct_acid_and_no_is(setup):
    directory,c,_,_,_,_=setup
    for number in (1,2):
        plan=read_json(directory/f"r{number}/hold_preparation_plan.json")
        for load in read_csv(directory/f"r{number}/deck_loads.csv"):
            if load["protocol"]!="workup":continue
            additions=[s for s in plan["steps"] if s["type"]=="transfer" and s["target"]==["reservoir",load["source_well"]]]
            total=sum(s["volume_ul"] for s in additions)
            acid=sum(s["volume_ul"]*.1 for s in additions if s["label"]=="10% FA stock")
            acn=sum(s["volume_ul"] for s in additions if s["label"]=="ACN")
            assert total==pytest.approx(float(load["load_ul"]))
            assert acid/total==pytest.approx(.0015 if load["reagent"]=="workup" else .001)
            assert acn/total==pytest.approx(.9 if load["reagent"]=="workup" else .5)
            assert not any("mesitylene" in s["label"] for s in additions)


def test_horizontal_raw_reservoir_never_uses_eight_channels(setup):
    directory,c,*_=setup
    for path in (directory/"preparation/preparation_manifest.json",directory/"r1/hold_preparation_plan.json",directory/"r2/hold_preparation_plan.json"):
        plan=read_json(path)
        for step in plan["steps"]:
            if step["type"]=="mix" and step["location"][0]=="raw":
                assert step["channels"]==1 and step["spread_mm"]==25
            if step["type"]=="transfer" and step["source"][0]=="raw":assert step["channels"]==1
    plan=Plan(c);plan.initial_liquid(["raw","H1"],5000)
    with pytest.raises(ValueError,match="NEVER"):plan.mix(["raw","H1"],8)


def test_r2_topups_use_original_stocks_and_keep_rockphos_in_place(setup):
    directory,c,inv,first,second,history=setup
    prep=read_json(directory/"preparation/preparation_manifest.json")
    plan=read_json(directory/"r2/refill_plan.json")
    transfers=[s for s in plan["steps"] if s["type"]=="transfer"]
    assert transfers and all("refill" in t["label"] for t in transfers)
    assert not any(t["target"]==["working1","C1"] for t in transfers)
    assert not any(t["target"]==["working4","D2"] for t in transfers)
    final={tuple(r["location"]):r["volume_ul"] for r in plan["expected_final_liquids"]}
    for load in read_csv(directory/"r2/deck_loads.csv"):
        if load["protocol"]=="dose_and_react":
            assert final[("working"+load["source_slot"],load["source_well"])]+1e-7>=float(load["load_ul"])
    bad=copy.deepcopy(history);bad[0]["pair_id"]="different history"
    with pytest.raises(ValueError,match="history differs"):build_refill(c,inv,second,bad,prep)


@pytest.mark.parametrize("fault",["too_much_pd","too_little_rockphos","missing","duplicate"])
def test_actual_weighed_charges_cannot_bypass_amount_or_coverage_guards(setup,fault):
    directory,c,inv,first,*_=setup
    base=read_json(directory/"preparation/preparation_manifest.json")
    charges=[dict(stock_id=r["stock_id"],actual_mass_mg=r["planned_mass_mg"],assay_fraction=r["assay_fraction"]) for r in base["stocks"] if r["stock_id"]!="IS_MASTER"]
    if fault=="too_much_pd":next(r for r in charges if r["stock_id"]=="Pd")["actual_mass_mg"]=90.1
    elif fault=="too_little_rockphos":next(r for r in charges if r["stock_id"]=="L03")["actual_mass_mg"]=1
    elif fault=="missing":charges.pop()
    else:charges.append(charges[0])
    with pytest.raises(ValueError):build_stock_preparation(c,inv,first,charges)


def test_stock_manifest_changes_and_preview_weights_cannot_release_live(setup):
    directory,c,inv,*_=setup
    path=directory/"preparation/preparation_manifest.json"
    with pytest.raises(ValueError,match="actual weighed"):load_preparation(c,inv,path,live=True)
    changed=copy.deepcopy(c);changed["demo"]=False;changed["liquids"]["pd_stock_mM"]=41
    with pytest.raises(ValueError,match="does not match"):load_preparation(changed,inv,path)


@pytest.mark.parametrize("stage",["preparation/prepare_stocks","r1/dose_and_react","r2/refill_stocks","r2/dose_and_react"])
def test_actual_sdk_executes_automated_preparation_and_holds(setup,stage):
    from opentrons.simulate import simulate
    directory,*_=setup
    with (directory/(stage+".py")).open() as stream:commands,_=simulate(stream)
    text=[c["payload"].get("text","") for c in commands]
    assert len(commands)>100
    if stage.endswith("dose_and_react"):
        start=next(i for i,t in enumerate(text) if "Setting Target Temperature" in t)
        finish=next(i for i,t in enumerate(text[start:],start) if t=="Deactivating Heater")
        assert any("ROBOT PREPARATION" in t for t in text[start:finish])
        assert not any("Moving Glass vial reaction block" in t for t in text[start:finish])
        if stage.startswith("r1"):
            assert any("ROBOT PREPARATION: CAL-SM" in t for t in text[start:finish])
            assert any("store them labeled" in t for t in text[:start])


def test_optional_known_mixtures_are_robotic_and_quantitative(setup):
    from hte.preparation import pilot_recipes
    _,c,inv,first,*_=setup
    c=copy.deepcopy(c);c['automation']['prepare_optional_pilot']=True
    prep=build_stock_preparation(c,inv,first)
    ops=transfer_operations(c,inv,dosing_rows(c,inv,first))
    hold=build_hold_preparation(c,ops,1,prep)
    final={tuple(r['location']):r['volume_ul'] for r in hold['expected_final_liquids']}
    assert len(hold['pilot_recipes'])==7
    from hte.planning import schedule
    assert schedule(c)["injections"]==71+14+len(hold["pilot_recipes"])
    for r in pilot_recipes(c):
        assert final[('cal_plate',r['well'])]==pytest.approx(1000)
        for prefix,key in (('SM','substrate_uM'),('P','product_uM')):
            assert r[prefix+'_ul']*r[prefix+'_stock_mM']==pytest.approx(r[key])
            assert r[prefix+'_ul']==0 or r[prefix+'_ul']>=20
        assert r['is_ul']*2==pytest.approx(200/3)
    assert all('CHECK' in r[p+'_source'] for r in pilot_recipes(c) for p in ('SM','P'))


def test_actual_mass_rounding_and_assay_still_cover_campaign(setup):
    directory,c,inv,first,*_=setup
    c=copy.deepcopy(c);c['stock_preparation']['analytical_minimum_weigh_mg']=5
    planned=build_stock_preparation(c,inv,first)
    charges=[dict(stock_id=r['stock_id'],actual_mass_mg=r['planned_mass_mg'],assay_fraction=.98 if r['stock_id']=='Pd' else r['assay_fraction']) for r in planned['stocks'] if r['stock_id']!='IS_MASTER']
    actual=build_stock_preparation(c,inv,first,charges)
    assert actual['actual_weighed_charges_supplied']
    stocks={r['stock_id']:r for r in actual['stocks']}
    assert stocks['Pd']['actual_mass_mg']==90
    assert stocks['Pd']['remaining_bulk_ul']>1830+100
    assert stocks['SM_FIT']['actual_mass_mg']>=5
