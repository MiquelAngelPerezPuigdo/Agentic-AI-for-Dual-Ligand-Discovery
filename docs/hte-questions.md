# HTE configuration checklist

Record the confirmed values in a campaign-specific copy of `hte_inputs/campaign.json` before generating live protocols. This checklist accompanies the [operator runbook](hte-runbook.md).

## Analytical method and export

- Exact two-minute method ID and measured injection-to-injection cycle, including overhead.
- Column, gradient, injection volume, quantitative DAD wavelength/channel and retention windows for substrate, product and naphthalene.
- Representative CSV/XLSX export: headers, sample/well mapping, retention-time and area units, method/channel fields, nondetections and failed injections.
- Complete-sequence export or an automatic completion marker for the local watcher.
- Raw DAD export format if optional MOCCA processing will be used.

Public HTEL equipment listings identify Vanquish Horizon Duo, ISQ-EM and DAD, and UZH lists `LC-ISQ-HTL-01` in Chromeleon. These listings do not establish the actual method or quantitative channel. [Equipment](https://www.chem.uzh.ch/en/research/services/htel/Equipment.html), [Chromeleon](https://www.chem.uzh.ch/en/research/services/massspec/Open-access_LC-and_GC-MS_with_Chromeleon.html).

## Calibration and sample compatibility

- Schedule authentic standards, calibration series, blanks and checks during the first reaction hold.
- Validate extraction/recovery, analyte stability and phase homogeneity after adding 50 µL of 1:1 water/ACN with 1% formic acid and 1 mM naphthalene to 50 µL reaction mixture.
- Confirm the proposed 20 µL aliquot into 180 µL diluent is appropriate: nominal maximum product concentration is 5 mM and naphthalene is 50 µM.
- Confirm final matrix, dilution, injection concentration, plate/seal, minimum volume and any filtration or centrifugation.

## Glass reaction block and heating

- Exact glass block, insert and seal, with a measured Opentrons labware definition.
- Secure mounting on the OT-2 heater-shaker universal flat adapter, latch/bolt clearance, allowable shaking mass and open/sealed travel clearance.
- Toluene loss, sealing and SO₂ compatibility at 95 °C for four hours.
- Actual liquid thermal lag, off-module cooling procedure and safe thermal handling.
- A second vial array or compatible removable tray for predosing ten substrate wells during round one.

The Para-Dox Gen II 104960 is a candidate with 1 mL inserts and a standard microplate footprint. Its footprint does not establish module fit or thermal performance. [Drawing](https://www.analytical-sales.com/drawings/104960_rev1c_PUBLIC.pdf).

## Stocks and solvent delivery

- Bottle/COA identities and assay values for all ligands, Pd(COD)(DQ) and substrate.
- Homogeneous 250 mM substrate/DCM, 30 mM ligand/toluene and 60 mM Pd/toluene stocks at dispensing temperature.
- Glovebox preparation/storage for ligands, labeled stocks and sufficient capped reserves.
- Source containers, dead volumes, aspiration/dispense heights and validated organic-solvent delivery settings.
- p20 single GEN2 and p300 eight-channel GEN2 configuration; source-dedicated noncontact tip reuse only after validation, with fresh sample tips.
- First-round DCM evaporation on the heater-shaker; second-round ambient evaporation under the approved ventilation setup, with a dry endpoint check before catalysts.

## Timing and local operation

- Rehearse dosing, heating, thermal equilibration, cooling, workup, manual moves, LC handling and the second-round LLM decision.
- Confirm uninterrupted LC and local OT-2 App availability and access to a plate shaker for the analytical plate.
- Confirm permitted Anthropic access from the operator workstation and test model access before the competition.
- Stocks and initial preselection are outside the clock. The clock stops after the ten second-round analyses.

Two four-hour holds and 76 analyses at two minutes each consume 632 minutes, leaving 88 minutes for all other operations. The provisional complete schedule is 729 minutes and therefore requires improvement supported by rehearsal measurements.
