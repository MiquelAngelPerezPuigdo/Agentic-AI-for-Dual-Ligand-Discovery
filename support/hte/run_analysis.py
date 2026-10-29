"""Analyze the single 55-injection sequence; no optimizer or paid API calls."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .analytics import normalize_export, calibration_from_peaks, complete_export, analyze
from .io import read_json, read_csv, well_name, write_json, write_csv, digest, new_output

SETTINGS_TEMPLATE = {
    "method_id": None, "channel": None,
    "references": {
        "substrate": {"retention_time_min": None, "window_min": None},
        "product": {"retention_time_min": None, "window_min": None},
        "internal_standard": {"retention_time_min": None, "window_min": None}},
    "quantification_limit_uM": {"substrate": None, "product": None},
}


def analysis_config(settings):
    return {
        'schema_version': 6,
        'chemistry': {'substrate': 'pyridine-2-sulfonyl fluoride', 'product': '2-fluoropyridine',
                      'substrate_molarity_M': .1, 'reaction_volume_ul': 100,
                      'ligand_a_mol_percent': 6, 'ligand_b_mol_percent': 6, 'pd_mol_percent': 12,
                      'temperature_C': 95, 'reaction_minutes': 240,
                      'preloaded_internal_standard': {'identity': 'naphthalene', 'cas': '91-20-3'}},
        'analytics': {
            'calibration_mode': 'internal_standard', 'internal_standard': 'naphthalene',
            'internal_standard_final_uM': 80, 'internal_standard_area_tolerance_fraction': .3,
            'minimum_calibration_r2': .995, 'calibration_check_tolerance_fraction': .15,
            'calibration_fit_tolerance_fraction': .15, 'calibration_lowest_level_tolerance_fraction': .2,
            'calibration_requirements': {'minimum_nonzero_levels': 5, 'require_zero_blank': True, 'minimum_independent_checks': 1},
            'negative_concentration_tolerance_uM': 1, 'yield_tolerance_percent': 5,
            'mass_balance_tolerance_fraction': .1, 'blank_max_product_umol': .01,
            'maximum_rejected_fraction': 0, 'missing_analyte_policy': 'censor',
            'export_format': 'htel_chromeleon_wide', 'export_sheet': None, 'column_mapping': None,
            **{k: settings[k] for k in SETTINGS_TEMPLATE}},
    }


def process(export_path, mapping_path, settings_path, output, reviewed_blanks=None, run_dir='run'):
    run_dir = Path(run_dir)
    tables = run_dir/'tables'
    sources = [('vendor-export'+Path(export_path).suffix, export_path), ('injections.csv', mapping_path),
               ('lc-settings.json', settings_path), ('dosing.csv', tables/'dosing.csv'),
               ('calibration-plan.csv', tables/'calibration-plan.csv'), ('robot-plan.json', tables/'plan.json'),
               ('run_screen.py', run_dir/'run_screen.py'), ('run-files.sha256.json', tables/'files.sha256.json')]
    # Pin the entire input set before copying or parsing any of it. A source
    # edited before its turn in the copy loop must not silently become accepted.
    hashes = {name: digest(path) for name, path in sources}
    out = new_output(output)
    inputs = out / 'inputs';inputs.mkdir()
    for name, path in sources:
        shutil.copyfile(path, inputs/name)
        if digest(inputs/name) != hashes[name] or digest(path) != hashes[name]:
            raise ValueError('Input changed during snapshot: '+str(path))
    if any(digest(path) != hashes[name] for name, path in sources):
        raise ValueError('Input changed during snapshot; finish editing/exporting before analysis')

    def stable_snapshot():
        if any(digest(inputs/name) != hashes[name] for name, _ in sources):
            raise ValueError('Archived analysis input changed; use a fresh output folder')

    checksums = read_json(inputs/'run-files.sha256.json')
    for name, published in [('dosing.csv', 'tables/dosing.csv'),
                            ('calibration-plan.csv', 'tables/calibration-plan.csv'),
                            ('robot-plan.json', 'tables/plan.json'), ('run_screen.py', 'run_screen.py')]:
        if hashes[name] != checksums[published]:
            raise ValueError('Published run file changed: '+published+
                             '; reconcile with the actual robot protocol before analysis')
    # All effective settings/tables come from the exact copies returned to the
    # user, never from originals that can be edited while analysis is running.
    config = analysis_config(read_json(inputs/'lc-settings.json'))
    from .analytics import validate_analytics_settings
    validate_analytics_settings(config)
    plan = read_csv(inputs/'calibration-plan.csv')
    dosing = read_csv(inputs/'dosing.csv')
    expected = {r['sample_id'] for r in [*plan, *dosing]}
    mappings = read_csv(inputs/'injections.csv')
    if len(mappings) != 55 or {r['sample_id'] for r in mappings} != expected:
        raise ValueError('Actual injection map must contain exactly the seven mixed standards and 48 planned reactions')
    expected_wells = {r['sample_id']: r['well'] for r in plan}
    expected_wells.update({r['sample_id']: r['lc_well'] for r in dosing})
    for row in mappings:
        if well_name(row.get('well', '')) != expected_wells[row['sample_id']]:
            raise ValueError('Injection map well differs from the robot LC plate for '+row['sample_id']+
                             '; reconcile the injection order with the actual LC sequence. '
                             'Do not relabel physical sample wells to make a sequence match.')
    stable_snapshot()
    write_json(out/'software.json',{name:digest(Path(__file__).parent/name) for name in ['analytics.py','run_analysis.py','single_run.py','io.py']})
    write_json(out/'analysis-config.json',config)
    normalize_export(config, inputs/('vendor-export'+Path(export_path).suffix), out/'all-peaks.csv', inputs/'injections.csv')
    peaks = read_csv(out/'all-peaks.csv')
    if {r['sample_id'] for r in peaks} != expected:
        raise ValueError('LC export does not cover the complete planned sequence')
    cal_ids = {r['sample_id'] for r in plan}
    write_csv(out/'calibration-peaks.csv',[r for r in peaks if r['sample_id'] in cal_ids])
    write_csv(out/'reaction-peaks.csv',[r for r in peaks if r['sample_id'] not in cal_ids])
    review_path = None
    if reviewed_blanks:
        reviews=[dict(sample_id=r['sample_id'],analyte=r['analyte'],method_id=config['analytics']['method_id'],
                                    reviewed_by=reviewed_blanks,note='Operator confirmed no analyte peak in the authentic zero-analyte blank.')
                               for r in plan if float(r['concentration_uM']) == 0
                               and not any(p['sample_id']==r['sample_id'] and abs(float(p['retention_time_min'])-config['analytics']['references'][r['analyte']]['retention_time_min'])<=config['analytics']['references'][r['analyte']]['window_min'] for p in peaks)]
        if reviews:
            review_path=out/'reviewed-blanks.csv'
            write_csv(review_path,reviews)
    calibration_from_peaks(config,out/'calibration-peaks.csv',inputs/'calibration-plan.csv',out/'calibration.csv',review_path)
    complete_export(config,out/'reaction-peaks.csv',inputs/'dosing.csv',out/'complete.json')
    stable_snapshot()
    _,report = analyze(config,dosing,read_csv(out/'reaction-peaks.csv'),read_csv(out/'calibration.csv'),out)
    stable_snapshot()
    write_json(out/'files.sha256.json',{p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file() and p.name!='files.sha256.json'})
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',required=True)
    parser.add_argument('--map',required=True)
    parser.add_argument('--settings',default='local_data/lc-settings.json')
    parser.add_argument('--output',required=True)
    parser.add_argument('--reviewed-blanks',help='Reviewer name, only after confirming absent analyte peaks in the zero-analyte standards')
    args=parser.parse_args()
    try:
        report=process(args.export,args.map,args.settings,args.output,args.reviewed_blanks)
    except (ValueError,KeyError,FileNotFoundError) as error:
        parser.exit(2,f'Analysis stopped: {error}\n')
    print('Results:',Path(args.output)/'results.csv')
    print('QC:',Path(args.output)/'qc_report.json')
    if not report['batch_qc_pass']:parser.exit(1,'Some reactions failed QC; inspect the report before using their yields.\n')


if __name__=='__main__':main()
