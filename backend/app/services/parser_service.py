"""
Parser Service — Orchestrator: OCR → Classify → Parse → Save → Update Status
"""
import os
import time
import logging
from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.services.ocr_service import get_ocr_provider
from app.services.ai_service import get_ai_classifier, calculate_field_confidences
from app.services.rich_extraction_service import extract_rich_content
from app.utils.audit import log_action
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def process_document_task(document_id: int) -> None:
    """Background-task entry point with a session independent of the request."""
    db = SessionLocal()
    try:
        process_document(document_id, db)
    finally:
        db.close()


def _set_progress(db: Session, doc: Document, progress: int, stage: str) -> None:
    doc.processing_progress = progress
    doc.processing_stage = stage
    db.commit()

# MIME type lookup
MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Document type → Parser class mapping
PARSER_MAP = {
    "Bank Statement":  ("app.parsers.bank_statement", "BankStatementParser"),
    "Invoice":         ("app.parsers.invoice_parser",  "InvoiceParser"),
    "Salary Slip":     ("app.parsers.salary_parser",   "SalaryParser"),
    "GST Return":      ("app.parsers.gst_parser",      "GSTParser"),
    "ITR":             ("app.parsers.itr_parser",       "ITRParser"),
    "Balance Sheet":   ("app.parsers.balance_sheet",   "BalanceSheetParser"),
    "Profit & Loss":   ("app.parsers.pnl_parser",      "ProfitAndLossParser"),
}


def _get_parser(doc_type: str):
    """Dynamically import and return the correct parser instance."""
    if doc_type not in PARSER_MAP:
        return None
    module_name, class_name = PARSER_MAP[doc_type]
    import importlib
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


def _get_mime(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return MIME_MAP.get(ext, "application/octet-stream")


def process_document(document_id: int, db: Session) -> dict:
    """
    Full pipeline: OCR → Classify → Parse → Save to DB.
    Returns a result dict with status info.
    """
    doc: Document = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Mark as Processing
    doc.status = ProcessingStatus.Processing
    _set_progress(db, doc, 5, "Starting")

    raw_text = ""
    doc_type = "Unknown"
    parsed_data = {}
    start_time = time.time()

    # ── Step 1: OCR ──────────────────────────────────────────────────────────
    try:
        _set_progress(db, doc, 15, "Extracting text")
        ocr = get_ocr_provider()
        mime = _get_mime(doc.file_path)
        raw_text, ocr_duration = ocr.extract_text(doc.file_path, mime)

        if not raw_text or len(raw_text.strip()) < 10:
            _fail_document(db, doc, document_id, "OCR produced empty output — document may be blank or corrupted.")
            return {"status": "Review Pending", "reason": "Blank or unreadable document"}

        log_action(db, document_id, "OCR Completed", "Success",
                   f"Provider: {type(ocr).__name__}, Duration: {ocr_duration:.2f}s, Chars: {len(raw_text)}")

    except Exception as e:
        _fail_document(db, doc, document_id, f"OCR Failed: {str(e)}")
        return {"status": "Review Pending", "reason": str(e)}

    # ── Step 2: Classify ──────────────────────────────────────────────────────
    try:
        _set_progress(db, doc, 40, "Classifying document")
        classifier = get_ai_classifier()
        doc_type = classifier.classify(raw_text)
        log_action(db, document_id, "Classification Completed", "Success",
                   f"Document type: {doc_type}")
    except Exception as e:
        doc_type = "Unknown"
        log_action(db, document_id, "Classification Failed", "Warning", str(e))

    # ── Step 3: Parse ─────────────────────────────────────────────────────────
    log_action(db, document_id, "Parsing Started", "In Progress",
               f"Document type: {doc_type}")

    try:
        _set_progress(db, doc, 55, "Extracting fields")
        parser = _get_parser(doc_type)
        if parser:
            parsed_data = parser.parse(raw_text)
        else:
            # Unknown type — send to review
            _review_document(db, doc, document_id, raw_text, doc_type,
                             f"Unknown document type: {doc_type}")
            return {"status": "Review Pending", "reason": f"Could not classify document"}

        total_time = time.time() - start_time
        log_action(db, document_id, "Parsing Completed", "Success",
                   f"Fields extracted: {len(parsed_data)}, Total time: {total_time:.2f}s")

    except Exception as e:
        _fail_document(db, doc, document_id, f"Parsing Failed: {str(e)}")
        return {"status": "Review Pending", "reason": str(e)}

    # ── Step 4: Validate Fields ───────────────────────────────────────────────
    from app.services.validation_service import validate_document
    _set_progress(db, doc, 75, "Validating fields")
    duplicate = False
    if doc.file_hash:
        duplicate = db.query(Document).filter(
            Document.file_hash == doc.file_hash,
            Document.id != doc.id,
        ).first() is not None
    field_validations, validation_status = validate_document(doc_type, parsed_data, duplicate=duplicate)
    field_confidences = calculate_field_confidences(parsed_data, raw_text, field_validations)
    _set_progress(db, doc, 82, "Extracting tables, signatures, and QR codes")
    rich_content = extract_rich_content(doc.file_path)
    log_action(db, document_id, "Validation Completed", validation_status,
               f"Fields checked: {len(field_validations)}, Overall: {validation_status}")

    # ── Step 5: Save Report ───────────────────────────────────────────────────
    total_time = time.time() - start_time
    _set_progress(db, doc, 85, "Generating report data")

    # Determine document status based on validation
    if validation_status == "Failed":
        new_doc_status = ProcessingStatus.Validation_Failed
        review_status  = "Pending"
    elif validation_status == "Review Required":
        new_doc_status = ProcessingStatus.Review_Pending
        review_status  = "Pending"
    else:
        new_doc_status = ProcessingStatus.Parsed
        # Successful parsing still requires a human approval before export.
        review_status  = "Pending"

    report_data = {
        "document_type": doc_type,
        "raw_text": raw_text,
        "parsed_fields": parsed_data,
        "field_confidences": field_confidences,
        "rich_content": rich_content,
    }

    # Check if a report already exists (reprocess case)
    existing_report = db.query(ParsedReport).filter(
        ParsedReport.document_id == document_id
    ).first()

    if existing_report:
        existing_report.parsed_data      = report_data
        existing_report.field_validations = field_validations
        existing_report.validation_status = validation_status
        existing_report.review_status     = review_status
        existing_report.remarks           = None  # Reset on reprocess
        existing_report.reviewed_by        = None
        db.commit()
        logger.info(
            "Updated parsed report document_id=%s report_id=%s validation_status=%s field_validations=%s",
            document_id, existing_report.id, validation_status,
            {field: result["status"] for field, result in field_validations.items()},
        )
    else:
        report = ParsedReport(
            document_id=document_id,
            parsed_data=report_data,
            field_validations=field_validations,
            validation_status=validation_status,
            review_status=review_status,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        logger.info(
            "Saved parsed report document_id=%s report_id=%s validation_status=%s field_validations=%s",
            document_id, report.id, validation_status,
            {field: result["status"] for field, result in field_validations.items()},
        )

    # Update document status and processing time
    doc.status = new_doc_status
    doc.processing_time = total_time
    _set_progress(db, doc, 100, "Completed")

    return {
        "status": new_doc_status.value,
        "document_type": doc_type,
        "validation_status": validation_status,
        "processing_time": total_time,
        "fields_extracted": len(parsed_data),
        "field_confidences": field_confidences,
    }


def _fail_document(db: Session, doc: Document, doc_id: int, reason: str):
    doc.status = ProcessingStatus.Review_Pending
    concise_reason = " ".join(str(reason).split())[:240]
    _set_progress(db, doc, 100, f"Failed: {concise_reason}")
    log_action(db, doc_id, "Parsing Failed", "Review Pending", reason)


def _review_document(db: Session, doc: Document, doc_id: int, raw_text: str,
                     doc_type: str, reason: str):
    doc.status = ProcessingStatus.Review_Pending
    concise_reason = " ".join(str(reason).split())[:240]
    _set_progress(db, doc, 100, f"Review required: {concise_reason}")
    # Reprocessing must update the existing report. Creating another row can
    # leave the UI reading stale data from the first report.
    report = db.query(ParsedReport).filter(ParsedReport.document_id == doc_id).first()
    if report is None:
        report = ParsedReport(document_id=doc_id)
        db.add(report)
    report.parsed_data = {
        "document_type": doc_type,
        "raw_text": raw_text,
        "parsed_fields": {},
        "processing_error": concise_reason,
    }
    report.field_validations = {}
    report.validation_status = "Review Pending"
    report.review_status = "Pending"
    report.reviewed_by = None
    report.remarks = concise_reason
    db.commit()
    log_action(db, doc_id, "Parsing Flagged for Review", "Review Pending", reason)
