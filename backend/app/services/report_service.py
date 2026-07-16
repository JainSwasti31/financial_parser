from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User


def _report_query(db: Session):
    return db.query(ParsedReport).options(
        joinedload(ParsedReport.document),
        joinedload(ParsedReport.reviewer),
    )


def _check_access(report: ParsedReport, current_user: User) -> None:
    if current_user.role != Role.Admin and report.document.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this report")


def serialize_report(report: ParsedReport) -> dict:
    document = report.document
    reviewer = report.reviewer
    parsed_data = report.parsed_data or {}
    return {
        "id": report.id,
        "document_id": report.document_id,
        "original_file": {
            "name": document.document_name,
            "type": document.document_type,
            "size": document.file_size,
            "uploaded_at": document.created_at.isoformat() if document.created_at else None,
            "file_hash": document.file_hash,
        },
        "document_status": document.status.value,
        "document_type": parsed_data.get("document_type"),
        "extracted_fields": parsed_data.get("parsed_fields", {}),
        "field_confidences": parsed_data.get("field_confidences", {}),
        "rich_content": parsed_data.get("rich_content", {}),
        "validation_results": report.field_validations or {},
        "validation_status": report.validation_status,
        "processing_time": document.processing_time,
        "review_status": report.review_status,
        "reviewed_by": {
            "id": reviewer.id,
            "name": reviewer.name,
            "email": reviewer.email,
        } if reviewer else None,
        "remarks": report.remarks,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        "export_available": (
            report.review_status == "Approved"
            and document.status == ProcessingStatus.Approved
            and report.reviewed_by is not None
        ),
        "export_block_reason": None if (
            report.review_status == "Approved"
            and document.status == ProcessingStatus.Approved
            and report.reviewed_by is not None
        ) else "Manual approval by an Admin or Analyst is required before export.",
    }


def list_reports(db: Session, current_user: User, page: int, page_size: int):
    query = _report_query(db).join(ParsedReport.document)
    if current_user.role != Role.Admin:
        query = query.filter(Document.uploaded_by == current_user.id)
    total = query.count()
    reports = query.order_by(ParsedReport.updated_at.desc(), ParsedReport.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return total, [serialize_report(report) for report in reports]


def get_report(db: Session, report_id: int, current_user: User) -> ParsedReport:
    report = _report_query(db).filter(ParsedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    _check_access(report, current_user)
    return report


def get_approved_report(db: Session, report_id: int, current_user: User) -> ParsedReport:
    report = get_report(db, report_id, current_user)
    if (
        report.review_status != "Approved"
        or report.document.status != ProcessingStatus.Approved
        or report.reviewed_by is None
    ):
        raise HTTPException(
            status_code=409,
            detail="Report export is available only after parsing and manual approval are complete.",
        )
    return report
