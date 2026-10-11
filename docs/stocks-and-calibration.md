# Combined reaction stock and five-level calibration

Reaction stock combines SM/IS. Calibration uses separate analyte/IS stocks at fixed IS concentration. LC diluent has its own reservoir channels.

## Reaction stock, container and deck source

The provisional larger-vial plan uses **250 µL reaction + 250 µL workup** at 0.1 M, five times the original scale. Final geometry/heating must be confirmed.

The user reports PyFluor soluble at **1.00 M in toluene**. Prepare **5.00 mL of 1.00 M PyFluor + 10.0 mM naphthalene in toluene** before the clock. At nominal molecular weights and 100% assay, this contains **805.80 mg PyFluor and 6.4085 mg naphthalene**. The planner corrects assays separately under `substrate_stock` and `naphthalene`. Bring the dissolved solutes to the final volume.

1. Prepare **50.0 mM naphthalene in toluene**, for example 12.817 mg in a final 2.00 mL, corrected for assay. Use a larger preparation if required by the balance.
2. Weigh the corrected PyFluor mass into a **10 mL glass vial with a toluene-compatible PTFE-faced closure**.
3. Add **1.00 mL of the 50.0 mM toluene IS master**, dissolve and bring to **5.00 mL final volume** with toluene using validated volumetric handling.
4. Confirm the combined solution is clear at dispensing temperature. Label both concentrations, solvent, assays, lots, preparation time and recheck conditions. Keep the reserve capped off deck.

The pipetting source is **A1 of the 12-channel reservoir in slot 2**, using a library geometry surrogate pending HTE substitution. All eight tips can aspirate from its long channel. The default reuse plan loads approximately **3.27 mL** for 60 reactions plus ten predoses, including the provisional **1.50 mL dead-volume allowance**. Use the actual generated `deck_loads.csv`, including when tip reuse is disabled. Keep the remainder of the 5 mL stock in the capped glass vial. This is not a Falcon tube. Confirm actual reservoir geometry and toluene compatibility; the fill limit is 11.9 mL per channel.

Each **25 µL** dose provides **25.00 µmol SM and 0.250 µmol naphthalene**. **Retain the toluene: no drying or evaporation is performed in either round.** Predose the ten round-two wells during the first hold and cap promptly. Validate retained volume and the storage interval; second-round dosing adds no further SM/IS. The retained **25 µL stock solvent counts in the final 250 µL reaction**, also in round two.

## Catalyst stocks and volume balance

Prepare ligands in the glovebox at **20.0 mM in toluene**, and Pd(COD)(DQ) at **40.0 mM in toluene**. Confirm every stock is homogeneous at dispensing temperature; solubility of SM does not establish catalyst-stock solubility. Use `stock_preparation.csv` for masses, separate assay corrections, margins and worst-case round-two reserves. Keep bulk reserves in compatible capped containers; load only the generated source quantities.

| Reaction | SM/IS stock, µL | Ligand A, µL | Ligand B, µL | Pd, µL | Total, µL |
|---|---:|---:|---:|---:|---:|
| Pair | 25 | 75 | 75 | 75 | 250 |
| L17 single reference | 25 | 150 | 0 | 75 | 250 |

This gives **0.1 M SM, 6 mol% of each ligand and 12 mol% Pd**; the reference uses 12 mol% L17. No extra neat toluene is needed with these stocks. A p300 single plus p300 eight-channel is proposed for efficient transfers; HTE must confirm installation and volume accuracy. The generator also supports p20 single with split transfers when explicitly configured, but timing must be remeasured.

## Workup and sample dilution

Reservoir channels **A4 and A6** hold the workup solvent: 1:1 water/ACN with 1% v/v HCOOH, **without additional naphthalene**. Add 250 µL per reaction and mix for two minutes after cooling/opening under HTE's SOP.

Reservoir channels **A5 and A7** hold the LC diluent: the validated 1:1 water/ACN with 1% v/v HCOOH, **without naphthalene or analyte**. Dispense 180 µL into each LC destination first, then transfer 20 µL of homogeneous extract with fresh sample tips, and mix the LC plate for two minutes. Full columns use eight channels for both solvent dispensing and sample transfer. Fresh sample tips condition only in their own reaction well before transfer, using the sample-specific slow-flow settings. Follow the [runbook sampling sequence](hte-runbook.md) for immersion, bubble checks, surplus disposal and failed-transfer recovery; repeated aspiration cannot make a two-phase extract quantitative.

With quantitative retention/recovery, 0.250 µmol IS in a nominal 500 µL extract is 500 µM. The 20 + 180 µL dilution gives **50 µM naphthalene** and, at 100% yield, **5,000 µM product**. Sample dilution reduces both analyte and IS concentration; their concentration ratio stays constant. Changing the aliquot to 5 µL plus 195 µL gives 12.5 µM IS and a 1,250 µM maximum product concentration. It requires changing `robot.single` to `p20_single_gen2` and revalidating/releasing that setup. Update the configuration, standards and generated files together; the code checks their IS concentration agreement.

## Separate analytical stocks

Prepare these before the clock, then prepare/run the working standards while the first reaction runs. Use the actual bottle/COA molecular weights and an HTE-approved LC-compatible solvent. ACN is a proposed stock solvent, subject to solubility and method validation.

| Analytical stock | Proposed final volume | Nominal preparation at 100% assay |
|---|---:|---|
| Authentic PyFluor, 100 mM, no IS | 2.00 mL | 32.232 mg, MW 161.16 |
| Authentic 2-fluoropyridine, 100 mM, no IS | 2.00 mL | Approximately 19.418 mg, MW 97.09; verify bottle |
| Pure naphthalene, 50 mM, in LC-compatible solvent | 2.00 mL | 12.817 mg, MW 128.17 |
| Each analyte working stock, 10 mM, no IS | 1.00 mL each | 100 µL of its 100 mM stock, bring to 1.00 mL |
| Pure analytical IS working stock, 1 mM | 2.00 mL | 40 µL of the 50 mM analytical master, bring to 2.00 mL |

Keep the **toluene naphthalene master for reaction dosing** and the **LC-compatible naphthalene master for calibration** distinctly labeled. Account for stock solvents when preparing the validated LC matrix. Do not add authentic SM/product calibration solutions to reaction wells.

## Five nonzero analyte levels with fixed reference

Prepare one series for SM and one for product. Each standard below has **1.00 mL final volume**, **50 µM naphthalene**, and the indicated known analyte concentration. The five nonzero fitted levels are 100, 500, 1,000, 2,500 and 6,000 µM. Also prepare an IS-containing zero-analyte blank and an independently prepared 5,000 µM check for each series. This gives **14 injections**, scheduled during the first four-hour reaction. These analytical blanks/checks do not occupy additional reaction wells.

| Final analyte, µM | Analyte stock | Analyte volume, µL | 1 mM IS, µL | Remaining solvent volume to final 1 mL, µL | Role |
|---:|---|---:|---:|---:|---|
| 0 | None | 0 | 50 | 950 | Zero-analyte calibration blank |
| 100 | 10 mM | 10 | 50 | 940 | Calibration level 1 |
| 500 | 10 mM | 50 | 50 | 900 | Calibration level 2 |
| 1,000 | 10 mM | 100 | 50 | 850 | Calibration level 3 |
| 2,500 | 100 mM | 25 | 50 | 925 | Calibration level 4 |
| 6,000 | 100 mM | 60 | 50 | 890 | Calibration level 5 |
| 5,000 | 100 mM | 50 | 50 | 900 | Independent check, excluded from fit |

Account for both stock solvents to obtain the **same validated matrix across standards and samples**. HTE must confirm the matrix recipe, phase behavior/recovery and LC compatibility before quantification. The table gives amounts and volume arithmetic.

Use IDs/roles from `hte_inputs/calibration_template.csv` and measured areas/method/channel. Zero must be a verified blank signal, not a missing export. Fit blank plus five levels; exclude `check` rows. Mix, cap and record every dilution; use fresh tips between standards. Prepare the independent check separately, with an independent stock when feasible. HTE must approve the detector range/LOQs and proposed ±15% check tolerance (`analytics.calibration_check_tolerance_fraction`).

Serial dilution of the combined reaction stock alone cannot make these fixed-IS standards: it keeps the SM:IS ratio at 100:1 and lowers both concentrations together. At 50 µM naphthalene it would supply 5,000 µM SM. Separate authentic analyte and pure analytical IS stocks let HTE vary the analyte while holding naphthalene at 50 µM.

## Validation of IS added before the reaction

Validate naphthalene recovery through capped storage, sealed heating and extraction/dilution, and check chemical/peak interference. Protect stocks/predoses against solvent loss.

IS loss can inflate area-ratio yields; no unmeasured correction is applied. Record recovery/compatibility in `validation.pre_reaction_internal_standard_validated` before live release. Revise context, calibration, stocks and protocols together if IS settings change.
