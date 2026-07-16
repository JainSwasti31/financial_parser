import unittest
from unittest.mock import patch

from app.parsers.itr_parser import ITRParser
from app.services.validation_service import validate_document


class ValidationServiceTests(unittest.TestCase):
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
