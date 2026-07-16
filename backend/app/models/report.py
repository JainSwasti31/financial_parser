from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ParsedReport(Base):
    __tablename__ = "parsed_reports"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    parsed_data = Column(JSON)
    field_validations = Column(JSON, nullable=True)  # Per-field validation results
    validation_status = Column(String)               # Passed / Failed / Review Required
    review_status = Column(String)                   # Pending / Approved / Rejected
    remarks = Column(Text, nullable=True)            # Reviewer remarks
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    document = relationship("Document")
    reviewer = relationship("User")

