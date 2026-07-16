"""Generate test fixture PDFs for all document types."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out_dir = os.path.join(os.path.dirname(__file__), "test_fixtures")
os.makedirs(out_dir, exist_ok=True)

fixtures = {
    "bank_statement.pdf": [
        "HDFC BANK LIMITED",
        "Account Statement",
        "Account Holder: Ramesh Kumar",
        "Account Number: 5020012345678901",
        "IFSC Code: HDFC0001234",
        "Statement Period: 01-Apr-2024 to 30-Apr-2024",
        "Opening Balance: INR 45,230.50",
        "Closing Balance: INR 62,850.75",
        "",
        "Date       | Description              | Debit      | Credit     | Balance",
        "02-Apr     | ATM Withdrawal           | 5,000.00   |            | 40,230.50",
        "05-Apr     | NEFT Credit - Salary     |            | 35,000.00  | 75,230.50",
        "10-Apr     | Amazon Purchase          | 2,500.00   |            | 72,730.50",
        "15-Apr     | Electricity Bill         | 1,200.00   |            | 71,530.50",
        "20-Apr     | UPI Transfer             | 8,679.75   |            | 62,850.75",
        "",
        "Total Credits: INR 35,000.00",
        "Total Debits: INR 17,379.75",
        "Transaction Count: 5",
    ],
    "invoice.pdf": [
        "TAX INVOICE",
        "Invoice Number: INV-2024-00456",
        "Invoice Date: 15-Apr-2024",
        "",
        "Vendor: TechSupply Solutions Pvt Ltd",
        "GST Number: 29AAGCT1234H1Z5",
        "",
        "Customer: Reliance Industries Ltd",
        "",
        "Description                    Qty   Unit Price   Amount",
        "Laptop HP EliteBook 840        2     85,000.00    1,70,000.00",
        "Wireless Mouse Logitech        5      1,500.00      7,500.00",
        "",
        "Subtotal: INR 1,77,500.00",
        "CGST (9%): INR 15,975.00",
        "SGST (9%): INR 15,975.00",
        "Invoice Amount: INR 2,09,450.00",
        "Tax Amount: INR 31,950.00",
    ],
    "salary_slip.pdf": [
        "SALARY SLIP - April 2024",
        "Company: Infosys Limited",
        "",
        "Employee Name: Priya Sharma",
        "Employee ID: INF00123456",
        "PAN: ABCDE1234F",
        "Month: April 2024",
        "",
        "Earnings:",
        "Basic Salary: INR 45,000.00",
        "HRA: INR 18,000.00",
        "Gross Salary: INR 77,000.00",
        "",
        "Deductions:",
        "Provident Fund (PF): INR 5,400.00",
        "Professional Tax: INR 200.00",
        "TDS: INR 4,200.00",
        "Total Deductions: INR 9,800.00",
        "",
        "Net Salary: INR 67,200.00",
    ],
    "gst_return.pdf": [
        "GST RETURN - GSTR-3B",
        "GSTIN: 27AAACR5055K1ZQ",
        "Business Name: Reliance Retail Ltd",
        "Filing Period: March 2024",
        "",
        "Outward Supplies (Sales):",
        "Taxable Value: INR 15,45,000.00",
        "CGST: INR 1,39,050.00",
        "SGST: INR 1,39,050.00",
        "IGST: INR 0.00",
        "Total Tax: INR 2,78,100.00",
    ],
    "itr.pdf": [
        "INCOME TAX RETURN - ITR-1",
        "Assessment Year: 2024-25",
        "PAN: ABCDE1234F",
        "",
        "Name: Rajesh Kumar",
        "",
        "Income Details:",
        "Gross Total Income: INR 12,50,000.00",
        "Total Deductions (80C, 80D etc): INR 1,50,000.00",
        "Taxable Income: INR 11,00,000.00",
        "",
        "Tax Computation:",
        "Tax Liability: INR 1,72,500.00",
        "Tax Paid (TDS): INR 1,80,000.00",
        "Refund: INR 7,500.00",
    ],
    "balance_sheet.pdf": [
        "BALANCE SHEET",
        "As at 31st March 2024",
        "Company: Tata Consultancy Services Ltd",
        "",
        "ASSETS",
        "Fixed Assets: INR 45,60,00,000",
        "Current Assets:",
        "  Cash: INR 12,30,00,000",
        "  Trade Receivables: INR 8,90,00,000",
        "Total Current Assets: INR 24,60,00,000",
        "Total Assets: INR 70,20,00,000",
        "",
        "LIABILITIES",
        "Current Liabilities: INR 15,80,00,000",
        "Long Term Liabilities: INR 12,40,00,000",
        "Total Liabilities: INR 28,20,00,000",
        "Shareholders Equity: INR 42,00,00,000",
    ],
    "profit_and_loss.pdf": [
        "PROFIT AND LOSS STATEMENT",
        "For the Year Ended 31st March 2024",
        "Company: Wipro Technologies Ltd",
        "",
        "Revenue: INR 92,50,00,000",
        "Cost of Goods Sold: INR 54,30,00,000",
        "Gross Profit: INR 38,20,00,000",
        "",
        "Operating Expenses:",
        "  Salaries: INR 14,60,00,000",
        "  Rent: INR 2,80,00,000",
        "  Marketing: INR 3,20,00,000",
        "Total Operating Expenses: INR 20,60,00,000",
        "",
        "EBITDA: INR 17,60,00,000",
        "Depreciation: INR 2,10,00,000",
        "Interest: INR 1,30,00,000",
        "Net Profit: INR 14,20,00,000",
    ],
}

for filename, lines in fixtures.items():
    filepath = os.path.join(out_dir, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, lines[0])
    c.setFont("Helvetica", 10)
    y -= 30
    for line in lines[1:]:
        if y < 60:
            c.showPage()
            y = h - 60
            c.setFont("Helvetica", 10)
        c.drawString(60, y, line)
        y -= 18
    c.save()
    print(f"Created: {filepath}")

print("All test fixtures generated!")
