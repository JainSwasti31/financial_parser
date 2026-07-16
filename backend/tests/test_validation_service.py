import unittest

from app.services.validation_service import validate_document


class ValidationServiceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
