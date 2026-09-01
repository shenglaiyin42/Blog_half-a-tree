#!/usr/bin/env python3
"""Build a polished A4 PDF from one blog article Markdown source."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    HRFlowable,
    ListFlowable,
    ListItem,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from publish_post import read_post


ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
FONT_NAME = "HalfATreeUnicode"
INK = colors.HexColor("#2f312e")
MUTED = colors.HexColor("#6e716b")
MOSS = colors.HexColor("#414640")
CLAY = colors.HexColor("#867968")
LINE = colors.HexColor("#ddddd6")
PAPER_DEEP = colors.HexColor("#f4f2ed")


def normalize_pdf_text(text: str) -> str:
    return text.replace("‑", "-").replace("–", "-").replace("—", "-")


INLINE_PATTERN = re.compile(
    r"(`[^`]+`|\*\*.+?\*\*|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)"
)


def paragraph_markup(markdown: str) -> str:
    markdown = normalize_pdf_text(markdown)
    rendered: list[str] = []
    cursor = 0
    for match in INLINE_PATTERN.finditer(markdown):
        rendered.append(html.escape(markdown[cursor : match.start()]))
        token = match.group(0)
        link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
        if token.startswith("**"):
            rendered.append(f"<b>{html.escape(token[2:-2])}</b>")
        elif token.startswith("`"):
            rendered.append(f'<font name="Courier">{html.escape(token[1:-1])}</font>')
        elif link_match:
            label, target = link_match.groups()
            rendered.append(
                f'<link href="{html.escape(target, quote=True)}" color="#414640">'
                f"{html.escape(label)}</link>"
            )
        else:
            rendered.append(f"<i>{html.escape(token[1:-1])}</i>")
        cursor = match.end()
    rendered.append(html.escape(markdown[cursor:]))
    return "".join(rendered)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=28,
            leading=38,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=13,
            leading=21,
            textColor=MOSS,
            spaceAfter=7,
        ),
        "cover_english": ParagraphStyle(
            "CoverEnglish",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            textColor=MUTED,
            spaceAfter=18,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=16,
            textColor=INK,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "english": ParagraphStyle(
            "GuideEnglish",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=14,
            textColor=MUTED,
            spaceAfter=11,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=17,
            leading=23,
            textColor=INK,
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            parent=base["Heading3"],
            fontName=FONT_NAME,
            fontSize=12.5,
            leading=18,
            textColor=MOSS,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "GuideH4",
            parent=base["Heading4"],
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=16,
            textColor=MOSS,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "note": ParagraphStyle(
            "GuideNote",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=15,
            textColor=INK,
        ),
        "small": ParagraphStyle(
            "GuideSmall",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=7.5,
            leading=11,
            textColor=INK,
            wordWrap="CJK",
        ),
        "toc_title": ParagraphStyle(
            "TOCTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=28,
            textColor=INK,
            spaceAfter=16,
        ),
        "toc_entry": ParagraphStyle(
            "TOCEntry",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=17,
            textColor=MOSS,
            leftIndent=8,
            firstLineIndent=-8,
        ),
    }


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, output: Path, article_title: str, **kwargs):
        super().__init__(str(output), pagesize=A4, **kwargs)
        self.article_title = normalize_pdf_text(article_title)
        self.heading_counter = 0
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="guide", frames=frame, onPage=self.draw_page))

    def beforeDocument(self) -> None:
        self.heading_counter = 0

    def draw_page(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(FONT_NAME, 7.5)
        canvas.setFillColor(MUTED)
        if doc.page > 1:
            canvas.drawString(self.leftMargin, A4[1] - 15 * mm, self.article_title[:48])
            canvas.setStrokeColor(LINE)
            canvas.line(self.leftMargin, A4[1] - 17 * mm, A4[0] - self.rightMargin, A4[1] - 17 * mm)
        canvas.drawString(self.leftMargin, 12 * mm, "半棵斋 | Half a Tree")
        canvas.drawRightString(A4[0] - self.rightMargin, 12 * mm, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name == "GuideH2":
            self.heading_counter += 1
            key = f"section-{self.heading_counter}"
            text = flowable.getPlainText()
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


def note_table(text: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(paragraph_markup(text), styles["note"])]], colWidths=[167 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f2ec")),
                ("BOX", (0, 0), (-1, -1), 0.7, CLAY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def markdown_table(
    header: list[str], rows: list[list[str]], styles: dict[str, ParagraphStyle]
) -> LongTable:
    column_count = len(header)
    available_width = 167 * mm
    if column_count == 2:
        widths = [available_width * 0.27, available_width * 0.73]
    elif column_count == 3:
        widths = [available_width * 0.22, available_width * 0.39, available_width * 0.39]
    else:
        widths = [available_width / column_count] * column_count
    cell_style = styles["small"] if column_count > 3 else styles["body"]
    data = [[Paragraph(paragraph_markup(cell), cell_style) for cell in header]]
    for row in rows:
        padded = row + [""] * (column_count - len(row))
        data.append([Paragraph(paragraph_markup(cell), cell_style) for cell in padded[:column_count]])
    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), PAPER_DEEP),
        ("TEXTCOLOR", (0, 0), (-1, 0), MOSS),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 if column_count > 3 else 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 if column_count > 3 else 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#faf9f6")))
    table.setStyle(TableStyle(commands))
    return table


def build_pdf(post_path: Path, output_path: Path) -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Required font not found: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    pdfmetrics.registerFontFamily(
        FONT_NAME, normal=FONT_NAME, bold=FONT_NAME, italic=FONT_NAME, boldItalic=FONT_NAME
    )
    metadata, markdown = read_post(post_path)
    styles = build_styles()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = GuideDocTemplate(
        output_path,
        str(metadata["title"]),
        leftMargin=22 * mm,
        rightMargin=21 * mm,
        topMargin=23 * mm,
        bottomMargin=21 * mm,
        title=str(metadata["title"]),
        author="半棵斋 | Half a Tree",
        subject=str(metadata["summary"]),
    )
    story = [
        Spacer(1, 17 * mm),
        Paragraph(paragraph_markup(str(metadata["title"])), styles["cover_title"]),
        Paragraph(f"健身  ·  {metadata['date']}", styles["cover_english"]),
        HRFlowable(width="100%", thickness=0.8, color=LINE, spaceBefore=7, spaceAfter=18),
    ]
    toc = TableOfContents()
    toc.levelStyles = [styles["toc_entry"]]
    lines = markdown.splitlines()
    index = 0
    before_toc = True
    while index < len(lines):
        block = lines[index].strip()
        if not block:
            index += 1
            continue
        if block == "[[TOC]]":
            story.extend(
                [
                    Spacer(1, 8 * mm),
                    Paragraph("半棵斋 | Half a Tree", styles["cover_english"]),
                    PageBreak(),
                    Paragraph("目录 / Contents", styles["toc_title"]),
                    toc,
                    PageBreak(),
                ]
            )
            before_toc = False
            index += 1
            continue
        if block.startswith("# "):
            index += 1
            continue
        if block.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1].strip()):
            header = split_table_row(block)
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_row(lines[index].strip()))
                index += 1
            story.extend([Spacer(1, 4), markdown_table(header, rows, styles), Spacer(1, 10)])
            continue
        heading_match = re.fullmatch(r"(#{2,4})\s+(.+)", block)
        if heading_match:
            level = len(heading_match.group(1))
            style = styles[f"h{level}"]
            story.extend([CondPageBreak(30 * mm), Paragraph(paragraph_markup(heading_match.group(2)), style)])
        elif block == "---":
            story.append(HRFlowable(width=30 * mm, thickness=0.6, color=LINE, spaceBefore=10, spaceAfter=12))
        elif block.startswith("> EN｜"):
            text = block[5:].strip()
            style = styles["cover_english"] if before_toc else styles["english"]
            story.append(Paragraph(paragraph_markup(text), style))
        elif block.startswith("> 说明｜"):
            story.extend([Spacer(1, 5), note_table(block[5:].strip(), styles), Spacer(1, 8)])
        elif block.startswith("> 下载｜"):
            pass
        elif block.startswith("> "):
            story.append(Paragraph(paragraph_markup(block[2:].strip()), styles["note"]))
        elif re.match(r"^[-*]\s+", block):
            items: list[str] = []
            while index < len(lines) and re.match(r"^[-*]\s+", lines[index].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[index].strip()))
                index += 1
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(paragraph_markup(item), styles["body"])) for item in items],
                    bulletType="bullet",
                    leftIndent=15,
                )
            )
            continue
        elif before_toc and block.startswith("**"):
            story.append(Paragraph(paragraph_markup(block), styles["cover_subtitle"]))
        else:
            story.append(Paragraph(paragraph_markup(block), styles["body"]))
        index += 1
    doc.multiBuild(story)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("post", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_pdf(args.post, args.output)


if __name__ == "__main__":
    main()
