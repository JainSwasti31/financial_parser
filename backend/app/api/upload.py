from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import save_uploaded_file
from app.core.config import settings

router = APIRouter()


@router.post("/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail=f"A batch may contain at most {settings.MAX_BATCH_SIZE} files.")
    uploaded, failed = [], []
    for file in files:
        try:
            document = await save_uploaded_file(file, current_user, db)
            uploaded.append({"id": document.id, "name": document.document_name, "status": document.status.value})
        except HTTPException as exc:
            db.rollback()
            failed.append({"name": file.filename, "status_code": exc.status_code, "error": exc.detail})
    return {"uploaded": uploaded, "failed": failed, "total": len(files)}

@router.post("/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = await save_uploaded_file(file, current_user, db)
    return doc
