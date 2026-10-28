#!/usr/bin/env python3
"""Build the current two-page bench sheet from the same plan as the robot."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
FILES=['run/README.md','run/WEIGHING.md','run/plan.json','run/deck.png','run/stock-map.png',
       'run/run_screen.py','scripts/build-bench-pdf.py']


def fingerprint():
    return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    target=ROOT/'run/bench-sheet.pdf';manifest=ROOT/'run/bench-sheet.build.json'
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
    p=json.loads((ROOT/'run/plan.json').read_text())
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
    story=[para('Dual-ligand screen / Bench sheet',title),
           para('One run · 48 pairs · 30 ligands · 100 µL reactions',heading),
           para('95 °C / 500 rpm / 4 h. 0.1 M SM; 6 mol% each ligand; 12 mol% Pd; naphthalene 10 mol%. One program runs from stocks through sampling. Source vials are glass, in the supplied HTEL holder.'),
           table([['Slot','Load'],['1','HTEL 48-position stock holder: weighing and vial map on page 2.'],['2','One prefilled 12-channel reservoir; loads below.'],['3','Para-Dox block with 48 empty reaction vials.'],['5, 8','300 µL tips for LEFT p300 single GEN2.'],['6','One empty 96-well LC plate; retain it throughout.'],['9','300 µL tips for RIGHT p300 eight-channel GEN2.'],['10','Heater-shaker / universal flat adapter. Slots 4, 7 and 11 empty.']],[45,465]),
           para('Bulk liquids / reservoir',heading),
           para('<b>Quench, 40 mL:</b> 36 mL ACN + 3.95 mL water + 50 µL formic acid. <b>LC diluent, 60 mL:</b> 30 mL ACN + 29.94 mL water + 60 µL formic acid.'),
           table([['Channels','Liquid','Load per channel'],['A1-A2','Toluene','9 mL'],['A3-A5','Quench','9 mL'],['A6-A10','LC diluent','10 mL'],['A11 / A12','ACN / empty','3.5 mL / empty']],[85,255,170]),
           para('Run in this order',heading),
           para('<b>1.</b> Weigh each ligand once into its source vial. Load all vials and liquids. Import <b>run_screen.py</b> locally; check offsets and simulate. Start once. Robot prepares stocks and doses 20 µL SM/IS + 30 µL A + 30 µL B + 20 µL Pd.'),
           para('<b>2.</b> At pauses: hand-cap reaction vials; cap sources and cover liquids. Move block 3 → 10. Start an external 4 h timer. At 3 h, uncover reservoir/LC plate and uncap analytical vials as requested. Robot prepares seven mixed standards in A7-G7; cover/recap in place. Stop heat/shaking at 4 h if an App pause blocks the program.'),
           para('<b>3.</b> Move sealed block 10 → 3 and cool. Resume the SAME program; keep all labware and tip racks in place. Robot preloads 480 µL LC diluent/well. Uncap at the prompt; robot adds 400 µL quench/vial. Open block: 750 rpm / 2 min, heater OFF; return to 3. Fresh-tip sampling: 20 µL/well.'),
           para('<b>4.</b> Recap reaction vials. LC plate: 6 → cooled 10; shake uncovered 750 rpm / 2 min, heater OFF. Seal and hand to LC once: seven standards FIRST, then 48 samples. Preserve actual injection map, original LC/MS files and robot logs.'),
           para('<b>Margins:</b> source vials ≤1.6 mL; ≥150 µL left. Reservoir channels retain ≥1.5 mL. Reaction vials end at 500 µL; LC wells at 500 µL. Aspiration 1.5 mm above bottom. Pause for liquid-handling faults.',small),PageBreak(),
           para('Weighing / stock-holder positions',title),
           para('All positions are in the HTEL stock holder in <b>slot 1</b>. Ligands occupy columns 1-5. Column 8 stays empty. The robot adds solvent directly in these vials. No stock transfers or refills.'),]
    rows=[['Vial','Label','Material','mg']]
    for s in p['stocks']:
        mass=f"{s['mass_mg']:.1f}"
        name=escape(s['name'])
        if s['stock_id']=='SM_IS':mass='96.7 SM<br/>+7.7 IS';name='Pyridine-2-sulfonyl fluoride + naphthalene'
        rows.append([s['location'][1],s['stock_id'],name,mass])
    story+=[table(rows,[34,75,335,66],7.5),Spacer(1,7),
            para('<b>Five empty working vials:</b> B7 HIGH, C7 LOW, D7 CHECK, E7 IS_WORK, F7 MATRIX. Weigh FIT/CHECK standards separately; weigh liquid product by difference. Weigh ligands in the glovebox and retain original reagent bottles there.',small),
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
