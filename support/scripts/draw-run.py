#!/usr/bin/env python3
"""Deck/stock maps and a staff/robot workflow for the active run plan."""
from pathlib import Path
import json
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

ROOT=Path(__file__).resolve().parents[2]


def draw_workflow(plan, out):
    """Match the nine staff-guide/App stages; show actions and handoffs."""
    c=plan['config']
    ink='#202a30';muted='#53636c';line='#bcc5c9'
    staff='#e4eef6';robot='#e3eee6';warm='#fbefd9'
    # Left/right cells are roles within a stage, not simultaneous commands.
    # Their sequence is explicit where hands-on actions interrupt robot work.
    stages=[
        ('Prepare chemicals',
         'Weigh each ligand once into its labelled vial.\nPrepare the two bulk workup liquids.\nLoad weighed chemicals; NO stock solvent yet.',
         'The robot will add stock solvent.\nFive labelled working vials start empty.'),
        ('Load once and start',
         'Load the stock holder, reservoir, reaction block,\nLC plate and tips in their mapped slots.\nImport run_screen.py; complete App checks.',
         'One local program runs all OT-2 stages.\nFollow its numbered pauses and move prompts.\nUse the same labware and tip racks throughout.'),
        ('Make stocks, then dose 48 reactions',
         'At the prompts: STOCK HOLDER 1 → 10 → 1.\nLeave reaction-stock vials open; analytical\nvials capped. Inspect stocks before dosing.',
         'Add solvent → pipette-mix → shake stocks\n750 rpm / 2 min, heater OFF → dose reactions.\n100 µL = 20 SM/IS + 30 L-A + 30 L-B + 20 Pd.'),
        ('Seal and start the heated hold',
         'Screw on all 48 REACTION caps.\nCover reservoir / LC plate.\nREACTION BLOCK 3 → 10; start timer at 4b.',
         f'Heat to {c["temperature_C"]} °C; shake at {c["reaction_rpm"]} rpm.\nNominal {c["reaction_minutes"]//60}-hour hold starts at the App prompt.\nThen stop heating and shaking.'),
        ('After the hold: prepare standards while reactions cool',
         'At the prompt: SEALED BLOCK 10 → 3.\nUncover reservoir / LC plate; open the ten\nanalytical vials. Reaction caps stay ON.',
         'Make analytical stocks and seven standards\nin LC wells A7–G7 while the sealed reaction\nblock cools. Keep the LC plate in slot 6.'),
        ('Open cooled reactions, quench and mix',
         'Operator decides when safe to open and\nmodule is ready for unheated workup. Uncap\nreactions; OPEN BLOCK 3 → 10 → 3 at prompts.',
         'Add 400 µL quench / reaction (500 µL total).\nShake open block: 750 rpm / 2 min, heater OFF.\nReturn to slot 3, then wait 15 s.'),
        ('Prepare LC samples: aliquot first, then diluent',
         'No labware move or manual pipetting.\nLeave the LC plate in slot 6.',
         'For each of six columns: transfer eight\n20 µL extract aliquots with fresh tips FIRST.\nThen add 480 µL diluent / well (2 × 240 µL)\nwith the eight-channel pipette.'),
        ('Mix the completed LC plate',
         'Recap reactions for storage.\nAt the prompt: UNCOVERED LC PLATE 6 → 10.\nRemove the plate when the App requests it.',
         'Mix 48 samples + seven standards:\n750 rpm / 2 min, heater OFF.\nEach filled LC well contains 500 µL.'),
        ('Take to HPLC-MS, then calculate yields',
         'Seal / label the LC plate; mark A1.\nFinish the robot program, then carry the plate\nflat to HPLC-MS with lc-injections.csv.',
         'LC / SOFTWARE: inject seven standards FIRST,\nthen 48 samples. Export integrated-peak CSV;\nrun calibrated yields / QC. Save data and logs.'),
    ]
    fig,ax=plt.subplots(figsize=(11.2,15.8))
    fig.subplots_adjust(left=.025,right=.985,top=.895,bottom=.065)
    ax.set(xlim=(0,11),ylim=(0,19));ax.axis('off')
    fig.suptitle('From weighed chemicals to measured yields',x=.51,y=.975,
                 fontsize=21,fontweight='bold',color=ink)
    fig.text(.51,.946,'One 48-reaction screen  •  Same step numbers as the staff guide and App',
             ha='center',fontsize=11,color=muted)
    fig.text(.145,.916,'STAFF / HANDS-ON',fontsize=11,fontweight='bold',color='#28576c')
    fig.text(.57,.916,'OT-2 / AUTOMATIC',fontsize=11,fontweight='bold',color='#345841')
    for i,(title,left,right) in enumerate(stages):
        top=18.95-i*2.10;bottom=top-1.86
        if i<8:
            ax.annotate('',xy=(.33,bottom-.26),xytext=(.33,top-.40),
                        arrowprops=dict(arrowstyle='-|>',lw=1.2,color=line),zorder=0)
        ax.add_patch(Circle((.33,top-.24),.23,facecolor=ink,edgecolor='none'))
        ax.text(.33,top-.24,str(i+1),ha='center',va='center',fontsize=10,
                fontweight='bold',color='white')
        ax.text(.78,top-.24,title,va='center',fontsize=12,fontweight='bold',color=ink)
        for x,text,color in [(0.78,left,staff),(5.91,right,warm if i==3 else robot)]:
            ax.add_patch(FancyBboxPatch((x,bottom),4.87,1.26,
                                       boxstyle='round,pad=0.03,rounding_size=0.06',
                                       facecolor=color,edgecolor='none'))
            ax.text(x+.14,bottom+.64,text,va='center',fontsize=9.5,
                    linespacing=1.45,color=ink)
    fig.text(.10,.038,'Move labware only at the App prompts. Read both columns, then follow the numbered staff guide.',
             fontsize=9.5,color=ink)
    fig.text(.10,.018,'Longer hold: remain at 4b until the agreed endpoint. Holds / waits are logged. Keep reaction caps ON during cooling.',
             fontsize=9,color=muted)
    for ext in ('svg','png'):
        file=out/f'workflow.{ext}'
        fig.savefig(file,dpi=180,facecolor='white',metadata={'Date':None} if ext=='svg' else None)
        if ext=='svg':file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    p=json.loads((ROOT/'run/tables/plan.json').read_text())
    out=ROOT/'run/images';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'one-run'})
    ink='#202a30';line='#bcc5c9';blue='#e4eef6';green='#e3eee6';amber='#fbefd9'
    fig,ax=plt.subplots(figsize=(9,7.4));fig.subplots_adjust(left=.04,right=.96,top=.87,bottom=.09)
    ax.set(xlim=(0,3),ylim=(0,4));ax.axis('off')
    titles={1:'STOCK HOLDER\nHTEL 48 × 2 mL\nShake before dosing',2:'AXYGEN RESERVOIR\n12 × 12 mL, V-bottom\nHigh profile; stays in place',
            3:'REACTION BLOCK\n48 × 2 mL Para-Dox\n100 µL per reaction',4:'EMPTY',5:'300 µL TIPS\nLeft single-channel',
            6:'VWR 96 DEEP-WELL\n2.2 mL, square V-bottom\n48 samples + 7 standards',7:'EMPTY',8:'300 µL TIPS\nLeft single-channel',
            9:'300 µL TIPS\nRight eight-channel',10:'HEATER-SHAKER\nUniversal flat adapter\nStaff load at App prompts',11:'EMPTY',12:'FIXED TIP WASTE'}
    for slot in range(1,13):
        x=(slot-1)%3;y=(slot-1)//3
        color=green if slot==1 else blue if slot in (2,6) else amber if slot in (3,10) else '#f5f5f3'
        ax.add_patch(Rectangle((x+.03,y+.035),.94,.93,facecolor=color,edgecolor=line,lw=1))
        ax.text(x+.09,y+.83,str(slot),fontsize=12,fontweight='bold',color=ink)
        ax.text(x+.5,y+.43,titles[slot],ha='center',va='center',fontsize=10,color=ink,linespacing=1.6)
    fig.suptitle('Staff loading — one semi-automated run',x=.5,y=.97,fontsize=18,fontweight='bold',color=ink)
    fig.text(.5,.91,'LEFT: p300 single GEN2     |     RIGHT: p300 eight-channel GEN2',ha='center',fontsize=10,color=ink)
    fig.text(.5,.04,'FRONT / OPERATOR  •  Staff move labware at App prompts. The robot pipettes, heats and shakes.',ha='center',fontsize=8.5,color=ink)
    for ext in ('svg','png'):
        file=out/f'deck.{ext}';fig.savefig(file,dpi=180,facecolor='white',metadata={'Date':None} if ext=='svg' else None)
        if ext=='svg':file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(16,10));fig.subplots_adjust(left=.045,right=.985,top=.83,bottom=.15)
    ax.set(xlim=(-.35,8),ylim=(-.15,6.4));ax.axis('off')
    positions={loc[1]:key for key,loc in p['locations'].items()}
    stocks={s['stock_id']:s for s in p['stocks']}
    descriptions={'SM_IS':'SM + naphthalene','Pd':'Pd(COD)(DQ)','IS_MASTER':'Naphthalene',
                  'SM_FIT':'SM fit master','SM_CHECK':'SM check master',
                  'P_FIT':'Product fit master','P_CHECK':'Product check master',
                  'HIGH':'SM + product\n5 mM each','LOW':'SM + product\n0.25 mM each',
                  'CHECK':'Independent check\n5 mM each','IS_WORK':'Naphthalene\n2 mM',
                  'MATRIX':'Solvent matrix'}
    for col in range(8):
        ax.text(col+.5,6.18,str(col+1),ha='center',fontsize=13,fontweight='bold',color=ink)
        for row,letter in enumerate('ABCDEF'):
            if col==0:ax.text(-.2,5.5-row,letter,ha='center',va='center',fontsize=13,fontweight='bold',color=ink)
            address=letter+str(col+1);key=positions.get(address,'')
            ligand=key.startswith('L') and key!='LOW'
            fill=green if ligand else amber if key in ('SM_IS','Pd') else blue if key else '#f4f4f2'
            ax.add_patch(Rectangle((col+.04,5-row+.04),.92,.92,facecolor=fill,edgecolor=line,lw=.9))
            ax.text(col+.10,5-row+.85,address,ha='left',va='center',fontsize=8,color='#53636c')
            if not key:
                ax.text(col+.5,5.5-row,'EMPTY',ha='center',va='center',fontsize=10,color='#7b868b');continue
            name=textwrap.fill(stocks[key]['name'],width=18,break_long_words=False,break_on_hyphens=True) if ligand else descriptions[key]
            if key=='L27':name='tris(3-chlorophenyl)\nphosphine'
            ax.text(col+.5,5-row+.69,key,ha='center',va='center',fontsize=12,fontweight='bold',color=ink)
            ax.text(col+.5,5-row+.43,name,ha='center',va='center',fontsize=9,color=ink,linespacing=1.2)
            mass=(f"{stocks[key]['mass_mg']:.1f} mg" if key in stocks else 'START EMPTY')
            if key=='SM_IS':mass='96.7 mg SM + 7.7 mg IS'
            ax.text(col+.5,5-row+.12,mass,ha='center',va='center',fontsize=8.5,fontweight='bold',color=ink)
    fig.suptitle('Load the stock vials — deck slot 1',y=.965,fontsize=25,fontweight='bold',color=ink)
    fig.text(.5,.91,'HTEL 48 × 2 mL holder  |  30 ligands, weighed once  |  A1 at the back-left',ha='center',fontsize=13,color=ink)
    fig.text(.5,.875,'BACK OF ROBOT',ha='center',fontsize=10,fontweight='bold',color='#53636c')
    fig.text(.5,.125,'FRONT / OPERATOR',ha='center',fontsize=10,fontweight='bold',color='#53636c')
    fig.text(.045,.08,'GREEN: ligand stocks     AMBER: reaction SM/IS and Pd     BLUE: analytical sources / working vials',fontsize=11,color=ink)
    fig.text(.045,.045,'Stock shake: reaction-stock vials OPEN, analytical vials capped. 750 rpm / 2 min, heater OFF. B7–F7 start empty; column 8 unused.',fontsize=10,color=ink)
    for ext in ('svg','png'):
        file=out/f'stock-map.{ext}';fig.savefig(file,dpi=180,facecolor='white',metadata={'Date':None} if ext=='svg' else None)
        if ext=='svg':file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    plt.close(fig)
    draw_workflow(p,out)


if __name__=='__main__':main()
