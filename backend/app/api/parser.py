from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.services.parser_service import process_document_task
from pydantic import BaseModel, Field

router = APIRouter()


class BulkProcessRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=20)


@router.post("/bulk")
def bulk_process(
    payload: BulkProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.user import Role
    accepted, rejected = [], []
    for document_id in dict.fromkeys(payload.document_ids):
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            rejected.append({"document_id": document_id, "reason": "Not found"})
            continue
        if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
            rejected.append({"document_id": document_id, "reason": "Not authorized"})
            continue
        if doc.status == ProcessingStatus.Processing:
            rejected.append({"document_id": document_id, "reason": "Already processing"})
            continue
        doc.status = ProcessingStatus.Processing
        doc.processing_progress = 0
        doc.processing_stage = "Queued"
        accepted.append(document_id)
    db.commit()
    for document_id in accepted:
        background_tasks.add_task(process_document_task, document_id)
    return {"accepted": accepted, "rejected": rejected}


@router.post("/process/{document_id}")
def trigger_process(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start OCR + AI parsing for a document asynchronously."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status == ProcessingStatus.Processing:
        raise HTTPException(status_code=409, detail="Document is already being processed")

    # Check access: Analysts can only process their own docs
    from app.models.user import Role
    if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to process this document")

    doc.status = ProcessingStatus.Processing
    doc.processing_progress = 0
    doc.processing_stage = "Queued"
    db.commit()
    background_tasks.add_task(process_document_task, document_id)
    return {"message": "Processing started", "document_id": document_id, "status": "Processing"}


@router.post("/reprocess/{document_id}")
def trigger_reprocess(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force re-process a document even if already parsed."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.models.user import Role
    if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Reset status to allow reprocessing
    doc.status = ProcessingStatus.Uploaded
    report = db.query(ParsedReport).filter(ParsedReport.document_id == document_id).first()
    if report:
        report.review_status = "Pending"
        report.reviewed_by = None
        report.remarks = None
    db.commit()

    doc.processing_progress = 0
    doc.processing_stage = "Queued"
    db.commit()
    background_tasks.add_task(process_document_task, document_id)
    return {"message": "Reprocessing started", "document_id": document_id, "status": "Processing"}


@router.get("/result/{document_id}")
def get_result(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current status and parsed result for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.models.user import Role
    if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    report = db.query(ParsedReport).filter(
        ParsedReport.document_id == document_id
    ).first()

    return {
        "document_id": document_id,
        "document_name": doc.document_name,
        "status": doc.status.value,
        "processing_time": doc.processing_time,
        "processing_progress": doc.processing_progress,
        "processing_stage": doc.processing_stage,
        "report": {
            "id": report.id,
            "document_type": report.parsed_data.get("document_type") if report else None,
            "raw_text": report.parsed_data.get("raw_text") if report else None,
            "parsed_fields": report.parsed_data.get("parsed_fields") if report else None,
            "field_confidences": report.parsed_data.get("field_confidences", {}) if report else None,
            "rich_content": report.parsed_data.get("rich_content", {}) if report else None,
            "field_validations": report.field_validations if report else None,
            "validation_status": report.validation_status if report else None,
            "review_status": report.review_status if report else None,
        } if report else None
    }
