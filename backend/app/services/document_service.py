import os
import hashlib
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.document import Document, ProcessingStatus
from app.models.user import User, Role
from app.models.report import ParsedReport
from app.utils.audit import log_action
from app.core.config import settings

UPLOAD_DIR = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

async def save_uploaded_file(file: UploadFile, current_user: User, db: Session) -> Document:
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF, JPG, or PNG.")
    
    # Calculate hash and size
    sha256_hash = hashlib.sha256()
    file_size = 0
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")
    
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 25MB limit.")
        
    sha256_hash.update(content)
    file_hash = sha256_hash.hexdigest()
    
    # Check duplicate
    existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_doc:
        raise HTTPException(status_code=409, detail="A document with this exact content has already been uploaded.")
    
    # Save file
    safe_filename = f"{file_hash[:8]}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Create DB entry
    new_doc = Document(
        document_name=file.filename,
        document_type=ext[1:].upper(),
        file_path=file_path,
        uploaded_by=current_user.id,
        status=ProcessingStatus.Uploaded,
        file_size=file_size,
        file_hash=file_hash
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # Audit log
    log_action(db, new_doc.id, "Document Uploaded", "Success", f"File saved as {safe_filename}")
    
    return new_doc

def get_documents_paginated(db: Session, current_user: User, page: int = 1, page_size: int = 10, search=None, document_type=None, status=None, uploaded_by=None, date_from=None, date_to=None, processing_time_min=None, processing_time_max=None):
    query = db.query(Document)
    
    if current_user.role != Role.Admin:
        query = query.filter(Document.uploaded_by == current_user.id)
    elif uploaded_by is not None:
        query = query.filter(Document.uploaded_by == uploaded_by)
    if status:
        query = query.filter(Document.status == status)
    if date_from:
        query = query.filter(Document.created_at >= date_from)
    if date_to:
        from datetime import timedelta
        query = query.filter(Document.created_at < date_to + timedelta(days=1))
    if processing_time_min is not None:
        query = query.filter(Document.processing_time >= processing_time_min)
    if processing_time_max is not None:
        query = query.filter(Document.processing_time <= processing_time_max)

    documents = query.order_by(Document.created_at.desc()).all()
    report_rows = db.query(ParsedReport).filter(ParsedReport.document_id.in_([doc.id for doc in documents])).all() if documents else []
    reports = {report.document_id: report for report in report_rows}
    searchable_fields = {
        "pan", "pan_number", "gst", "gst_number", "gstin",
        "invoice_number", "invoice_no", "account_number", "account_no",
        "employee_name", "company_name",
    }

    def normalize(value):
        return "".join(character for character in str(value).casefold() if character.isalnum())

    def normalize_document_type(value):
        normalized = normalize(str(value).replace("&", "and"))
        for extension in ("jpeg", "pdf", "jpg", "png"):
            if normalized.endswith(extension):
                normalized = normalized[:-len(extension)]
                break
        return normalized

    def matches(doc):
        report = reports.get(doc.id)
        parsed = (report.parsed_data or {}) if report else {}
        if document_type:
            requested_type = document_type.strip().casefold()
            available_types = {
                str(value).strip().casefold()
                for value in (parsed.get("document_type"), doc.document_type)
                if value
            }
            normalized_requested = normalize_document_type(document_type)
            filename_type = normalize_document_type(doc.document_name)
            if requested_type not in available_types and normalized_requested != filename_type:
                return False
        if search:
            needle = search.strip().casefold()
            normalized_needle = normalize(needle)
            fields = parsed.get("parsed_fields", {}) or {}
            values = [value for key, value in fields.items() if key.casefold() in searchable_fields]
            upload_date = doc.created_at.strftime("%Y-%m-%d %d/%m/%Y %m/%d/%Y %d-%m-%Y") if doc.created_at else ""
            values.extend([doc.document_name, upload_date])
            if not any(
                needle in str(value).casefold()
                or (normalized_needle and normalized_needle in normalize(value))
                for value in values if value is not None
            ):
                return False
        return True

    filtered = [doc for doc in documents if matches(doc)]
    total = len(filtered)
    items = filtered[(page - 1) * page_size:page * page_size]
    
    return total, items

def delete_document_by_id(db: Session, doc_id: int):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # Delete from filesystem
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        
    db.delete(doc)
    db.commit()
