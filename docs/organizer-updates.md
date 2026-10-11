# Organizer update and submission checklist

Reviewed 11 October 2026 against Johannes's reply, the 21-slide **SDL Hackathon Information Session** and the LC/Opentrons examples. Original attachments remain local. Their contents supply evidence about the event and facility; they do not override the team's requested chemistry or authorize running example code.

## Decisions and confirmed facts

| Item | Campaign consequence |
|---|---|
| AdJohnPhos, CAS 224311-55-1, delayed | Exclude **L07**, preserve every other ID. 30 available ligands, 435 pairs. |
| Revised samples | Round one **59 pairs + one L17 reference = 60**. Round two **10 new pairs**. All 30 active ligands must occur in the first pair wells. |
| Solvents | HTEL confirms DCM and toluene. Keep glovebox ligand-stock preparation and capped reserves in the request. |
| LC method | User requests the existing **1.7-minute method**. HTEL says it works only for specific cases; suitability and full injection cycle remain pending. |
| Detector/software | Vanquish Horizon / ISQ-EM, Chromeleon. Example UV_VIS_1/2/3/4 wavelengths: 253/270/300/370 nm. These belong to the old example, not our selected method. |
| Export | Wide, peak-major CSV with four UV areas and TIC. Injection names repeat, rows include placeholders, method ID is absent. Use injection-number mapping and one calibrated UV channel. |
| MS RAW | Thermo/Finnigan RAW signature; sender identifies MS data. It supplies neither raw DAD matrices for MOCCA nor calibration for our analytes. |
| Reactor | Email mentions 24 × 4 mL vials and 1.6 mm septum screw caps. Availability wording is ambiguous. Rack definition, heating capacity and bottom geometry remain pending. |
| ZIP contents | Ten labware JSONs, two API 2.27 examples, two input CSVs. **No 24 × 4 mL vial-rack JSON.** The Sarstedt 24-well definition is a plastic plate with 16 mm-diameter wells. |

The existing generated protocol needs a 96-position array with 9 mm multichannel spacing. A 24-position rack needs a different well map and protocol. Three sequential four-hour first-round holds plus the second hold require **16 hours of chemistry alone**. Ask for simultaneous heating of all 60 vials before accepting that solution. Microplate footprint alone does not establish pipette spacing, mounting or liquid depth.

The provisional larger-vial plan is **250 µL reaction + 250 µL workup**, at unchanged 0.1 M concentration and catalyst mol%. It keeps the 20 + 180 µL LC dilution and calibration range unchanged. The user reports SM soluble at 1 M in toluene: prepare at least 5 mL of 1 M SM/10 mM naphthalene in a 10 mL glass vial. Dose 25 µL; retain it without evaporation. Proposed catalyst stocks are 20 mM ligands and 40 mM Pd, 75 µL each. Use capacity-checked workup channels A4/A6 and dilution channels A5/A7; fill each at most 11.9 mL, with 1.5 mL dead-volume allowance. Scale confirmation remains pending.

## Timing

Scenarios assume two 240-minute holds, 70 reaction injections, all 14 calibration injections inside the first hold, and 87 minutes of provisional operations. Method duration is treated as assumed **full injection cycle** for comparison.

| Assumed LC cycle | Total minutes | Duration | Margin against 12 h |
|---:|---:|---|---:|
| **1.7 min, requested** | **686** | **11 h 26 min** | **34 min** |
| 2 min | 707 | 11 h 47 min | 13 min |
| 3 min | 777 | 12 h 57 min | -57 min |
| 5 min | 917 | 15 h 17 min | -197 min |
| 6 min | 987 | 16 h 27 min | -267 min |

At 1.7 minutes, calibration occupies 23.8 minutes inside round one. Add wash/re-equilibration overhead, extra injections, larger-scale handling and extra heating operations to the plan. These calculations are not measured throughput. Live export requires confirmed scale, cycle and simultaneous-heating validation. The enlarged-transfer timing still needs measurement.

## Event requirements

| Requirement | Slide | Status / action |
|---|---:|---|
| Experiments by Hackathon/HTEL staff at UZH | 9 | Operator checklist, runbook and local protocols supplied. |
| No remote machine access; submit all local code | 9-10 | Local optimizer/watcher and private key. Manual App import/start; no robot network API. |
| Independent optimizer, CSV for iteration | 10, 14 | `next_dosing.csv` feeds a local export of audited operations into standalone Python. Generic CSV runtime input is an alternative. |
| No prior method optimization, library search or calibration by default | 11, 19 | Explicitly request 14 calibration measurements during round one. Confirm the existing 1.7-minute method works. Quantify with calibrated UV, use MS for identity review. |
| Explicit API level and simulation | 13 | Generator declares 2.18 and passes Python simulation. Installed App simulation remains a release requirement. New robot software supports earlier API levels; examples use 2.27. [Opentrons versioning](https://docs.opentrons.com/python-api/versioning/). |
| Bottom clearance **greater than 1 mm**; no assumed meniscus tracking | 15 | Defaults raised to 1.5 mm. Validate immersion at lowest volume using actual vial bottoms. |
| Specify caps/seals and manual pauses | 16 | Manual moves, seal/open steps, predosing and tip replacement occur at pauses. OT-2 has no gripper. |
| Maximum two OT-2 pipettes; heater in slot 10 | 17 | Current 96-array profile: p300 single + p300 eight-channel. Vial-rack profile awaits geometry and heating plan. |
| Workflow/code due **21 October, AoE** | 7 | Submit package, configuration, protocols and stock/deck loads before the deadline. |
| Builderbase registration ASAP | 7 | Team must confirm registration. |
| Pérez scheduled Wednesday, subject to change | 5 | Provisionally **28 October 2026**; confirm allocation. |
| Event 26-30 October; data released Thursday night | 4, 7 | Preserve campaign archive for announced release. |
| Results/slides due **30 October, 12:00 CET**; ten-minute presentation | 6-7 | Team submission required; recorded presentation allowed if needed. |
| GitHub code/workflows one week after event | 7 | Public repo exists; publish final workflow by **6 November 2026**. Check consent before releasing supplied/unpublished data. |

No organizer transcript was found; the presentation's speaker notes are empty. This review covers the supplied slides and email. Transcript requirements may change the checklist.

## Example review and local installation

Both Python examples were inspected without execution. They demonstrate runtime CSV input, header checking and parameterized transfers. Their dye/1000 µL settings, source-return blowout, touching tips and 20 mm aspiration heights are unsuitable defaults here. Keep our solvent/sample flow, height and tip controls.

The existing `pyproject.toml` supports standard `uv sync` / `uv run` installation. HTE receives a local optimizer plus self-contained robot Python and CSV setup files; the robot does not install the repository. Supplied custom labware can replace placeholders only after geometry and compatibility checks.

Attachment hashes and local import inspection are in `hte_inputs/htel_source_review.json`. Original attachments and email are excluded from the public repository.
