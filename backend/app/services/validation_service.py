"""
Validation Service — per-field validation for each document type.

Each validator returns a field_validations dict:
  {
    "field_name": {
      "value": "...",
      "status": "valid" | "invalid" | "missing",
      "message": "..."
    }
  }

Overall validation_status:
  - "Passed"           — all mandatory fields valid
  - "Review Required"  — some optional fields invalid / missing
  - "Failed"           — mandatory fields missing or invalid
"""
import re
from datetime import datetime
from typing import Dict, Any, Tuple


# ─── Regex Patterns ────────────────────────────────────────────────────────────

PAN_RE       = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE     = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
IFSC_RE      = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
ACCOUNT_RE   = re.compile(r"^\d{9,18}$")

# ─── Field-level helpers ───────────────────────────────────────────────────────

def _check(field: str, value, validator_fn=None, mandatory: bool = True) -> dict:
    """Build a single field validation result."""
    val = str(value).strip() if value not in (None, "", "null") else None
    if not val:
        return {
            "value": None,
            "status": "missing",
            "message": f"{'Mandatory' if mandatory else 'Optional'} field is missing.",
            "mandatory": mandatory,
        }
    if validator_fn:
        ok, msg = validator_fn(val)
        return {"value": val, "status": "valid" if ok else "invalid", "message": msg, "mandatory": mandatory}
    return {"value": val, "status": "valid", "message": "OK", "mandatory": mandatory}


def _pan(v: str): return (bool(PAN_RE.match(v.upper())), "Valid PAN" if PAN_RE.match(v.upper()) else f"Invalid PAN format: '{v}' (expected AAAAA9999A)")
def _gstin(v: str): return (bool(GSTIN_RE.match(v.upper())), "Valid GSTIN" if GSTIN_RE.match(v.upper()) else f"Invalid GSTIN format: '{v}'")
def _ifsc(v: str): return (bool(IFSC_RE.match(v.upper())), "Valid IFSC" if IFSC_RE.match(v.upper()) else f"Invalid IFSC format: '{v}' (expected ABCD0123456)")
def _account(v: str): return (bool(ACCOUNT_RE.match(re.sub(r"[\s\-]", "", v))), "Valid account number" if ACCOUNT_RE.match(re.sub(r"[\s\-]", "", v)) else f"Invalid account number: '{v}'")
def _date(v: str):
    value = v.strip()
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")
    for fmt in formats:
        try:
            datetime.strptime(value, fmt)
            return True, "Valid date"
        except ValueError:
            continue
    return False, f"Invalid date format: '{v}'"
def _amount(v: str):
    clean = re.sub(r"[₹,\s]", "", v)
    try: float(clean); return True, "Valid amount"
    except: return False, f"Cannot parse amount: '{v}'"


# ─── Per-document-type Validators ──────────────────────────────────────────────

def _validate_bank_statement(fields: dict) -> dict:
    return {
        "bank_name":       _check("bank_name",       fields.get("bank_name")),
        "account_holder":  _check("account_holder",  fields.get("account_holder")),
        "account_number":  _check("account_number",  fields.get("account_number"), _account),
        "ifsc_code":       _check("ifsc_code",        fields.get("ifsc_code"),       _ifsc),
        "statement_period":_check("statement_period", fields.get("statement_period")),
        "opening_balance": _check("opening_balance",  fields.get("opening_balance"),  _amount),
        "closing_balance": _check("closing_balance",  fields.get("closing_balance"),  _amount),
        "total_credits":   _check("total_credits",    fields.get("total_credits"),    _amount, mandatory=False),
        "total_debits":    _check("total_debits",     fields.get("total_debits"),     _amount, mandatory=False),
    }

def _validate_invoice(fields: dict) -> dict:
    return {
        "invoice_number":  _check("invoice_number",  fields.get("invoice_number")),
        "invoice_date":    _check("invoice_date",     fields.get("invoice_date"), _date),
        "vendor_name":     _check("vendor_name",      fields.get("vendor_name")),
        "customer_name":   _check("customer_name",    fields.get("customer_name")),
        "gst_number":      _check("gst_number",       fields.get("gst_number"),      _gstin, mandatory=False),
        "invoice_amount":  _check("invoice_amount",   fields.get("invoice_amount"),  _amount),
        "tax_amount":      _check("tax_amount",       fields.get("tax_amount"),      _amount, mandatory=False),
    }

def _validate_salary(fields: dict) -> dict:
    return {
        "employee_name":    _check("employee_name",    fields.get("employee_name")),
        "company_name":     _check("company_name",     fields.get("company_name")),
        "employee_id":      _check("employee_id",      fields.get("employee_id"),   mandatory=False),
        "pan":              _check("pan",               fields.get("pan"),           _pan,    mandatory=False),
        "month":            _check("month",             fields.get("month")),
        "gross_salary":     _check("gross_salary",     fields.get("gross_salary"),  _amount),
        "net_salary":       _check("net_salary",       fields.get("net_salary"),    _amount),
        "pf":               _check("pf",               fields.get("pf"),            _amount, mandatory=False),
        "professional_tax": _check("professional_tax", fields.get("professional_tax"), _amount, mandatory=False),
    }

def _validate_gst(fields: dict) -> dict:
    return {
        "gstin":          _check("gstin",          fields.get("gstin"),          _gstin),
        "business_name":  _check("business_name",  fields.get("business_name")),
        "filing_period":  _check("filing_period",  fields.get("filing_period")),
        "taxable_value":  _check("taxable_value",  fields.get("taxable_value"),  _amount),
        "cgst":           _check("cgst",           fields.get("cgst"),           _amount, mandatory=False),
        "sgst":           _check("sgst",           fields.get("sgst"),           _amount, mandatory=False),
        "igst":           _check("igst",           fields.get("igst"),           _amount, mandatory=False),
        "total_tax":      _check("total_tax",      fields.get("total_tax"),      _amount),
    }

def _validate_itr(fields: dict) -> dict:
    return {
        "pan":              _check("pan",              fields.get("pan"),              _pan),
        "assessment_year":  _check("assessment_year",  fields.get("assessment_year")),
        "gross_income":     _check("gross_income",     fields.get("gross_income"),     _amount),
        "tax_paid":         _check("tax_paid",         fields.get("tax_paid"),         _amount),
        "refund":           _check("refund",           fields.get("refund"),           _amount, mandatory=False),
        "total_deductions": _check("total_deductions", fields.get("total_deductions"), _amount, mandatory=False),
        "taxable_income":   _check("taxable_income",   fields.get("taxable_income"),   _amount),
    }

def _validate_balance_sheet(fields: dict) -> dict:
    return {
        "total_assets":       _check("total_assets",       fields.get("total_assets"),       _amount),
        "total_liabilities":  _check("total_liabilities",  fields.get("total_liabilities"),  _amount),
        "equity":             _check("equity",             fields.get("equity"),             _amount),
        "current_assets":     _check("current_assets",     fields.get("current_assets"),     _amount, mandatory=False),
        "current_liabilities":_check("current_liabilities",fields.get("current_liabilities"),_amount, mandatory=False),
        "fixed_assets":       _check("fixed_assets",       fields.get("fixed_assets"),       _amount, mandatory=False),
    }

def _validate_pnl(fields: dict) -> dict:
    return {
        "revenue":             _check("revenue",             fields.get("revenue"),             _amount),
        "gross_profit":        _check("gross_profit",        fields.get("gross_profit"),        _amount),
        "operating_expenses":  _check("operating_expenses",  fields.get("operating_expenses"),  _amount),
        "net_profit":          _check("net_profit",          fields.get("net_profit"),          _amount),
        "ebitda":              _check("ebitda",              fields.get("ebitda"),              _amount, mandatory=False),
    }

_VALIDATORS = {
    "Bank Statement": _validate_bank_statement,
    "Invoice":        _validate_invoice,
    "Salary Slip":    _validate_salary,
    "GST Return":     _validate_gst,
    "ITR":            _validate_itr,
    "Balance Sheet":  _validate_balance_sheet,
    "Profit & Loss":  _validate_pnl,
}


# ─── Main entry point ──────────────────────────────────────────────────────────

def validate_document(doc_type: str, parsed_fields: dict, duplicate: bool = False) -> Tuple[dict, str]:
    """
    Returns (field_validations, validation_status).

    validation_status values:
      - "Passed"           all mandatory fields present and valid
      - "Review Required"  warnings only (optional fields invalid/missing)
      - "Failed"           one or more mandatory fields missing or invalid
    """
    validator = _VALIDATORS.get(doc_type)
    if not validator:
        return {}, "Review Required"  # Unknown type — needs human review

    field_validations = validator(parsed_fields)

    if duplicate:
        field_validations["duplicate_document"] = {
            "value": True,
            "status": "invalid",
            "message": "A document with identical content already exists.",
            "mandatory": True,
        }

    has_mandatory_fail = any(
        r["status"] in ("invalid", "missing")
        for field, r in field_validations.items()
        if r.get("mandatory", False)
    )

    has_any_fail = any(r["status"] != "valid" for r in field_validations.values())

    if has_mandatory_fail:
        overall = "Failed"
    elif has_any_fail:
        overall = "Review Required"
    else:
        overall = "Passed"

    return field_validations, overall
