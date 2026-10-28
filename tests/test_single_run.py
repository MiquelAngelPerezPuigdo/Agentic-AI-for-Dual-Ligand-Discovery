import re
import ast
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from hte.io import read_json, read_csv, digest
from hte.single_run import build_plan, generate, RESERVOIR

ROOT=Path(__file__).resolve().parents[1]


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
    assert all(20<=op['volume']<=250 for group in ['steps_before_reaction','steps_during_hold','steps_quench','steps_sample']
               for op in plan[group] if op['type']=='transfer')


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
    apply(plan['steps_during_hold'])
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
    for name in read_json(ROOT/'run/files.sha256.json'):
        assert digest(tmp_path/name)==digest(ROOT/'run'/name),name
    tree=ast.parse((tmp_path/'01_prepare_dose_react.py').read_text())
    definitions=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                     and any(isinstance(t,ast.Name) and t.id=='DEFINITIONS' for t in n.targets))
    supplied=read_json(ROOT/'hte_inputs/labware/htel_vialholder_48_2mL.json')
    assert definitions['stocks']['wells']==supplied['wells']
    assert definitions['stocks']['dimensions']['zDimension']==45


def test_real_sdk_protocols_and_continuing_tip_positions():
    from opentrons.simulate import simulate
    logs=[]
    for file in ['01_prepare_dose_react.py','02_workup.py']:
        with (ROOT/'run'/file).open() as stream:log,_=simulate(stream)
        logs.append(log)
    picks=[[e['payload']['text'] for e in log if e['level']==0 and 'Picking up tip' in e['payload'].get('text','')] for log in logs]
    assert len(picks[0])==121 and len(picks[1])==50
    assert not set(picks[0])&set(picks[1])  # No attempts to pick tips consumed in file 1.
    assert 'B4' in picks[1][1] and 'slot 8' in picks[1][1]
    assert not any('Replace empty tip racks' in e['payload'].get('text','') for log in logs for e in log)
    assert all('1.5 mm' in (ROOT/'run'/p).read_text() for p in ['01_prepare_dose_react.py','02_workup.py'])
    moves=[[e['payload']['text'] for e in log if e['payload'].get('text','').startswith('Moving ')] for log in logs]
    assert [len(group) for group in moves]==[2,4]
    assert not any('htelvialholder' in text or 'axygen' in text for group in moves for text in group)


def test_staff_links_and_one_authoritative_protocol_folder():
    files=[ROOT/'README.md',ROOT/'DEVELOPMENT.md',*(ROOT/'run').glob('*.md'),*(ROOT/'docs').glob('*.md')]
    for file in files:
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            p=urlsplit(link)
            if not p.scheme and p.path:assert (file.parent/p.path).exists(),(file,link)
    assert not (ROOT/'protocols').exists()
    assert set(p.name for p in (ROOT/'run').glob('*.py'))=={'01_prepare_dose_react.py','02_workup.py'}


def test_larger_dead_volume_cannot_silently_drain_sources(monkeypatch):
    from hte.single_run import CONFIG
    monkeypatch.setitem(CONFIG,'tube_dead_ul',350)
    with pytest.raises(ValueError,match='reserve|mixing|reservoir load'):build_plan()
