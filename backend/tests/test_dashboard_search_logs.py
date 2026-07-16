import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.logs import list_logs
from app.core.database import Base
from app.models.audit_log import AuditLog
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User
from app.services.dashboard_service import get_dashboard_data
from app.services.document_service import get_documents_paginated


class DashboardSearchLogTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.admin = User(name="Admin", email="dashboard-admin@example.com", password_hash="x", role=Role.Admin)
        self.db.add(self.admin)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_document(self, name, status, parsed_type, fields, days_ago=0, processing_time=1.0):
        document = Document(document_name=name, document_type="PDF", file_path=name, uploaded_by=self.admin.id, status=status, processing_time=processing_time, file_size=100, file_hash=f"hash-{name}", created_at=datetime.now() - timedelta(days=days_ago))
        self.db.add(document)
        self.db.commit()
        report = ParsedReport(document_id=document.id, parsed_data={"document_type": parsed_type, "parsed_fields": fields}, validation_status="Passed", review_status="Approved" if status == ProcessingStatus.Approved else "Pending")
        self.db.add(report)
        self.db.add(AuditLog(document_id=document.id, action="Parsing Completed", status="Success"))
        self.db.commit()
        return document

    def test_dashboard_recalculates_after_new_documents(self):
        self.add_document("invoice.pdf", ProcessingStatus.Approved, "Invoice", {"invoice_number": "INV-42"}, processing_time=2.0)
        first = get_dashboard_data(self.db, self.admin, days=7, months=3)
        self.assertEqual(first["total_uploaded_documents"], 1)
        self.assertEqual(first["successfully_parsed"], 1)
        self.assertEqual(first["processing_success_rate"], 100.0)

        self.add_document("gst.pdf", ProcessingStatus.Validation_Failed, "GST Return", {"gstin": "27ABCDE1234F1Z5"}, days_ago=1, processing_time=4.0)
        second = get_dashboard_data(self.db, self.admin, days=7, months=3)
        self.assertEqual(second["total_uploaded_documents"], 2)
        self.assertEqual(second["failed_parsing"], 1)
        self.assertEqual(second["processing_success_rate"], 50.0)
        self.assertEqual(second["average_processing_time"], 3.0)
        self.assertEqual(sum(item["count"] for item in second["daily_uploads"]), 2)
        self.assertEqual({item["type"] for item in second["documents_by_type"]}, {"Invoice", "GST Return"})

    def test_search_filters_json_fields_and_logs(self):
        invoice = self.add_document("invoice.pdf", ProcessingStatus.Approved, "Invoice", {"invoice_number": "INV-SEARCH-9", "company_name": "Acme Corp"}, processing_time=2.5)
        self.add_document("bank.pdf", ProcessingStatus.Review_Pending, "Bank Statement", {"account_number": "999988887777"}, processing_time=8.0)

        total, items = get_documents_paginated(self.db, self.admin, search="acme", document_type="Invoice", status=ProcessingStatus.Approved, page=1, page_size=10)
        self.assertEqual(total, 1)
        self.assertEqual(items[0].id, invoice.id)

        total, items = get_documents_paginated(self.db, self.admin, document_type="PDF", page=1, page_size=10)
        self.assertEqual(total, 2)

        self.add_document("profit_and_loss.pdf", ProcessingStatus.Uploaded, "Profit & Loss", {}, processing_time=None)
        report = self.db.query(ParsedReport).order_by(ParsedReport.id.desc()).first()
        self.db.delete(report)
        self.db.commit()
        total, items = get_documents_paginated(self.db, self.admin, document_type="Profit & Loss", page=1, page_size=10)
        self.assertEqual(total, 1)
        self.assertEqual(items[0].document_name, "profit_and_loss.pdf")

        total, items = get_documents_paginated(self.db, self.admin, search="999988887777", processing_time_min=5, page=1, page_size=10)
        self.assertEqual(total, 1)
        self.assertEqual(items[0].document_name, "bank.pdf")

        logs = list_logs(1, 20, invoice.id, "Parsing", self.admin, self.db)
        self.assertEqual(logs["total"], 1)
        self.assertEqual(logs["items"][0]["document_id"], invoice.id)


if __name__ == "__main__":
    unittest.main()
