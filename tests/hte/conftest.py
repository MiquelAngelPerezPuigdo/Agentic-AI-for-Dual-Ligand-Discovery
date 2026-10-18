"""Synthetic preparation input for software-only live-release contract tests."""
import copy

import pytest

from hte.io import write_json
from hte.preparation import build_stock_preparation, export_stock_preparation


@pytest.fixture
def synthetic_shallow_bulk_sources(tmp_path):
    """Exercise release bookkeeping without claiming the Falcon sources are safe.

    This deliberately artificial definition must stay in pytest's temporary
    directory. It is NOT a proposed container or validated physical geometry.
    """
    from opentrons.protocol_api.labware import get_labware_definition

    def configure(config):
        definition = copy.deepcopy(get_labware_definition(config["automation"]["bulk_labware"]))
        definition["namespace"] = "synthetic_tests_only"
        definition["parameters"]["loadName"] = "synthetic_shallow_bulk_sources_never_run_on_hardware"
        definition["metadata"]["displayName"] = "SYNTHETIC TEST ONLY — NOT PHYSICAL LABWARE"
        definition["dimensions"]["zDimension"] = 40
        for well in definition["wells"].values():
            well.update(depth=35, z=5)
        path = tmp_path / "SYNTHETIC_NOT_PHYSICAL_bulk_sources.json"
        write_json(path, definition)
        config["automation"]["bulk_definition_path"] = str(path)
        config["automation"]["bulk_container_status"] = "SYNTHETIC SOFTWARE TEST ONLY; never use this geometry on a robot"
        return path

    return configure


@pytest.fixture
def actual_stock_preparation(tmp_path, synthetic_shallow_bulk_sources):
    def prepare(config,inventory,design):
        synthetic_shallow_bulk_sources(config)
        plan=build_stock_preparation(config,inventory,design)
        charges=[dict(stock_id=r["stock_id"],actual_mass_mg=r["planned_mass_mg"],assay_fraction=r["assay_fraction"])
                 for r in plan["stocks"] if r["stock_id"]!="IS_MASTER"]
        out=export_stock_preparation(config,inventory,design,tmp_path/"fictional-weighed-charges",charges=charges)
        config["automation"]["preparation_manifest_path"]=str(out/"preparation_manifest.json")
        return out
    return prepare
