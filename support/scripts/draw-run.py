#!/usr/bin/env python3
"""Two uncluttered maps, both read from the active run plan."""
from pathlib import Path
import json
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
    titles={1:'STOCK VIALS\nHTEL 48 × 2 mL\nStays in place',2:'ONE RESERVOIR\n12 channels\nStays in place',
            3:'REACTION BLOCK\n48 × 2 mL Para-Dox\n100 µL per reaction',4:'EMPTY',5:'300 µL TIPS\nLeft single-channel',
            6:'ONE LC PLATE\n48 samples + 7 standards\n500 µL per filled well',7:'EMPTY',8:'300 µL TIPS\nLeft single-channel',
            9:'300 µL TIPS\nRight eight-channel',10:'HEATER-SHAKER\nUniversal flat adapter',11:'EMPTY',12:'FIXED TIP WASTE'}
    for slot in range(1,13):
        x=(slot-1)%3;y=(slot-1)//3
        color=green if slot==1 else blue if slot in (2,6) else amber if slot in (3,10) else '#f5f5f3'
        ax.add_patch(Rectangle((x+.03,y+.035),.94,.93,facecolor=color,edgecolor=line,lw=1))
        ax.text(x+.09,y+.83,str(slot),fontsize=12,fontweight='bold',color=ink)
        ax.text(x+.5,y+.43,titles[slot],ha='center',va='center',fontsize=10,color=ink,linespacing=1.6)
    fig.suptitle('Load once — one 48-reaction run',x=.5,y=.97,fontsize=19,fontweight='bold',color=ink)
    fig.text(.5,.91,'LEFT: p300 single GEN2     |     RIGHT: p300 eight-channel GEN2',ha='center',fontsize=10,color=ink)
    fig.text(.5,.04,'FRONT / OPERATOR    •    Only the reaction block and final LC plate move to the shaker.',ha='center',fontsize=9,color=ink)
    for ext in ('svg','png'):
        file=out/f'deck.{ext}';fig.savefig(file,dpi=180,facecolor='white')
        if ext=='svg':file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,6.1));fig.subplots_adjust(left=.065,right=.98,top=.83,bottom=.16)
    ax.set(xlim=(-.35,8),ylim=(-.15,6.4));ax.axis('off')
    positions={loc[1]:key for key,loc in p['locations'].items()}
    short={'IS_MASTER':'IS master','SM_CHECK':'SM check','P_CHECK':'P check','SM_FIT':'SM fit','P_FIT':'P fit','IS_WORK':'IS work'}
    for col in range(8):
        ax.text(col+.5,6.18,str(col+1),ha='center',fontsize=11,fontweight='bold',color=ink)
        for row,letter in enumerate('ABCDEF'):
            if col==0:ax.text(-.2,5.5-row,letter,ha='center',va='center',fontsize=11,fontweight='bold',color=ink)
            key=positions.get(letter+str(col+1),'')
            fill=green if key.startswith('L') and key!='LOW' else amber if key in ('SM_IS','Pd') else blue if key else '#f4f4f2'
            ax.add_patch(Rectangle((col+.04,5-row+.04),.92,.92,facecolor=fill,edgecolor=line,lw=.9))
            ax.text(col+.5,5.5-row,short.get(key,key) or 'empty',ha='center',va='center',fontsize=10,color=ink,fontweight='bold' if key else 'normal')
    fig.suptitle('Stock-vial holder — slot 1',y=.97,fontsize=20,fontweight='bold',color=ink)
    fig.text(.5,.89,'HTEL 48 × 2 mL glass vials     •     A1 at the back-left     •     Single-channel pipetting only',ha='center',fontsize=10,color=ink)
    fig.text(.07,.085,'GREEN: ligands, weighed once     AMBER: reaction SM/IS and Pd     BLUE: analytical sources / dilutions',fontsize=9,color=ink)
    fig.text(.07,.04,'HIGH, LOW, CHECK, IS work and MATRIX start empty. Column 8 stays empty. Masses: WEIGHING.md.',fontsize=9,color=ink)
    for ext in ('svg','png'):
        file=out/f'stock-map.{ext}';fig.savefig(file,dpi=180,facecolor='white')
        if ext=='svg':file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__=='__main__':main()
