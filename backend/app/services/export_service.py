import csv
import json
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.report_service import serialize_report


def _display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def report_rows(report) -> list[tuple[str, str, str]]:
    data = serialize_report(report)
    original = data["original_file"]
    reviewer = data["reviewed_by"] or {}
    rows = [
        ("Original File Information", "File Name", _display(original.get("name"))),
        ("Original File Information", "File Type", _display(original.get("type"))),
        ("Original File Information", "File Size (bytes)", _display(original.get("size"))),
        ("Original File Information", "Uploaded At", _display(original.get("uploaded_at"))),
        ("Original File Information", "File Hash", _display(original.get("file_hash"))),
    ]
    rows.extend(("Extracted Fields", key, _display(value)) for key, value in data["extracted_fields"].items())
    rows.extend(("AI Confidence", key, f"{value}%") for key, value in data.get("field_confidences", {}).items())
    rows.extend(("Rich Extraction", key, _display(value)) for key, value in data.get("rich_content", {}).items())
    rows.extend(
        ("Validation Results", key, f"{value.get('status', '')}: {value.get('message', '')}")
        for key, value in data["validation_results"].items()
    )
    rows.extend([
        ("Processing", "Processing Time (seconds)", _display(data["processing_time"])),
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


def generate_pdf(report) -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 48
    pdf.setTitle(f"Report {report.id}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Financial Document Report")
    y -= 28
    current_section = None
    for section, field, value in report_rows(report):
        if y < 60:
            pdf.showPage()
            y = height - 48
        if section != current_section:
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(40, y, section)
            y -= 18
            current_section = section
        text = f"{field}: {value}"
        pdf.setFont("Helvetica", 8)
        while text:
            line, text = text[:110], text[110:]
            pdf.drawString(52, y, line)
            y -= 12
            if y < 60:
                pdf.showPage()
                y = height - 48
    pdf.save()
    return output.getvalue()


def generate_excel(report) -> bytes:
    rows = [("Section", "Field", "Value"), *report_rows(report)]
    sheet_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for column_index, value in enumerate(row, 1):
            column = chr(64 + column_index)
            cells.append(
                f'<c r="{column}{row_index}" t="inlineStr"><is><t>{escape(_display(value))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>'
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()
