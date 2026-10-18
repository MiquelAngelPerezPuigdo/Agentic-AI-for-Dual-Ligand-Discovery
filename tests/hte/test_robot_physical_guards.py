"""Physical constraints that the Opentrons command simulator does not certify."""
import json
from pathlib import Path

import pytest

from hte.inventory import campaign_inventory
from hte.io import read_csv, read_json
from hte.planning import required_validations
from hte.preparation import (LIQUID_RUNTIME, build_stock_preparation, export_stock_preparation,
                             preparation_timing, validate_source_reach)
from hte.protocols import export

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def inputs():
    config = read_json(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config, confirmed=True)
    first = read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv")
    return config, inventory, first


def test_deep_falcon_default_fails_reach_for_both_pipettes(inputs):
    config, inventory, first = inputs
    plan = build_stock_preparation(config, inventory, first)
    assessment = plan["source_reach_assessment"]
    assert assessment["status"] == "blocked"
    assert not assessment["physical_clearance_validated"]
    bulk = [issue for issue in assessment["issues"] if issue["source"][0].startswith("BULK")]
    assert {issue["tiprack"] for issue in bulk} == {"opentrons_96_tiprack_300ul", "opentrons_96_tiprack_1000ul"}
    assert all(issue["required_insertion_mm"] == 116 for issue in bulk)
    assert {issue["available_tip_reach_mm"] for issue in bulk} == {51.83, 80.05}
    with pytest.raises(ValueError, match="source reach"):
        validate_source_reach(config, plan)


def test_custom_shallow_geometry_is_rechecked_not_manifest_claim(inputs, tmp_path):
    from opentrons.protocol_api.labware import get_labware_definition
    config, inventory, first = inputs
    plan = build_stock_preparation(config, inventory, first)
    definition = get_labware_definition(config["automation"]["bulk_labware"])
    definition["metadata"]["displayName"] = "SYNTHETIC reach-check fixture; never use on hardware"
    definition["parameters"]["loadName"] = "synthetic_shallow_bulk_test_only"
    definition["dimensions"]["zDimension"] = 40
    for well in definition["wells"].values():
        well.update(depth=35, z=5)
    path = tmp_path / "SYNTHETIC_shallow_source.json"
    path.write_text(json.dumps(definition))
    config["automation"]["bulk_definition_path"] = str(path)
    assert validate_source_reach(config, plan)["status"] == "geometric_check_passed"
    # A manifest's claimed pass cannot override a changed physical definition.
    plan["source_reach_assessment"]["status"] = "geometric_check_passed"
    for well in definition["wells"].values():
        well["depth"] = 117.5
    path.write_text(json.dumps(definition))
    with pytest.raises(ValueError, match="source reach"):
        validate_source_reach(config, plan)


def test_live_stock_and_reaction_exports_reject_deep_default_even_with_flags(inputs, tmp_path):
    config, inventory, first = inputs
    config["analytics"]["method_id"] = "TEST_ONLY_METHOD"
    for key in required_validations(config):
        config["validation"][key] = True
    plan = build_stock_preparation(config, inventory, first)
    charges = [dict(stock_id=row["stock_id"], actual_mass_mg=row["planned_mass_mg"], assay_fraction=row["assay_fraction"])
               for row in plan["stocks"] if row["stock_id"] != "IS_MASTER"]
    with pytest.raises(ValueError, match="source reach"):
        export_stock_preparation(config, inventory, first, tmp_path / "live", charges, live=True)
    preview = export_stock_preparation(config, inventory, first, tmp_path / "preview", charges)
    with pytest.raises(ValueError, match="source reach"):
        export(config, inventory, first, tmp_path / "live-r1", live=True, stage="dose_and_react",
               preparation_path=preview / "preparation_manifest.json")


def test_preparation_lower_bound_matches_split_strokes_and_mixing(inputs):
    config, *_ = inputs
    plan = {"steps": [dict(type="pause", message="operator"),
                      dict(type="transfer", pipette="large", volume_ul=1500),
                      dict(type="mix", pipette="large", volume_ul=900, cycles=8)]}
    result = preparation_timing(config, plan)
    # Two 750 uL strokes, one 1 uL reverse surplus retained across them,
    # two prewet cycles, two 2 uL air gaps and one second delay per stroke.
    transfer = 2 * 751 * (1 / 200 + 1 / 400) + 1505 / 200 + 1504 / 400 + 2
    mixing = 8 * (900 / 200 + 900 / 400 + 1)
    assert result["seconds"] == pytest.approx(transfer + mixing)
    assert result["transfer_strokes"] == 2 and result["mix_events"] == 1
    assert result["manual_pause_count"] == 1
    assert not result["physical_duration_measured"]


class FakeProtocol:
    def __init__(self, clock, simulated=False):
        self.clock, self.simulated, self.comments = clock, simulated, []

    def is_simulating(self):
        return self.simulated

    def comment(self, message):
        self.comments.append(message)

    def pause(self, message):
        self.clock[0] = 241


def timer_classes(config):
    namespace = {"CONFIG": config}
    exec(LIQUID_RUNTIME, namespace)
    return namespace["ReactionHoldTimer"], namespace["execute_liquid_plan"]


def test_expired_operator_pause_aborts_before_next_liquid_action(inputs):
    config, *_ = inputs
    timer_type, execute = timer_classes(config)
    clock = [0.0]
    protocol = FakeProtocol(clock)
    timer = timer_type(protocol, 240, 60, clock=lambda: clock[0])
    plan = {"steps": [dict(type="pause", message="wait for operator"),
                      dict(type="transfer", pipette="single", volume_ul=100)]}
    with pytest.raises(RuntimeError, match="expired during preparation"):
        execute(protocol, plan, {}, None, check_deadline=timer.check)
    records = [json.loads(comment.removeprefix("HOLD_TIMING ")) for comment in protocol.comments]
    assert records[-1]["event"] == "preparation_deadline_exceeded"
    assert records[-1]["elapsed_seconds"] == 241 and records[-1]["failed"]


def test_hold_end_overrun_is_recorded_and_rejected(inputs):
    config, *_ = inputs
    timer_type, _ = timer_classes(config)
    clock = [0.0]
    protocol = FakeProtocol(clock)
    timer = timer_type(protocol, 240, 60, clock=lambda: clock[0])
    clock[0] = 301
    with pytest.raises(RuntimeError, match="timing tolerance"):
        timer.finish()
    assert json.loads(protocol.comments[-1].removeprefix("HOLD_TIMING "))["overrun_seconds"] == 61


def test_simulation_never_claims_physical_hold_duration(inputs):
    config, *_ = inputs
    timer_type, _ = timer_classes(config)
    clock = [0.0]
    protocol = FakeProtocol(clock, simulated=True)
    timer = timer_type(protocol, 240, 60, clock=lambda: clock[0])
    clock[0] = 1000
    timer.check()
    assert timer.remaining() == 240
    timer.finish()
    record = json.loads(protocol.comments[-1].removeprefix("HOLD_TIMING "))
    assert record["elapsed_seconds"] is None and not record["physical_duration_measured"]
