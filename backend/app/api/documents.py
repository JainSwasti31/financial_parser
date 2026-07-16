from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User, Role
from app.models.document import Document, ProcessingStatus
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.document_service import get_documents_paginated, delete_document_by_id
from app.utils.audit import log_action

router = APIRouter()

@router.get("/", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    document_type: str | None = None,
    status: ProcessingStatus | None = None,
    uploaded_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    processing_time_min: float | None = Query(None, ge=0),
    processing_time_max: float | None = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total, items = get_documents_paginated(db, current_user, page, page_size, search, document_type, status, uploaded_by, date_from, date_to, processing_time_min, processing_time_max)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role != Role.Admin and doc.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this document")
        
    return doc

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(require_role([Role.Admin])),
    db: Session = Depends(get_db)
):
    delete_document_by_id(db, document_id)
    # Log deletion
    log_action(db, document_id, "Document Deleted", "Success", f"Deleted by Admin {current_user.email}")
    return {"message": "Document deleted successfully"}
