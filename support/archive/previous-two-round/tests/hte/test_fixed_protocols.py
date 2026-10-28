"""The published robot files must track their source and fixed well layout."""
import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

from hte.io import read_csv, read_json, write_csv, write_json
from hte.inventory import campaign_inventory
from hte.planning import required_validations
from hte.preparation import export_stock_preparation

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build-fixed-ot2-protocols.py"


def test_published_files_reproduce_and_r2_workup_has_only_fixed_steps(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("build_fixed_ot2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path / "fixed"
    monkeypatch.setattr(module, "DEST", out)
    module.main()  # Checks two different hypothetical R2 selections give the same workup.
    published = ROOT / "protocols/fixed-campaign"
    paths = [p.relative_to(out) for p in out.rglob("*") if p.is_file()]
    assert paths
    for path in paths:
        assert (out / path).read_bytes() == (published / path).read_bytes(), path
    for path in out.rglob("*.py"):
        source = path.read_text()
        assert "HTE PRE-FLIGHT" in source
        tree = ast.parse(source)
        demo = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "DEMO" for t in n.targets))
        assert ast.literal_eval(demo.value) is False
    tree = ast.parse((out / "round2-workup/workup.py").read_text())
    ops = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "OPERATIONS" for t in n.targets))
    assert {op["stage"] for op in ops} == {"workup", "dilution", "sampling"}
    samples = [op for op in ops if op["stage"] == "sampling"]
    well_map = read_csv(out / "round2-workup/well-map.csv")
    assert len(samples) == len(well_map) == 23
    assert [(op["reagent"], op["source_well"], op["destination_wells"][0]) for op in samples] == [
        (row["sample_id"], row["well"], row["lc_well"]) for row in well_map]


def test_local_manifest_and_r2_layout_check_rejects_changes(tmp_path):
    config = read_json(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config, confirmed=True)
    design = read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv")
    config["analytics"]["method_id"] = "TEST_ONLY_METHOD"
    for key in required_validations(config):
        config["validation"][key] = True  # Software fixture, not a physical sign-off.
    path = export_stock_preparation(config, inventory, design, tmp_path / "prep", live=True)
    manifest = path / "preparation_manifest.json"
    command = [sys.executable, str(ROOT / "scripts/check-fixed-campaign.py")]
    assert subprocess.run(command + ["--preparation", str(manifest)], cwd=ROOT).returncode == 0
    changed = read_json(manifest)
    changed["recipe_digest"] = "changed"
    write_json(tmp_path / "bad.json", changed)
    assert subprocess.run(command + ["--preparation", str(tmp_path / "bad.json")], cwd=ROOT,
                          capture_output=True).returncode != 0
    well_map = read_csv(ROOT / "protocols/fixed-campaign/round2-workup/well-map.csv")
    write_csv(tmp_path / "r2.csv", well_map)
    assert subprocess.run(command + ["--r2-dosing", str(tmp_path / "r2.csv")], cwd=ROOT).returncode == 0
    well_map[0]["well"] = "A2"
    write_csv(tmp_path / "r2.csv", well_map)
    assert subprocess.run(command + ["--r2-dosing", str(tmp_path / "r2.csv")], cwd=ROOT,
                          capture_output=True).returncode != 0
