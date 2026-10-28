import copy
from pathlib import Path

import pytest

from hte.io import read_csv,write_csv,write_json,read_json
from hte.run_analysis import process

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def lc(tmp_path):
    settings={'method_id':'SYNTHETIC_TEST_ONLY','channel':'UV_VIS_1',
              'references':{name:dict(retention_time_min=rt,window_min=.03) for name,rt in
                            [('substrate',.3),('product',.7),('internal_standard',1.2)]},
              'quantification_limit_uM':{'substrate':10,'product':10}}
    mapping=read_csv(ROOT/'run/tables/lc-injections.csv')
    for row in mapping:row['method_id']=settings['method_id']
    truth={r['sample_id']:25+i%51 for i,r in enumerate(read_csv(ROOT/'run/tables/dosing.csv'))}
    cal={r['sample_id']:float(r['concentration_uM']) for r in read_csv(ROOT/'run/tables/calibration-plan.csv')}
    rows=[]
    for index,inj in enumerate(mapping):
        key=inj['sample_id']
        values={'substrate':cal[key],'product':cal[key]} if key in cal else {
            'substrate':800*(1-truth[key]/100),'product':800*truth[key]/100}
        peaks=[(settings['references'][analyte]['retention_time_min'],conc*(2 if analyte=='substrate' else 3))
               for analyte,conc in values.items() if conc>0]
        peaks.append((1.2,1000))
        scale=.96+.01*(index%9)
        for peak,(rt,area) in enumerate(peaks,1):
            rows.append({'inj_no':inj['inj_no'],'injection_name':key,'type':'Unknown','vial_position':inj['well'],
                         'inj_volume(uL)':2,'channel_for_peak_detection':'UV_VIS_1',
                         'number_of_det_peaks':len(peaks),'peak_no':peak,'retention_time(min)':rt,
                         **{f'area_uvvis{i}(AU*min)':area*scale*(1 if i==1 else 10*i) for i in range(1,5)}})
    paths={k:tmp_path/v for k,v in {'export':'export.csv','mapping':'map.csv','settings':'settings.json'}.items()}
    write_csv(paths['export'],rows);write_csv(paths['mapping'],mapping);write_json(paths['settings'],settings)
    return paths,rows,mapping,settings,truth,tmp_path


def invoke(lc,review='Test reviewer'):
    paths,_,_,_,_,tmp_path=lc
    return process(paths['export'],paths['mapping'],paths['settings'],tmp_path/'result',review,ROOT/'run')


def test_full_htel_export_to_calibrated_yields_with_mixed_standards(lc):
    report=invoke(lc)
    assert report['batch_qc_pass'] and report['samples']==48
    _,_,_,_,truth,tmp_path=lc
    for row in read_csv(tmp_path/'result/results.csv'):
        assert float(row['yield_percent'])==pytest.approx(truth[row['sample_id']],abs=1e-8)
        assert float(row['conversion_percent'])==pytest.approx(truth[row['sample_id']],abs=1e-8)
    assert len(read_csv(tmp_path/'result/calibration.csv'))==14  # Two analytes, seven physical standards.
    assert len(read_csv(tmp_path/'result/reviewed-blanks.csv'))==2
    assert (tmp_path/'result/inputs/vendor-export.csv').read_bytes()==lc[0]['export'].read_bytes()
    assert (tmp_path/'result/inputs/run_screen.py').read_bytes()==(ROOT/'run/run_screen.py').read_bytes()
    assert (tmp_path/'result/files.sha256.json').is_file()


@pytest.mark.parametrize('fault',['missing_injection','incomplete_peaks','wrong_method','missing_channel','bad_fit','bad_check','ambiguous_peak','no_blank_review','missing_loq'])
def test_lc_faults_do_not_silently_produce_accepted_yields(lc,fault):
    paths,rows,mapping,settings,truth,tmp_path=lc
    if fault=='missing_injection':rows[:]=[r for r in rows if r['injection_name']!='R1-048']
    elif fault=='incomplete_peaks':
        for row in rows:
            if row['injection_name']=='CAL-01':row['number_of_det_peaks']=4
    elif fault=='wrong_method':mapping[0]['method_id']='OTHER'
    elif fault=='missing_channel':rows[4]['area_uvvis1(AU*min)']='n.a.'
    elif fault in ('bad_fit','bad_check'):
        for row in rows:
            if row['injection_name']==('CAL-01' if fault=='bad_fit' else 'CAL-CHECK') and row['retention_time(min)']==.7:
                row['area_uvvis1(AU*min)']*=.1
    elif fault=='ambiguous_peak':
        # A second in-window product peak in a calibration injection.
        original=next(r for r in rows if r['injection_name']=='CAL-02' and r['retention_time(min)']==.7)
        extra={**original,'peak_no':4,'retention_time(min)':.71};rows.append(extra)
        for r in rows:
            if r['injection_name']=='CAL-02':r['number_of_det_peaks']=4
    elif fault=='missing_loq':settings['quantification_limit_uM']['product']=None
    write_csv(paths['export'],rows);write_csv(paths['mapping'],mapping);write_json(paths['settings'],settings)
    messages={'missing_injection':'Mapped injections','incomplete_peaks':'Calibration peak method or QC',
              'wrong_method':'Injection mapping','missing_channel':'missing RT/number',
              'bad_fit':'back-calculation|Calibration R2','bad_check':'Independent calibration check',
              'ambiguous_peak':'requires one measured product','no_blank_review':'requires one measured substrate',
              'missing_loq':'LOQ'}
    with pytest.raises((ValueError,KeyError),match=messages[fault]):
        invoke(lc,review=None if fault=='no_blank_review' else 'Test reviewer')


def test_abnormal_is_fails_reaction_qc(lc):
    paths,rows,_,_,_,tmp_path=lc
    for row in rows:
        if row['injection_name']=='R1-001' and row['retention_time(min)']==1.2:row['area_uvvis1(AU*min)']*=5
    write_csv(paths['export'],rows)
    report=invoke(lc)
    assert not report['batch_qc_pass'] and report['rejected']==1


def test_zero_product_is_an_upper_bound_not_an_invented_yield(lc):
    paths,rows,_,_,_,tmp_path=lc
    rows[:]=[r for r in rows if not(r['injection_name']=='R1-001' and r['retention_time(min)']==.7)]
    for row in rows:
        if row['injection_name']=='R1-001':row['number_of_det_peaks']=2
    write_csv(paths['export'],rows)
    report=invoke(lc)
    row=next(r for r in read_csv(tmp_path/'result/results.csv') if r['sample_id']=='R1-001')
    assert row['yield_percent']==''
    assert float(row['yield_upper_bound_percent'])==pytest.approx(1.25)


def test_htel_plate_prefixed_vial_positions_are_accepted(lc):
    paths,rows,_,_,_,_=lc
    for row in rows:row['vial_position']='B:'+row['vial_position']
    write_csv(paths['export'],rows)
    assert invoke(lc)['batch_qc_pass']


def test_export_cannot_mix_physical_lc_plates(lc):
    paths,rows,_,_,_,_=lc
    for row in rows:
        prefix='C:' if row['injection_name']=='R1-001' else 'B:'
        row['vial_position']=prefix+row['vial_position']
    write_csv(paths['export'],rows)
    with pytest.raises(ValueError,match='plate prefix .* differs from .*one LC plate'):
        invoke(lc)


def test_changed_injection_order_requires_the_correct_physical_map(lc):
    paths,rows,mapping,_,truth,tmp_path=lc
    first,last='R1-001','R1-048'
    original={r['sample_id']:r['inj_no'] for r in mapping}
    # Real specimens retain their names/wells but are injected in a different order.
    for row in rows:
        if row['injection_name']==first:row['inj_no']=original[last]
        elif row['injection_name']==last:row['inj_no']=original[first]
    write_csv(paths['export'],rows)
    with pytest.raises(ValueError,match='physical well .* differs from mapped well'):
        invoke(lc)
    # Updating only injection numbers, as instructed, restores the correct assignment.
    for row in mapping:
        if row['sample_id']==first:row['inj_no']=original[last]
        elif row['sample_id']==last:row['inj_no']=original[first]
    write_csv(paths['mapping'],mapping)
    report=process(paths['export'],paths['mapping'],paths['settings'],tmp_path/'corrected-result',
                   'Test reviewer',ROOT/'run')
    assert report['batch_qc_pass']
    for row in read_csv(tmp_path/'corrected-result/results.csv'):
        assert float(row['yield_percent'])==pytest.approx(truth[row['sample_id']],abs=1e-8)


def test_map_cannot_relabel_physical_wells_to_another_pair(lc):
    paths,_,mapping,_,_,_=lc
    a=next(r for r in mapping if r['sample_id']=='R1-001')
    b=next(r for r in mapping if r['sample_id']=='R1-048')
    a['well'],b['well']=b['well'],a['well']
    write_csv(paths['mapping'],mapping)
    with pytest.raises(ValueError,match='Injection map well differs from the robot LC plate'):
        invoke(lc)
