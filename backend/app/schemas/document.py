from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.document import ProcessingStatus
from app.schemas.user import UserResponse

class DocumentBase(BaseModel):
    document_name: str
    document_type: str
    status: ProcessingStatus
    file_size: int
    processing_time: Optional[float] = None
    processing_progress: int = 0
    processing_stage: str = "Uploaded"

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    file_hash: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # We can include the uploader details if we use joinedload
    uploader: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DocumentResponse]
