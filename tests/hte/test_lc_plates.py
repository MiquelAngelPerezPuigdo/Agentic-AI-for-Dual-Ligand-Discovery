"""Final LC plates are filled robotically, shaken and handed off without vial transfers."""
import ast
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from hte.demo import run, synthetic_config
from hte.inventory import campaign_inventory
from hte.io import read_csv, read_json
from hte.planning import schedule, validate_config, workup_timing
from hte.protocols import RUNTIME, export

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    out = tmp_path_factory.mktemp("lc-plates")/"demo"
    run(out, ROOT/"hte_inputs/ligands.csv", ROOT/"hte_inputs/campaign.json")
    return out


@pytest.mark.parametrize("round_number,batch_size", [(1, 48), (2, 48), (1, 24), (2, 24)])
def test_final_plate_simulations_preserve_doses_and_move_only_complete_plates(campaign, tmp_path, round_number, batch_size):
    from opentrons.simulate import simulate
    config = read_json(campaign/"campaign.json")
    config["robot"]["lc_batch_size"] = batch_size
    if batch_size == 24:
        config["robot"]["lc_single_plate_per_round"] = False  # Generic synthetic regression, outside this campaign.
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", config)
    out = tmp_path/"protocols"
    export(config, inv, read_csv(campaign/f"round{round_number}_design.csv"), out)
    ops = read_json(out/"operations.json")
    sequence = read_csv(out/"lc_sequence.csv")
    plates = read_csv(out/"lc_plates.csv")
    assert len(plates) == (2 if round_number == 1 and batch_size == 24 else 1)
    assert sum(int(p["sample_count"]) for p in plates) == len(sequence)
    # Every physical (plate, well) has exactly 980 + 20 uL; padding is never an injection.
    volumes = defaultdict(float)
    for op in ops:
        if op["stage"] in ("dilution", "sampling"):
            for well in op["destination_wells"]:
                volumes[(op["lc_batch"], well)] += op["volume_ul_per_channel"]
    for row in sequence:
        assert volumes[(int(row["lc_batch"]), row["well"])] == pytest.approx(1000)
        assert row["lc_plate_id"] == f"R{round_number}-LC{int(row['lc_batch']):02d}"
    if round_number == 2:
        assert volumes[(1, "H3")] == 980
        assert "H3" not in {r["well"] for r in sequence}
    # No retained tip crosses a plate handoff. Surplus accounting matches actual runtime order.
    ordered = [o for o in ops if o["stage"] == "workup"]
    for batch in range(1, len(plates)+1):
        ordered += [o for stage in ("dilution", "sampling") for o in ops
                    if o["stage"] == stage and o.get("lc_batch") == batch]
    held = None
    for op in ordered:
        key = (op["stage"], op["source_slot"], op["source_well"], op["pipette"], op.get("lc_batch"))
        assert bool(held) == op["retained_tip_from_previous"]
        if held: assert key == held
        held = key if op["retain_tip_for_next"] else None
    assert held is None
    with (out/"workup.py").open() as f:
        commands, _ = simulate(f)
    texts = [c["payload"].get("text", "") for c in commands]
    first_reservoir_aspiration = next(
        i for i, command in enumerate(commands)
        if command["payload"].get("text", "").startswith("Aspirating")
        and command["payload"]["location"].labware.first_parent() == "2")
    uncover = [i for i, text in enumerate(texts)
               if "UNCOVER the prepared liquid reservoir in slot 2" in text]
    assert uncover and min(uncover) < first_reservoir_aspiration
    if len(plates) == 1:
        # The first withdrawal is LC diluent: opening reaction vials comes later.
        assert "Leave the cooled reaction vials CAPPED" in texts[min(uncover)]
        opening = next(i for i, text in enumerate(texts) if "Separately CONFIRM" in text)
        assert first_reservoir_aspiration < opening
    else:
        assert "keep it uncovered through LC preparation" in texts[min(uncover)]
    # The block is opened once, mixed open, sampled open, then each completed
    # sampling batch is capped once for archive. No intermediate recap/reopen.
    opening = [i for i, t in enumerate(texts) if "UNSCREW/REMOVE" in t]
    quench = [i for i, t in enumerate(texts) if t.startswith("workup:")]
    open_shake = next(i for i, t in enumerate(texts) if "Leave every quenched reaction vial OPEN" in t)
    shakes = [i for i, t in enumerate(texts) if t.startswith("Setting Heater-Shaker to Shake")]
    assert len(opening) == 1 and opening[0] < min(quench) <= max(quench) < open_shake < shakes[0]
    assert len(shakes) == 1 + len(plates)
    assert all("Shake at 750 RPM" in texts[i] for i in shakes)
    assert all(texts[i+1].startswith("Delaying for 2 minutes") for i in shakes)
    assert any("Deactivating Heater" in t for t in texts[:shakes[0]])
    assert not any("Setting Target Temperature of Heater-Shaker" in t for t in texts)
    assert "heater OFF" in texts[open_shake] and "Do not recap" in texts[open_shake]
    assert not any("RECAP ONLY" in t for t in texts[:shakes[0]])
    sampling_prompts = [t for t in texts if "Sampling batch " in t]
    assert len(sampling_prompts) == len(plates)
    assert all("remain OPEN since quenching" in t and "no additional cap removal is needed" in t
               for t in sampling_prompts)
    lc_moves = [t for t in texts if t.startswith(f"Moving R{round_number}-LC")]
    assert len(lc_moves) == 2*len(plates)
    for plate in plates:
        label = plate["lc_plate_id"]
        move = texts.index(f"Moving {label} to opentrons_universal_flat_adapter")
        end = texts.index(f"Moving {label} to off-deck")
        assert "UNCOVERED" in texts[move-2]
        assert "RECAP ONLY the sampled reaction vials once for archive" in texts[move-2]
        assert "keep any not-yet-sampled reaction vials OPEN" in texts[move-2]
        assert "Deactivating Heater" in texts[move-3]
        assert any("Shake at 750 RPM" in t for t in texts[move:end])
        assert any("Delaying for 2 minutes" in t for t in texts[move:end])
        assert not any(t.startswith(("Aspirating", "Dispensing")) for t in texts[move:end])
        # All assigned nominal sample dispenses precede this plate's module move.
        members = {r["sample_id"] for r in sequence if r["lc_plate_id"] == label}
        assert sum(any(t.startswith(sample+":") for sample in members) for t in texts[:move]) == len(members)
    assert not any("transfer 900" in t or "fresh manual-pipette" in t for t in texts)


def test_lc_module_cooling_guard_waits_before_loading():
    from opentrons.protocol_api import HeaterShakerContext
    tree = ast.parse(RUNTIME)
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name in ("wait_for_cool_module", "shake_and_release_lc")]
    events = []
    # Use the actual SDK contract: a fabricated temperature attribute hid a robot-only bug.
    hs = create_autospec(HeaterShakerContext, instance=True, spec_set=True)
    hs.current_temperature = 55
    for name in ("deactivate_heater", "deactivate_shaker", "open_labware_latch", "close_labware_latch"):
        setattr(hs, name, lambda n=name: events.append(n))
    hs.set_and_wait_for_shake_speed = lambda rpm: events.append(("shake", rpm, hs.current_temperature))
    def pause(message):
        events.append(message)
        if message.startswith("Wait until"): hs.current_temperature = 25
    protocol = SimpleNamespace(is_simulating=lambda: False, pause=pause,
        move_labware=lambda *a, **k: events.append(("move", hs.current_temperature)),
        delay=lambda **k: events.append(k))
    ns = dict(hs=hs, protocol=protocol, CONFIG=read_json(ROOT/"hte_inputs/campaign.json"),
              ROUND=1, lc="plate", adapter="adapter", protocol_api=SimpleNamespace(OFF_DECK="off-deck"))
    exec(compile(ast.Module(body=functions, type_ignores=[]), "cooling-guard", "exec"), ns)
    ns["shake_and_release_lc"](1)
    assert any(isinstance(e, str) and e.startswith("Wait until") for e in events)
    assert ("shake", 750, 25) in events
    assert all(e[1] <= 30 for e in events if isinstance(e, tuple) and e[0] == "move")


@pytest.mark.parametrize("round_number", [1, 2])
def test_actual_sdk_executes_live_cooling_branch_before_quench(campaign, round_number):
    from io import StringIO
    from opentrons.simulate import simulate
    source = (campaign/f"round{round_number}/workup.py").read_text()
    # Exercise the normally skipped hardware-temperature read in the real SDK's
    # simulated context. DEMO remains True: this never releases runnable hardware code.
    source = source.replace("if not protocol.is_simulating():", "if True:")
    commands, _ = simulate(StringIO(source))
    texts = [c["payload"].get("text", "") for c in commands]
    opening = next(i for i, t in enumerate(texts) if "Separately CONFIRM" in t)
    quench = next(i for i, t in enumerate(texts) if t.startswith("workup:"))
    assert any("Deactivating Heater" in t for t in texts[:opening])
    assert opening < quench


def test_round2_changeover_confirms_new_vials_are_uncapped_before_dosing(campaign):
    from opentrons.simulate import simulate
    with (campaign/"round2/dose_and_react.py").open() as stream:
        commands, _ = simulate(stream)
    texts = [c["payload"].get("text", "") for c in commands]
    changeover = next(i for i, t in enumerate(texts) if "Round two: CONFIRM" in t)
    first_dose = next(i for i, t in enumerate(texts) if t.startswith("Aspirating"))
    assert changeover < first_dose
    assert "REMOVE ALL 23" in texts[changeover] and "23 NEW EMPTY" in texts[changeover]


@pytest.mark.parametrize("key,value", [("mix_rpm", 0), ("mix_rpm", 1500), ("mix_rpm", 751), ("lc_mix_rpm", 0), ("lc_mix_rpm", 1000), ("lc_mix_rpm", 751), ("lc_mix_minutes", 0), ("lc_max_module_temperature_C", 60)])
def test_invalid_plate_shaking_settings_rejected(key, value):
    c = synthetic_config(ROOT/"hte_inputs/campaign.json")
    c["liquids"][key] = value
    with pytest.raises(ValueError): validate_config(c)


def test_plate_geometry_is_unchanged_and_split_overlap_is_round_specific():
    original = read_json(ROOT/"hte_inputs/labware/vwr_96_wellplate_2200ul.json")
    derived = read_json(ROOT/"hte_inputs/labware/vwr_96_wellplate_2200ul_hs.json")
    assert original["wells"] == derived["wells"] and original["ordering"] == derived["ordering"]
    c = synthetic_config(ROOT/"hte_inputs/campaign.json")
    c["robot"]["lc_single_plate_per_round"] = False  # Generic timing regression only.
    c["robot"]["lc_batch_size"] = 24
    c["timing"].update(staged_lc_overlap_minutes=35, staged_lc_overlap_minutes_by_round={"1":35, "2":0})
    assert schedule(c)["manual_lc_plate_moves"] == 6
    assert schedule(c)["planned_total_minutes"] == pytest.approx(829.7)
    c["timing"]["staged_lc_overlap_minutes_by_round"] = {"1":25, "2":10}
    with pytest.raises(ValueError, match="preceding injection windows"): schedule(c)


def test_campaign_forbids_r1_plate_splitting():
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    assert config["robot"]["lc_single_plate_per_round"]
    config["robot"]["lc_batch_size"] = 24
    with pytest.raises(ValueError, match="splitting R1 is disabled"):
        validate_config(config)


@pytest.mark.parametrize("round_number,reuse", [(1, True), (2, True), (1, False), (2, False)])
def test_timing_subtotal_matches_actual_simulator_pumps_and_delays(campaign, tmp_path, round_number, reuse):
    import re
    from opentrons.simulate import simulate
    config = read_json(campaign/"campaign.json")
    config["pipetting"]["reuse_tips"] = reuse
    if not reuse: config["stock_preparation"]["substrate_margin_factor"] = 1.2
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", config)
    out = tmp_path/"protocols"
    export(config, inv, read_csv(campaign/f"round{round_number}_design.csv"), out)
    report = read_json(out/"workup_timing.json")
    with (out/"workup.py").open() as f:
        commands, _ = simulate(f)
    seconds = 0
    for command in commands:
        payload = command["payload"]
        text = payload.get("text", "")
        pump = re.match(r"(?:Aspirating|Dispensing) ([\d.]+) uL .* at ([\d.]+) uL/sec", text)
        if pump:
            seconds += float(pump[1])/float(pump[2])
        elif text.startswith("Delaying for"):
            seconds += payload["minutes"]*60+payload["seconds"]
    assert seconds/60 == pytest.approx(report["calculated_subtotal_minutes"])
    assert report["individual_screw_cap_actions"] == 2*(48 if round_number == 1 else 23)
    assert report["manual_workup_block_and_lc_moves"] == 4
    assert not report["physical_run_measured"] and report["excluded"]
