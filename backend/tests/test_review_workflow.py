import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.review import approve_document, update_fields
from app.core.database import Base
from app.models.audit_log import AuditLog
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.user = User(name="Analyst", email="analyst@example.com", password_hash="x", role=Role.Analyst)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.document = Document(
            document_name="invalid-bank.pdf",
            document_type="PDF",
            file_path="invalid-bank.pdf",
            uploaded_by=self.user.id,
            status=ProcessingStatus.Validation_Failed,
            file_size=100,
            file_hash="unique-test-hash",
        )
        self.db.add(self.document)
        self.db.commit()
        self.db.refresh(self.document)

        fields = {
            "bank_name": "Example Bank",
            "account_holder": "Test User",
            "account_number": "1234567890",
            "ifsc_code": "INVALID",
            "statement_period": "June 2026",
            "opening_balance": "1000",
            "closing_balance": "1200",
            "total_credits": "300",
            "total_debits": "100",
        }
        self.report = ParsedReport(
            document_id=self.document.id,
            parsed_data={"document_type": "Bank Statement", "parsed_fields": fields},
            validation_status="Failed",
            review_status="Pending",
        )
        self.db.add(self.report)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_edit_invalid_field_then_approve_and_audit(self):
        result = update_fields(
            self.document.id,
            {"ifsc_code": "HDFC0123456"},
            self.user,
            self.db,
        )
        self.assertEqual(result["field_validations"]["ifsc_code"]["status"], "valid")
        self.assertEqual(result["validation_status"], "Passed")
        self.assertEqual(self.document.status, ProcessingStatus.Review_Pending)

        approve_document(self.document.id, "Checked against original", self.user, self.db)
        self.db.refresh(self.report)
        self.db.refresh(self.document)

        self.assertEqual(self.report.review_status, "Approved")
        self.assertEqual(self.report.reviewed_by, self.user.id)
        self.assertEqual(self.document.status, ProcessingStatus.Approved)
        self.assertEqual(self.db.query(AuditLog).count(), 2)


if __name__ == "__main__":
    unittest.main()
