"""The browser handoff must link to real files and match robot solvent loads."""
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from hte.io import read_json
from hte.preparation import Plan, raw_sources


ROOT = Path(__file__).resolve().parents[2]


def test_browser_procedure_and_deck_links_resolve():
    for relative in ("docs/HTE-START-HERE.md", "docs/deck-loading.md"):
        document = ROOT / relative
        links = re.findall(r"\]\(([^)]+)\)", document.read_text())
        assert links
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            path = (document.parent / unquote(parsed.path)).resolve()
            assert path.is_file(), f"Broken link in {relative}: {link}"
            if parsed.fragment and path.suffix == ".md":
                headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", path.read_text(), re.MULTILINE)
                slugs = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}
                assert unquote(parsed.fragment) in slugs, f"Broken heading link in {relative}: {link}"


def test_published_solvent_positions_and_minimums_match_generated_plan():
    config = read_json(ROOT / "hte_inputs/campaign.json")
    assert not config["automation"]["prepare_optional_pilot"]
    expected = {}
    for phase, label in (("stocks", "Stocks"), ("hold", "Hold")):
        _, rows = raw_sources(Plan(config), phase)
        for row in rows:
            reagent = {"ACN": "Acetonitrile", "FA": "Formic acid"}.get(row["reagent"], row["reagent"].title())
            expected[(label, str(row["slot"]), row["well"])] = (reagent, row["minimum_load_ul"] / 1000)
    pattern = r"^\| (Stocks|Hold) \| (\d+) \| ([A-H]1) \| ([A-Za-z ]+) \| ([\d.]+) \|$"
    matches = re.findall(pattern, (ROOT / "docs/deck-loading.md").read_text(), re.MULTILINE)
    published = {(phase, slot, well): (reagent, float(volume)) for phase, slot, well, reagent, volume in matches}
    assert len(matches) == len(published) == len(expected)
    assert published == expected
