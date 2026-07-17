import os
import sys

# Add backend directory to sys path if running standalone, else relative imports work
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

def log_action(db: Session, document_id: int | None, action: str, status: str, remarks: str = None, processing_time: float = None):
    """
    Utility function to easily insert an audit log entry.
    """
    log_entry = AuditLog(
        document_id=document_id,
        action=action,
        status=status,
        remarks=remarks,
        processing_time=processing_time
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
