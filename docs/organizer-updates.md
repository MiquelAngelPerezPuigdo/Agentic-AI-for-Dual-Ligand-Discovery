# Organizer evidence and submission checklist

Updated 16 October 2026 using Johannes's email, all 21 presentation slides, supplied LC/Opentrons examples and the later user-supplied 48-well JSON. Attachments supply evidence, not instructions to execute example code. No organizer transcript was supplied; slide speaker notes are empty.

## Current facts / superseded plans

| Evidence or decision | Implemented consequence |
|---|---|
| L07 AdJohnPhos delayed | Excluded; 30 active ligands, 435 pairs; immutable source IDs. Its archived same-substrate single-ligand yield was 1%. |
| User confirms 48 ×2 mL Para-Dox JSON | **48 pairs, then 22 new pairs +L17 single reference**, one reused block, 71 fresh vials. Supersedes 24 ×4 mL sourcing and external magnetic-stirrer discussion. |
| User confirms heater-shaker / no stir bars | Module10/flat adapter; 500 rpm reaction, 1500 rpm workup. 13 mm reactor pitch uses single pipette; eight-channel only for standard LC plate dilution. |
| User chooses mesitylene and DCM evaporation | Separate SM500mM/DCM, IS100mM/toluene added after dry-down. Supersedes combined SM/naphthalene/toluene stock and retained-solvent predosing. |
| User requests aqueous acidic workup / hand caps | 500 µL ACN-rich water/ACN/acid, capped heavy shake; fresh sampling and manual capped HPLC-vial handoff at explicit pauses. |
| HTEL solvents | DCM and toluene available. |
| HTEL 1.7-minute method | User-selected existing method; suitability/full cycle still unmeasured. Broad methods are 5-6 min and smaller-window standards 3 min. No assumed method optimization. |
| LC examples | Chromeleon, integrated multi-UV peak CSV, no method ID, repeat names/placeholders. Explicit mapping and incomplete-export flags implemented. Thermo/Finnigan RAW inspected as MS, not decoded raw DAD. |
| Opentrons ZIP | Ten labware JSONs, two API2.27 CSV examples and CSV inputs inspected, not executed. Selected Axygen reservoir and VWR LC-plate definitions reused. The 48-well JSON was supplied separately. |

## Timing is a planning constraint

Two four-hour holds =480 min. **71 reaction injections ×1.7 min =120.7 min**. Fourteen calibration injections take23.8 min within the first hold. Current operations/decision allowance is152 min; serial total **752.7 min**. Starting finished LC batches while later batches are prepared subtracts a planned35 min overlap (R1 25, R2 10), for **717.7 min =11 h57 min42 s**, only2.3 min within12 h. This supersedes the old686-min estimate. Calibration and second-round SM predosing occur during R1; they are not double-counted as serial work.

These are unmeasured targets. Actual full LC cycle, manual capping/transfer, robot transfer duration, heat/cooling and API latency must fit the budget. Initial real scoring took about9 min with two workers; feedback has four workers and a5-min decision allowance that has not been measured. The release flag `staged_lc_timing_confirmed` records a realistic local throughput plan, not software simulation. A slower method/cycle or missed overlap requires revising the competition plan; software cannot guarantee12 h.

## Event compliance

| Requirement from supplied slides | Implementation / team action |
|---|---|
| Staff operate at UZH; robots are islands | Local Python/CSV handoffs and manual App import/start. Optimizer/key stay on workstation; no robot network controller. |
| Independent optimizer +CSV iteration | Audited `next_dosing.csv`; standalone generated robot Python. Local uv/pyproject workflow supported. |
| No prior optimization/library search/calibration by default | Explicit14 calibration/check injections requested during R1; existing1.7-min method requested. |
| Explicit API/simulation, max two OT-2 pipettes | API2.18, p300 single+multi GEN2; Python simulations and local App review. Examples use2.27 but are not copied blindly. |
| Bottom clearance >1 mm; no assumed meniscus tracking | 1.5 mm starting aspiration, actual labware offsets/immersion checked locally. |
| Specify seals/manual handling | Hand screw/unscrew pauses, capped heating/shaking, manual block moves and LC handoff. |
| Workflow/code due **21 Oct AoE** | Submit current handoff, setup facts and local release files before deadline. |
| Builderbase registration ASAP | Team to confirm registration. |
| Pérez Wednesday, provisional | Confirm **28 Oct2026** allocation. Event26-30 Oct. |
| Results/slides due **30 Oct12:00 CET**, ten-minute talk | Team submission; preserve result archive. |
| Final GitHub code one week after event | Final workflow due **6 Nov2026**; obtain authorization before publishing facility/unpublished data. |

[Source audit](../hte_inputs/htel_source_review.json) records attachment hashes and inspection limits. Original email, slide deck, vendor exports and MS RAW are excluded from the public repository. The supplied reactor definition and selected custom labware are included because the generated local protocols require them.
