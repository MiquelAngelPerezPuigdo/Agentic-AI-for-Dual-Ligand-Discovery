# HTE configuration checklist

Confirmed: solvents/Chromeleon; L07 excluded; **59 pairs + one reference, then ten pairs**. Request **1.7-minute LC**. See [event requirements](organizer-updates.md).

Record confirmed answers in the campaign configuration before live release.

## Hardware and scale

- Can sealed vials run **off the OT-2 on conventional hotplate/magnetic stirrer(s)**, with aluminum blocks and small stir bars?
- Heat/stir **60 vials together at 95 °C for four hours** (three concurrent 24-vial blocks if needed), then ten vials. Confirm hotplates, stirring at 250 µL, bar size and thermal lag.
- Confirm **250 µL reaction + 250 µL workup**, vial depth/bottom, mounting, deck/cap clearance, shaking and toluene/SO2-compatible sealing.
- Send vial-rack JSON; current 9 mm/on-robot protocols need revision for 24-vial/external heating. Account for stir bars at aspiration.

## LC method, export and calibration

- Supply the existing **1.7-minute** method ID, column/gradient, injection volume and **full injection-to-injection cycle**. Confirm separation of PyFluor, 2-fluoropyridine and naphthalene in our matrix. No prior method optimization is assumed.
- Select UV wavelength/channel using authentic standards; supply RT windows/LOQs. Example wavelengths are not our method.
- Explicitly request **14 calibration injections during round one**: five nonzero levels, a zero-analyte/IS blank and an independent check per analyte. Use [stock/calibration instructions](stocks-and-calibration.md); calibration is not a default HTEL service.
- Export required low/zero signals; clarify `n.a.`, peak-count mismatches and failed injections.
- Provide injection-number/sample-ID/method mapping and a complete-sequence marker; names may repeat.
- MOCCA requires raw **DAD**; supplied MS RAW is for identity review.

## Stocks, sampling and local operation

- Validate **greater than 1 mm** bottom clearance and immersion at the lowest volume, organic-solvent pipetting, noncontact stock-tip reuse and fresh sample-tip conditioning.
- Use plastic stock racks, glovebox preparation, capped reserves and 20/40 mM ligand/Pd recipes; no separate solubility study.
- Validate IS recovery, homogeneous extraction and LC matrix. Confirm sample 1% HCOOH compatibility with 0.1% mobile phase.
- Fit p300 single left/eight-channel right. Confirm capped predose storage, cooling and LC shaking; manual actions at pauses.
- Time handling/full cycle and reserve instruments: provisional 686 min, 34 min margin.
- Confirm local Anthropic access, private key delivery and stock preparation/initial selection outside the clock.

