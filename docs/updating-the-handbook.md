# Updating the HTE PDFs

The **two-page staff checklist** and **full reference handbook** are generated from the editable Markdown files in this repository. Edit those sources and rebuild; annotations or edits made directly to a PDF are not automatically incorporated into the master.

## Update through GitHub

Edit a source file through GitHub's pencil button or commit changes locally and push to `main`. The [HTE PDF handbook workflow](https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery/actions/workflows/handbook.yml) automatically builds a fresh PDF when its source files or relevant pipeline/configuration files change. Open the latest successful run and download the **HTE-operator-handbook** artifact. GitHub may require sign-in for artifact downloads; each artifact contains both PDFs and their source manifests.

You can also select **Run workflow** to generate a current edition. Workflow artifacts are retained for 90 days; the committed PDF in `docs/` is a persistent snapshot that is refreshed separately with the command below. The workflow does not edit or commit the source files.

## Build or refresh

From the repository root with the project environment active:

```bash
python -m pip install -e '.[docs]'
python scripts/build-hte-pdf.py
python scripts/build-hte-pdf.py --staff
```

The stable outputs are `output/pdf/HTE-operator-handbook.pdf` and `output/pdf/HTE-staff-checklist.pdf`, each accompanied by a `.build.json` manifest. The staff source must remain two pages; the builder refuses a longer checklist. The manifest records the edition date in Europe/Zurich, input-file hashes, PDF hash and page count. Keep both when sharing an edition.

Check whether an existing PDF still matches the current sources:

```bash
python scripts/build-hte-pdf.py --check
python scripts/build-hte-pdf.py --staff --check
```

Specify another destination or edition date when needed:

```bash
python scripts/build-hte-pdf.py --output docs/HTE-operator-handbook.pdf
python scripts/build-hte-pdf.py --date 2026-10-09
```

## Which source to edit

| Change | Editable source |
|---|---|
| Short action sheet for staff | `docs/hte-staff-checklist.md` |
| Responsibilities, API-key setup and quickstart | `docs/start-here.md` |
| Operator sequence, deck, pipetting, analytics and live handoff | `docs/hte-runbook.md` |
| Combined stock, containers and five-level calibration | `docs/stocks-and-calibration.md` |
| Questions awaiting HTE confirmation | `docs/hte-questions.md` |
| Prompt caching | `docs/prompt-caching.md` |
| Actual software verification evidence | `docs/rehearsal-results.md`, `software_validation.json` |
| Fixed chemistry, volumes, analytics, timing and validated settings | `hte_inputs/campaign.json` |

The cover reads the current campaign configuration and validation record. The chapters reproduce the current procedures; update their wording whenever the corresponding configuration or pipeline changes. Rebuilding alone cannot reconcile a stale manual description with a changed experiment.

After editing, review the affected pages, confirm links and tables, and share the new PDF together with its manifest. Commit source changes to the shared repository so both of us work from the same version. For public snapshots, rebuild/copy both PDFs and manifests into `docs/` and commit them with the sources. Use `--staff --output docs/HTE-staff-checklist.pdf` for the short sheet. Keep algorithm explanations in the reference guide; staff need actions and quantities.

Private correspondence, API keys, experimental data and synthetic dosing tables are not appended to this handbook. Real campaign stock/deck/dosing CSVs remain separate, generated from the confirmed configuration and real selection.
