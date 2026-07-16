from calendar import month_abbr
from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.models.user import Role, User


SUCCESS_STATUSES = {ProcessingStatus.Parsed, ProcessingStatus.Approved}
FAILED_STATUSES = {ProcessingStatus.Validation_Failed, ProcessingStatus.Rejected}


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _previous_month(value: date) -> date:
    return (value.replace(day=1) - timedelta(days=1)).replace(day=1)


def get_dashboard_data(db: Session, current_user: User, days: int = 14, months: int = 6) -> dict:
    query = db.query(Document)
    if current_user.role != Role.Admin:
        query = query.filter(Document.uploaded_by == current_user.id)
    documents = query.all()
    document_ids = [document.id for document in documents]
    reports = db.query(ParsedReport).filter(ParsedReport.document_id.in_(document_ids)).all() if document_ids else []
    report_types = {report.document_id: (report.parsed_data or {}).get("document_type") for report in reports}

    total = len(documents)
    successful = sum(document.status in SUCCESS_STATUSES for document in documents)
    failed = sum(document.status in FAILED_STATUSES for document in documents)
    completed = successful + failed
    processing_times = [document.processing_time for document in documents if document.processing_time is not None]
    type_counts = Counter(report_types.get(document.id) or document.document_type or "Unknown" for document in documents)

    today = date.today()
    daily_dates = [today - timedelta(days=offset) for offset in reversed(range(days))]
    daily_counter = Counter(document.created_at.date() for document in documents if document.created_at)

    current_month = _month_start(today)
    month_dates = []
    cursor = current_month
    for _ in range(months):
        month_dates.append(cursor)
        cursor = _previous_month(cursor)
    month_dates.reverse()
    monthly_counter = Counter(_month_start(document.created_at.date()) for document in documents if document.created_at)

    logs_query = db.query(AuditLog)
    if current_user.role != Role.Admin:
        logs_query = logs_query.filter(AuditLog.document_id.in_(document_ids)) if document_ids else logs_query.filter(False)
    logs = logs_query.order_by(AuditLog.created_at.desc()).limit(10).all()
    names = {document.id: document.document_name for document in documents}

    return {
        "total_uploaded_documents": total,
        "successfully_parsed": successful,
        "failed_parsing": failed,
        "processing_success_rate": round((successful / completed * 100) if completed else 0, 2),
        "average_processing_time": round(sum(processing_times) / len(processing_times), 2) if processing_times else 0,
        "documents_by_type": [{"type": key, "count": value} for key, value in sorted(type_counts.items())],
        "daily_uploads": [{"date": value.isoformat(), "count": daily_counter[value]} for value in daily_dates],
        "monthly_uploads": [{"month": f"{month_abbr[value.month]} {value.year}", "count": monthly_counter[value]} for value in month_dates],
        "recent_activity": [{
            "id": log.id,
            "document_id": log.document_id,
            "document_name": names.get(log.document_id),
            "action": log.action,
            "status": log.status,
            "remarks": log.remarks,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in logs],
    }
