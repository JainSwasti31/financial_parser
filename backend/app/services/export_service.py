import csv
import json
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.report_service import serialize_report


BRAND = colors.HexColor("#4F46E5")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
PANEL = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")


def _label(value: str) -> str:
    return str(value).replace("_", " ").strip().title()


def _display(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str, indent=2)
    return str(value)


def _file_size(value) -> str:
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def report_rows(report) -> list[tuple[str, str, str]]:
    data = serialize_report(report)
    original = data["original_file"]
    reviewer = data["reviewed_by"] or {}
    rows = [
        ("Report Summary", "Report ID", _display(data["id"])),
        ("Report Summary", "Document ID", _display(data["document_id"])),
        ("Report Summary", "Document Type", _display(data["document_type"])),
        ("Report Summary", "Document Status", _display(data["document_status"])),
        ("Report Summary", "Validation Status", _display(data["validation_status"])),
        ("Report Summary", "Created At", _display(data["created_at"])),
        ("Report Summary", "Updated At", _display(data["updated_at"])),
        ("Original File Information", "File Name", _display(original.get("name"))),
        ("Original File Information", "File Type", _display(original.get("type"))),
        ("Original File Information", "File Size", _file_size(original.get("size"))),
        ("Original File Information", "Uploaded At", _display(original.get("uploaded_at"))),
        ("Original File Information", "File Hash", _display(original.get("file_hash"))),
    ]
    rows.extend(("Extracted Fields", _label(key), _display(value)) for key, value in data["extracted_fields"].items())
    rows.extend(("AI Confidence", _label(key), f"{value}%") for key, value in data.get("field_confidences", {}).items())
    rich_content = data.get("rich_content", {})
    for key, value in rich_content.items():
        count = len(value) if isinstance(value, list) else None
        field = f"{_label(key)} ({count} found)" if count is not None else _label(key)
        rows.append(("Rich Extraction", field, _display(value)))
    rows.extend(
        ("Validation Results", _label(key), f"{_label(value.get('status', ''))} — {value.get('message', '')}".strip(" —"))
        for key, value in data["validation_results"].items()
    )
    rows.extend([
        ("Processing", "Processing Time", f"{data['processing_time']:.2f} seconds" if data["processing_time"] is not None else "—"),
        ("Review", "Review Status", _display(data["review_status"])),
        ("Review", "Reviewed By", _display(reviewer.get("name"))),
        ("Review", "Reviewer Email", _display(reviewer.get("email"))),
        ("Review", "Remarks", _display(data["remarks"])),
    ])
    return rows


def generate_csv(report) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Section", "Field", "Value"])
    writer.writerows(report_rows(report))
    return output.getvalue().encode("utf-8-sig")


def _pdf_page(canvas, document):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(BORDER)
    canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "Financial Document Parser")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _pdf_value_chunks(value: str, max_chars: int = 1200, max_lines: int = 30) -> list[str]:
    """Keep any single PDF table row small enough to fit on a page."""
    text = str(value)
    source_lines = text.splitlines() or [text]
    chunks, current, current_chars = [], [], 0
    for source_line in source_lines:
        # Long unbroken values such as hashes or compact JSON still need
        # bounded chunks so ReportLab can paginate them.
        pieces = [source_line[index:index + max_chars] for index in range(0, len(source_line), max_chars)] or [""]
        for piece in pieces:
            if current and (len(current) >= max_lines or current_chars + len(piece) > max_chars):
                chunks.append("\n".join(current))
                current, current_chars = [], 0
            current.append(piece)
            current_chars += len(piece)
    if current:
        chunks.append("\n".join(current))
    return chunks or ["—"]


def generate_pdf(report) -> bytes:
    data = serialize_report(report)
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title=f"Financial Document Report {report.id}",
        author="Financial Document Parser",
    )
    sample = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=INK, alignment=TA_LEFT, spaceAfter=5)
    subtitle = ParagraphStyle("ReportSubtitle", parent=sample["Normal"], fontSize=10, leading=14, textColor=MUTED, spaceAfter=14)
    section_style = ParagraphStyle("Section", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=BRAND, spaceBefore=9, spaceAfter=6)
    field_style = ParagraphStyle("Field", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=INK)
    value_style = ParagraphStyle("Value", parent=sample["Normal"], fontSize=8.5, leading=11, textColor=INK, alignment=TA_LEFT)
    badge_style = ParagraphStyle("Badge", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_CENTER)

    story = [
        Paragraph("Financial Document Report", title),
        Paragraph(escape(data["original_file"].get("name") or "Unnamed document"), subtitle),
        Table(
            [[Paragraph(escape(data.get("document_type") or "Unknown"), badge_style), Paragraph(escape(data.get("review_status") or "Pending"), badge_style)]],
            colWidths=[48 * mm, 38 * mm],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND), ("BOX", (0, 0), (-1, -1), 0.5, BRAND), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]),
        ),
        Spacer(1, 8),
    ]

    grouped = {}
    for section, field, value in report_rows(report):
        grouped.setdefault(section, []).append((field, value))
    for section, rows in grouped.items():
        story.append(Paragraph(escape(section), section_style))
        table_data = []
        for field, value in rows:
            chunks = _pdf_value_chunks(value)
            for chunk_index, chunk in enumerate(chunks):
                display_field = field if chunk_index == 0 else f"{field} (continued)"
                table_data.append([
                    Paragraph(escape(str(display_field)), field_style),
                    Paragraph(escape(chunk).replace("\n", "<br/>"), value_style),
                ])
        table = Table(table_data, colWidths=[48 * mm, 120 * mm], repeatRows=0, hAlign="LEFT", splitByRow=1)
        commands = [
            ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        for row_index in range(len(table_data)):
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PANEL if row_index % 2 == 0 else colors.white))
        table.setStyle(TableStyle(commands))
        story.extend([table, Spacer(1, 5)])

    document.build(story, onFirstPage=_pdf_page, onLaterPages=_pdf_page)
    return output.getvalue()


def _excel_styles() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FF172033"/><sz val="16"/><name val="Calibri"/></font><font><b/><color rgb="FF4F46E5"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF4F46E5"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF1F5F9"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'


def generate_excel(report) -> bytes:
    rows = [("Financial Document Report", "", ""), ("Section", "Field", "Value"), *report_rows(report)]
    sheet_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for column_index, value in enumerate(row, 1):
            column = chr(64 + column_index)
            style = 1 if row_index == 1 else 2 if row_index == 2 else 3 if column_index == 1 else 4
            cells.append(f'<c r="{column}{row_index}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{escape(_display(value))}</t></is></c>')
        height = ' ht="26" customHeight="1"' if row_index == 1 else ""
        sheet_rows.append(f'<row r="{row_index}"{height}>{"".join(cells)}</row>')
    last_row = len(rows)
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="24" customWidth="1"/><col min="2" max="2" width="30" customWidth="1"/><col min="3" max="3" width="80" customWidth="1"/></cols><sheetData>' + "".join(sheet_rows) + f'</sheetData><autoFilter ref="A2:C{last_row}"/><mergeCells count="1"><mergeCell ref="A1:C1"/></mergeCells></worksheet>')
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Financial Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        archive.writestr("xl/styles.xml", _excel_styles())
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()
