#!/usr/bin/env python3
"""Build the current two-page bench sheet from the same plan as the robot."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[2]
FILES=['run/README.md','run/WEIGHING.md','run/tables/plan.json','run/images/deck.png','run/images/stock-map.png',
       'run/run_screen.py','support/scripts/build-bench-pdf.py']


def fingerprint():
    return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    target=ROOT/'run/bench-sheet.pdf';manifest=ROOT/'run/tables/bench-sheet.build.json'
    if args.check:
        m=json.loads(manifest.read_text())
        if m['sources']!=fingerprint() or m['pdf_sha256']!=hashlib.sha256(target.read_bytes()).hexdigest():
            raise SystemExit('Bench PDF is stale; rebuild it.')
        print('Bench PDF matches current run sources.');return
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak
    from pypdf import PdfReader
    p=json.loads((ROOT/'run/tables/plan.json').read_text())
    base=ParagraphStyle('base',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=6)
    title=ParagraphStyle('title',parent=base,fontName='Times-Roman',fontSize=22,leading=26,spaceAfter=9)
    heading=ParagraphStyle('heading',parent=base,fontName='Helvetica-Bold',fontSize=11,leading=15,spaceBefore=8)
    small=ParagraphStyle('small',parent=base,fontSize=7.5,leading=9)
    def para(text,style=base):return Paragraph(text,style)
    def table(rows,widths,font=8):
        rows=[[para(str(c),small if font<8 else base) for c in row] for row in rows]
        t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeeb')),('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LINEBELOW',(0,0),(-1,0),.5,colors.gray),('LINEBELOW',(0,1),(-1,-1),.2,colors.lightgrey),
                               ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                               ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        return t
    story=[para('HTE staff / Bench sheet',title),
           para('One semi-automated run · 48 pairs · 30 ligands',heading),
           para('<b>Staff weigh; the robot adds stock solvent.</b> Staff move labware and handle caps, then take the final plate to HPLC-MS. 100 µL reactions: 0.1 M SM, 6 mol% each ligand, 12 mol% Pd, 10 mol% naphthalene. 95 °C / 500 rpm / nominal 4 h.'),
           table([['Slot','Load'],['1','HTEL stock holder: map on page 2. Moves 1 → 10 → 1 before dosing.'],['2','Axygen 12-channel, 12 mL/channel, high-profile V-bottom reservoir.'],['3','Para-Dox block with 48 empty reaction vials.'],['5, 8','300 µL tips for LEFT p300 single GEN2.'],['6','VWR 96 deep-well, 2.2 mL, V-bottom square-well LC plate.'],['9','300 µL tips for RIGHT p300 eight-channel GEN2.'],['10','Heater-shaker / universal flat adapter. Slots 4, 7 and 11 empty.']],[45,465]),
           para('Bulk liquids / reservoir',heading),
           para('<b>Quench, 40 mL:</b> 36 mL ACN + 3.95 mL water + 50 µL formic acid. <b>LC diluent, 60 mL:</b> 30 mL ACN + 29.94 mL water + 60 µL formic acid.'),
           table([['Channels','Liquid','Load per channel'],['A1-A2','Toluene','9 mL'],['A3-A5','Quench','9 mL'],['A6-A10','LC diluent','10 mL'],['A11 / A12','ACN / empty','3.5 mL / empty']],[85,255,170]),
           para('Follow these steps / same numbers in the staff guide and App',heading),
           table([['Step','Staff action','Robot / result'],
                  ['1','Weigh into labelled vials (page 2). Make bulk liquids above. Load weighed chemicals with <b>no stock solvent added</b>.','Stock solvents are added by the robot.'],
                  ['2','Load deck. Open A1-F5 and A6/B6; keep ten analytical vials capped. Check offsets, 150 µL source pickup and both capped assemblies ≤45 mm. Import <b>run_screen.py</b>.','Follow staff-guide setup checks, then start. Numbered pauses give the next action.'],
                  ['3','At move prompts: <b>stock holder 1 → 10 → 1</b>. Inspect stocks; leave reaction sources open.','Makes/mixes stocks; shakes 750 rpm / 2 min, heater OFF; doses 48 reactions.'],
                  ['4','Cap all <b>48 reaction vials</b>. Cover reservoir/LC. Move <b>reaction block 3 → 10</b>. Start timer at hold-start prompt.','95 °C / 500 rpm; nominal 4 h heated hold.'],
                  ['5','After heating stops: <b>sealed block 10 → 3</b>. Uncover reservoir/LC; open ten analytical vials. Reaction caps stay on.','Makes seven standards A7-G7 while sealed reactions cool. LC plate stays in 6.'],
                  ['6','Operator decides when safe to open and module ready for unheated workup. Uncap reactions; <b>open block 3 → 10 → 3</b> at prompts.','400 µL quench/vial (500 µL total); 750 rpm / 2 min, heater OFF; settle 15 s.'],
                  ['7','No manual pipetting or labware move. Keep LC plate in slot 6.','Per column: eight fresh-tip 20 µL aliquots FIRST, then 480 µL diluent/well (8-channel, 2 × 240 µL).'],
                  ['8','Recap reaction vials for storage. Move <b>uncovered LC plate 6 → 10</b>, then remove when asked.','Final LC plate mix: 750 rpm / 2 min, heater OFF.'],
                  ['9','Seal/label plate and mark A1. Finish robot program. Carry flat to <b>HPLC-MS with lc-injections.csv</b>.',f'HTEL {p["config"]["lc_method_minutes"]:g}-min LC: 7 standards A7-G7 FIRST, then 48 samples A1-H6. {55*p["config"]["lc_method_minutes"]:g} min + overhead.']],[30,285,195]),
           para('<b>Timing:</b> longer holds and pre-quench waits are allowed/logged. For a longer hold, remain at 4b until the agreed endpoint; heating/shaking stay on there. Return LC/MS files, actual injection map/method, yields/QC, robot log and run notes.',small),PageBreak(),
           para('Weighing / stock-holder positions',title),
           para('All positions are in the HTEL stock holder in <b>slot 1</b>. Ligands occupy columns 1-5. Column 8 stays empty. The robot adds solvent directly in these vials. No stock transfers or refills.'),]
    rows=[['Vial','Label','Material','mg']]
    for s in p['stocks']:
        mass=f"{s['mass_mg']:.1f}"
        name=escape(s['name'])
        if s['stock_id']=='SM_IS':mass='96.7 SM<br/>+7.7 IS';name='Pyridine-2-sulfonyl fluoride + naphthalene'
        rows.append([s['location'][1],s['stock_id'],name,mass])
    story+=[table(rows,[34,75,335,66],7.5),Spacer(1,7),
            para('<b>Five empty working vials:</b> B7 HIGH, C7 LOW, D7 CHECK, E7 IS_WORK, F7 MATRIX. <b>FIT</b> supplies the LC calibration; separately weighed <b>CHECK</b> sources supply an LC accuracy check. The robot makes all dilutions. Weigh liquid product by difference. Weigh ligands in the glovebox and retain original reagent bottles there.',small),
            para('Full procedure, maps, Python files and LC instructions: <link href="https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery/tree/main/run" color="#28576c">github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery / run</link>',small)]
    def footer(canvas,doc):
        canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(40,24,'HTEL · One 48-reaction screen · 28 October 2026')
        canvas.drawRightString(A4[0]-40,24,str(doc.page))
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=34,bottomMargin=36).build(story,onFirstPage=footer,onLaterPages=footer)
    pages=len(PdfReader(target).pages)
    if pages!=2:raise ValueError(f'Expected two compact pages, got {pages}')
    manifest.write_text(json.dumps(dict(pages=pages,sources=fingerprint(),pdf_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2)+'\n')
    print('Built two-page bench sheet.')


if __name__=='__main__':main()
