# HTE configuration checklist

Confirmed: solvents/Chromeleon; L07 excluded; **59 pairs + one reference, then ten pairs**. Request **1.7-minute LC**. See [event requirements](organizer-updates.md).

Record confirmed answers in the campaign configuration before live release.

## Hardware and scale

- Clarify Para-Dox availability and send the missing **24 × 4 mL vial-rack JSON**. The ZIP defines a plastic plate.
- Confirm **60 sealed vials heated together at 95 °C for four hours**, uniform heating/mixing and thermal lag. Sequential 24-vial holds exceed the deadline. Provide a second predose array.
- Confirm **250 µL reaction + 250 µL workup**, vial depth/bottom, mounting, deck/cap clearance, shaking and toluene/SO2-compatible sealing.
- Current 96-array protocols require 9 mm pitch. A 24-vial setup requires revised maps/pipettes/heating.

## LC method, export and calibration

- Supply the existing **1.7-minute** method ID, column/gradient, injection volume and **full injection-to-injection cycle**. Confirm separation of PyFluor, 2-fluoropyridine and naphthalene in our matrix. No prior method optimization is assumed.
- Select UV wavelength/channel using authentic standards; supply RT windows/LOQs. Example wavelengths are not our method.
- Explicitly request **14 calibration injections during round one**: five nonzero levels, a zero-analyte/IS blank and an independent check per analyte. Use [stock/calibration instructions](stocks-and-calibration.md); calibration is not a default HTEL service.
- Export required low/zero signals; clarify `n.a.`, peak-count mismatches and failed injections.
- Provide injection-number/sample-ID/method mapping and a complete-sequence marker; names may repeat.
- MOCCA requires raw **DAD**; supplied MS RAW is for identity review.

## Stocks, sampling and local operation

- Validate **greater than 1 mm** bottom clearance and immersion at the lowest volume, organic-solvent pipetting, noncontact stock-tip reuse and fresh sample-tip conditioning.
- Confirm stock assays/solubility, glovebox ligand preparation/storage and capped reserves. Store combined SM/IS stock in glass; validate reservoir contact with toluene.
- Validate IS recovery, homogeneous extraction and LC matrix. Confirm sample 1% HCOOH compatibility with 0.1% mobile phase.
- Confirm proposed p300 single/eight-channel mounts, 20/40 mM ligand/Pd solubility, capped 25 µL predose storage, cooling and LC shaking. Manual actions occur at pauses.
- Time handling/full cycle and reserve instruments: provisional 686 min, 34 min margin.
- Confirm local Anthropic access, private key delivery and stock preparation/initial selection outside the clock.

Due **21 October AoE**: code/workflow. Confirm Builderbase/Wednesday slot. Slides/results: **30 October 12:00 CET**, ten-minute talk. GitHub final: 6 November.
