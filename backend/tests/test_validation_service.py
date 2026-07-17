import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.parsers.itr_parser import ITRParser
from app.parsers.invoice_parser import InvoiceParser
from app.services.validation_service import validate_document
from app.services.parser_service import process_document
from app.api.parser import get_result
from app.core.database import Base
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User
from app.models.audit_log import AuditLog


class ValidationServiceTests(unittest.TestCase):
    @patch("app.parsers.invoice_parser.gemini_extract", return_value='{"invoice_number":"INV-1","gstin":"29ABCDE123"}')
    def test_invoice_parser_normalizes_aliases_and_extracts_identifiers_from_text(self, _mock_extract):
        fields = InvoiceParser().parse("""TAX INVOICE
GST Number: 29ABCDE123
PAN: BXPP54321
IFSC Code: nova12
Account Number: 5010""")

        self.assertEqual(fields["gst_number"], "29ABCDE123")
        self.assertEqual(fields["pan"], "BXPP54321")
        self.assertEqual(fields["ifsc_code"], "nova12")
        self.assertEqual(fields["account_number"], "5010")

    @patch("app.parsers.itr_parser.gemini_extract", side_effect=RuntimeError("quota exceeded"))
    def test_itr_falls_back_when_gemini_quota_is_exhausted(self, _mock_extract):
        text = """INCOME TAX RETURN - ITR-1
Assessment Year: 2024-25
PAN: ABCDE1234F
Gross Total Income: INR 12,50,000.00
Total Deductions (80C, 80D): INR 1,50,000.00
Taxable Income: INR 11,00,000.00
Tax Paid (TDS): INR 1,80,000.00
Refund: INR 7,500.00"""
        fields = ITRParser().parse(text)
        validations, status = validate_document("ITR", fields)

        self.assertEqual(fields["gross_income"], "INR 12,50,000.00")
        self.assertEqual(fields["tax_paid"], "INR 1,80,000.00")
        self.assertEqual(validations["assessment_year"]["status"], "valid")
        self.assertEqual(status, "Passed")

    def test_invalid_pan_is_flagged(self):
        fields = {
            "pan": "BAD-PAN",
            "assessment_year": "2025-26",
            "gross_income": "100000",
            "tax_paid": "10000",
            "taxable_income": "90000",
        }

        validations, status = validate_document("ITR", fields)

        self.assertEqual(validations["pan"]["status"], "invalid")
        self.assertEqual(status, "Failed")

    def test_invalid_gstin_is_flagged(self):
        fields = {
            "gstin": "12INVALIDGSTIN",
            "business_name": "Example Ltd",
            "filing_period": "June 2026",
            "taxable_value": "1000",
            "total_tax": "180",
        }

        validations, status = validate_document("GST Return", fields)

        self.assertEqual(validations["gstin"]["status"], "invalid")
        self.assertEqual(status, "Failed")

    def test_invoice_flags_present_invalid_tax_and_bank_identifiers(self):
        fields = {
            "invoice_number": "INV-INVALID-1", "invoice_date": "17-07-2026",
            "vendor_name": "Vendor", "customer_name": "Customer",
            "gst_number": "29ABCDE123", "pan": "BXPP54321",
            "ifsc_code": "nova12", "account_number": "5010",
            "invoice_amount": "1180",
        }
        validations, status = validate_document("Invoice", fields)
        for field in ("gst_number", "pan", "ifsc_code", "account_number"):
            with self.subTest(field=field):
                self.assertEqual(validations[field]["status"], "invalid")
        self.assertEqual(status, "Review Required")

    @patch("app.services.parser_service.extract_rich_content", return_value={})
    @patch("app.services.parser_service._get_parser")
    @patch("app.services.parser_service.get_ai_classifier")
    @patch("app.services.parser_service.get_ocr_provider")
    def test_invoice_pipeline_persists_and_api_returns_field_validations(
        self, get_ocr_provider, get_ai_classifier, get_parser, _extract_rich_content
    ):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        try:
            user = User(name="Analyst", email="pipeline@example.com", password_hash="x", role=Role.Analyst)
            db.add(user)
            db.commit()
            db.refresh(user)
            document = Document(
                document_name="invalid-invoice.pdf", document_type="PDF",
                file_path="invalid-invoice.pdf", uploaded_by=user.id,
                status=ProcessingStatus.Uploaded, file_size=100,
                file_hash="pipeline-invalid-invoice",
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            get_ocr_provider.return_value.extract_text.return_value = ("invoice text with invalid identifiers", 0.01)
            get_ai_classifier.return_value.classify.return_value = "Invoice"
            parser = MagicMock()
            parser.parse.return_value = {
                "invoice_number": "INV-1", "invoice_date": "17-07-2026",
                "vendor_name": "Vendor", "customer_name": "Customer",
                "gst_number": "29ABCDE123", "pan": "BXPP54321",
                "ifsc_code": "nova12", "account_number": "5010",
                "invoice_amount": "100",
            }
            get_parser.return_value = parser

            process_document(document.id, db)
            report = db.query(ParsedReport).filter_by(document_id=document.id).one()
            self.assertEqual(report.validation_status, "Review Required")
            self.assertEqual(report.field_validations["pan"]["status"], "invalid")

            response = get_result(document.id, user, db)
            self.assertEqual(response["report"]["validation_status"], "Review Required")
            self.assertEqual(response["report"]["field_validations"]["gst_number"]["status"], "invalid")
        finally:
            db.close()

    def test_invalid_ifsc_then_corrected_fields_pass(self):
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

        validations, status = validate_document("Bank Statement", fields)
        self.assertEqual(validations["ifsc_code"]["status"], "invalid")
        self.assertEqual(status, "Failed")

        fields["ifsc_code"] = "HDFC0123456"
        validations, status = validate_document("Bank Statement", fields)
        self.assertEqual(validations["ifsc_code"]["status"], "valid")
        self.assertEqual(status, "Passed")

    def test_invalid_date_and_duplicate_are_failures(self):
        fields = {
            "invoice_number": "INV-1",
            "invoice_date": "31/02/2026",
            "vendor_name": "Vendor",
            "customer_name": "Customer",
            "invoice_amount": "1180",
        }

        validations, status = validate_document("Invoice", fields, duplicate=True)

        self.assertEqual(validations["invoice_date"]["status"], "invalid")
        self.assertEqual(validations["duplicate_document"]["status"], "invalid")
        self.assertEqual(status, "Failed")

    def test_financial_date_and_period_formats(self):
        invoice = {
            "invoice_number": "INV-2", "invoice_date": "15-Apr-2026",
            "vendor_name": "Vendor", "customer_name": "Customer", "invoice_amount": "100",
        }
        validations, status = validate_document("Invoice", invoice)
        self.assertEqual(validations["invoice_date"]["status"], "valid")
        self.assertEqual(status, "Review Required")  # optional GST/tax fields are absent

        bank = {
            "bank_name": "Bank", "account_holder": "User", "account_number": "123456789",
            "ifsc_code": "HDFC0123456", "statement_period": "01-Apr-2024 to 30-Apr-2024",
            "opening_balance": "0", "closing_balance": "100",
        }
        validations, _ = validate_document("Bank Statement", bank)
        self.assertEqual(validations["statement_period"]["status"], "valid")

        gst = {"gstin": "27ABCDE1234F1Z5", "business_name": "Business", "filing_period": "March 2024", "taxable_value": "100", "total_tax": "18"}
        validations, _ = validate_document("GST Return", gst)
        self.assertEqual(validations["filing_period"]["status"], "valid")

        itr = {"pan": "ABCDE1234F", "assessment_year": "2025-26", "gross_income": "100", "tax_paid": "10", "taxable_income": "90"}
        validations, _ = validate_document("ITR", itr)
        self.assertEqual(validations["assessment_year"]["status"], "valid")

    def test_malformed_periods_are_invalid(self):
        gst = {"gstin": "27ABCDE1234F1Z5", "business_name": "Business", "filing_period": "Month 99", "taxable_value": "100", "total_tax": "18"}
        validations, status = validate_document("GST Return", gst)
        self.assertEqual(validations["filing_period"]["status"], "invalid")
        self.assertEqual(status, "Failed")

    def test_financial_amount_formats(self):
        valid_values = (
            "INR 45,230.50", "INR 15,45,000.00", "₹ 1,25,000",
            "Rs. 2,500.75", "$1,234.56", "USD 1000", "(1,250.00)", "-500.25",
        )
        for value in valid_values:
            with self.subTest(value=value):
                validations, _ = validate_document("Balance Sheet", {
                    "total_assets": value, "total_liabilities": "0", "equity": "0",
                })
                self.assertEqual(validations["total_assets"]["status"], "valid")

        invalid_values = ("INR twelve", "1,23,45", "12,34.567", "NaN", "Infinity", "1.2.3", "(₹ 100)-")
        for value in invalid_values:
            with self.subTest(value=value):
                validations, status = validate_document("Balance Sheet", {
                    "total_assets": value, "total_liabilities": "0", "equity": "0",
                })
                self.assertEqual(validations["total_assets"]["status"], "invalid")
                self.assertEqual(status, "Failed")


if __name__ == "__main__":
    unittest.main()
