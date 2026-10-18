#!/usr/bin/env python3
"""Draw the current OT-2 pipetting layout as an editable SVG and print-resolution PNG."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.inventory import campaign_inventory
from hte.io import read_json
from hte.planning import dosing_rows, pd_material_budget, transfer_operations, validate_config
from hte.io import read_csv

INK, MUTED, LINE = "#242C31", "#5C666B", "#CDD3D4"
TEAL, AMBER, BLUE, PURPLE = "#24766C", "#A96E24", "#276D9B", "#75628F"


def draw(output):
    c = read_json(ROOT/"hte_inputs/campaign.json")
    validate_config(c)
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", c)
    design = read_csv(ROOT/"campaigns/hackathon2026/round1_design.csv")
    budget = pd_material_budget(c, transfer_operations(c, inv, dosing_rows(c, inv, design)))
    plt.rcParams.update({"font.family":"DejaVu Sans", "svg.fonttype":"none", "svg.hashsalt":"hte-deck"})
    fig, ax = plt.subplots(figsize=(16.6, 12), facecolor="white")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set(xlim=(0,16.6), ylim=(0,12)); ax.axis("off")

    def text(x,y,s,size=11,weight="normal",color=INK,ha="left",va="center",**kw):
        return ax.text(x,y,s,fontsize=size,fontweight=weight,color=color,ha=ha,va=va,**kw)

    def box(x,y,w,h,fill="white",edge=LINE,lw=.9,r=.05,**kw):
        patch=FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",
                            facecolor=fill,edgecolor=edge,linewidth=lw,**kw)
        ax.add_patch(patch)
        return patch

    def grid(x,y,w,h,rows,cols,color,active=None):
        box(x,y,w,h,"#F3F5F4",r=.06)
        dx,dy=w/(cols+1),h/(rows+1)
        radius=min(dx,dy)*.30
        for row in range(rows):
            for col in range(cols):
                on=active is None or (row,col) in active
                ax.add_patch(Circle((x+(col+1)*dx,y+h-(row+1)*dy),radius,
                                    facecolor=color if on else "white",edgecolor=color if on else LINE,
                                    linewidth=.6,alpha=.8 if on else 1))

    def vial(x,y,color,height=.77):
        box(x,y,.42,height,"#FAFBFB",edge="#91A0A5",r=.07)
        box(x+.035,y+.045,.35,height*.48,color,edge="none",r=.04,alpha=.30)
        box(x-.015,y+height-.05,.45,.17,INK,edge=INK,r=.025)

    def arrow(x1,y1,x2,y2,color=INK):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=13,
                                     linewidth=1.2,color=color))

    text(.65,11.53,"OT-2 / experimental setup",25,fontfamily="DejaVu Serif")
    text(.67,11.03,"Round 1 deck map  •  48 × 2 mL Para-Dox  •  load only the current stage’s CSV volumes",11.5,color=MUTED)
    text(.67,10.65,"LEFT MOUNT   p300 single GEN2",10,weight="bold")
    text(5.56,10.65,"RIGHT MOUNT   p300 eight-channel GEN2",10,weight="bold")

    # OT-2 deck convention: slots 1–3 at the front, 10–12 at the back.
    slots={s:(.65+((s-1)%3)*3.30,2.97+((s-1)//3)*1.90) for s in range(1,13)}
    titles={1:"Ligand rack",2:"12-channel reservoir",3:"48-vial reaction block",4:"Working stock rack",
            5:"Single-channel tips",6:"Final LC plate",7:"Keep empty",8:"Eight-channel tips",
            9:"Eight-channel tips",10:"Heater-shaker",11:"Keep empty",12:"Fixed tip waste"}
    for slot,(x,y) in slots.items():
        empty=slot in (7,11)
        box(x,y,3.15,1.75,"#FAFAF8" if empty else "white",lw=.9)
        text(x+.16,y+1.48,str(slot),11,weight="bold",color=MUTED)
        text(x+.57,y+1.48,titles[slot],11,weight="bold")
        if empty:
            ax.plot([x+.25,x+2.90],[y+.30,y+1.13],color="#E2E5E4",lw=.9)
            text(x+1.575,y+.73,"Clear access around module",9,color=MUTED,ha="center")

    # Actual ligand positions are read from the same immutable inventory as the protocols.
    for slot in (1,4):
        x,y=slots[slot]
        labels={r["source_well"]:(key,TEAL) for key,r in inv.items() if int(r["source_slot"])==slot}
        if slot==c["stock_preparation"]["substrate_source_slot"]:
            labels[c["stock_preparation"]["substrate_source_well"]]=("SM/IS",BLUE)
        for source in budget["source_loads"]:
            if source["slot"]==slot: labels[source["well"]]=("Pd",AMBER)
        left,bottom,width,height=x+.37,y+.28,2.59,.93
        dx,dy=width/6,height/4
        for col in range(6):
            text(left+(col+.5)*dx,y+1.26,str(col+1),7.3,color=MUTED,ha="center")
        for row,letter in enumerate("ABCD"):
            cy=bottom+(3.5-row)*dy
            text(x+.20,cy,letter,7.3,color=MUTED,ha="center")
            for col in range(6):
                cx=left+(col+.5)*dx
                key=f"{letter}{col+1}"
                label,color=labels.get(key,("",LINE))
                ax.add_patch(Circle((cx,cy),.105,facecolor=color if label else "white",edgecolor=color,
                                    linewidth=.8,alpha=.15 if label else 1))
                text(cx,cy,label,6.9 if label=="SM/IS" else 7.3,weight="bold",ha="center",color=color)
        note="L01–L24; L07 position empty" if slot==1 else "L25–L31 + SM/IS + two Pd sources"
        text(x+1.575,y+.115,note,8.1,color=MUTED,ha="center")

    x,y=slots[2]
    pools=c["stock_preparation"]["reservoir_source_pools"]
    quench={int(w[1:]) for w in pools["workup"]}; diluent={int(w[1:]) for w in pools["LC_diluent"]}
    for col in range(1,13):
        xx=x+.18+(col-1)*.236
        fill="#DBE9E7" if col in quench else "#DCEAF3" if col in diluent else "#F4F5F5"
        box(xx,y+.42,.185,.70,fill,r=.03)
        text(xx+.0925,y+.29,str(col),7.1,ha="center",color=MUTED)
    text(x+.18,y+.115,"Quench: 4/6/9  •  LC diluent: 5/7/10/11/12",7.9,color=MUTED)

    for slot in (5,8,9):
        x,y=slots[slot];grid(x+.18,y+.34,2.79,.84,8,12,"#8899A4")
        text(x+1.575,y+.135,"300 µL tips",9,color=MUTED,ha="center")
    x,y=slots[3];grid(x+.18,y+.35,2.79,.84,6,8,PURPLE)
    text(x+1.575,y+.135,"Glass vials • 13 mm pitch • single only",8.4,color=MUTED,ha="center")
    x,y=slots[6];grid(x+.18,y+.35,2.79,.84,8,12,BLUE,{(r,col) for r in range(8) for col in range(6)})
    text(x+1.575,y+.135,"96 wells / 2.2 mL • 1 mL per LC sample",8.4,color=MUTED,ha="center")
    x,y=slots[10]
    box(x+.18,y+.45,2.79,.73,"#DDE1E0",edge="#9DA8AB",r=.10)
    box(x+.40,y+.57,2.35,.48,"#F3F5F4",edge="#89989B",r=.07)
    text(x+1.575,y+.82,"Universal flat adapter",9.2,ha="center")
    text(x+1.575,y+.29,"Receives ONE block or plate at a time",8.4,color=MUTED,ha="center")
    x,y=slots[12]
    box(x+.54,y+.38,2.07,.77,"#EBEEED",edge="#9AA7AB",r=.05)
    box(x+.46,y+1.04,2.23,.12,"#8D9BA0",edge="none",r=.02)
    text(x+1.575,y+.70,"Used tips",10,color=MUTED,ha="center")

    text(5.50,2.70,"FRONT / OPERATOR",9,color=MUTED,ha="center")
    arrow(4.12,2.70,4.53,2.70,color=MUTED);arrow(6.87,2.70,6.46,2.70,color=MUTED)

    # Off-deck materials and the local analytical/decision route.
    sx=11.03
    text(sx,10.17,"OFF DECK",12,weight="bold")
    ax.plot([sx,15.96],[9.91,9.91],color=LINE,lw=.9)
    vial(sx+.05,8.72,TEAL)
    text(sx+.69,9.41,"Ligand bulk stocks",12,weight="bold")
    text(sx+.69,9.08,"20 mM in toluene • capped glass",10.3)
    text(sx+.69,8.78,"Prepare in glovebox; mix off deck",10.3)
    text(sx,8.27,"Working tubes: 2 mL; maximum fill 1.95 mL.",10,color=MUTED)
    text(sx,7.98,"Gently invert capped tubes; let bubbles clear.",10,color=MUTED)

    vial(sx+.05,6.46,AMBER)
    text(sx+.69,7.26,"Pd(COD)(DQ) — ONE bulk",12,weight="bold")
    text(sx+.69,6.92,f"{budget['weigh_mg']:g} mg → {budget['make_to_final_ul']/1000:.2f} mL final",11.2)
    text(sx+.69,6.60,"40 mM • toluene • 8 mL glass vial",10.3)
    text(sx,6.12,"R1: slot 4 A3/B3, 1.91 mL each",10.4,weight="bold")
    text(sx,5.82,"R2: fresh A3, 1.83 mL from the SAME bulk",10.4)
    text(sx,5.51,"Keep 10 mg solid for scope. Recipe at 100% assay;",9.1,color=MUTED)
    text(sx,5.27,"adjust final volume for the actual assay.",9.1,color=MUTED)

    vial(sx+.05,3.86,BLUE)
    text(sx+.69,4.56,"Combined SM + mesitylene",12,weight="bold")
    text(sx+.69,4.24,"1 M + 100 mM in toluene • 2 mL bulk",10.3)
    text(sx+.69,3.93,"R1: slot 4 D2, 1.31 mL",10.3)
    text(sx,3.54,"Keep 575 µL off deck for the 23 R2 predoses.",10,color=MUTED)
    text(sx,3.15,"LC UV areas → local Python → Claude → R2 CSV",10,weight="bold")

    ax.plot([.65,15.96],[2.38,2.38],color=LINE,lw=.9)
    text(.65,2.09,"MANUAL MOVES / REACTION BLOCK",10,weight="bold")
    text(8.83,2.09,"MANUAL MOVES / FINAL LC PLATE",10,weight="bold")
    for x,label in ((.65,"Slot 3"),(3.13,"Slot 10"),(5.90,"Slot 3")):
        text(x,1.62,label,16,weight="bold",color=PURPLE)
    arrow(1.63,1.62,2.91,1.62,PURPLE);arrow(4.28,1.62,5.68,1.62,PURPLE)
    text(.65,1.16,"Reaction: hand-capped, 95 °C / 500 rpm / 4 h",10.6)
    text(.65,.82,"Quench: hand-capped, heater OFF / 1500 rpm / 2 min",10.6)
    text(.65,.49,"Cool before opening. Repeat the 3 → 10 → 3 route for quench mixing.",9.1,color=MUTED)
    for x,label in ((8.83,"Slot 6"),(11.30,"Slot 10"),(14.18,"HPLC")):
        text(x,1.62,label,16,weight="bold",color=BLUE)
    arrow(9.84,1.62,11.05,1.62,BLUE);arrow(12.51,1.62,13.93,1.62,BLUE)
    text(8.83,1.16,"20 µL extract + 980 µL diluent • one final plate per round",10.6)
    text(8.83,.82,"Shake uncovered: heater OFF / 1000 rpm / 2 min; then seal for LC",10.1)
    text(8.83,.49,"Reaction block stays in slot 3 while the LC plate occupies the shaker.",9.1,color=MUTED)
    text(.65,.16,"Schematic, not to scale. Confirm mounting, offsets, seals and splash-free speeds locally. Source racks stay off the heater-shaker.",8.5,color=MUTED)

    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output.with_suffix(".svg"),facecolor="white",metadata={"Date":None})
    fig.savefig(output.with_suffix(".png"),facecolor="white",dpi=220)
    plt.close(fig)
    print(output.with_suffix(".svg"))
    print(output.with_suffix(".png"))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"docs/figures/ot2-deck-setup")
    draw(parser.parse_args().output)
