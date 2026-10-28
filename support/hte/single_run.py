"""One fixed 48-reaction screen: direct source vials and one loaded deck."""
from __future__ import annotations

import copy
import math
from collections import Counter
from pathlib import Path

from .io import read_csv, read_json, write_csv, write_json, digest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {
    "reaction_ul": 100, "substrate_M": 0.1, "ligand_mol_percent": 6, "pd_mol_percent": 12,
    "substrate_stock_mM": 500, "ligand_stock_mM": 20, "pd_stock_mM": 60,
    "temperature_C": 95, "reaction_minutes": 240, "reaction_rpm": 500,
    "stock_mix_rpm": 750, "stock_mix_seconds": 120,
    "workup_ul": 400, "aliquot_ul": 20, "lc_diluent_ul": 480,
    "open_mix_rpm": 750, "open_mix_seconds": 120,
    "tube_dead_ul": 150, "tube_max_ul": 1600, "reservoir_dead_ul": 1500,
    "ligand_consumption_margin": 1.15, "minimum_ligand_mass_mg": 2,
    "aspirate_height_mm": 1.5, "sample_aspirate_height_mm": 1.5,
    "reaction_definition": "support/hte_inputs/labware/paradox_48_wellplate_2000ul_hs.json",
    "lc_definition": "support/hte_inputs/labware/vwr_96_wellplate_2200ul_hs.json",
    "reservoir_definition": "support/hte_inputs/labware/axygen_12_reservoir_12000ul.json",
    "stock_definition": "support/hte_inputs/labware/htel_vialholder_48_2mL.json",
}
RESERVOIR = [
    ("A1", "toluene", 9000), ("A2", "toluene", 9000),
    ("A3", "quench", 9000), ("A4", "quench", 9000), ("A5", "quench", 9000),
    ("A6", "lc_diluent", 10000), ("A7", "lc_diluent", 10000),
    ("A8", "lc_diluent", 10000), ("A9", "lc_diluent", 10000), ("A10", "lc_diluent", 10000),
    ("A11", "acetonitrile", 3500),
]


def build_plan():
    c = copy.deepcopy(CONFIG)
    design = read_csv(ROOT / "support/campaigns/hackathon2026/round1_design.csv")
    all_ligands = read_csv(ROOT / "support/hte_inputs/ligands.csv")
    ligands = {r["ligand_id"]: r for r in all_ligands if r["ligand_id"] != "L07"}
    counts = Counter(row[k] for row in design for k in ("ligand_a", "ligand_b"))
    if len(design) != 48 or set(counts) != set(ligands) or len({r['pair_id'] for r in design}) != 48:
        raise ValueError("Expected the canonical 48 unique pairs covering all 30 ligands")
    holder = read_json(ROOT / c['stock_definition'])
    free = iter(well for col in holder['ordering'] for well in col)
    locations = {key: ['stocks', next(free)] for key in ligands}
    stocks = []
    for key, row in ligands.items():
        mw = float(row['molecular_weight_g_mol'])
        required = counts[key] * 30 * c['ligand_consumption_margin'] + c['tube_dead_ul'] + 1
        mass = math.ceil(max(c['minimum_ligand_mass_mg'], required * .02 * mw / 1000) * 10) / 10
        volume = mass / mw * 1e6 / c['ligand_stock_mM']
        stocks.append(dict(stock_id=key, name=row['name'], mass_mg=mass, add_solvent_ul=volume,
                           solvent='toluene', location=locations[key], stock_mM=20, uses=counts[key]))
    roles = ['SM_IS', 'Pd', 'IS_MASTER', 'SM_FIT', 'SM_CHECK', 'P_FIT', 'P_CHECK',
             'HIGH', 'LOW', 'CHECK', 'IS_WORK', 'MATRIX']
    for key in roles:
        locations[key] = ['stocks', next(free)]
    stocks += [
        dict(stock_id='SM_IS', name='Pyridine-2-sulfonyl fluoride + naphthalene', mass_mg=96.7,
             naphthalene_mass_mg=7.7, add_solvent_ul=1200, solvent='toluene', location=locations['SM_IS'], stock_mM=500),
        dict(stock_id='Pd', name='Pd(COD)(DQ)', mass_mg=27.3, add_solvent_ul=1200,
             solvent='toluene', location=locations['Pd'], stock_mM=60),
        dict(stock_id='IS_MASTER', name='Naphthalene (analytical master)', mass_mg=10,
             add_solvent_ul=10 / 128.17 * 1e6 / 50, solvent='acetonitrile', location=locations['IS_MASTER'], stock_mM=50),
    ]
    for key in ['SM_FIT', 'SM_CHECK', 'P_FIT', 'P_CHECK']:
        mw, conc = (161.16, 20) if key.startswith('SM') else (97.09, 40)
        stocks.append(dict(stock_id=key, name='Pyridine-2-sulfonyl fluoride' if key.startswith('SM') else '2-Fluoropyridine',
                           mass_mg=5, add_solvent_ul=5 / mw * 1e6 / conc,
                           solvent='lc_diluent', location=locations[key], stock_mM=conc))
    liquids = {(f'res', well): float(volume) for well, _, volume in RESERVOIR}
    initial = dict(liquids)
    for loc in locations.values(): liquids[tuple(loc)] = 0
    steps, current_tip = [], {1: None, 8: None}
    def drop():
        steps.append(dict(type='drop'))
        current_tip.update({1: None, 8: None})
    def transfer(source, dest, volume, *, chemical=None, channels=1, sample=False):
        nonlocal steps
        count = math.ceil(volume / 250)
        each = volume / count
        if each < 20 - 1e-6: raise ValueError(f'Transfer below p300 minimum: {each}')
        key = chemical or str(source)
        for _ in range(count):
            extra = 1 if current_tip[channels] != key else 0
            withdrawal = channels * (each + extra)
            if isinstance(source, str):
                pool = [well for well, liquid, _ in RESERVOIR if liquid == source]
                src = next((['res', well] for well in pool if liquids[('res', well)] - withdrawal >= c['reservoir_dead_ul'] - 1e-6), None)
                if src is None: raise ValueError('Insufficient reservoir load for ' + source)
            else: src = source
            loc = tuple(src)
            dead = c['reservoir_dead_ul'] if src[0] == 'res' else c['tube_dead_ul'] if src[0]=='stocks' else 0
            if liquids[loc] - withdrawal < dead - 1e-6: raise ValueError(f'Source reserve exhausted: {src}')
            liquids[loc] -= withdrawal
            for target in dest if channels == 8 else [dest]:
                address = tuple(target)
                liquids[address] = liquids.get(address, 0) + each
                if address[0]=='stocks' and liquids[address] > c['tube_max_ul'] + 1e-6:
                    raise ValueError('Stock exceeds headspace limit: ' + str(address))
            steps.append(dict(type='transfer', source=src, dest=dest, volume=each, channels=channels,
                              fresh=extra == 1, chemical=key, sample=sample))
            current_tip[channels] = key
    def mix(loc, cycles=6):
        drop()
        available = liquids[tuple(loc)]
        volume = min(200, available - (c['tube_dead_ul'] if loc[0]=='stocks' else 30))
        if volume < 20: raise ValueError('Not enough liquid for safe mixing')
        steps.append(dict(type='mix', location=loc, volume=volume, cycles=cycles))
        current_tip[1] = None
    def group_fill(records):
        for liquid in sorted({s['solvent'] for s in records}):
            for stock in records:
                if stock['solvent'] == liquid:
                    transfer(liquid, stock['location'], stock['add_solvent_ul'], chemical=liquid)
            drop()
        for stock in records: mix(stock['location'], 8)

    group_fill([s for s in stocks if s['stock_id'] in {*ligands, 'SM_IS', 'Pd'}])
    steps.append(dict(type='shake_stocks', rpm=c['stock_mix_rpm'], seconds=c['stock_mix_seconds']))
    steps.append(dict(type='pause', message='Stock-holder shaking complete. Reaction stocks prepared in their final tubes. Confirm holder back in slot 1, A1 at back-left. Keep 30 ligand vials A1:F5 plus SM_IS A6 and Pd B6 OPEN for dosing. Keep analytical/working vials C6,D6,E6,F6,A7,B7,C7,D7,E7,F7 CAPPED until the standards-preparation prompt. Check liquids, bubbles and visible solids. All 48 reaction vials must be EMPTY and UNCAPPED in slot 3. Resume for dosing.'))
    for key, volume in [('SM_IS', 20), *[(k, 30) for k in ligands], ('Pd', 20)]:
        affected = design if key in ('SM_IS', 'Pd') else [r for r in design if key in (r['ligand_a'], r['ligand_b'])]
        for index, row in enumerate(affected):
            transfer(locations[key], ['reaction', row['well']], volume, chemical=key)
            steps[-1]['mix_source'] = index == 0 and key in {*ligands, 'Pd'}
        drop()
    split_reaction = len(steps)
    group_fill([s for s in stocks if s['stock_id'] in {'IS_MASTER', 'SM_FIT', 'SM_CHECK', 'P_FIT', 'P_CHECK'}])
    # Diluent additions are grouped to conserve clean tips.
    working = [('HIGH', [('SM_FIT',100),('P_FIT',50)],250),
               ('CHECK',[('SM_CHECK',100),('P_CHECK',50)],250),
               ('IS_WORK',[('IS_MASTER',20)],480)]
    for target, _, dil in working: transfer('lc_diluent', locations[target], dil, chemical='lc_diluent')
    drop()
    for target, sources, _ in working:
        for source, vol in sources:transfer(locations[source], locations[target], vol)
        mix(locations[target])
    for target, source in [('LOW', 'HIGH')]:
        transfer('lc_diluent', locations[target], 380, chemical='lc_diluent')
        transfer(locations[source], locations[target], 20)
        mix(locations[target])
    transfer('toluene', locations['MATRIX'], 100, chemical='toluene')
    transfer('quench', locations['MATRIX'], 400, chemical='quench')
    mix(locations['MATRIX'])
    calibration = []
    levels = [(0, None, 0), (10, 'LOW', 20), (50, 'LOW', 100), (200, 'HIGH', 20),
              (500, 'HIGH', 50), (1000, 'HIGH', 100), (800, 'CHECK', 80)]
    for i, (concentration, strength, amount) in enumerate(levels):
        sample_id = 'CAL-' + ('BLANK' if i == 0 else 'CHECK' if i == 6 else f'{i:02d}')
        well = 'ABCDEFG'[i] + '7'
        for analyte in ('substrate','product'):
            calibration.append(dict(sample_id=sample_id, well=well, analyte=analyte, role='check' if i==6 else 'calibration',
                                    concentration_uM=concentration, internal_standard_concentration_uM=80,
                                    internal_standard_identity='naphthalene', internal_standard_cas='91-20-3',
                                    area='', internal_standard_area='', method_id='', channel=''))
        dest = ['lc', well]
        transfer('lc_diluent', dest, 460 - amount, chemical='lc_diluent')
        transfer(locations['IS_WORK'], dest, 20)
        transfer(locations['MATRIX'], dest, 20)
        if amount: transfer(locations[strength], dest, amount)
        mix(dest, 4)
    drop()
    split_hold = len(steps)
    for col in range(1, 7):
        transfer('lc_diluent', [['lc', row+str(col)] for row in 'ABCDEFGH'], 480, chemical='lc_diluent', channels=8)
    drop()
    for row in design: transfer('quench', ['reaction', row['well']], 400, chemical='quench')
    drop()
    split_quench = len(steps)
    for row in design:
        transfer(['reaction', row['well']], ['lc', row['lc_well']], 20, chemical=row['sample_id'], sample=True)
        drop()
    for stock in stocks:
        loc = tuple(stock['location'])
        stock['final_remaining_ul'] = liquids[loc]
        if liquids[loc] < c['tube_dead_ul'] - 1e-6: raise ValueError('Tube reserve violated')
    dosing = [dict(**row, reaction_volume_ul=100, substrate_umol=10, workup_ul=400, aliquot_ul=20,
                   diluent_ul=480, internal_standard_final_uM=80) for row in design]
    first_tips=sum(op['type']=='mix' or op['type']=='transfer' and op['channels']==1 and op['fresh'] for op in steps[:split_hold])
    total_tips=sum(op['type']=='mix' or op['type']=='transfer' and op['channels']==1 and op['fresh'] for op in steps)
    if not first_tips < total_tips <= 192:raise ValueError('Single-channel tip budget exceeds two racks')
    return dict(config=c, locations=locations, stocks=stocks, dosing=dosing, calibration=calibration,
                tips=dict(single_before_workup=first_tips,single_total=total_tips,multi_columns=1),
                reservoir=[dict(well=w, liquid=k, load_ul=v, final_remaining_ul=liquids[('res',w)]) for w,k,v in RESERVOIR],
                steps_before_reaction=steps[:split_reaction], steps_during_hold=steps[split_reaction:split_hold],
                steps_quench=steps[split_hold:split_quench], steps_sample=steps[split_quench:],
                final_volumes=[dict(location=list(k), volume_ul=v) for k,v in liquids.items()],
                source_files={p: digest(ROOT/p) for p in ['support/hte_inputs/ligands.csv', 'support/campaigns/hackathon2026/round1_design.csv',
                                                         c['stock_definition'],c['reaction_definition'],c['lc_definition'],c['reservoir_definition']]})


RUNTIME = '''
import time
from opentrons import protocol_api
requirements = {"robotType": "OT-2", "apiLevel": "2.18"}
metadata = {"protocolName": "Single 48-reaction screen"}

def run(ctx: protocol_api.ProtocolContext):
    c = PLAN['config']
    hs = ctx.load_module('heaterShakerModuleV1', 10)
    adapter = hs.load_adapter('opentrons_universal_flat_adapter')
    lw = {name: ctx.load_labware_from_definition(DEFINITIONS[name], slot)
          for name, slot in [('stocks',1),('res', 2), ('reaction', 3), ('lc', 6)]}
    lt = [ctx.load_labware('opentrons_96_tiprack_300ul', s) for s in (5, 8)]
    rt = ctx.load_labware('opentrons_96_tiprack_300ul', 9)
    single = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=lt)
    multi = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=[rt])
    def drop():
        for p in (single, multi):
            if p.has_tip: p.drop_tip()
    def pick(p):
        try: p.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause('Replace empty tip racks for this pipette in the SAME slots; then resume.')
            p.reset_tipracks();p.pick_up_tip()
    def steps(items):
        for op in items:
            if op['type'] == 'drop': drop();continue
            if op['type'] == 'pause': drop();ctx.pause(op['message']);continue
            if op['type'] == 'shake_stocks': drop();shake_stocks(op);continue
            if op['type'] == 'mix':
                drop();pick(single)
                well=lw[op['location'][0]][op['location'][1]]
                single.flow_rate.aspirate=60;single.flow_rate.dispense=100
                single.mix(op['cycles'],op['volume'],well.bottom(1.5));single.drop_tip();continue
            p=multi if op['channels']==8 else single
            if op['fresh']:
                if p.has_tip:p.drop_tip()
                pick(p)
            if not p.has_tip:raise RuntimeError('Tip continuity lost: do not skip steps or resume midway.')
            src=lw[op['source'][0]][op['source'][1]]
            dest=op['dest'][0] if op['channels']==8 else op['dest']
            target=lw[dest[0]][dest[1]]
            v=op['volume'];extra=1 if op['fresh'] else 0
            slow=op.get('sample',False)
            p.flow_rate.aspirate=15 if slow else 60
            p.flow_rate.dispense=30 if slow else 100
            if op.get('mix_source'):
                p.mix(2,min(100,v),src.bottom(1.5))
            if op['fresh']:
                for _ in range(2):
                    p.aspirate(v+extra,src.bottom(1.5));ctx.delay(seconds=.5)
                    p.dispense(v+extra,src.bottom(1.5))
            p.aspirate(v+extra,src.bottom(1.5));ctx.delay(seconds=.5)
            flow=p.flow_rate.aspirate
            p.flow_rate.aspirate=flow*.1 if slow else flow
            p.air_gap(2);p.flow_rate.aspirate=flow
            p.dispense(v+2,target.top(2));ctx.delay(seconds=.5)
    def move_block_to_module():
        hs.open_labware_latch();ctx.move_labware(lw['reaction'],adapter,use_gripper=False);hs.close_labware_latch()
    def move_block_back():
        hs.deactivate_shaker();hs.deactivate_heater();hs.open_labware_latch()
        ctx.move_labware(lw['reaction'],3,use_gripper=False)
    def cool_module():
        hs.close_labware_latch()
        hs.deactivate_shaker();hs.deactivate_heater()
        while not ctx.is_simulating() and (hs.current_temperature is None or hs.current_temperature>30):
            ctx.pause('Heater is OFF. Wait for the heater-shaker plate reading to reach <=30 C before unheated shaking. Cooling is passive. Reaction-vial cooling is confirmed separately before opening. Resume afterward.')
    def shake_stocks(op):
        cool_module()
        ctx.pause('Before dosing: leave the 30 ligand vials A1:F5 plus SM_IS A6 and Pd B6 OPEN for stock shaking. Keep the ten analytical/working vials C6,D6,E6,F6,A7,B7,C7,D7,E7,F7 CAPPED. The confirmed compatible stock holder moves from 1 to heater-shaker 10 at the next prompt. Reservoir and LC plate stay in place. Stock shaking: 750 rpm for 2 minutes, heater OFF.')
        hs.open_labware_latch()
        ctx.move_labware(lw['stocks'],adapter,use_gripper=False)
        hs.close_labware_latch()
        ctx.comment('STOCK SHAKE START: reaction-stock vials OPEN; analytical vials capped; heater off; before all reaction dosing.')
        try:
            hs.set_and_wait_for_shake_speed(op['rpm']);ctx.delay(seconds=op['seconds'])
        finally:
            hs.deactivate_shaker();hs.deactivate_heater()
        hs.open_labware_latch()
        ctx.move_labware(lw['stocks'],1,use_gripper=False)
        ctx.delay(seconds=15)
    ctx.pause('Use ONLY the one-run loading sheet. Stock holder home: 1; it moves to 10 and back for pre-dose shaking. ONE reservoir and SAME LC plate stay on deck. Check offsets, 1.5 mm bottom clearance, capped stock-vial height <=45 mm and confirmed stock-holder mounting on the flat adapter. Slots 4/7/11 empty. p300 single LEFT; p300 eight-channel RIGHT. No pipette change. Confirm actual labware/solvent compatibility before resuming.')
    ctx.pause('Load weighed solids directly in their listed final glass vials. Five working vials start EMPTY. Open ligand vials A1:F5 plus SM_IS A6 and Pd B6 in the STOCK holder. Keep analytical vials C6:F7 capped until the three-hour prompt. Load 48 EMPTY UNCAPPED reaction vials and an EMPTY LC plate. Reservoir: staff-sheet loads. Do not use earlier two-round files.')
    steps(PLAN['steps_before_reaction']);drop()
    ctx.pause('Hand-tighten ALL 48 reaction-vial screw caps. The 32 reaction-stock vials are finished and may remain OPEN. Keep the ten analytical/working vials capped until their preparation prompt. Cover the reservoir and empty LC plate in place. Move block 3 -> heater-shaker 10 at the next prompt. No source-holder or reservoir swaps.')
    move_block_to_module()
    start=None
    try:
        hs.set_and_wait_for_temperature(c['temperature_C']);hs.set_and_wait_for_shake_speed(c['reaction_rpm'])
        hold_seconds=c['reaction_minutes']*60
        standards_after=max(0,hold_seconds-60*60)
        start=time.monotonic();deadline=start+hold_seconds
        ctx.pause('REACTION HOLD START: start an external timer NOW. Nominal heated hold is 4 hours. Longer holds and a later quench are permitted; record actual times. Resume now for the standards-preparation prompt after 3 hours. Heating and shaking continue during App pauses, so a long pause extends the heated hold.')
        # Make aqueous standards in the last hour rather than leaving them for four hours.
        ctx.delay(seconds=standards_after if ctx.is_simulating() else max(0,start+standards_after-time.monotonic()))
        ctx.pause('Three hours into the nominal reaction hold: REMOVE reservoir and LC plate covers in place. Uncap analytical source/working vials C6,D6,E6,F6,A7,B7,C7,D7,E7,F7 in the STOCK holder. Used ligand, SM_IS and Pd stocks may remain OPEN. Resume to prepare standards; record any extension of the nominal heated hold.')
        steps(PLAN['steps_during_hold']);drop()
        ctx.pause('Seven mixed-analyte standards prepared in LC wells A7:G7. Cover the LC plate and reservoir IN PLACE against evaporation. All source/working vials are now finished and may remain OPEN. Resume to finish the nominal hold; longer actual holds are recorded. Remove covers only at the workup prompt. One final LC handoff.')
        if not ctx.is_simulating() and time.monotonic()>=deadline:
            ctx.comment('Nominal hold elapsed during standards preparation/pauses. Continuing with the completed standards; actual heated duration is recorded at heater-off.')
        ctx.delay(seconds=min(60*60,hold_seconds) if ctx.is_simulating() else max(0,deadline-time.monotonic()))
    finally:
        hs.deactivate_shaker();hs.deactivate_heater()
        if start is not None:
            if ctx.is_simulating():ctx.comment('HEATED HOLD COMPLETE (SIMULATION): nominal duration only; no physical elapsed time measured.')
            else:ctx.comment(f'HEATED HOLD COMPLETE: actual elapsed heated hold {(time.monotonic()-start)/60:.2f} min; heater OFF.')
    heat_off=time.monotonic()
    ctx.pause('Four-hour nominal hold complete; heater and shaker OFF. Longer actual hold or delay before quench is allowed; record times. Move the SEALED reaction block back to slot 3 at the next prompt using approved thermal handling. Leave ALL reaction vials capped and allow block/vials to cool to <=30 C before opening. Continue this SAME program; retain all labware and tip racks.')
    move_block_back()
    # Same context and pipettes: preserve deck state and used tips through workup.
    cool_module()
    ctx.pause('Confirm the SEALED reaction vials AND block in slot 3 have cooled to <=30 C before opening; check with a suitable contact temperature probe. The module reading covers its own plate. Extra cooling/waiting time is allowed and recorded before quench. Use the SAME reservoir, LC plate and partly used tip racks; standards occupy A7:G7. REMOVE LC/reservoir covers. Keep reaction vials capped while LC diluent is added. Used source/working vials may remain OPEN.')
    # First fill LC destinations, then request uncapping before any quench.
    dilution=[op for op in PLAN['steps_quench'] if op.get('chemical')=='lc_diluent']
    steps(dilution);drop()
    ctx.pause('Now unscrew all 48 cooled reaction-vial caps. Robot adds 400 uL quench per vial. Keep all vials OPEN for the following 750 rpm / 2 minute mixing and sampling.')
    quench=[op for op in PLAN['steps_quench'] if op.get('chemical')=='quench']
    if not ctx.is_simulating():ctx.comment(f'QUENCH START: {(time.monotonic()-heat_off)/60:.2f} min since heater-off, including cooling and handling.')
    steps(quench);drop()
    if not ctx.is_simulating():ctx.comment(f'QUENCH COMPLETE: {(time.monotonic()-heat_off)/60:.2f} min since heater-off.')
    move_block_to_module()
    try:
        hs.set_and_wait_for_shake_speed(750);ctx.delay(seconds=120)
    finally:hs.deactivate_shaker();hs.deactivate_heater()
    move_block_back();ctx.delay(seconds=15)
    steps(PLAN['steps_sample']);drop()
    ctx.pause('Recap reaction vials for storage. Leave LC plate UNCOVERED. Move ONLY the LC plate from 6 to the cooled heater-shaker at the next prompt; preserve A1 orientation. Stock-vial holder and reservoir remain in place.')
    hs.open_labware_latch();ctx.move_labware(lw['lc'],adapter,use_gripper=False);hs.close_labware_latch()
    try:
        hs.set_and_wait_for_shake_speed(750);ctx.delay(seconds=120)
    finally:hs.deactivate_shaker();hs.deactivate_heater()
    hs.open_labware_latch();ctx.move_labware(lw['lc'],protocol_api.OFF_DECK,use_gripper=False)
    ctx.pause('Seal the LC plate and hand it to LC ONCE. Inject the seven standards FIRST, followed by the 48 samples, using lc-injections.csv and the actual 1.7-minute method settings. Never inject unused wells. Archive real export, actual injection map and robot logs. There is no second reaction batch.')
'''


def generate(output):
    output = Path(output);output.mkdir(parents=True, exist_ok=True)
    tables = output/'tables';tables.mkdir(exist_ok=True)
    plan = build_plan()
    defs = {key: read_json(ROOT / plan['config'][setting]) for key, setting in
            [('stocks','stock_definition'),('res','reservoir_definition'),('reaction','reaction_definition'),('lc','lc_definition')]}
    # The analytical vials are capped until standards preparation.
    # Use a conservative travel envelope; retain HTEL's well coordinates.
    defs['stocks']['dimensions']['zDimension']=max(45,defs['stocks']['dimensions']['zDimension'])
    # HTEL confirmed the holder seats securely on the universal flat adapter.
    # No pipetting occurs while this holder is on the module.
    defs['stocks']['stackingOffsetWithLabware']={'opentrons_universal_flat_adapter':{'x':0,'y':0,'z':0}}
    (output / 'run_screen.py').write_text(
        '# Generated by hte.single_run; self-contained, local OT-2 only.\n'
        + f'PLAN={plan!r}\nDEFINITIONS={defs!r}\n' + RUNTIME)
    write_json(tables/'plan.json',plan)
    write_csv(tables/'dosing.csv',plan['dosing'])
    write_csv(tables/'calibration-plan.csv',plan['calibration'])
    write_csv(tables/'weighing.csv',[
        dict(ID=s['stock_id'],material=s['name'],mass_mg=s['mass_mg'],
             naphthalene_in_same_tube_mg=s.get('naphthalene_mass_mg',''),slot=1,well=s['location'][1],
             robot_adds_ul=round(s['add_solvent_ul'],1),solvent=s['solvent'],remaining_ul=round(s['final_remaining_ul'],1))
        for s in plan['stocks']])
    write_csv(tables/'tube-map.csv',[dict(ID=key,slot=1,well=loc[1],initial='weighed chemicals' if key in {s['stock_id'] for s in plan['stocks']} else 'empty') for key,loc in plan['locations'].items()])
    write_csv(tables/'reservoir.csv',plan['reservoir'])
    cal_unique=list({r['sample_id']:r for r in plan['calibration']}.values())
    injections=[dict(inj_no=i,sample_id=row['sample_id'],well=row['well'] if i<=len(cal_unique) else row['lc_well'],method_id='')
                for i,row in enumerate([*cal_unique,*plan['dosing']],1)]
    write_csv(tables/'lc-injections.csv',injections)
    generated=['run_screen.py',*[f'tables/{name}' for name in ['plan.json','dosing.csv','calibration-plan.csv',
               'weighing.csv','tube-map.csv','reservoir.csv','lc-injections.csv']]]
    write_json(tables/'files.sha256.json',{name:digest(output/name) for name in generated})
    return plan
