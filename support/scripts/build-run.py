#!/usr/bin/env python3
"""Rebuild the one-run protocol, tables and browser weighing sheet."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'support'))
from hte.single_run import generate
from hte.run_analysis import SETTINGS_TEMPLATE
from hte.io import write_json


def main():
    out=ROOT/'run'
    plan=generate(out)
    write_json(out/'tables/lc-settings-template.json',SETTINGS_TEMPLATE)
    rows=['# Weigh these chemicals into the stock vials\n',
          '**Staff weigh; the OT-2 adds solvent.** Use the **HTEL 48-position 2 mL glass-vial holder in slot 1**. Weigh each ligand once into its labelled vial and load it with no stock solvent added. The robot makes the stocks there. [Stock map](images/stock-map.png) · [Staff guide](README.md).\n',
          'Only the vials below receive weighed material. There are **30 ligands**: unavailable L07 is omitted and original ID numbering is retained. The five labeled dilution/matrix vials start empty; column 8 remains empty.\n',
          '| Vial | Label | Chemical | Weigh (mg) |\n|---|---|---|---:|\n']
    for s in plan['stocks']:
        mass=f"{s['mass_mg']:.1f}"
        if s['stock_id']=='SM_IS':mass+=' SM **+ 7.7 naphthalene**'
        rows.append(f"| {s['location'][1]} | {s['stock_id']} | {s['name']} | {mass} |\n")
    rows += ['\n**SM_IS:** weigh both listed solids into the same vial. **FIT and CHECK:** separate, independent standard weighings. Weigh liquid 2-fluoropyridine by difference. Weigh ligands in the glovebox and retain the original bottles there.\n',
             '\n| Empty vial | Label | Robot prepares |\n|---|---|---|\n']
    descriptions={'HIGH':'5 mM SM + 5 mM product','LOW':'0.25 mM SM + 0.25 mM product',
                  'CHECK':'5 mM SM + 5 mM product, from independent CHECK masters',
                  'IS_WORK':'2 mM naphthalene','MATRIX':'100 µL toluene + 400 µL quench'}
    for key,description in descriptions.items():rows.append(f"| {plan['locations'][key][1]} | {key} | {description} |\n")
    rows.append('\nUse the vial labels and positions shown here, not an earlier two-round map. [Machine-readable weighing list](tables/weighing.csv) · [All vial positions](tables/tube-map.csv).\n')
    (out/'WEIGHING.md').write_text(''.join(rows))
    print(out)


if __name__=='__main__':main()
