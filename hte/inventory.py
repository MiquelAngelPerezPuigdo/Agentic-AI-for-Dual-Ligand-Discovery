from __future__ import annotations

from itertools import combinations
from rdkit import Chem
from rdkit.Chem import Descriptors

from .io import finite, read_csv


def load_inventory(path, confirmed=False):
    rows = read_csv(path)
    if not rows:
        raise ValueError("Ligand inventory is empty")
    seen, locations, cas_numbers = set(), set(), set()
    for row in rows:
        key = row["ligand_id"]
        if key in seen or not key:
            raise ValueError(f"Duplicate or empty ligand ID: {key}")
        seen.add(key)
        if not row["cas"] or row["cas"] in cas_numbers:
            raise ValueError("Inventory CAS numbers must be present and unique")
        cas_numbers.add(row["cas"])
        slot, well = int(row["source_slot"]), row["source_well"]
        if slot not in (1, 4) or well not in [f"{r}{c}" for c in range(1, 7) for r in "ABCD"]:
            raise ValueError(f"Invalid ligand source address: {key}")
        if (slot, well) in locations:
            raise ValueError("Duplicate ligand source location")
        locations.add((slot, well))
        mol = Chem.MolFromSmiles(row["smiles"])
        if mol is None:
            raise ValueError(f"Invalid ligand SMILES: {key}")
        mw = finite(row["molecular_weight_g_mol"], key+" molecular weight", 1)
        if abs(mw-Descriptors.MolWt(mol)) > 0.001:
            raise ValueError(f"Ligand molecular weight differs from its structure: {key}")
        if int(row["phosphorus_atoms"]) != sum(a.GetAtomicNum() == 15 for a in mol.GetAtoms()):
            raise ValueError(f"Ligand phosphorus count differs from its structure: {key}")
        if confirmed and row.get("identity_confirmed") != "true":
            raise ValueError(f"Unresolved identity {key}: {row.get('identity_note', '')}")
    return {row["ligand_id"]: row for row in rows}


def pair_id(a, b):
    if a == b:
        raise ValueError("Dual-ligand candidates must contain distinct ligands")
    return "__".join(sorted((a, b)))


def campaign_inventory(path, config, confirmed=False):
    """Keep stable workbook IDs while excluding explicitly unavailable reagents."""
    inventory = load_inventory(path, confirmed=confirmed)
    excluded = config["design"].get("excluded_ligands", [])
    if not isinstance(excluded, list):
        raise ValueError("excluded_ligands must be a list of ID/CAS/reason records")
    seen = set()
    for entry in excluded:
        key = entry.get("ligand_id")
        if key not in inventory or key in seen or entry.get("cas") != inventory[key]["cas"]:
            raise ValueError("Excluded ligand must have a unique matching inventory ID and CAS")
        if not entry.get("reason"):
            raise ValueError("Excluded ligand requires an availability reason")
        seen.add(key)
    controls = [*(config["design"]["round1_controls"] or []), *(config["design"]["round2_controls"] or [])]
    if any(control.get(k) in seen for control in controls for k in ("ligand_a", "ligand_b")):
        raise ValueError("An excluded ligand cannot be a campaign reference")
    active = {key: row for key, row in inventory.items() if key not in seen}
    if len(active) < 2:
        raise ValueError("At least two available ligands are required")
    return active


def candidates(inventory):
    return [{"pair_id": pair_id(a, b), "ligand_a": a, "ligand_b": b}
            for a, b in combinations(sorted(inventory), 2)]
