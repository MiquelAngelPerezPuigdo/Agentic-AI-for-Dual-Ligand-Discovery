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
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPO = "https://github.com/MiquelAngelPerezPuigdo/Agentic-AI-for-Dual-Ligand-Discovery"
CHAPTERS = [
    ("hte-runbook.md", "Experiment"),
    ("stocks-and-calibration.md", "Stocks and calibration"),
    ("start-here.md", "Local pipeline"),
]
INK = colors.HexColor("#242423")
GRAY = colors.HexColor("#64645F")
PALE = colors.HexColor("#F0EFEB")
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 42
WIDTH = PAGE_WIDTH - 2*MARGIN


def readable(text):
    replacements = {"–": "-", "—": "-", "‑": "-", "−": "-", "₂": "2", "₃": "3", "≥": ">="}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def register_fonts():
    for name, face in [("HTE", "Helvetica"), ("HTE-Bold", "Helvetica-Bold"),
                       ("HTE-Italic", "Helvetica-Oblique"), ("HTE-BoldItalic", "Helvetica-BoldOblique")]:
        pdfmetrics.registerFont(pdfmetrics.Font(name, face, "WinAnsiEncoding"))
    pdfmetrics.registerFontFamily("HTE", normal="HTE", bold="HTE-Bold", italic="HTE-Italic", boldItalic="HTE-BoldItalic")


def styles():
    sheet = StyleSheet1()
    specifications = {
        "body": dict(fontName="HTE", fontSize=9.5, leading=12.4, spaceAfter=4, textColor=INK),
        "chapter": dict(fontName="HTE-Bold", fontSize=15, leading=19, spaceAfter=9, textColor=INK, keepWithNext=True),
        "section": dict(fontName="HTE-Bold", fontSize=10.8, leading=14, spaceBefore=8, spaceAfter=4, textColor=INK, keepWithNext=True),
        "subsection": dict(fontName="HTE-Bold", fontSize=9.7, leading=13, spaceBefore=8, spaceAfter=4, textColor=INK, keepWithNext=True),
        "small": dict(fontName="HTE", fontSize=8, leading=11, spaceAfter=7, textColor=GRAY),
        "cell": dict(fontName="HTE", fontSize=8.7, leading=11.2, textColor=INK),
        "cell_header": dict(fontName="HTE-Bold", fontSize=8.5, leading=11.2, textColor=INK),
        "code": dict(fontName="Courier", fontSize=7.7, leading=10, spaceBefore=3, spaceAfter=8,
                     borderPadding=7, backColor=PALE, textColor=INK),
        "title": dict(fontName="Times-Roman", fontSize=25, leading=29, textColor=INK, spaceAfter=5),
        "subtitle": dict(fontName="HTE", fontSize=9, leading=13, textColor=GRAY, spaceAfter=13),
    }
    for name, attributes in specifications.items():
        sheet.add(ParagraphStyle(name, alignment=TA_LEFT, splitLongWords=True, allowWidows=0, allowOrphans=0, **attributes))
    return sheet


def inline(tokens, table=False, internal_chapters=True):
    output = []
    for token in tokens:
        kind = token["type"]
        children = token.get("children", [])
        raw = escape(readable(token.get("raw", "")))
        if kind == "text": output.append(raw)
        elif kind == "strong": output.append("<b>"+inline(children, table, internal_chapters)+"</b>")
        elif kind == "emphasis": output.append("<i>"+inline(children, table, internal_chapters)+"</i>")
        elif kind == "codespan": output.append('<font name="Courier" size="'+("7.5" if table else "8.5")+'">'+raw+"</font>")
        elif kind in ("softbreak", "linebreak"): output.append(" " if kind == "softbreak" else "<br/>")
        elif kind == "link":
            target = token["attrs"]["url"]
            filename = Path(urlparse(target).path).name
            local = next((i for i, (name, _) in enumerate(CHAPTERS, 1) if name == filename), None)
            target = f"#chapter-{local}" if internal_chapters and local and not urlparse(target).scheme else target
            if not urlparse(target).scheme and not target.startswith("#"):
                parsed = urlparse(target)
                path = posixpath.normpath(posixpath.join("docs", parsed.path))
                target = REPO+"/blob/main/"+path
                if parsed.query: target += "?"+parsed.query
                if parsed.fragment: target += "#"+parsed.fragment
            output.append('<link href="'+escape(target, quote=True)+'" color="#6B5A37">'+inline(children, table, internal_chapters)+"</link>")
        elif kind == "inline_html": output.append(raw)
        else: raise ValueError(f"Unsupported Markdown inline type: {kind}; add support before rebuilding")
    return "".join(output)


def plain(token):
    return token.get("raw", "")+"".join(plain(child) for child in token.get("children", []))


class Handbook(BaseDocTemplate):
    def __init__(self, output, edition, source_hash, staff=False):
        self.staff = staff
        self.document_title = "Bench sheet" if staff else "Experiment & local pipeline"
        super().__init__(str(output), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=45, bottomMargin=42, title=self.document_title,
                         author="Dual-ligand fluorination project", subject="HTEL / OT-2 experimental procedure")
        self.edition, self.source_hash = edition, source_hash
        frame = Frame(MARGIN, 42, WIDTH, PAGE_HEIGHT-87, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="handbook", frames=frame, onPage=self.furniture))

    def furniture(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#C9C7C0"))
        canvas.line(MARGIN, 33, PAGE_WIDTH-MARGIN, 33)
        canvas.setFillColor(GRAY)
        canvas.setFont("HTE", 7.4)
        canvas.drawString(MARGIN, 21, "HTEL / Dual-ligand fluorination")
        canvas.drawRightString(PAGE_WIDTH-MARGIN, 21, f"{self.edition.strftime('%d %b %Y')}  /  {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if hasattr(flowable, "bookmark"):
            self.canv.bookmarkPage(flowable.bookmark)
            self.canv.addOutlineEntry(flowable.getPlainText(), flowable.bookmark, level=0 if self.staff else flowable.toc_level)


def markdown_blocks(tokens, sheet, chapter, counter, compact=False):
    output = []
    for token in tokens:
        kind = token["type"]
        if kind == "blank_line": continue
        if kind in ("paragraph", "block_text"):
            output.append(Paragraph(inline(token["children"], internal_chapters=not compact), sheet["body"]))
        elif kind == "heading":
            level = token["attrs"]["level"]
            if level == 1: continue  # The chapter heading replaces the source title.
            paragraph = Paragraph(inline(token["children"], internal_chapters=not compact), sheet["section" if level == 2 else "subsection"])
            if level == 2:
                counter[0] += 1
                paragraph.bookmark, paragraph.toc_level = f"section-{chapter}-{counter[0]}", 1
            output.append(paragraph)
        elif kind == "block_code":
            raw = readable(token["raw"]).rstrip("\n")
            longest = max((pdfmetrics.stringWidth(line, "Courier", 8) for line in raw.splitlines()), default=0)
            if longest > WIDTH-20:
                raise ValueError("A code line exceeds PDF width; wrap the command in its Markdown source")
            output.append(KeepTogether([Preformatted(raw, sheet["code"])]))
        elif kind == "list":
            items = [ListItem(markdown_blocks(item["children"], sheet, chapter, counter, compact), spaceAfter=2 if compact else 3)
                     for item in token["children"]]
            ordered = token["attrs"]["ordered"]
            output.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                       start=token["attrs"].get("start", 1) if ordered else "\u2022",
                                       leftIndent=16, bulletFontName="HTE", bulletFontSize=9,
                                       spaceAfter=4 if compact else 7))
        elif kind == "table":
            head = token["children"][0]
            body = token["children"][1]
            source_rows = [head["children"]]+[row["children"] for row in body["children"]]
            ncols = len(source_rows[0])
            # Bounded weights give technical descriptions room without starving narrow numeric columns.
            weights = [max(7, min(38, max(len(plain(row[i])) for row in source_rows)))**0.5 for i in range(ncols)]
            col_widths = [WIDTH*weight/sum(weights) for weight in weights]
            if compact and ncols == 2:
                first = plain(source_rows[0][0]).strip()
                narrow = {"Slot": 44, "Step": 86, "Stock": 104}.get(first, 104)
                col_widths = [narrow, WIDTH-narrow]
            elif not compact and ncols == 2 and plain(source_rows[0][0]).strip() == "Action":
                col_widths = [108, WIDTH-108]
            elif ncols == 2 and plain(source_rows[0][0]).strip() == "Slot":
                col_widths = [58, WIDTH-58]
            elif ncols == 3 and plain(source_rows[0][0]).strip() == "Stock":
                col_widths = [102, WIDTH-182, 80]
            elif ncols == 3 and plain(source_rows[0][0]).strip() == "Solution":
                col_widths = [65, WIDTH-205, 140]
            elif compact and ncols == 4:
                col_widths = [70, 116, 154, WIDTH-340]
            rows = [[Paragraph(inline(cell["children"], table=True, internal_chapters=not compact), sheet["cell_header" if r == 0 else "cell"])
                     for cell in row] for r, row in enumerate(source_rows)]
            table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5 if compact else 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 if compact else 3),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#A6A299")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#DAD8D1")),
            ]))
            if len(rows) <= 9 and table.wrap(WIDTH, PAGE_HEIGHT)[1] <= 300:
                output.append(KeepTogether([table, Spacer(1, 6)]))
            else:
                output.extend([table, Spacer(1, 6)])
        elif kind == "block_quote":
            output.extend(markdown_blocks(token["children"], sheet, chapter, counter, compact))
        elif kind == "thematic_break": output.append(PageBreak())
        else: raise ValueError(f"Unsupported Markdown block type: {kind}; add support before rebuilding")
    return output


def input_record(staff=False):
    paths = (["docs/hte-staff-checklist.md", "docs/stocks-and-calibration.md"] if staff
             else ["docs/"+name for name, _ in CHAPTERS])+[
        "hte_inputs/campaign.json", "hte_inputs/calibration_template.csv", "hte_inputs/ligands.csv",
        "software_validation.json", "scripts/build-hte-pdf.py", "hte/planning.py", "hte/io.py",
    ]
    paths += ["hte/protocols.py", "hte/scoring.py", "hte/analytics.py", "hte/analytical_practice.py", "hte/cli.py",
              "hte/ingestion.py", "hte/workflow.py", "hte/design.py", "hte/initialization.py",
              "pyproject.toml", "uv.lock", "hte/analytical_stocks.py", "scripts/hte-lc-results.py",
              "hte/transfer.py", "hte/preparation.py", "scripts/hte-return-package.py",
              "hte_inputs/labware/axygen_8_reservoir_30000ul.json",
              "hte_inputs/labware/paradox_48_wellplate_2000ul_hs.json",
              "hte_inputs/labware/vwr_96_wellplate_2200ul_hs.json",
              "campaigns/hackathon2026/round1_design.csv", "campaigns/hackathon2026/scoring/campaign_provenance.json"]
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return hashes, fingerprint


def build(output, edition):
    register_fonts()
    sheet = styles()
    source_hashes, source_hash = input_record()
    story = [Paragraph("Dual-ligand fluorination", sheet["title"]),
             Paragraph("HTEL / Experiment &amp; local pipeline / Local OT-2", sheet["subtitle"])]
    parser = mistune.create_markdown(renderer="ast", plugins=["table"])
    for number, (filename, title) in enumerate(CHAPTERS, 1):
        if number > 1:
            story.append(PageBreak())
        heading = Paragraph(f"{number:02d} / {title}", sheet["chapter"])
        heading.bookmark, heading.toc_level = f"chapter-{number}", 0
        story.append(heading)
        source = (ROOT/"docs"/filename).read_text()
        story.extend(markdown_blocks(parser(source), sheet, number, [0]))
    output.parent.mkdir(parents=True, exist_ok=True)
    Handbook(output, edition, source_hash).build(story)
    from pypdf import PdfReader
    pages = len(PdfReader(output).pages)
    manifest = {"edition_date": edition.isoformat(), "edition_timezone": "Europe/Zurich", "source_sha256": source_hash,
                "sources": source_hashes, "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "pages": pages,
                "editable_master": "docs/hte-runbook.md, docs/stocks-and-calibration.md, docs/start-here.md; rebuild with scripts/build-hte-pdf.py",
                "private_email_included": False, "api_calls": 0}
    output.with_suffix(".build.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def build_staff(output, edition):
    register_fonts()
    sheet = styles()
    sheet["body"].fontSize, sheet["body"].leading, sheet["body"].spaceAfter = 9.5, 12.5, 5
    for name in ("cell", "cell_header"):
        sheet[name].fontSize, sheet[name].leading = 9, 11.6
    sheet["section"].fontSize, sheet["section"].spaceBefore, sheet["section"].spaceAfter = 11, 7, 5
    sheet["chapter"].fontSize, sheet["chapter"].spaceAfter = 17, 7
    hashes, source_hash = input_record(staff=True)
    parts = (ROOT/"docs/hte-staff-checklist.md").read_text().split("\n---\n")
    if len(parts) != 2:
        raise ValueError("Staff source must have exactly two pages separated by a standalone ---")
    parser = mistune.create_markdown(renderer="ast", plugins=["table"])
    story = []
    for number, part in enumerate(parts, 1):
        if number > 1:
            story.append(PageBreak())
        title = "Dual-ligand screen / "+("Setup" if number == 1 else "Run")
        story.extend([Paragraph(title, sheet["title"]),
                      Paragraph("HTEL / Bench sheet / Local OT-2", sheet["small"])])
        story.extend(markdown_blocks(parser(part), sheet, number, [0], compact=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    Handbook(output, edition, source_hash, staff=True).build(story)
    from pypdf import PdfReader
    pages = len(PdfReader(output).pages)
    if pages != 2:
        raise ValueError(f"Staff checklist grew to {pages} pages; shorten its source before distributing")
    manifest = {"edition_date": edition.isoformat(), "edition_timezone": "Europe/Zurich", "source_sha256": source_hash,
                "sources": hashes, "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "pages": pages,
                "editable_master": "docs/hte-staff-checklist.md; rebuild with scripts/build-hte-pdf.py --staff",
                "private_email_included": False, "api_calls": 0, "staff_only": True}
    output.with_suffix(".build.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--staff", action="store_true", help="Build the two-page operator checklist, without background explanations")
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(ZoneInfo("Europe/Zurich")).date(), help="Edition date, YYYY-MM-DD; default Europe/Zurich today")
    parser.add_argument("--check", action="store_true", help="Verify an existing PDF and its manifest against current sources; do not rebuild")
    args = parser.parse_args()
    args.output = args.output or ROOT/("output/pdf/HTE-staff-checklist.pdf" if args.staff else "output/pdf/HTE-operator-handbook.pdf")
    if args.check:
        manifest = json.loads(args.output.with_suffix(".build.json").read_text())
        if manifest["source_sha256"] != input_record(args.staff)[1] or manifest["pdf_sha256"] != hashlib.sha256(args.output.read_bytes()).hexdigest():
            raise SystemExit("The PDF or its sources changed. Rebuild before distributing it.")
        print("PDF and source manifest match; "+str(manifest["pages"])+" pages")
    else:
        manifest = build_staff(args.output, args.date) if args.staff else build(args.output, args.date)
        print(json.dumps({"output": str(args.output), "pages": manifest["pages"], "source_sha256": manifest["source_sha256"]}))


if __name__ == "__main__":
    main()
