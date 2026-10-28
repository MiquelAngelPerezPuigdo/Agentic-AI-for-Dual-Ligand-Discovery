"""Robot stock preparation and measured-volume bookkeeping, separate from pair selection.

Concentrations use the explicitly accepted solvent-addition approximation. No robot
command claims to read a volumetric mark or weigh a solid. Humans supply weighed
charges, bulk liquids, caps and rack moves; every precise liquid transfer is robotic.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from .io import (atomic_text, digest, finite, new_output, object_digest, read_csv,
                 read_json, write_csv, write_json)
from .planning import dosing_rows, stock_plan, transfer_operations, validate_config

ANALYTICAL = {"SM_FIT":"A1", "SM_CHECK":"B1", "P_FIT":"C1", "P_CHECK":"D1",
              "SM_LOW":"A2", "P_LOW":"B2", "SM_HIGH":"C2", "P_HIGH":"D2", "IS_WORK":"A3", "SM_CHECK_LOW":"B3", "P_CHECK_LOW":"C3",
              "SM_CHECK_HIGH":"D3", "P_CHECK_HIGH":"A4"}


class Plan:
    def __init__(self, config, large=False):
        self.large=large
        self.config, self.steps, self.amounts, self.dead = config, [], {}, {}
        self.initial, self.delivered, self.discarded = {}, defaultdict(float), defaultdict(float)

    def initial_liquid(self, location, volume, dead=0):
        key=tuple(location)
        if key in self.amounts:
            raise ValueError("Duplicate preparation liquid address")
        self.initial[key]=self.amounts[key]=finite(volume,"preparation source volume",0);self.dead[key]=dead

    def transfer(self, source, target, volume, label, channels=1):
        volume=finite(volume,"preparation transfer",0)
        if volume < 1e-8:return
        src,dst=tuple(source),tuple(target)
        p=self.config["pipetting"]
        use_large=self.large and channels==1 and volume>297
        capacity=1000 if use_large else 20 if channels==1 and self.config["robot"]["single"]=="p20_single_gen2" else 300
        count=math.ceil(volume/(capacity-p["surplus_ul"]-p["air_gap_ul"]))
        minimum=100 if capacity==1000 else p["minimum_p20_ul"] if capacity==20 else p["minimum_p300_single_ul"]
        if volume/count < minimum:
            raise ValueError(f"{label}: split transfer below pipette minimum")
        used=(volume+p["surplus_ul"])*channels
        if self.amounts.get(src,0)-used < self.dead.get(src,0)-1e-7:
            raise ValueError(f"Insufficient robot-preparation source: {src} for {label}")
        self.amounts[src]-=used;self.amounts[dst]=self.amounts.get(dst,0)+volume*channels
        limit=29000 if dst[0]=="raw" else self.config["stock_preparation"]["reservoir_max_fill_ul"] if dst[0]=="reservoir" else self.config["robot"]["lc_working_volume_ul"] if dst[0]=="cal_plate" else self.config["automation"]["bulk_max_fill_ul"] if dst[0].startswith("BULK") else self.config["stock_preparation"]["tube_max_fill_ul"]
        if self.amounts[dst]>limit+1e-7:raise ValueError("Robot preparation overfills "+str(dst))
        self.dead.setdefault(dst,self.config["automation"]["bulk_dead_ul"] if dst[0].startswith("BULK") else 100 if dst[0].startswith("working") or dst[0]=="analytical" else 1500 if dst[0] in ("raw","reservoir") else 0)
        self.delivered[dst]+=volume*channels;self.discarded[src]+=p["surplus_ul"]*channels
        self.steps.append(dict(type="transfer",source=list(src),target=list(dst),volume_ul=volume,
                               label=label,channels=channels,pipette="large" if use_large else "multi" if channels==8 else "single"))

    def mix(self, location, channels=1):
        key=tuple(location)
        if key[0]=="raw" and channels!=1:raise ValueError("Horizontal raw-reservoir channels must NEVER use the eight-channel pipette")
        use_large=self.large and channels==1 and self.amounts[key]-self.dead.get(key,0)>=600
        capacity=1000 if use_large else 20 if channels==1 and self.config["robot"]["single"]=="p20_single_gen2" else 300
        volume=min(900 if use_large else self.config["automation"]["mix_ul"],capacity-3,
                   (self.amounts[key]-self.dead.get(key,0))/channels)
        if volume<=0:raise ValueError("No liquid available for preparation mixing")
        self.steps.append(dict(type="mix",location=list(key),volume_ul=volume,channels=channels,
                               cycles=max(self.config["automation"]["mix_cycles"],32) if key[0]=="raw" else self.config["automation"]["mix_cycles"],
                               spread_mm=25 if key[0]=="raw" else 0,pipette="large" if use_large else "multi" if channels==8 else "single"))

    def raw(self, fluid, target, volume, pools):
        remaining=finite(volume,"raw solvent addition",0)
        for source in pools[fluid]:
            key=tuple(source);available=self.amounts[key]-self.dead[key]-self.config["pipetting"]["surplus_ul"]
            part=min(remaining,available)
            # Avoid leaving a sub-minimum final portion in the next source.
            if 0 < remaining-part < 20:part-=20
            if part>=20:
                self.transfer(source,target,part,fluid);remaining-=part
            if remaining<1e-7:return
        raise ValueError("Raw source capacity exceeded for "+fluid)

    def report(self):
        result = dict(steps=self.steps,initial_liquids=[dict(location=list(k),volume_ul=v,dead_ul=self.dead[k]) for k,v in self.initial.items()],
                    expected_final_liquids=[dict(location=list(k),volume_ul=v) for k,v in self.amounts.items()],
                    discarded_surplus_ul=sum(self.discarded.values()),
                    concentration_basis="Nominal solvent addition; solute displacement and contraction are not measured",
                    physical_run_completed=False)
        result["pumping_wait_lower_bound"] = preparation_timing(self.config, result)
        result["source_reach_assessment"] = source_reach_assessment(self.config, result)
        return result


def preparation_timing(config, plan):
    """Lower bound from the actual LIQUID_RUNTIME strokes, excluding all motion."""
    seconds = 0.0
    strokes = mixes = pauses = 0
    p = config["pipetting"]
    for step in plan["steps"]:
        kind = step["type"]
        pauses += kind == "pause"
        if kind not in ("transfer", "mix"):
            continue
        large = step["pipette"] == "large"
        aspirate, dispense = (200, 400) if large else (100, 150)
        if kind == "mix":
            mixes += 1
            seconds += step["cycles"] * (step["volume_ul"] / aspirate + step["volume_ul"] / dispense + 1)
            continue
        capacity = 1000 if large else 20 if step["pipette"] == "single" and config["robot"]["single"] == "p20_single_gen2" else 300
        count = math.ceil(step["volume_ul"] / (capacity - p["air_gap_ul"] - p["surplus_ul"]))
        volume = step["volume_ul"] / count
        strokes += count
        seconds += p["prewet_cycles"] * (volume + p["surplus_ul"]) * (1 / aspirate + 1 / dispense)
        seconds += (step["volume_ul"] + p["surplus_ul"] + count * p["air_gap_ul"]) / aspirate
        seconds += (step["volume_ul"] + count * p["air_gap_ul"]) / dispense + count
    return {"seconds": seconds, "minutes": seconds / 60, "transfer_strokes": strokes,
            "mix_events": mixes, "manual_pause_count": pauses, "physical_duration_measured": False,
            "excluded": ["gantry and vertical motion", "tip pickup/drop and tip-rack replacement",
                         "manual pauses, caps, carrier changes and pipette installation"],
            "interpretation": "Programmed pumping and liquid waits only; actual preparation takes longer."}


def source_reach_assessment(config, plan):
    """Reject nozzle entry into a source; simulation does not model pipette-body collisions.

    Tip length minus the official tip overlap is a conservative reach ceiling,
    not a certification of sidewall clearance or material compatibility.
    """
    try:
        from opentrons.protocol_api.labware import get_labware_definition
    except ImportError:
        return {"status": "unavailable", "issues": ["Install the pinned Opentrons SDK (project robot extra) to check official source/tip geometry"],
                "physical_clearance_validated": False}
    cache = {}

    def definition(name, path=None):
        key = path or name
        if key not in cache:
            cache[key] = read_json(path) if path else get_labware_definition(name)
        return cache[key]

    def source_definition(key):
        if key.startswith("BULK"):
            return definition(config["automation"]["bulk_labware"], config["automation"].get("bulk_definition_path"))
        if key.startswith("working") or key == "analytical":
            return definition(config["robot"]["ligand_source_labware"])
        if key == "raw":
            return definition("", config["automation"]["raw_definition_path"])
        kind = "lc" if key == "cal_plate" else "reservoir" if key == "reservoir" else None
        if kind:
            return definition(config["robot"].get(kind + "_labware"), config["robot"].get(kind + "_definition_path"))
        raise ValueError("Unknown preparation source geometry: " + key)

    issues, checked = [], set()
    for step in plan["steps"]:
        if step["type"] not in ("transfer", "mix"):
            continue
        location = step["source"] if step["type"] == "transfer" else step["location"]
        tip_name = ("opentrons_96_tiprack_1000ul" if step["pipette"] == "large" else
                    "opentrons_96_tiprack_20ul" if step["pipette"] == "single" and config["robot"]["single"] == "p20_single_gen2" else
                    "opentrons_96_tiprack_300ul")
        identity = (*location, tip_name)
        if identity in checked:
            continue
        checked.add(identity)
        well = source_definition(location[0])["wells"][location[1]]
        parameters = definition(tip_name)["parameters"]
        available = parameters["tipLength"] - parameters["tipOverlap"]
        insertion = well["depth"] - 1.5  # Current runtime's explicit aspiration height.
        if insertion > available:
            issues.append({"source": location, "tiprack": tip_name, "source_depth_mm": well["depth"],
                           "aspiration_height_mm": 1.5, "required_insertion_mm": insertion,
                           "tip_length_mm": parameters["tipLength"], "tip_overlap_mm": parameters["tipOverlap"],
                           "available_tip_reach_mm": available,
                           "reason": "Aspiration would place the pipette nozzle inside the source container"})
    return {"status": "blocked" if issues else "geometric_check_passed", "issues": issues,
            "checked_source_tip_combinations": len(checked), "physical_clearance_validated": False,
            "limitation": "Conservative tip/nozzle reach only; validate actual container fit, offsets, liquid depth and solvent compatibility locally."}


def validate_source_reach(config, plan):
    assessment = source_reach_assessment(config, plan)
    if assessment["status"] != "geometric_check_passed":
        first = assessment["issues"][0]
        raise ValueError("Unsafe or unverified stock source reach; live release blocked. " + str(first))
    return assessment


def raw_sources(plan, phase):
    """Coarse minimum loads; operator pours liquids, robot meters every addition."""
    initial=phase=="stocks"
    pools={"toluene":[],"water":[],"ACN":[],"FA":[]}
    recipe=([("toluene",w,27500) for w in ("A1","B1","C1","D1")]+[("water","E1",27500),("ACN","F1",27500),("FA","G1",2000)] if initial else
            [("ACN",w,25000) for w in ("A1","B1","C1")]+[("water",w,27500 if plan.config["automation"].get("prepare_optional_pilot") else 25000) for w in ("D1","E1")]+[("toluene","F1",2000),("FA","G1",2500)])
    rows=[]
    for fluid,well,volume in recipe:
        source=["raw",well];plan.initial_liquid(source,volume,1500);pools[fluid].append(source)
        rows.append(dict(phase=phase,reagent=fluid,slot=2 if initial else 3,well=well,
                         minimum_load_ul=volume,instruction="Pour at least this amount; no precise manual pipetting. Keep below 29 mL/channel."))
    return pools,rows


def matrix(plan,target,volume,pools,acid_source,toluene_credit_ul=0):
    # Match final samples, accounting for toluene already delivered in the IS stock.
    volume=finite(volume,"analytical matrix final volume",0.000001)
    credit=finite(toluene_credit_ul,"analytical matrix toluene credit",0,volume)
    if credit > plan.amounts.get(tuple(target),0)+1e-7:
        raise ValueError("Analytical matrix toluene credit exceeds liquid already delivered")
    liquid=plan.config["liquids"];reaction=plan.config["chemistry"]["reaction_volume_ul"]
    extract=reaction+liquid["workup_ul"];total=liquid["aliquot_ul"]+liquid["diluent_ul"]
    aliquot=liquid["aliquot_ul"];diluent=liquid["diluent_ul"]
    toluene=reaction/extract*aliquot/total
    acn=(liquid["workup_ul"]*liquid["quench_acetonitrile_fraction"]/extract*aliquot+diluent*liquid["lc_diluent_acetonitrile_fraction"])/total
    acid=(liquid["workup_ul"]*liquid["workup_formic_acid_percent"]/100/extract*aliquot+diluent*liquid["lc_diluent_formic_acid_percent"]/100)/total
    toluene_addition=finite(volume*toluene-credit,"analytical matrix remaining toluene",0)
    plan.raw("toluene",target,toluene_addition,pools)
    plan.raw("ACN",target,volume*acn,pools)
    plan.transfer(acid_source,target,volume*acid/.1,"10% aqueous FA stock")
    plan.raw("water",target,volume*max(0,1-toluene-acn-acid/.1),pools)
    plan.mix(target,channels=8 if target[0]=="reservoir" else 1)


def stock_records(config,inventory,design,charges=None):
    operations=transfer_operations(config,inventory,dosing_rows(config,inventory,design))
    stocks=stock_plan(config,inventory,operations)
    unique={r["reagent"]:dict(r) for r in reversed(stocks) if r["reagent"] in {*inventory,"substrate_stock"}}
    unique.update({r["stock_id"]:dict(r) for r in stocks if r["reagent"]=="Pd"})
    records=[]
    for key,row in unique.items():
        reagent=row["reagent"]
        mw=float(inventory[key]["molecular_weight_g_mol"]) if key in inventory else config["chemistry"]["pd_molecular_weight_g_mol"] if reagent=="Pd" else config["chemistry"]["substrate_molecular_weight_g_mol"]
        records.append(dict(stock_id=key,reagent=reagent,name=row["name"],planned_mass_mg=row["mass_mg"],mw=mw,
                            stock_mM=row["stock_mM"],kind="direct" if reagent=="Pd" or key in config["automation"]["direct_stock_ids"] else "reaction",
                            source_slot=row["source_slot"],source_well=row["source_well"],
                            full_campaign_required_ul=row.get("full_campaign_required_ul"),
                            solvent="toluene",prepare_ul=row["prepare_ul"]))
    from .analytical_stocks import preparation
    for row in preparation(config):
        if row["stock_mM"]!=10:continue
        key=("SM" if row["analyte"]=="substrate" else "P")+("_FIT" if row["role"]=="fit" else "_CHECK")
        records.append(dict(stock_id=key,reagent="substrate_stock" if key.startswith("SM") else "product_standard",
            name="Independent authentic "+key,planned_mass_mg=row["mass_mg"],
            mw=config["chemistry"]["substrate_molecular_weight_g_mol"] if key.startswith("SM") else 97.09,
            stock_mM=10,kind="analytical",solvent="matrix",prepare_ul=row["prepare_ul"]))
    is_source=config["automation"]["internal_standard_source"]
    records.append(dict(stock_id="IS_SOURCE",reagent="internal_standard",name="Naphthalene source in toluene",
        planned_mass_mg=is_source["planned_mass_mg"],mw=config["liquids"]["internal_standard_molecular_weight_g_mol"],
        stock_mM=is_source["stock_mM"],kind="direct",solvent="toluene",
        source_slot=is_source["slot"],source_well=is_source["well"]))
    given={}
    for row in charges or []:
        key=row["stock_id"]
        if key in given:raise ValueError("Duplicate weighed stock charge: "+key)
        given[key]=row
    if charges is not None and set(given)!={r["stock_id"] for r in records}:
        raise ValueError("Weighed charges must cover each stock_id exactly once")
    for record in records:
        key=record["stock_id"];reagent=record["reagent"]
        assays=config["stock_preparation"].get("assay_fractions",{})
        assay=assays.get(key,assays.get(reagent,1))
        if charges is not None:
            mass=finite(given[key]["actual_mass_mg"],key+" actual mass",.000001)
            assay=finite(given[key]["assay_fraction"],key+" assay",.000001,1)
        else:mass=record["planned_mass_mg"]
        limit=config["stock_preparation"].get("available_mass_mg",{}).get(reagent)
        if limit is not None and mass>limit+1e-8:raise ValueError(key+" exceeds available mass; preserve scope reserve")
        record.update(mass_mg_used=mass,mass_basis="actual_recorded" if charges is not None else "nominal_target",
                      assay_fraction=assay,prepare_ul=mass*assay/record["mw"]/record["stock_mM"]*1e6)
        capacity=config["stock_preparation"]["tube_max_fill_ul"] if record["kind"]=="direct" else config["automation"]["bulk_max_fill_ul"]
        if record["prepare_ul"]>capacity+1e-7:
            raise ValueError("Stock exceeds container capacity: "+key)
        if reagent=="Pd" and record["prepare_ul"]+1e-8<record["full_campaign_required_ul"]:
            raise ValueError("Direct Pd source cannot cover both rounds and dead volume: "+key)
    pd_mass=sum(r["mass_mg_used"] for r in records if r["reagent"]=="Pd")
    pd_limit=min(config["stock_preparation"]["available_mass_mg"]["Pd"],config["stock_preparation"]["fixed_stock_mass_mg"]["Pd"])
    if pd_mass>pd_limit+1e-8:
        raise ValueError("Combined Pd charges exceed available mass; preserve scope reserve")
    # This master is derived from the weighed source, never a second manual charge.
    master_mM,master_ul=2,8000
    records.append(dict(stock_id="IS_MASTER",reagent="internal_standard",name="Analytical naphthalene master",
        planned_mass_mg=0,mass_mg_used=master_mM*master_ul*config["liquids"]["internal_standard_molecular_weight_g_mol"]/1e6,mass_basis="derived_from_IS_SOURCE",
        assay_fraction=1,mw=config["liquids"]["internal_standard_molecular_weight_g_mol"],
        stock_mM=master_mM,kind="analytical",solvent="matrix",prepare_ul=master_ul))
    bulk=[r for r in records if r["kind"]!="direct"]
    for i,row in enumerate(bulk):
        batch=i//12+1;side=(i%12)//6;well=config["automation"]["bulk_wells"][i%6]
        # Analytic records share their own final carrier batch; slot assignment remains explicit.
        row.update(carrier_id=f"BULK-{batch:02d}-{3 if side==0 else 6}",carrier_slot=3 if side==0 else 6,source_well=well)
    return records,stocks,operations


def bulk_load(plan,records,config,prepared=False):
    for carrier in dict.fromkeys(r["carrier_id"] for r in records):
        rows=[r for r in records if r["carrier_id"]==carrier]
        plan.steps.append(dict(type="pause",message=("Load EXISTING prepared Axygen reservoir " if prepared else "Load the Axygen reservoir with preweighed charges ")+carrier+" in slot "+str(rows[0]["carrier_slot"])+". Check channel IDs against bulk_carriers.csv. REMOVE the cover before pipetting. No manual liquid measurement."))
        plan.steps.append(dict(type="load",key=carrier,slot=rows[0]["carrier_slot"],labware=config["automation"]["bulk_labware"],definition_path=config["automation"].get("bulk_definition_path"),label=carrier))


def bulk_off(plan,records):
    for carrier in dict.fromkeys(r["carrier_id"] for r in records):
        plan.steps += [dict(type="pause",message="Cover "+carrier+" with its solvent-compatible cover. Store the whole labeled reservoir for automated R2 refill; no hand aliquoting."),dict(type="off",key=carrier)]


def build_stock_preparation(config,inventory,design,charges=None):
    validate_automation(config,inventory)
    records,stocks,operations=stock_records(config,inventory,design,charges)
    plan=Plan(config,large=True);pools,raw_loads=raw_sources(plan,"stocks")
    auto=config["automation"];is_config=auto["internal_standard_source"]
    is_source=["working"+str(is_config["slot"]),is_config["well"]]
    acid=["working"+str(auto["initial_acid_source"]["slot"]),auto["initial_acid_source"]["well"]]
    plan.raw("water",acid,1620,pools);plan.raw("FA",acid,180,pools);plan.mix(acid)
    matrix(plan,["raw","H1"],25000,pools,acid)
    def ensure_matrix(volume):
        if plan.amounts[("raw","H1")]-1500 < volume+1:
            matrix(plan,["raw","H1"],min(20000,29000-plan.amounts[("raw","H1")]),pools,acid)
    # Naphthalene must be dissolved and checked before preparing the combined SM stock.
    for row in sorted(records, key=lambda r: r["stock_id"] != "IS_SOURCE"):
        if row["kind"]!="direct":continue
        target=["working"+str(row["source_slot"]),row["source_well"]]
        plan.raw("toluene",target,row["prepare_ul"],pools);plan.mix(target)
        if row["stock_id"]=="IS_SOURCE":
            plan.steps.append(dict(type="pause",message="Confirm the robot-prepared naphthalene source at slot " + str(is_config["slot"]) + " " + is_config["well"] + " is fully dissolved and visibly clear before it is used. If crystals remain, stop and resolve dissolution; do not transfer a suspension as an internal standard. Keep this source OPEN during stock preparation."))
    deck=working_loads(config,operations,stocks)
    for batch in sorted({r["carrier_id"].split('-')[1] for r in records if r["kind"]!="direct"}):
        group=[r for r in records if r["kind"]!="direct" and r["carrier_id"].split('-')[1]==batch]
        # Analytic carriers are placed after the working rack swap; group boundaries are explicit below.
        reaction=[r for r in group if r["kind"]=="reaction"]
        analytical=[r for r in group if r["kind"]=="analytical"]
        for subset,analytical_mode in ((reaction,False),(analytical,True)):
            if not subset:continue
            bulk_load(plan,subset,config)
            for row in subset:
                target=[row["carrier_id"],row["source_well"]]
                is_volume=0
                if row["stock_id"]=="substrate_stock":
                    umol=row["mass_mg_used"]*row["assay_fraction"]/row["mw"]*1000*config["chemistry"]["preloaded_internal_standard"]["mol_percent_relative_to_substrate"]/100
                    is_volume=umol/is_config["stock_mM"]*1000
                elif row["stock_id"]=="IS_MASTER":
                    is_volume=row["stock_mM"]*row["prepare_ul"]/is_config["stock_mM"]
                if is_volume:plan.transfer(is_source,target,is_volume,"naphthalene stock")
                if row["stock_id"]=="IS_MASTER":
                    matrix(plan,target,row["prepare_ul"],pools,acid,toluene_credit_ul=is_volume)
                else:
                    if row["solvent"]=="toluene":plan.raw("toluene",target,row["prepare_ul"]-is_volume,pools)
                    else:
                        ensure_matrix(row["prepare_ul"])
                        plan.transfer(["raw","H1"],target,row["prepare_ul"],"analytical matrix")
                    plan.mix(target)
                if not analytical_mode:
                    for load in [r for r in deck if r["reagent"]==row["stock_id"]]:
                        plan.transfer(target,["working"+str(load["source_slot"]),load["source_well"]],load["load_ul"],"fill "+row["stock_id"])
                row["remaining_bulk_ul"]=plan.amounts[tuple(target)]
            if analytical_mode:
                ensure_matrix(1565+(1564 if auto.get("prepare_optional_pilot") else 0))
                plan.steps += [dict(type="pause",message="Store working stock rack 4 capped. Load a NEW empty 2 mL analytical rack in slot 4; leave working rack 1 in place with the naphthalene source."),dict(type="off",key="working4"),dict(type="load",key="analytical",slot=4,labware=config["robot"]["ligand_source_labware"],label="Analytical source rack")]
                for row in subset:
                    if row["stock_id"]=="IS_MASTER":continue
                    target=[row["carrier_id"],row["source_well"]]
                    aliquot=min(1800,plan.amounts[tuple(target)]-auto["bulk_dead_ul"]-1)
                    if aliquot<600:raise ValueError("Authentic master charge too small for robotic preparation")
                    plan.transfer(target,["analytical",ANALYTICAL[row["stock_id"]]],aliquot,"authentic master "+row["stock_id"])
                master=next(r for r in subset if r["stock_id"]=="IS_MASTER")
                plan.transfer([master["carrier_id"],master["source_well"]],["analytical",ANALYTICAL["IS_WORK"]],1000,"2 mM naphthalene master")
                for analyte in ("SM","P"):
                    for level,master_ul,matrix_ul in (("LOW",20,380),("HIGH",400,400)):
                        dest=["analytical",ANALYTICAL[analyte+"_"+level]]
                        plan.transfer(["analytical",ANALYTICAL[analyte+"_FIT"]],dest,master_ul,"FIT working dilution")
                        plan.transfer(["raw","H1"],dest,matrix_ul,"analytical matrix");plan.mix(dest)
                if auto.get("prepare_optional_pilot"):
                    for analyte in ("SM","P"):
                        for level,master_ul,matrix_ul in (("LOW",20,380),("HIGH",400,400)):
                            dest=["analytical",ANALYTICAL[analyte+"_CHECK_"+level]]
                            plan.transfer(["analytical",ANALYTICAL[analyte+"_CHECK"]],dest,master_ul,"CHECK pilot working dilution")
                            plan.transfer(["raw","H1"],dest,matrix_ul,"analytical matrix");plan.mix(dest)
                plan.mix(["analytical",ANALYTICAL["IS_WORK"]])
            bulk_off(plan,subset)
            if analytical_mode:
                plan.steps += [dict(type="pause",message="Cap and store the analytical source rack for robotic calibration during R1. Restore working stock rack 4 to slot 4. Keep every stock ID/address unchanged."),dict(type="off",key="analytical"),dict(type="move",key="working4",slot=4)]
    for row in records:
        if row["kind"]!="direct":row["remaining_bulk_ul"]=plan.amounts[(row["carrier_id"],row["source_well"])]
    report=plan.report()
    # Check reserve demands from worst-case R2 before any hardware file is released.
    for row in records:
        if row["kind"]=="direct":
            if row["reagent"] in ("Pd","internal_standard"):continue  # Pd demand was checked above; IS consumption is fully tracked by Plan.
            first=sum(r["consumption_ul"] for r in deck if r["reagent"]==row["stock_id"])
            reserve=sum(r["round2_reserve_ul"] for r in stocks if r["reagent"]==row["stock_id"])
            minimum=max(first+reserve+100, *(r["load_ul"] for r in deck if r["reagent"]==row["stock_id"]))
            if row["prepare_ul"]+1e-7 < minimum:raise ValueError("Direct stock cannot cover both rounds: "+row["stock_id"])
            continue
        if row["kind"]!="reaction" or row["stock_id"]=="substrate_stock":continue
        reserved=sum(r["round2_reserve_ul"] for r in stocks if r["reagent"]==row["stock_id"])
        if row["remaining_bulk_ul"]+1e-7 < reserved+config["automation"]["bulk_dead_ul"]:
            raise ValueError("Prepared bulk cannot cover R2 and dead volume: "+row["stock_id"])
    report.update(stocks=records,raw_loads=raw_loads,working_loads=deck,
                  config_digest=object_digest(config),inventory_digest=object_digest(inventory),design_digest=object_digest(design),
                  actual_weighed_charges_supplied=charges is not None,
                  weighing_basis="actual_recorded" if charges is not None else "nominal_target",
                  design_signature=design_signature(design))
    return report


def working_loads(config,operations,stocks):
    used=defaultdict(float)
    for op in operations:
        if op["stage"] in ("substrate","assembly","internal_standard"):
            used[(op["reagent"],op["source_slot"],op["source_well"])]+=op["aspirated_ul_per_channel"]*op["channels"]
    result=[]
    for stock in stocks:
        key=(stock["reagent"],int(stock["source_slot"]),stock["source_well"])
        if key not in used:continue
        required=used[key]+stock["dead_ul"]
        load=max(required if key[0]=="Pd" else math.ceil(required/10)*10,stock["on_deck_ul"])
        result.append(dict(reagent=key[0],source_slot=key[1],source_well=key[2],load_ul=load,consumption_ul=used[key]))
    return result


# Kept self-contained in every exported Python file; no project installation on the OT-2.
LIQUID_RUNTIME = r'''
class ReactionHoldTimer:
    """Observe actual elapsed time; an operator must handle expiry while App-paused."""
    def __init__(self, protocol, seconds, max_overrun_seconds, clock=None):
        import time
        self.protocol, self.target, self.tolerance = protocol, seconds, max_overrun_seconds
        self.clock = clock or time.monotonic
        self.start = self.clock()
        self.simulation = protocol.is_simulating()
        self.failed = False
        self.record("started")

    def elapsed(self):
        return self.clock() - self.start

    def record(self, event):
        import json
        elapsed = None if self.simulation else self.elapsed()
        self.protocol.comment("HOLD_TIMING " + json.dumps({"event": event, "target_seconds": self.target,
            "elapsed_seconds": elapsed, "overrun_seconds": None if elapsed is None else max(0, elapsed - self.target),
            "maximum_recording_overrun_seconds": self.tolerance, "simulation": self.simulation,
            "physical_duration_measured": not self.simulation, "failed": self.failed}, sort_keys=True))

    def check(self):
        if not self.simulation and self.elapsed() >= self.target:
            self.failed = True
            self.record("preparation_deadline_exceeded")
            raise RuntimeError("Reaction hold expired during preparation. Heater/shaker will stop; reject this run pending deviation review. An App pause cannot be interrupted by this Python guard.")

    def remaining(self):
        return self.target if self.simulation else max(0, self.target - self.elapsed())

    def finish(self):
        if not self.simulation and self.elapsed() > self.target + self.tolerance:
            self.failed = True
            self.record("hold_overrun_rejected")
            raise RuntimeError("Reaction hold exceeded its recorded timing tolerance; reject this run pending deviation review.")
        self.record("hold_completed")


def execute_liquid_plan(protocol, plan, labware, single, multi=None, large=None, check_deadline=None):
    from opentrons.types import Point
    import math
    def check():
        if check_deadline is not None: check_deadline()
    def tip(pipette):
        try: pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            protocol.pause("Replace all empty tip racks for this pipette in the same slots, then resume.")
            pipette.reset_tipracks();pipette.pick_up_tip()
    p=CONFIG["pipetting"]
    for step in plan["steps"]:
        check()
        kind=step["type"]
        if kind=="pause":protocol.pause(step["message"])
        elif kind=="load":
            definition=PREP_DEFINITIONS.get(step.get("definition_path"))
            labware[step["key"]]=(protocol.load_labware_from_definition(definition,step["slot"],step["label"]) if definition else protocol.load_labware(step["labware"],step["slot"],step["label"]))
        elif kind=="off":protocol.move_labware(labware[step["key"]],protocol_api.OFF_DECK,use_gripper=False)
        elif kind=="move":protocol.move_labware(labware[step["key"]],step["slot"],use_gripper=False)
        elif kind=="mix":
            pipette=large if step["pipette"]=="large" else multi if step["channels"]==8 else single;tip(pipette)
            pipette.flow_rate.aspirate=200 if pipette is large else 100;pipette.flow_rate.dispense=400 if pipette is large else 150
            well=labware[step["location"][0]][step["location"][1]]
            for cycle in range(step["cycles"]):
                check()
                spread=step.get("spread_mm",0)*(1 if cycle%2 else -1)
                pipette.aspirate(step["volume_ul"],well.bottom(1.5).move(Point(x=spread,y=0,z=0)));protocol.delay(seconds=.5)
                pipette.dispense(step["volume_ul"],well.bottom(3 if spread else 1.5).move(Point(x=-spread,y=0,z=0)));protocol.delay(seconds=.5)
            pipette.drop_tip()
        elif kind=="transfer":
            pipette=large if step["pipette"]=="large" else multi if step["channels"]==8 else single;tip(pipette)
            pipette.flow_rate.aspirate=200 if pipette is large else 100;pipette.flow_rate.dispense=400 if pipette is large else 150
            source=labware[step["source"][0]][step["source"][1]]
            target=labware[step["target"][0]][step["target"][1]]
            count=math.ceil(step["volume_ul"]/(pipette.max_volume-p["air_gap_ul"]-p["surplus_ul"]))
            volume=step["volume_ul"]/count
            protocol.comment("ROBOT PREPARATION: "+step["label"]+", "+str(step["volume_ul"])+" uL nominal")
            for _ in range(p["prewet_cycles"]):
                check()
                pipette.aspirate(volume+p["surplus_ul"],source.bottom(1.5));pipette.dispense(volume+p["surplus_ul"],source.bottom(1.5))
            for stroke in range(count):
                check()
                pipette.aspirate(volume+(p["surplus_ul"] if stroke==0 else 0),source.bottom(1.5));protocol.delay(seconds=.5)
                pipette.air_gap(p["air_gap_ul"])
                pipette.dispense(volume+p["air_gap_ul"],target.top(2));protocol.delay(seconds=.5)
            pipette.drop_tip()
        else:raise RuntimeError("Unknown preparation action")
        check()
'''


def definitions(config):
    paths={config["automation"]["raw_definition_path"]}
    if config["automation"].get("bulk_definition_path"):paths.add(config["automation"]["bulk_definition_path"])
    return {path:read_json(path) for path in paths}


def recipe_digest(config):
    auto={k:v for k,v in config["automation"].items() if k!="preparation_manifest_path"}
    return object_digest({key:config[key] for key in ("chemistry","liquids","stock_preparation","robot","pipetting")}|{"automation":auto,"source_definitions":definitions(config)})


def design_signature(rows):
    return object_digest([{k:str(row.get(k,"")) for k in ("round","sample_id","well","kind","pair_id","ligand_a","ligand_b")} for row in rows])


def validate_automation(config,inventory):
    a=config["automation"]
    if a.get("enabled") is not True or a.get("concentration_basis")!="nominal_solvent_addition" or a.get("approximation_accepted") is not True:
        raise ValueError("Schema 6 requires the declared, accepted nominal robot-preparation concentration basis")
    if a["preparation_large_pipette"] not in ("p1000_single_gen2","p1000_single"):
        raise ValueError("Use the actual available p1000 single model for preparation")
    if type(a["mix_cycles"]) is not int or not 1<=a["mix_cycles"]<=50:raise ValueError("Choose 1-50 preparation mixing cycles")
    finite(a["mix_ul"],"preparation mixing volume",20,297)
    is_source=a.get("internal_standard_source")
    if not isinstance(is_source,dict):raise ValueError("Configure the weighed naphthalene internal_standard_source; neat-liquid IS settings are obsolete")
    finite(is_source.get("stock_mM"),"naphthalene source concentration",.000001)
    finite(is_source.get("planned_mass_mg"),"naphthalene source mass",.000001)
    if any(key.startswith("neat_is_") for key in a):raise ValueError("Remove obsolete neat-liquid IS settings")
    positions={(int(r["source_slot"]),r["source_well"]) for r in inventory.values()}
    positions.add((config["stock_preparation"]["substrate_source_slot"],config["stock_preparation"]["substrate_source_well"]))
    positions.update((s["slot"],s["well"]) for s in config["stock_preparation"]["pd_source_pool"])
    for key in ("internal_standard_source","initial_acid_source"):
        source=a[key];location=(source["slot"],source["well"])
        if location in positions or source["slot"] not in (1,4) or source["well"] not in {r+str(col) for r in "ABCD" for col in range(1,7)}:
            raise ValueError("Preparation source overlaps an occupied/invalid working position")
        positions.add(location)
    raw=read_json(a["raw_definition_path"])
    if set(raw["wells"])!={r+"1" for r in "ABCDEFGH"} or any(w["totalLiquidVolume"]<29000 or w.get("xDimension",0)<60 for w in raw["wells"].values()):
        raise ValueError("Use the supplied horizontal A1-H1 30 mL raw reservoir geometry")
    finite(a["bulk_dead_ul"],"bulk source dead volume",100,2000)
    if type(a.get("prepare_optional_pilot",False)) is not bool:raise ValueError("Optional pilot must be a boolean")
    if len(a["bulk_wells"])!=6 or len(set(a["bulk_wells"]))!=6:raise ValueError("Specify six distinct bulk carrier wells")
    if a.get("bulk_definition_path"):
        bulk=read_json(a["bulk_definition_path"])
        if any(w not in bulk["wells"] or bulk["wells"][w]["totalLiquidVolume"]<a["bulk_max_fill_ul"] for w in a["bulk_wells"]):
            raise ValueError("Compatible bulk definition must contain the six configured wells/capacities")


def load_preparation(config,inventory,path,live=False):
    report=read_json(path)
    if report.get("recipe_digest")!=recipe_digest(config) or report.get("inventory_digest")!=object_digest(inventory):
        if config.get("demo") and not live and not report.get("actual_weighed_charges_supplied"):return None
        raise ValueError("Stock preparation manifest does not match this campaign recipe/inventory")
    if live and not report.get("actual_weighed_charges_supplied") and not (report.get("weighing_basis")=="nominal_target" and report.get("live_export") is True):
        raise ValueError("Live run requires a live stock preparation generated using target or recorded masses")
    if live: validate_source_reach(config, report)
    return report


def export_stock_preparation(config,inventory,design,output,charges=None,live=False):
    validate_config(config,live=live,live_scope="first_reaction")
    plan=build_stock_preparation(config,inventory,design,charges)
    if live: validate_source_reach(config, plan)
    plan["recipe_digest"]=recipe_digest(config);plan["live_export"]=live
    out=new_output(output);write_json(out/"preparation_manifest.json",plan)
    if charges is not None:write_csv(out/"weighed_charges_used.csv",charges)
    write_csv(out/"bulk_carriers.csv",[dict(stock_id=r["stock_id"],carrier_id=r.get("carrier_id","WORKING RACK"),slot=r.get("carrier_slot",r.get("source_slot","")),well=r.get("source_well",""),preloaded_mass_mg=0 if r["stock_id"]=="IS_MASTER" else r["mass_mg_used"],preload_action="EMPTY: robot adds naphthalene source and matrix components" if r["stock_id"]=="IS_MASTER" else "Weigh SM ONLY; robot adds naphthalene source" if r["stock_id"]=="substrate_stock" else "Weigh listed amount independently",nominal_stock_mM=r["stock_mM"],robot_prepared_ul=r["prepare_ul"])
        for r in plan["stocks"]])
    write_csv(out/"raw_reagents_to_load.csv",plan["raw_loads"])
    source="from opentrons import protocol_api\n"
    source+=repr_constants(config,plan,live)
    source+='requirements={"robotType":"OT-2","apiLevel":"2.18"}\nmetadata={"protocolName":"Robot stock preparation — preweighed charges"}\n'
    source+=LIQUID_RUNTIME
    source+='''
def run(protocol: protocol_api.ProtocolContext):
    if DEMO and not protocol.is_simulating():raise RuntimeError("Preview only; complete local release checks and generate the live protocol")
    tips=protocol.load_labware("opentrons_96_tiprack_20ul" if CONFIG["robot"]["single"]=="p20_single_gen2" else "opentrons_96_tiprack_300ul",5)
    large_tips=[protocol.load_labware("opentrons_96_tiprack_1000ul",s) for s in (8,9)]
    single=protocol.load_instrument(CONFIG["robot"]["single"],"left",tip_racks=[tips])
    large=protocol.load_instrument(CONFIG["automation"]["preparation_large_pipette"],"right",tip_racks=large_tips)
    labware={"working1":protocol.load_labware(CONFIG["robot"]["ligand_source_labware"],1),"working4":protocol.load_labware(CONFIG["robot"]["ligand_source_labware"],4),
        "raw":protocol.load_labware_from_definition(PREP_DEFINITIONS[CONFIG["automation"]["raw_definition_path"]],2)}
    direct_stocks = ", ".join(row["stock_id"] + " at slot " + str(row["source_slot"]) + " " + row["source_well"] for row in PLAN["stocks"] if row["kind"] == "direct")
    protocol.pause("Load ALL PREWEIGHED DIRECT STOCKS from bulk_carriers.csv: " + direct_stocks + ". These tubes must already contain their individually weighed solids. All other working tubes start EMPTY. The IS_SOURCE tube contains weighed SOLID naphthalene; the robot adds its toluene. Load raw solvents per raw_reagents_to_load.csv. No hand aliquoting. Caps OPEN; slots 7 and 11 empty. Bulk carriers will be requested by ID.")
    execute_liquid_plan(protocol,PLAN,labware,single,large=large)
    protocol.pause("Stocks ready. Replace the RIGHT p1000 single with p300 eight-channel GEN2, and 1000 uL tip racks 8/9 with 300 uL racks, through the local App installation/calibration workflow. Leave the left single installed. Cap and retain all labeled carriers and analytical rack. Leave working racks 1/4 in their exact positions. Remove raw reservoir 2; install a NEW EMPTY 12-channel workup reservoir in slot 2. Load the reaction block in slot 3 with " + str(CONFIG["design"]["round1_total"]) + " NEW EMPTY R1 vials and the empty calibration LC plate in slot 6 for the R1 protocol. No precise manual liquid transfers.")
'''
    atomic_text(out/"prepare_stocks.py",source)
    write_json(out/"files.sha256.json",{p.name:digest(p) for p in out.iterdir() if p.is_file()})
    return out


def repr_constants(config,plan,live):
    return f"CONFIG={config!r}\nPLAN={plan!r}\nDEMO={not live!r}\nPREP_DEFINITIONS={definitions(config)!r}\n"


def calibration_recipes(config):
    """All aliquots meet the p300 minimum; each authentic analyte has its own blank/check."""
    from .analytics import calibration_identity
    rows=[]
    is_ul=config["analytics"]["internal_standard_final_uM"]/2000*1000
    for analyte,prefix in (("substrate","SM"),("product","P")):
        for suffix,concentration in (("BLANK",0),("01",10),("02",50),("03",150),("04",350),("05",800),("CHECK",2000/3)):
            source=prefix+"_CHECK" if suffix=="CHECK" else prefix+"_LOW" if concentration<=50 else prefix+"_HIGH"
            stock=10 if suffix=="CHECK" else .5 if concentration<=50 else 5
            volume=concentration/stock if concentration else 0
            rows.append(dict(sample_id=f"CAL-{prefix}-{suffix}",role="check" if suffix=="CHECK" else "calibration",
                analyte=analyte,concentration_uM=concentration,plate_id="CALIBRATION",well="ABCDEFG"[len(rows)%7]+str(1 if prefix=="SM" else 2),
                source_id=source,stock_mM=stock,analyte_ul=volume,is_ul=is_ul,matrix_ul=1000-is_ul-volume,
                internal_standard_concentration_uM=config["analytics"]["internal_standard_final_uM"],**calibration_identity(config)))
    return rows


def pilot_recipes(config):
    """Optional known mixtures, independently robot-diluted from CHECK masters."""
    from .analytics import calibration_identity
    liquid=config["liquids"]
    maximum=(config["chemistry"]["substrate_molarity_M"]*config["chemistry"]["reaction_volume_ul"]*1e6
             /(config["chemistry"]["reaction_volume_ul"]+liquid["workup_ul"])
             *liquid["aliquot_ul"]/(liquid["aliquot_ul"]+liquid["diluent_ul"]))
    rows=[]
    for i,fraction in enumerate((0,.1,.5,.9,1,None,.5),1):
        sm=maximum*(1-fraction) if fraction is not None else 0
        product=maximum*fraction if fraction is not None else 0
        row=dict(sample_id=f"PILOT-{i:02d}",role="carryover_blank" if fraction is None else "independent_repeat" if i==7 else "mixture",
                 substrate_uM=sm,product_uM=product,internal_standard_uM=config["analytics"]["internal_standard_final_uM"],
                 well="ABCDEFG"[i-1]+"3",plate_id="CALIBRATION",is_ul=config["analytics"]["internal_standard_final_uM"]/2,**calibration_identity(config))
        for prefix,concentration in (("SM",sm),("P",product)):
            stock=.5 if 0<concentration<100 else 5
            row[prefix+"_source"]=prefix+"_CHECK_"+("LOW" if stock==.5 else "HIGH")
            row[prefix+"_stock_mM"]=stock;row[prefix+"_ul"]=concentration/stock
        row["matrix_ul"]=1000-row["is_ul"]-row["SM_ul"]-row["P_ul"]
        rows.append(row)
    return rows


def build_hold_preparation(config,operations,round_number,prep=None):
    """Run while the reaction is sealed on slot 10; keep slot 3 free again before cooling."""
    plan=Plan(config);pools,raw_loads=raw_sources(plan,"hold")
    plan.steps += [dict(type="pause",message="The reaction is running on slot 10. Load the raw 8-channel solvent reservoir in slot 3 per raw_reagents_to_load.csv; leave the reaction block on the heater. Slot 2 must contain a NEW EMPTY 12-channel reservoir. No manual solvent measurement."),
        dict(type="load",key="raw",slot=3,labware="",definition_path=config["automation"]["raw_definition_path"],label="Raw workup solvents")]
    plan.raw("water",["raw","H1"],4500,pools);plan.raw("FA",["raw","H1"],500,pools)
    plan.mix(["raw","H1"])
    if round_number==1:
        plan.steps += [dict(type="pause",message="Cap/store working rack 4 and replace it with the robot-prepared ANALYTICAL source rack. UNCAP the analytical source tubes before resuming pipetting. Working rack 1 stays in slot 1. Load the EMPTY calibration plate in slot 6; it will be pipette-mixed because the heater-shaker is occupied."),
                      dict(type="off",key="working4"),dict(type="load",key="analytical",slot=4,labware=config["robot"]["ligand_source_labware"],label="Analytical source rack")]
        source_volumes={"SM_FIT":1378,"P_FIT":1378,"SM_CHECK":1800,"P_CHECK":1800,"SM_LOW":400,"P_LOW":400,"SM_HIGH":800,"P_HIGH":800,"IS_WORK":1000}
        if prep:
            final={tuple(r["location"]):r["volume_ul"] for r in prep["expected_final_liquids"]}
            source_volumes={key:final[("analytical",well)] for key,well in ANALYTICAL.items() if ("analytical",well) in final}
        optional=config["automation"].get("prepare_optional_pilot",False)
        if optional and not prep:
            source_volumes.update(SM_CHECK=1378,P_CHECK=1378,SM_CHECK_LOW=400,P_CHECK_LOW=400,SM_CHECK_HIGH=800,P_CHECK_HIGH=800)
        for key,volume in source_volumes.items():plan.initial_liquid(["analytical",ANALYTICAL[key]],volume,100)
        matrix_wells=config["automation"]["calibration_matrix_wells"]+(["A2"] if optional else [])
        for well in matrix_wells:
            matrix(plan,["reservoir",well],9000,pools,["raw","H1"])
        matrix_pools={"matrix":[["reservoir",w] for w in matrix_wells]}
        for source in matrix_pools["matrix"]:plan.dead[tuple(source)]=config["stock_preparation"]["reservoir_dead_ul"]
        for row in calibration_recipes(config):
            target=["cal_plate",row["well"]]
            plan.raw("matrix",target,row["matrix_ul"],matrix_pools)
            plan.transfer(["analytical",ANALYTICAL["IS_WORK"]],target,row["is_ul"],"calibration IS")
            if row["analyte_ul"]:plan.transfer(["analytical",ANALYTICAL[row["source_id"]]],target,row["analyte_ul"],row["sample_id"])
            plan.mix(target)
        if optional:
            for row in pilot_recipes(config):
                target=["cal_plate",row["well"]]
                plan.raw("matrix",target,row["matrix_ul"],matrix_pools)
                plan.transfer(["analytical",ANALYTICAL["IS_WORK"]],target,row["is_ul"],"pilot IS")
                for prefix in ("SM","P"):
                    if row[prefix+"_ul"]:plan.transfer(["analytical",ANALYTICAL[row[prefix+"_source"]]],target,row[prefix+"_ul"],row["sample_id"]+" "+prefix)
                plan.mix(target)
        plan.steps += [dict(type="pause",message="Calibration plate is robot-prepared and pipette-mixed. Apply the compatible seal and move slot 6 DIRECTLY to HPLC at the next move prompt. Start the 14-injection calibration sequence now, while the reaction continues; if optional pilot enabled, acquire its separate seven-injection sequence afterward. No manual dilution or shaking. Preserve the calibration well map."),dict(type="off",key="cal_plate"),
            dict(type="pause",message="Cap/store the analytical source rack. Restore working rack 4 to slot 4."),dict(type="off",key="analytical"),dict(type="move",key="working4",slot=4)]
    use=defaultdict(float)
    for op in operations:
        if op["stage"] in ("workup","dilution"):
            use[(op["reagent"],op["source_well"])]+=op["aspirated_ul_per_channel"]*op["channels"]
    for (reagent,well),consumption in use.items():
        volume=math.ceil((consumption+config["stock_preparation"]["reservoir_dead_ul"])/10)*10
        target=["reservoir",well]
        acn=config["liquids"]["quench_acetonitrile_fraction" if reagent=="workup" else "lc_diluent_acetonitrile_fraction"]
        acid=config["liquids"]["workup_formic_acid_percent" if reagent=="workup" else "lc_diluent_formic_acid_percent"]/100
        plan.raw("ACN",target,volume*acn,pools)
        plan.transfer(["raw","H1"],target,volume*acid/.1,"10% FA stock")
        plan.raw("water",target,volume*max(0,1-acn-acid/.1),pools);plan.mix(target,channels=8)
    plan.steps += [dict(type="pause",message="Workup liquids are now robot-prepared in slot 2. Cover them until workup. Remove the RAW reservoir from slot 3 at the next move prompt, so the reaction block can return there. Leave the prepared reservoir 2 in place. No hand refilling."),dict(type="off",key="raw")]
    result=plan.report();result.update(raw_loads=raw_loads,calibration_recipes=calibration_recipes(config) if round_number==1 else [],pilot_recipes=pilot_recipes(config) if round_number==1 and config["automation"].get("prepare_optional_pilot") else [])
    result["hold_timing_policy"] = {"reaction_seconds": config["chemistry"]["reaction_minutes"] * 60,
        "max_hold_overrun_seconds": finite(config["chemistry"].get("max_hold_overrun_seconds", 60), "hold overrun recording tolerance", 0),
        "external_operator_timer_required": True,
        "limitation": "The Python guard stops work and rejects an expired hold after App resume; it cannot stop the module while a manual pause blocks execution."}
    return result


def build_refill(config,inventory,design,history,prep):
    if prep["design_signature"]!=design_signature(history):raise ValueError("R2 refill history differs from the prepared first-round design")
    operations=transfer_operations(config,inventory,dosing_rows(config,inventory,design))
    target=working_loads(config,operations,stock_plan(config,inventory,operations,False))
    from .planning import validate_dosing
    first_ops=transfer_operations(config,inventory,validate_dosing(config,inventory,history))
    amounts={tuple(r["location"]):r["volume_ul"] for r in prep["expected_final_liquids"]}
    for op in first_ops:
        if op["source_slot"] in (1,4):
            key=("working"+str(op["source_slot"]),op["source_well"])
            amounts[key]-=op["aspirated_ul_per_channel"]*op["channels"]
    plan=Plan(config)
    records={r["stock_id"]:r for r in prep["stocks"]}
    for location,volume in amounts.items():
        if location[0].startswith("working") or location[0].startswith("BULK"):
            plan.initial_liquid(location,volume,config["automation"]["bulk_dead_ul"] if location[0].startswith("BULK") else 100)
    needed=[]
    for load in target:
        location=("working"+str(load["source_slot"]),load["source_well"])
        fill=max(0,load["load_ul"]-amounts.get(location,0))
        if fill:
            if load["reagent"]=="Pd":raise ValueError("Retained direct Pd source cannot cover R2; no bulk refill exists")
            if load["reagent"]=="substrate_stock":raise ValueError("Retained SM/IS source cannot cover R2; no stock refill is planned")
            record=records[load["reagent"]]
            if record["kind"]=="direct":raise ValueError("Retained direct stock cannot cover R2")
            needed.append((record,location,fill))
    for batch in sorted({r[0]["carrier_id"].split('-')[1] for r in needed}):
        subset=[r for r in needed if r[0]["carrier_id"].split('-')[1]==batch]
        carriers=list({r["carrier_id"]:r for r,_,_ in subset}.values())
        bulk_load(plan,carriers,config,prepared=True)
        for record,location,fill in subset:
            source=[record["carrier_id"],record["source_well"]]
            plan.mix(source);plan.transfer(source,list(location),fill,"automatic R2 refill "+record["stock_id"]);plan.mix(location)
        bulk_off(plan,carriers)
    plan.steps.append(dict(type="pause",message="R2 ligand sources refilled robotically. Retain original SM/IS tube 4 D2, RockPhos and all four Pd tubes without refill. Restore the SAME reaction block in slot 3 with 23 NEW EMPTY vials. R2 dosing will add 25 uL SM/IS to each before catalysts. Replace reservoir 2 with a NEW EMPTY one for R2 workup-fluid preparation. Load raw sources only when the R2 hold requests them. No hand aliquoting."))
    return plan.report()


def refill_source(config,plan,live=False):
    if live: validate_source_reach(config, plan)
    source='from opentrons import protocol_api\n'+repr_constants(config,plan,live)
    source+='requirements={"robotType":"OT-2","apiLevel":"2.18"}\nmetadata={"protocolName":"Automatic R2 stock refill"}\n'+LIQUID_RUNTIME
    source+='''
def run(protocol: protocol_api.ProtocolContext):
    if DEMO and not protocol.is_simulating():raise RuntimeError("Preview only; actual stock preparation/history required")
    tips=protocol.load_labware("opentrons_96_tiprack_20ul" if CONFIG["robot"]["single"]=="p20_single_gen2" else "opentrons_96_tiprack_300ul",5)
    multi_tips=[protocol.load_labware("opentrons_96_tiprack_300ul",s) for s in (8,9)]
    single=protocol.load_instrument(CONFIG["robot"]["single"],"left",tip_racks=[tips])
    multi=protocol.load_instrument("p300_multi_gen2","right",tip_racks=multi_tips)
    labware={"working1":protocol.load_labware(CONFIG["robot"]["ligand_source_labware"],1),"working4":protocol.load_labware(CONFIG["robot"]["ligand_source_labware"],4)}
    protocol.pause("Retain the ORIGINAL working tubes at slots 1/4, with the recorded residual volumes after R1. UNCAP the ligand working tubes before resuming automatic top-ups. Keep the retained SM/IS and Pd tubes capped; they need no refill. Do not replace/discard RockPhos. Temporarily remove the reaction block and LC plate from slots 3/6 for stock-carrier loading. Do not reweigh chemicals or add stock by hand. Review any R1 spill/transfer failure before using the calculated top-ups.")
    execute_liquid_plan(protocol,PLAN,labware,single,multi)
'''
    return source
