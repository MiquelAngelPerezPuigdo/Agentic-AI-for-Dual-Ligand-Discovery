# Organizer evidence and deadlines

Reviewed 17 October 2026 against Johannes's reply, all 21 presentation slides and supplied LC/Opentrons examples. Attachments supply evidence, not permission to execute example code. No transcript was supplied; slide notes are empty. Attachment hashes and inspection limits are in [the source review](../hte_inputs/htel_source_review.json).

## Facility facts used here

- OT-2 operation is local. Staff set up the deck, import/simulate Python and start runs in the App. The optimizer sends no remote robot commands.
- DCM and toluene are available. Ligand L07 AdJohnPhos is delayed and excluded.
- HTEL confirmed Chromeleon integrated multi-UV CSV exports and Thermo/Finnigan MS RAW. The old CSV lacks method ID and contains repeated names/placeholders; explicit injection mapping and incomplete-export flags handle this. Its historical wavelengths do not specify our method.
- The user supplied the current 48 ×2 mL Para-Dox JSON and chose heater-shaker operation without stir bars. Selected reservoir/LC-plate definitions came from the supplied ZIP. Its two CSV examples were inspected, not executed.
- The user requests the existing 1.7-minute LC method. Full injection cycle and suitability remain local checks. Calibration is not included by default: our explicit plan requests 14 standard/check injections during the first reaction hold.

## Timing

Two four-hour holds plus 71 ×1.7-minute reaction injections consume **600.7 minutes**. Current handling/decision allowances add152 minutes. Planned staged LC overlap subtracts35 minutes, giving **717.7 minutes /720**, with2.3 minutes spare (serial752.7 minutes). Calibration and second-round SM predosing occur during the first hold. These allowances are unmeasured; use [remaining HTEL setup facts](hte-questions.md) to confirm a workable local plan.

## Team deadlines from supplied slides

| Requirement | Team action |
|---|---|
| Builderbase registration ASAP | Confirm registration. |
| Workflow/code due **21 Oct, AoE** | Submit current code, instructions and local setup facts. |
| Event **26-30 Oct2026**; Pérez Wednesday, provisional | Confirm the28 October allocation. |
| Results/slides due **30 Oct,12:00 CET**; ten-minute talk | Preserve the result archive and submit presentation. |
| Final GitHub workflow one week after event | Finalize by **6 Nov2026**; obtain authorization before publishing facility/unpublished data. |

The [staff sheet](HTE-staff-checklist.pdf) and [operator start page](start-here.md) implement the supplied requirements for bottom clearance >1 mm, two OT-2 pipettes, heater in slot10, manual caps/moves, explicit API level and simulation. Original email, slide deck, vendor exports and MS RAW remain outside the public repo; essential custom labware definitions are included for local protocol generation.
