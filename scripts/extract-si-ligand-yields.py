#!/usr/bin/env python3
"""Extract only SI Table S2 (S35), then match experimental yields by CAS to our IDs."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.io import read_csv, read_json, write_json


def extract(si_path, inventory_path, literature_path, output):
    page = PdfReader(si_path).pages[34].extract_text()
    table = page.split("Table S2.", 1)[1].split("Table S3.", 1)[0]
    rows = re.findall(r"^(.+?)\s+(\d{2,7}-\d{2}-\d)\s+(Training|Predicted)\s+(\d+)\s+(\d+)\s*$",
                      table, flags=re.MULTILINE)
    if len(rows) != 18:
        raise ValueError(f"Expected the 18 Table S2 rows on S35, found {len(rows)}; inspect the PDF")
    inventory = read_csv(inventory_path)
    by_cas = {row["cas"]: row for row in inventory}
    if len(by_cas) != len(inventory):
        raise ValueError("Inventory CAS numbers must be unique for evidence matching")
    yields = []
    for name, cas, group, kraken_id, value in rows:
        if cas not in by_cas:
            raise ValueError(f"SI ligand CAS {cas} is absent from this campaign")
        yields.append({"ligand_id": by_cas[cas]["ligand_id"], "name": name.strip(),
                       "inventory_name": by_cas[cas]["name"], "cas": cas,
                       "yield_percent": int(value), "yield_basis": "19F NMR",
                       "si_selection_group": group, "kraken_id": int(kraken_id),
                       "source_table": "S2", "source_page": "S35"})
    if len({row["cas"] for row in yields}) != 18:
        raise ValueError("Duplicate CAS in the extracted Table S2 rows")
    evidence = read_json(literature_path)
    evidence["yields"] = yields
    evidence["source_document_sha256"] = hashlib.sha256(Path(si_path).read_bytes()).hexdigest()
    evidence["extraction"] = {"page_label": "S35", "pdf_page_number": 35, "table": "S2",
        "rows": 18, "matching_key": "CAS", "method": "pypdf text extraction of Table S2 only",
        "selection_group_meaning": "Training/Predicted describes selection; all listed yields are measured 19F NMR yields"}
    matched = {row["ligand_id"] for row in yields}
    evidence["ligands_without_table_S2_data"] = [
        {"ligand_id": row["ligand_id"], "name": row["name"], "yield_percent": None}
        for row in inventory if row["ligand_id"] not in matched]
    evidence["condition_assignment_note"] = (
        "The general screening procedure is on S20 (150 C, Pd2(dba)3, 20 mol% ligand, "
        "toluene 0.2 M, N2 glovebox; generally 18 h, PyFluor example 4 h). "
        "Table S2 does not state row-specific time and precursor deviations. "
        "Its t-BuBrettPhos value is 77%; the separate S20 PyFluor example is 83% "
        "and the S30 air example is 71%. Preserve these separate experiments.")
    write_json(output, evidence)
    return len(yields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--si", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, default=ROOT/"hte_inputs/ligands.csv")
    parser.add_argument("--literature", type=Path, default=ROOT/"hte_inputs/literature.json")
    parser.add_argument("--output", type=Path, default=ROOT/"hte_inputs/literature.json")
    args = parser.parse_args()
    count = extract(args.si, args.inventory, args.literature, args.output)
    print(f"Extracted {count} experimental yields, CAS-matched to ligand IDs: {args.output}")


if __name__ == "__main__":
    main()
