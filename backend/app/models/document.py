from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ProcessingStatus(str, enum.Enum):
    Uploaded = "Uploaded"
    Processing = "Processing"
    Parsed = "Parsed"
    Validation_Failed = "Validation Failed"
    Review_Pending = "Review Pending"
    Approved = "Approved"
    Rejected = "Rejected"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True)
    document_type = Column(String, index=True)
    file_path = Column(String)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(ProcessingStatus), default=ProcessingStatus.Uploaded)
    processing_time = Column(Float, nullable=True) # Time taken in seconds
    processing_progress = Column(Integer, default=0, nullable=False)
    processing_stage = Column(String, default="Uploaded", nullable=False)
    file_size = Column(Integer) # Size in bytes
    file_hash = Column(String, index=True, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    uploader = relationship("User")
