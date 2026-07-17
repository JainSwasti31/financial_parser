from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import Role, User

router = APIRouter()


@router.get("/")
def list_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), document_id: int | None = None, action: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(AuditLog).outerjoin(Document, AuditLog.document_id == Document.id)
    if current_user.role != Role.Admin:
        query = query.filter(Document.uploaded_by == current_user.id)
    if document_id is not None:
        query = query.filter(AuditLog.document_id == document_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": log.id,
            "document_id": log.document_id,
            "action": log.action,
            "status": log.status,
            "remarks": log.remarks,
            "processing_time": log.processing_time,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in logs],
    }
