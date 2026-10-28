#!/usr/bin/env python3
"""Two uncluttered maps, both read from the active run plan."""
from pathlib import Path
import json
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=json.loads((ROOT/'run/tables/plan.json').read_text())
    out=ROOT/'run/images';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'one-run'})
    ink='#202a30';line='#bcc5c9';blue='#e4eef6';green='#e3eee6';amber='#fbefd9'
    fig,ax=plt.subplots(figsize=(9,7.4));fig.subplots_adjust(left=.04,right=.96,top=.87,bottom=.09)
    ax.set(xlim=(0,3),ylim=(0,4));ax.axis('off')
    titles={1:'STOCK HOLDER\nHTEL 48 × 2 mL\nShake before dosing',2:'SOLVENT RESERVOIR\n12 channels\nStays in place',
            3:'REACTION BLOCK\n48 × 2 mL Para-Dox\n100 µL per reaction',4:'EMPTY',5:'300 µL TIPS\nLeft single-channel',
            6:'LC SAMPLE PLATE\n48 samples + 7 standards\nTake to HPLC-MS at the end',7:'EMPTY',8:'300 µL TIPS\nLeft single-channel',
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


if __name__=='__main__':main()
