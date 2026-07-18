import unittest
from zipfile import ZipFile
from io import BytesIO

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.reports import _export
from app.core.database import Base
from app.models.audit_log import AuditLog
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User
from app.services.export_service import generate_csv, generate_excel, generate_pdf
from app.services.report_service import get_approved_report


class ReportExportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.user = User(name="Reviewer", email="reviewer@example.com", password_hash="x", role=Role.Analyst)
        self.db.add(self.user)
        self.db.commit()
        self.document = Document(document_name="statement.pdf", document_type="PDF", file_path="statement.pdf", uploaded_by=self.user.id, status=ProcessingStatus.Review_Pending, processing_time=1.25, file_size=200, file_hash="report-export-hash")
        self.db.add(self.document)
        self.db.commit()
        self.report = ParsedReport(
            document_id=self.document.id,
            parsed_data={"document_type": "Bank Statement", "parsed_fields": {"account_number": "1234567890", "ifsc_code": "HDFC0123456"}},
            field_validations={"ifsc_code": {"status": "valid", "message": "Valid IFSC"}},
            validation_status="Passed",
            review_status="Pending",
        )
        self.db.add(self.report)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_export_fails_before_approval_then_generates_all_formats(self):
        with self.assertRaises(HTTPException) as error:
            get_approved_report(self.db, self.report.id, self.user)
        self.assertEqual(error.exception.status_code, 409)

        self.report.review_status = "Approved"
        self.report.reviewed_by = self.user.id
        self.report.remarks = "Verified"
        self.document.status = ProcessingStatus.Approved
        self.db.commit()
        approved = get_approved_report(self.db, self.report.id, self.user)

        pdf = generate_pdf(approved)
        excel = generate_excel(approved)
        csv_data = generate_csv(approved)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(excel.startswith(b"PK"))
        self.assertIn(b"Extracted Fields", csv_data)
        with ZipFile(BytesIO(excel)) as archive:
            self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())

        for name, generator, media_type, extension in (
            ("pdf", generate_pdf, "application/pdf", "pdf"),
            ("excel", generate_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
            ("csv", generate_csv, "text/csv", "csv"),
        ):
            response = _export(self.report.id, name, generator, media_type, extension, self.user, self.db)
            self.assertEqual(response.status_code, 200)
        logs = self.db.query(AuditLog).filter(AuditLog.action == "Report Generated").all()
        self.assertEqual(len(logs), 3)

    def test_pdf_paginates_oversized_extracted_values(self):
        self.report.parsed_data = {
            "document_type": "Bank Statement",
            "parsed_fields": {
                "transactions": [
                    {"date": "2026-01-01", "description": "Long transaction description " * 5, "amount": index}
                    for index in range(150)
                ]
            },
            "rich_content": {"tables": [], "signatures": [], "qr_codes": []},
        }
        self.db.commit()

        pdf = generate_pdf(self.report)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
