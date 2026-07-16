from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.document import Document, ProcessingStatus
from app.models.report import ParsedReport
from app.utils.audit import log_action
from app.services.validation_service import validate_document

router = APIRouter()


def _require_reviewer(current_user: User):
    if current_user.role not in (Role.Admin, Role.Analyst):
        raise HTTPException(status_code=403, detail="Only Admin and Analyst roles can review documents")


def _get_doc_and_report(document_id: int, db: Session, current_user: User):
    """Shared helper: fetch doc + report, enforce access."""
    _require_reviewer(current_user)
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to review this document")
    report = db.query(ParsedReport).filter(ParsedReport.document_id == document_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No parsed report found. Process the document first.")
    # Repair reports created by the old parser flow, which marked parsing as
    # approved without moving the document to Approved or recording a reviewer.
    if report.review_status == "Approved" and (
        doc.status != ProcessingStatus.Approved or report.reviewed_by is None
    ):
        report.review_status = "Pending"
        report.reviewed_by = None
        db.commit()
    return doc, report


@router.get("/{document_id}")
def get_review(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full review data: parsed fields, per-field validation, remarks."""
    doc, report = _get_doc_and_report(document_id, db, current_user)
    return {
        "document_id": document_id,
        "document_name": doc.document_name,
        "document_status": doc.status.value,
        "document_type": report.parsed_data.get("document_type") if report.parsed_data else None,
        "parsed_fields": report.parsed_data.get("parsed_fields") if report.parsed_data else {},
        "field_confidences": report.parsed_data.get("field_confidences", {}) if report.parsed_data else {},
        "rich_content": report.parsed_data.get("rich_content", {}) if report.parsed_data else {},
        "field_validations": report.field_validations or {},
        "validation_status": report.validation_status,
        "review_status": report.review_status,
        "remarks": report.remarks,
        "reviewed_by": report.reviewed_by,
    }


@router.put("/{document_id}/fields")
def update_fields(
    document_id: int,
    updated_fields: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit extracted field values and re-run per-field validation."""
    doc, report = _get_doc_and_report(document_id, db, current_user)

    # Merge updated fields into existing parsed_fields
    existing_data = report.parsed_data or {}
    existing_fields = existing_data.get("parsed_fields", {})
    existing_fields.update(updated_fields)

    # Re-run validation on updated fields
    doc_type = existing_data.get("document_type", "Unknown")
    field_validations, validation_status = validate_document(doc_type, existing_fields)

    # Persist
    updated_data = {**existing_data, "parsed_fields": existing_fields}
    confidences = dict(existing_data.get("field_confidences", {}))
    confidences.update({field: 100 for field in updated_fields})
    updated_data["field_confidences"] = confidences
    report.parsed_data = updated_data
    report.field_validations = field_validations
    report.validation_status = validation_status
    report.review_status = "Pending"
    report.reviewed_by = None
    if validation_status == "Failed":
        doc.status = ProcessingStatus.Validation_Failed
    elif validation_status == "Review Required":
        doc.status = ProcessingStatus.Review_Pending
    else:
        doc.status = ProcessingStatus.Review_Pending
    db.commit()

    log_action(db, document_id, "Fields Updated", "Success",
               f"Updated by {current_user.email}: {list(updated_fields.keys())}")

    return {
        "message": "Fields updated and re-validated",
        "updated_fields": list(updated_fields.keys()),
        "field_validations": field_validations,
        "validation_status": validation_status,
        "field_confidences": confidences,
    }


@router.post("/{document_id}/approve")
def approve_document(
    document_id: int,
    remarks: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a document — set review_status=Approved, Document.status=Approved."""
    doc, report = _get_doc_and_report(document_id, db, current_user)

    report.review_status = "Approved"
    report.reviewed_by = current_user.id
    report.remarks = remarks
    doc.status = ProcessingStatus.Approved
    db.commit()

    log_action(db, document_id, "Document Approved", "Approved",
               f"Approved by {current_user.email}. Remarks: {remarks or 'None'}")

    return {"message": "Document approved successfully", "document_id": document_id}


@router.post("/{document_id}/reject")
def reject_document(
    document_id: int,
    remarks: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a document — set review_status=Rejected, Document.status=Rejected."""
    doc, report = _get_doc_and_report(document_id, db, current_user)

    if not remarks:
        raise HTTPException(status_code=400, detail="Remarks are required when rejecting a document.")

    report.review_status = "Rejected"
    report.reviewed_by = current_user.id
    report.remarks = remarks
    doc.status = ProcessingStatus.Rejected
    db.commit()

    log_action(db, document_id, "Document Rejected", "Rejected",
               f"Rejected by {current_user.email}. Reason: {remarks}")

    return {"message": "Document rejected", "document_id": document_id}
