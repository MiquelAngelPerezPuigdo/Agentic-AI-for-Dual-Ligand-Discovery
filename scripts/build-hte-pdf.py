#!/usr/bin/env python3
"""Build the editable-source HTE handbook; no API calls or robot execution."""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
from html import escape
import json
import posixpath
from pathlib import Path
import sys
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import mistune
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.planning import required_validations, schedule  # noqa: E402

REPO = "https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery"
CHAPTERS = [
    ("start-here.md", "Quickstart and responsibilities"),
    ("hte-runbook.md", "Complete operator runbook"),
    ("stocks-and-calibration.md", "Combined stock and analytical calibration"),
    ("hte-questions.md", "Facts to confirm with HTE"),
    ("prompt-caching.md", "Claude prompt caching and costs"),
    ("rehearsal-results.md", "Software rehearsal evidence"),
]
BLUE = colors.HexColor("#183B56")
TEAL = colors.HexColor("#087E8B")
GRAY = colors.HexColor("#52616B")
PALE = colors.HexColor("#F2F6F9")
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 42
WIDTH = PAGE_WIDTH - 2*MARGIN


def readable(text):
    replacements = {"–": "-", "—": "-", "‑": "-", "−": "-", "₂": "2", "₃": "3", "≥": ">="}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def register_fonts():
    fonts = Path(reportlab.__file__).parent/"fonts"
    for name, filename in [("HTE", "Vera.ttf"), ("HTE-Bold", "VeraBd.ttf"),
                           ("HTE-Italic", "VeraIt.ttf"), ("HTE-BoldItalic", "VeraBI.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts/filename)))
    pdfmetrics.registerFontFamily("HTE", normal="HTE", bold="HTE-Bold", italic="HTE-Italic", boldItalic="HTE-BoldItalic")


def styles():
    sheet = StyleSheet1()
    specifications = {
        "body": dict(fontName="HTE", fontSize=9.7, leading=14.4, spaceAfter=8, textColor=BLUE),
        "chapter": dict(fontName="HTE-Bold", fontSize=19, leading=24, spaceAfter=12, textColor=BLUE, keepWithNext=True),
        "section": dict(fontName="HTE-Bold", fontSize=12.4, leading=17, spaceBefore=14, spaceAfter=7, textColor=TEAL, keepWithNext=True),
        "subsection": dict(fontName="HTE-Bold", fontSize=10.5, leading=15, spaceBefore=10, spaceAfter=6, textColor=BLUE, keepWithNext=True),
        "small": dict(fontName="HTE", fontSize=8.1, leading=11.5, spaceAfter=8, textColor=GRAY),
        "cell": dict(fontName="HTE", fontSize=8.3, leading=11.8, textColor=BLUE),
        "cell_header": dict(fontName="HTE-Bold", fontSize=8.1, leading=11.5, textColor=colors.white),
        "code": dict(fontName="Courier", fontSize=8, leading=11, spaceBefore=4, spaceAfter=12,
                     borderPadding=9, backColor=PALE, textColor=BLUE),
        "title": dict(fontName="HTE-Bold", fontSize=26, leading=32, textColor=BLUE, spaceAfter=12),
        "subtitle": dict(fontName="HTE", fontSize=12, leading=17, textColor=GRAY, spaceAfter=18),
    }
    for name, attributes in specifications.items():
        sheet.add(ParagraphStyle(name, alignment=TA_LEFT, splitLongWords=True, allowWidows=0, allowOrphans=0, **attributes))
    return sheet


def inline(tokens, table=False):
    output = []
    for token in tokens:
        kind = token["type"]
        children = token.get("children", [])
        raw = escape(readable(token.get("raw", "")))
        if kind == "text": output.append(raw)
        elif kind == "strong": output.append("<b>"+inline(children, table)+"</b>")
        elif kind == "emphasis": output.append("<i>"+inline(children, table)+"</i>")
        elif kind == "codespan": output.append('<font name="Courier" size="'+("7.5" if table else "8.5")+'">'+raw+"</font>")
        elif kind in ("softbreak", "linebreak"): output.append(" " if kind == "softbreak" else "<br/>")
        elif kind == "link":
            target = token["attrs"]["url"]
            filename = Path(urlparse(target).path).name
            local = next((i for i, (name, _) in enumerate(CHAPTERS, 1) if name == filename), None)
            target = f"#chapter-{local}" if local and not urlparse(target).scheme else target
            if not urlparse(target).scheme and not target.startswith("#"):
                parsed = urlparse(target)
                path = posixpath.normpath(posixpath.join("docs", parsed.path))
                target = REPO+"/blob/main/"+path
                if parsed.query: target += "?"+parsed.query
                if parsed.fragment: target += "#"+parsed.fragment
            output.append('<link href="'+escape(target, quote=True)+'" color="#087E8B">'+inline(children, table)+"</link>")
        elif kind == "inline_html": output.append(raw)
        else: raise ValueError(f"Unsupported Markdown inline type: {kind}; add support before rebuilding")
    return "".join(output)


def plain(token):
    return token.get("raw", "")+"".join(plain(child) for child in token.get("children", []))


class Handbook(BaseDocTemplate):
    def __init__(self, output, edition, source_hash):
        super().__init__(str(output), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=45, bottomMargin=42, title="HTE operator handbook",
                         author="Agentic AI for Dual-Ligand Discovery", subject="Local OT-2 dual-ligand screening; editable-source HTE handoff")
        self.edition, self.source_hash = edition, source_hash
        frame = Frame(MARGIN, 42, WIDTH, PAGE_HEIGHT-87, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="handbook", frames=frame, onPage=self.furniture))

    def furniture(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D8E1E8"))
        canvas.line(MARGIN, 33, PAGE_WIDTH-MARGIN, 33)
        canvas.setFillColor(GRAY)
        canvas.setFont("HTE", 7.4)
        canvas.drawString(MARGIN, 21, f"HTE operator handbook | {self.edition.isoformat()} | source {self.source_hash[:10]}")
        canvas.drawRightString(PAGE_WIDTH-MARGIN, 21, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if hasattr(flowable, "bookmark"):
            self.canv.bookmarkPage(flowable.bookmark)
            self.canv.addOutlineEntry(flowable.getPlainText(), flowable.bookmark, level=flowable.toc_level)
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page, flowable.bookmark))


def markdown_blocks(tokens, sheet, chapter, counter):
    output = []
    for token in tokens:
        kind = token["type"]
        if kind == "blank_line": continue
        if kind in ("paragraph", "block_text"):
            output.append(Paragraph(inline(token["children"]), sheet["body"]))
        elif kind == "heading":
            level = token["attrs"]["level"]
            if level == 1: continue  # The chapter heading replaces the source title.
            paragraph = Paragraph(inline(token["children"]), sheet["section" if level == 2 else "subsection"])
            if level == 2:
                counter[0] += 1
                paragraph.bookmark, paragraph.toc_level = f"section-{chapter}-{counter[0]}", 1
            output.append(paragraph)
        elif kind == "block_code":
            raw = readable(token["raw"]).rstrip("\n")
            longest = max((pdfmetrics.stringWidth(line, "Courier", 8) for line in raw.splitlines()), default=0)
            if longest > WIDTH-20:
                raise ValueError("A code line exceeds PDF width; wrap the command in its Markdown source")
            output.append(Preformatted(raw, sheet["code"]))
        elif kind == "list":
            items = [ListItem(markdown_blocks(item["children"], sheet, chapter, counter), spaceAfter=3)
                     for item in token["children"]]
            ordered = token["attrs"]["ordered"]
            output.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                       start=token["attrs"].get("start", 1) if ordered else "\u2022",
                                       leftIndent=16, bulletFontName="HTE", bulletFontSize=9,
                                       spaceAfter=7))
        elif kind == "table":
            head = token["children"][0]
            body = token["children"][1]
            source_rows = [head["children"]]+[row["children"] for row in body["children"]]
            ncols = len(source_rows[0])
            # Bounded weights give technical descriptions room without starving narrow numeric columns.
            weights = [max(7, min(38, max(len(plain(row[i])) for row in source_rows)))**0.5 for i in range(ncols)]
            col_widths = [WIDTH*weight/sum(weights) for weight in weights]
            rows = [[Paragraph(inline(cell["children"], table=True), sheet["cell_header" if r == 0 else "cell"])
                     for cell in row] for r, row in enumerate(source_rows)]
            table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8E1E8")),
            ]))
            if len(rows) <= 9 and table.wrap(WIDTH, PAGE_HEIGHT)[1] <= 300:
                output.append(KeepTogether([table, Spacer(1, 12)]))
            else:
                output.extend([table, Spacer(1, 12)])
        elif kind == "block_quote":
            output.extend(markdown_blocks(token["children"], sheet, chapter, counter))
        elif kind == "thematic_break": output.append(Spacer(1, 10))
        else: raise ValueError(f"Unsupported Markdown block type: {kind}; add support before rebuilding")
    return output


def input_record():
    paths = ["docs/"+name for name, _ in CHAPTERS]+[
        "hte_inputs/campaign.json", "hte_inputs/calibration_template.csv", "hte_inputs/ligands.csv",
        "software_validation.json", "scripts/build-hte-pdf.py", "hte/planning.py", "hte/io.py",
    ]
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return hashes, fingerprint


def build(output, edition):
    register_fonts()
    sheet = styles()
    config = json.loads((ROOT/"hte_inputs/campaign.json").read_text())
    validation = json.loads((ROOT/"software_validation.json").read_text())
    source_hashes, source_hash = input_record()
    timing = schedule(config)
    chemistry, liquid = config["chemistry"], config["liquids"]
    missing = [key for key in required_validations(config) if config["validation"].get(key) is not True]
    story = [Paragraph("HTE operator handbook", sheet["title"]),
             Paragraph("Local OT-2 dual-ligand fluorination screen", sheet["subtitle"]),
             Paragraph(f"Edition: {edition.strftime('%d %B %Y')} (Europe/Zurich). Generated from editable repository sources.", sheet["small"])]
    status = "HTE configuration review - bench checks remain open" if missing else "Recorded bench checks complete - use the campaign-specific generated handoff"
    story.append(Paragraph(status, sheet["section"]))
    cover_rows = [
        ("Campaign", f"{config['design']['round1_total']} first-round wells; {config['design']['round2_total']} second-round wells"),
        ("Reaction", f"{chemistry['substrate_molarity_M']*chemistry['reaction_volume_ul']:g} µmol substrate; {chemistry['reaction_volume_ul']:g} µL toluene; {chemistry['temperature_C']:g} °C; {chemistry['reaction_minutes']:g} min per round"),
        ("Catalysts", f"{chemistry['ligand_a_mol_percent']:g} mol% each ligand; {chemistry['pd_mol_percent']:g} mol% Pd(COD)(DQ)"),
        ("Sample dilution", f"{liquid['aliquot_ul']:g} µL extract + {liquid['diluent_ul']:g} µL IS-free LC diluent"),
        ("Software evidence", f"{validation['tests']['tests']} local tests; {validation['tests']['failures']} failures. Rehearsal chemistry and Claude responses are synthetic."),
        ("Bench readiness", f"{len(missing)} applicable validation fields still unconfirmed; exact hardware and analytical settings must be supplied by HTE."),
        ("Provisional timing", f"{timing['serial_total_minutes']:g} min planned / {timing['deadline_minutes']:g} min competition limit"),
    ]
    table = Table([[Paragraph(escape(label), sheet["cell"]), Paragraph(escape(readable(value)), sheet["cell"])]
                   for label, value in cover_rows], colWidths=[126, WIDTH-126])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("BACKGROUND", (0, 0), (0, -1), PALE),
                              ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                              ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8E1E8"))]))
    story.extend([table, Spacer(1, 16), Paragraph("How to keep this handbook current", sheet["section"]),
                  Paragraph("Edit the Markdown sources in <b>docs/</b> and the relevant campaign configuration, then regenerate locally or download the fresh GitHub workflow edition. The PDF is a dated export; the editable sources remain the master. Keep the PDF with its build manifest to check for later source changes.", sheet["body"]),
                  Preformatted("python scripts/build-hte-pdf.py", sheet["code"]),
                  Paragraph(f'<link href="{REPO}" color="#087E8B">Open the shared repository</link> - see <link href="{REPO}/blob/main/docs/updating-the-handbook.md" color="#087E8B">PDF update instructions</link>.', sheet["body"]),
                  Paragraph("Generated quantities from the real selected campaign take precedence over the synthetic demo. This handbook includes the procedures and outstanding decisions; it does not supply unmeasured geometry or analytical settings.", sheet["small"]),
                  PageBreak(), Paragraph("Contents", sheet["chapter"])])
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc0", fontName="HTE-Bold", fontSize=9.6, leading=13, spaceBefore=6, textColor=BLUE),
                       ParagraphStyle("toc1", fontName="HTE", fontSize=8.8, leading=11.5, leftIndent=14, firstLineIndent=0, textColor=GRAY)]
    story.append(toc)
    parser = mistune.create_markdown(renderer="ast", plugins=["table"])
    for number, (filename, title) in enumerate(CHAPTERS, 1):
        story.append(PageBreak())
        heading = Paragraph(f"{number}. {title}", sheet["chapter"])
        heading.bookmark, heading.toc_level = f"chapter-{number}", 0
        story.extend([heading, Paragraph(f'<link href="{REPO}/blob/main/docs/{filename}" color="#087E8B">Editable source: docs/{filename}</link>', sheet["small"])])
        story.extend(markdown_blocks(parser((ROOT/"docs"/filename).read_text()), sheet, number, [0]))
    output.parent.mkdir(parents=True, exist_ok=True)
    Handbook(output, edition, source_hash).multiBuild(story)
    from pypdf import PdfReader
    reader = PdfReader(output)
    manifest = {"edition_date": edition.isoformat(), "edition_timezone": "Europe/Zurich", "source_sha256": source_hash,
                "sources": source_hashes, "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "pages": len(reader.pages),
                "editable_master": "docs/*.md and hte_inputs/campaign.json; rebuild with scripts/build-hte-pdf.py",
                "private_email_included": False, "api_calls": 0}
    output.with_suffix(".build.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"output/pdf/HTE-operator-handbook.pdf")
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(ZoneInfo("Europe/Zurich")).date(), help="Edition date, YYYY-MM-DD; default Europe/Zurich today")
    parser.add_argument("--check", action="store_true", help="Verify an existing PDF and its manifest against current sources; do not rebuild")
    args = parser.parse_args()
    if args.check:
        manifest = json.loads(args.output.with_suffix(".build.json").read_text())
        if manifest["source_sha256"] != input_record()[1] or manifest["pdf_sha256"] != hashlib.sha256(args.output.read_bytes()).hexdigest():
            raise SystemExit("The PDF or its sources changed. Rebuild before distributing it.")
        print("PDF and source manifest match; "+str(manifest["pages"])+" pages")
    else:
        manifest = build(args.output, args.date)
        print(json.dumps({"output": str(args.output), "pages": manifest["pages"], "source_sha256": manifest["source_sha256"]}))


if __name__ == "__main__":
    main()
