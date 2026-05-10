from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path("/Users/omer/aws-analytics-pipeline")
DEFAULT_INPUT = ROOT / "docs/nyc-heat-risk-class-board-plan.md"
DEFAULT_OUTPUT = Path("/Users/omer/Downloads/NYC_Heating_Risk_Tahta_Prova_Paketi_Omer_Canbolat.pdf")


def register_fonts() -> tuple[str, str, str]:
    font_dir = Path("/System/Library/Fonts/Supplemental")
    regular = font_dir / "Arial Unicode.ttf"
    bold = font_dir / "Arial Bold.ttf"
    title = font_dir / "Georgia Bold.ttf"
    pdfmetrics.registerFont(TTFont("DocRegular", str(regular)))
    pdfmetrics.registerFont(TTFont("DocBold", str(bold)))
    pdfmetrics.registerFont(TTFont("DocTitle", str(title)))
    return "DocRegular", "DocBold", "DocTitle"


REGULAR, BOLD, TITLE = register_fonts()


def clean_inline(text: str) -> str:
    text = html.escape(text.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='DocBold' color='#14493A'>\1</font>", text)
    return text


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=TITLE,
            fontSize=23,
            leading=27,
            textColor=colors.HexColor("#14493A"),
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=TITLE,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#14493A"),
            spaceBefore=11,
            spaceAfter=7,
            borderWidth=0,
            borderColor=colors.HexColor("#DACDBB"),
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName=BOLD,
            fontSize=11.4,
            leading=14,
            textColor=colors.HexColor("#D86F54"),
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=REGULAR,
            fontSize=9.1,
            leading=12.1,
            textColor=colors.HexColor("#172126"),
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "Meta",
            fontName=BOLD,
            fontSize=8.4,
            leading=11,
            textColor=colors.HexColor("#465158"),
            backColor=colors.HexColor("#E6F1EC"),
            borderColor=colors.HexColor("#CADECF"),
            borderWidth=0.5,
            borderPadding=5,
            spaceAfter=4,
        ),
        "quote": ParagraphStyle(
            "Quote",
            fontName=BOLD,
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#26342F"),
            backColor=colors.HexColor("#F6EAD7"),
            borderColor=colors.HexColor("#C99A44"),
            borderWidth=0.8,
            borderPadding=8,
            spaceBefore=5,
            spaceAfter=7,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=8,
            leading=9.6,
            textColor=colors.white,
            backColor=colors.HexColor("#11231A"),
            borderPadding=8,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=REGULAR,
            fontSize=8.9,
            leading=11.8,
            leftIndent=8,
            firstLineIndent=0,
            textColor=colors.HexColor("#172126"),
        ),
        "table": ParagraphStyle(
            "Table",
            fontName=REGULAR,
            fontSize=7.6,
            leading=9.2,
            textColor=colors.HexColor("#172126"),
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            fontName=BOLD,
            fontSize=7.7,
            leading=9.4,
            textColor=colors.white,
        ),
    }


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(REGULAR, 7.5)
    canvas.setFillColor(colors.HexColor("#6F777B"))
    canvas.drawString(14 * mm, 9 * mm, "NYC Heating Risk | Tahta + Brosur + Sunum Kontrol Paketi")
    canvas.drawRightString(196 * mm, 9 * mm, f"Sayfa {doc.page}")
    canvas.restoreState()


def paragraph(text: str, style):
    return Paragraph(clean_inline(text), style)


def table_from_lines(lines: list[str], styles):
    rows: list[list[Paragraph]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        row_style = styles["table_head"] if not rows else styles["table"]
        rows.append([Paragraph(clean_inline(cell), row_style) for cell in cells])
    if not rows:
        return []
    width = A4[0] - 28 * mm
    col_count = max(len(row) for row in rows)
    col_widths = [width / col_count] * col_count
    tbl = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14493A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFAF2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DACDBB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [tbl, Spacer(1, 5)]


def build_story(markdown: str, styles):
    story = []
    lines = markdown.splitlines()
    i = 0
    bullet_buffer: list[str] = []

    def flush_bullets():
        nonlocal bullet_buffer
        if not bullet_buffer:
            return
        items = [ListItem(paragraph(item, styles["bullet"]), leftIndent=8) for item in bullet_buffer]
        story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=13, bulletFontName=BOLD))
        story.append(Spacer(1, 3))
        bullet_buffer = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            i += 1
            continue

        if stripped.startswith("```"):
            flush_bullets()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            story.append(Preformatted("\n".join(code_lines), styles["code"], maxLineLength=100))
            continue

        if stripped.startswith("|"):
            flush_bullets()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            story.extend(table_from_lines(table_lines, styles))
            continue

        if stripped.startswith("- ["):
            bullet_buffer.append(stripped.replace("- [ ]", "☐").replace("- [x]", "☑"))
            i += 1
            continue

        if stripped.startswith("- "):
            bullet_buffer.append(stripped[2:])
            i += 1
            continue

        if stripped.startswith(">"):
            flush_bullets()
            story.append(paragraph(stripped.lstrip("> "), styles["quote"]))
            i += 1
            continue

        if stripped.startswith("# "):
            flush_bullets()
            story.append(paragraph(stripped[2:], styles["title"]))
            i += 1
            continue

        if stripped.startswith("## "):
            flush_bullets()
            if story and len([flow for flow in story if isinstance(flow, Paragraph)]) > 12:
                # Keep major sections from turning into dense walls on a single page.
                story.append(Spacer(1, 3))
            story.append(paragraph(stripped[3:], styles["h2"]))
            i += 1
            continue

        if stripped.startswith("### "):
            flush_bullets()
            story.append(paragraph(stripped[4:], styles["h3"]))
            i += 1
            continue

        if stripped == "---":
            flush_bullets()
            story.append(Spacer(1, 5))
            i += 1
            continue

        flush_bullets()
        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith(("#", "-", ">", "|", "```")) or nxt == "---":
                break
            paragraph_lines.append(nxt)
            i += 1
        text = " ".join(paragraph_lines)
        style = styles["meta"] if text.startswith("**") and ":" in text[:40] else styles["body"]
        story.append(paragraph(text, style))

    flush_bullets()
    return story


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    styles = make_styles()
    markdown = input_path.read_text(encoding="utf-8")
    story = build_story(markdown, styles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="NYC Heating Risk - Tahta ve Sunum Kontrol Paketi",
        author="Omer Canbolat",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(output_path)


if __name__ == "__main__":
    main()
