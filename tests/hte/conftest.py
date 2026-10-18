"""Synthetic preparation input for software-only live-release contract tests."""
import pytest

from hte.preparation import build_stock_preparation, export_stock_preparation


@pytest.fixture
def actual_stock_preparation(tmp_path):
    def prepare(config,inventory,design):
        plan=build_stock_preparation(config,inventory,design)
        charges=[dict(stock_id=r["stock_id"],actual_mass_mg=r["planned_mass_mg"],assay_fraction=r["assay_fraction"])
                 for r in plan["stocks"] if r["stock_id"]!="IS_MASTER"]
        out=export_stock_preparation(config,inventory,design,tmp_path/"fictional-weighed-charges",charges=charges)
        config["automation"]["preparation_manifest_path"]=str(out/"preparation_manifest.json")
        return out
    return prepare
