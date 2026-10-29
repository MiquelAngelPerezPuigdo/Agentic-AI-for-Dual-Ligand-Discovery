import re
import ast
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from hte.io import read_json, read_csv, digest
from hte.single_run import build_plan, generate, RESERVOIR

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def plan():return build_plan()


def test_single_weighing_each_ligand_and_one_glass_holder(plan):
    ligands=[r for r in plan['stocks'] if re.fullmatch(r'L\d+',r['stock_id'])]
    assert len(ligands)==len({r['stock_id'] for r in ligands})==30
    assert len({tuple(loc) for loc in plan['locations'].values()})==42
    assert {loc[0] for loc in plan['locations'].values()}=={'stocks'}
    assert all(loc[1][-1]!='8' for loc in plan['locations'].values())
    definition=read_json(ROOT/plan['config']['stock_definition'])
    assert len(definition['wells'])==48
    assert all(definition['wells'][loc[1]]['totalLiquidVolume']==2000 for loc in plan['locations'].values())


def test_reserves_headspace_and_material_budget(plan):
    assert max(s['add_solvent_ul'] for s in plan['stocks'])<=1600
    assert min(s['final_remaining_ul'] for s in plan['stocks'])>=150
    assert min(r['final_remaining_ul'] for r in plan['reservoir'])>=1500
    assert all(r['load_ul']<=10000 for r in plan['reservoir'])
    assert next(s for s in plan['stocks'] if s['stock_id']=='Pd')['mass_mg']==27.3
    assert next(s for s in plan['stocks'] if s['stock_id']=='L03')['mass_mg']<10
    assert sum(s['mass_mg'] for s in plan['stocks'] if re.fullmatch('L\\d+',s['stock_id']))<85
    assert plan['tips']['single_total']==170
    assert plan['tips']['multi_columns']==6
    assert all(20<=op['volume']<=250 for group in ['steps_before_reaction','steps_calibration','steps_quench','steps_sample']
               for op in plan[group] if op['type']=='transfer')


def test_stock_shaking_after_preparation_before_any_reaction_dose(plan):
    ops=plan['steps_before_reaction']
    index,shake=next((i,op) for i,op in enumerate(ops) if op['type']=='shake_stocks')
    assert sum(op['type']=='shake_stocks' for op in ops)==1
    assert shake['rpm']==750 and shake['seconds']==120
    assert len({tuple(op['location']) for op in ops[:index] if op['type']=='mix'})==32
    reaction_doses=[i for i,op in enumerate(ops) if op['type']=='transfer' and op['dest'][0]=='reaction']
    assert min(reaction_doses)>index


def test_lc_aliquots_precede_diluent_one_complete_column_at_a_time(plan):
    # Reaction workup stays separate: LC wells receive quenched extracts, not raw reactions.
    quench_totals=defaultdict(float)
    for op in plan['steps_quench']:
        if op['type']!='transfer':continue
        assert op['chemical']=='quench' and op['dest'][0]=='reaction'
        quench_totals[op['dest'][1]]+=op['volume']
    assert quench_totals=={r['well']:400 for r in plan['dosing']}

    transfers=[op for op in plan['steps_sample'] if op['type']=='transfer']
    expected={r['lc_well']:r for r in plan['dosing']}
    volumes=defaultdict(float)
    previous_column_end=-1
    for column in range(1,7):
        wells={row+str(column) for row in 'ABCDEFGH'}
        aliquots=[(i,op) for i,op in enumerate(transfers)
                  if op['channels']==1 and op['dest'][1] in wells]
        dilutions=[(i,op) for i,op in enumerate(transfers)
                   if op['channels']==8 and any(dest[1] in wells for dest in op['dest'])]
        assert len(aliquots)==8 and len(dilutions)==2
        assert {op['dest'][1] for _,op in aliquots}==wells
        assert previous_column_end<min(i for i,_ in aliquots)
        assert max(i for i,_ in aliquots)<min(i for i,_ in dilutions)
        for _,op in aliquots:
            well=op['dest'][1]
            assert op['dest'][0]=='lc' and volumes[well]==0
            assert op['source']==['reaction',expected[well]['well']]
            assert op['chemical']==expected[well]['sample_id']
            assert op['sample'] and op['fresh'] and op['volume']==20
            volumes[well]+=op['volume']
        assert [op['fresh'] for _,op in dilutions]==[True,False]
        for _,op in dilutions:
            assert op['source'][0]=='res' and op['chemical']=='lc_diluent'
            assert op['volume']==240
            assert {tuple(dest) for dest in op['dest']}=={('lc',well) for well in wells}
            for well in wells:volumes[well]+=op['volume']
        assert all(volumes[well]==500 for well in wells)
        previous_column_end=max(i for i,_ in dilutions)
    assert len(transfers)==60 and len(volumes)==48


def test_molar_and_solvent_balance_through_every_liquid_transfer(plan):
    # Independently propagate conserved solutes and toluene through real transfer steps.
    volume={('res',w):v for w,_,v in RESERVOIR}
    solute=defaultdict(lambda:defaultdict(float))
    for w,kind,v in RESERVOIR:
        if kind=='toluene':solute[('res',w)]['toluene_ul']=v
    for s in plan['stocks']:
        loc=tuple(s['location']);key=s['stock_id'];amount=s['stock_mM']*s['add_solvent_ul']/1000
        if key=='SM_IS':solute[loc].update(SM=amount,N=amount/10)
        elif key=='IS_MASTER':solute[loc]['N']=amount
        else:solute[loc]['SM' if key.startswith('SM_') else 'P' if key.startswith('P_') else key]=amount
    def apply(steps):
        for op in steps:
            if op['type']!='transfer':continue
            src=tuple(op['source']);n=op['channels'];v=op['volume'];extra=1 if op['fresh'] else 0
            before=volume[src];concentration={k:a/before for k,a in solute[src].items()}
            withdrawal=n*(v+extra)
            volume[src]-=withdrawal
            for k,c in concentration.items():solute[src][k]-=c*withdrawal
            for dest in op['dest'] if n==8 else [op['dest']]:
                dest=tuple(dest);volume[dest]=volume.get(dest,0)+v
                for k,c in concentration.items():solute[dest][k]+=c*v
    apply(plan['steps_before_reaction'])
    for r in plan['dosing']:
        loc=('reaction',r['well']);a=solute[loc]
        assert volume[loc]==pytest.approx(100)
        assert a['SM']==pytest.approx(10)
        assert a['N']==pytest.approx(1)
        assert a['Pd']==pytest.approx(1.2)
        assert a[r['ligand_a']]==pytest.approx(.6)
        assert a[r['ligand_b']]==pytest.approx(.6)
        # A known 50% conversion, used only in this synthetic accounting test.
        a['SM']=5;a['P']=5
    apply(plan['steps_calibration'])
    for row in plan['calibration']:
        loc=('lc',row['well']);key='SM' if row['analyte']=='substrate' else 'P'
        assert volume[loc]==pytest.approx(500)
        assert solute[loc][key]/500*1e6==pytest.approx(row['concentration_uM'])
        assert solute[loc]['N']/500*1e6==pytest.approx(80)
        assert solute[loc]['toluene_ul']==pytest.approx(4)
    apply(plan['steps_quench']);apply(plan['steps_sample'])
    for row in plan['dosing']:
        loc=('lc',row['lc_well'])
        assert volume[loc]==pytest.approx(500)
        assert solute[loc]['P']/500*1e6==pytest.approx(400)
        assert solute[loc]['SM']/500*1e6==pytest.approx(400)
        assert solute[loc]['N']/500*1e6==pytest.approx(80)
        assert solute[loc]['toluene_ul']==pytest.approx(4)


def test_published_files_are_current(tmp_path):
    generate(tmp_path)
    for name in read_json(ROOT/'run/tables/files.sha256.json'):
        assert digest(tmp_path/name)==digest(ROOT/'run'/name),name
    tree=ast.parse((tmp_path/'run_screen.py').read_text())
    definitions=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                     and any(isinstance(t,ast.Name) and t.id=='DEFINITIONS' for t in n.targets))
    supplied=read_json(ROOT/'support/hte_inputs/labware/htel_vialholder_48_2mL.json')
    assert definitions['stocks']['wells']==supplied['wells']
    assert definitions['stocks']['dimensions']['zDimension']==45
    assert definitions['stocks']['stackingOffsetWithLabware']['opentrons_universal_flat_adapter']=={'x':0,'y':0,'z':0}
    for name in ('weighing.csv','tube-map.csv'):
        rows=read_csv(tmp_path/'tables'/name)
        assert {r['slot'] for r in rows}=={'10'}
        assert {r['after_stock_shake_slot'] for r in rows}=={'1'}


def test_real_sdk_continuous_protocol_and_tip_positions():
    from opentrons.simulate import simulate
    with (ROOT/'run/run_screen.py').open() as stream:log,_=simulate(stream)
    texts=[e['payload'].get('text','') for e in log]
    picks=[e['payload']['text'] for e in log if e['level']==0 and 'Picking up tip' in e['payload'].get('text','')]
    assert len(picks)==len(set(picks))==176  # 170 single tips + six eight-tip columns; no rack refill.
    assert sum('slot 9' in pick for pick in picks)==6
    assert sum('slot 5' in pick or 'slot 8' in pick for pick in picks)==170
    assert not any('Replace empty tip racks' in text for text in texts)
    source=(ROOT/'run/run_screen.py').read_text()
    assert '1.5 mm' in source
    assert 'starting_tip' not in source and 'STAGE=' not in source
    moves=[text for text in texts if text.startswith('Moving ')]
    assert len(moves)==7
    assert 'Stock holder' in moves[0] and moves[0].endswith('to slot 1')
    assert not any('Stock holder' in text for text in moves[1:])
    assert not any('Solvent reservoir' in text for text in moves)
    first_move=texts.index(moves[0])
    stock_preparation=[t for t in texts[:first_move] if t.startswith(('Aspirating','Dispensing','Mixing')) and 'Stock holder' in t]
    assert stock_preparation and all(' on slot 10' in t for t in stock_preparation)
    stock_dosing=[t for t in texts[first_move:] if t.startswith('Aspirating') and 'Stock holder' in t]
    assert stock_dosing and all(' on slot 1 at ' in t for t in stock_dosing)
    assert not any('Reaction block' in t and t.startswith('Dispensing') for t in texts[:first_move])
    speeds=[int(re.search(r'Shake at (\d+) RPM',text)[1]) for text in texts if 'Setting Heater-Shaker to Shake at' in text]
    assert speeds==[750,500,750,750]
    # Workup follows the completed hold in the same simulation, without a restart.
    phases=['3a. Shake the stock holder', 'STOCK SHAKE START', '3b. Check stocks before dosing',
            '4a. Seal the reactions', '4b. Start the reaction timer',
            'HEATED HOLD COMPLETE', '5. Move the sealed reaction block to cool',
            'CALIBRATION PREPARATION START',
            '6. Continue when cooling is complete',
            '7. Prepare LC samples', '8. Mix the completed LC sample plate',
            '9. Hand the sample plate to HPLC-MS']
    positions=[next(i for i,text in enumerate(texts) if phase in text) for phase in phases]
    assert positions==sorted(positions)


@pytest.mark.parametrize('hold_pause_seconds,expected_hold_minutes',[(0,240),(6*3600,360)])
def test_heated_hold_and_operator_cooling_wait_are_logged(hold_pause_seconds,expected_hold_minutes):
    # Use the SDK for robot I/O and an accelerated clock for the live timing branch.
    from types import SimpleNamespace
    from opentrons.simulate import get_protocol_api
    namespace={'__name__':'timing_test'}
    exec(compile((ROOT/'run/run_screen.py').read_text(),'run_screen.py','exec'),namespace)
    elapsed=[0.0];comments=[];pauses=[]
    namespace['time']=SimpleNamespace(monotonic=lambda:elapsed[0])
    sdk=get_protocol_api('2.18',robot_type='OT-2')
    class OperatorCooledModule:
        def __init__(self,module):self.module=module
        def __getattr__(self,name):
            if name=='current_temperature':
                raise AssertionError('Cooling must wait for the operator, not a numerical module threshold')
            return getattr(self.module,name)
    class TimedContext:
        def __getattr__(self,name):return getattr(sdk,name)
        def is_simulating(self):return False
        def load_module(self,*args,**kwargs):
            return OperatorCooledModule(sdk.load_module(*args,**kwargs))
        def delay(self,seconds=0,**kwargs):
            assert seconds>=0
            elapsed[0]+=seconds
            return sdk.delay(seconds=seconds,**kwargs)
        def pause(self,message):
            pauses.append(message)
            assert len(pauses)<100
            if message.startswith('4b. Start the reaction timer'):elapsed[0]+=hold_pause_seconds
            if message.startswith('6. Continue when cooling is complete'):elapsed[0]+=45*60
            return sdk.pause(message)
        def comment(self,message):
            comments.append(message)
            return sdk.comment(message)
    namespace['run'](TimedContext())
    heated=next(t for t in comments if t.startswith('HEATED HOLD COMPLETE: actual'))
    assert float(re.search(r'heated hold ([\d.]+) min',heated)[1])==pytest.approx(expected_hold_minutes,abs=.01)
    quench=next(t for t in comments if t.startswith('QUENCH START:'))
    assert float(re.search(r'QUENCH START: ([\d.]+) min',quench)[1])>=45
    assert any(t.startswith('QUENCH COMPLETE:') for t in comments)
    assert not any(p.startswith(('5a.','5b.')) for p in pauses)
    assert pauses[-1].startswith('9. Hand the sample plate to HPLC-MS')


def test_staff_links_and_one_authoritative_protocol_folder():
    files=[ROOT/'README.md',*(ROOT/'run').rglob('*.md'),*(ROOT/'support').rglob('*.md')]
    for file in files:
        if (ROOT/'support/archive/previous-two-round') in file.parents:
            continue  # Preserved historical pages retain their original paths.
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            p=urlsplit(link)
            if not p.scheme and p.path:assert (file.parent/p.path).exists(),(file,link)
    assert not (ROOT/'protocols').exists()
    assert set(p.name for p in (ROOT/'run').glob('*.py'))=={'run_screen.py'}
    assert {p.name for p in (ROOT/'run').iterdir() if p.is_file()}=={
        'README.md','WEIGHING.md','ANALYSIS.md','run_screen.py','bench-sheet.pdf'}


def test_larger_dead_volume_cannot_silently_drain_sources(monkeypatch):
    from hte.single_run import CONFIG
    monkeypatch.setitem(CONFIG,'tube_dead_ul',350)
    with pytest.raises(ValueError,match='reserve|mixing|reservoir load'):build_plan()
