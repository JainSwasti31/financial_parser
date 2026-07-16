import unittest

from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.parser import BulkProcessRequest, bulk_process
from app.core.database import Base
from app.models.document import Document, ProcessingStatus
from app.models.user import Role, User
from app.services.ai_service import calculate_field_confidences
from app.services.rich_extraction_service import extract_rich_content


class BonusFeatureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(name="Analyst", email="bonus@example.com", password_hash="x", role=Role.Analyst)
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_confidences_reflect_validation_and_manual_evidence(self):
        fields = {"pan": "ABCDE1234F", "ifsc_code": "INVALID", "missing": None}
        validations = {"pan": {"status": "valid"}, "ifsc_code": {"status": "invalid"}, "missing": {"status": "missing"}}
        scores = calculate_field_confidences(fields, "PAN ABCDE1234F", validations)
        self.assertEqual(scores["pan"], 98)
        self.assertEqual(scores["ifsc_code"], 42)
        self.assertEqual(scores["missing"], 0)

    def test_bulk_process_queues_owned_documents(self):
        documents = []
        for index in range(2):
            document = Document(document_name=f"batch-{index}.pdf", document_type="PDF", file_path=f"batch-{index}.pdf", uploaded_by=self.user.id, status=ProcessingStatus.Uploaded, file_size=10, file_hash=f"batch-hash-{index}")
            self.db.add(document)
            documents.append(document)
        self.db.commit()
        tasks = BackgroundTasks()
        result = bulk_process(BulkProcessRequest(document_ids=[document.id for document in documents]), tasks, self.user, self.db)
        self.assertEqual(result["accepted"], [document.id for document in documents])
        self.assertEqual(len(tasks.tasks), 2)
        for document in documents:
            self.db.refresh(document)
            self.assertEqual(document.status, ProcessingStatus.Processing)
            self.assertEqual(document.processing_stage, "Queued")

    def test_rich_extraction_is_failure_tolerant(self):
        self.assertEqual(extract_rich_content("does-not-exist.pdf"), {"tables": [], "signatures": [], "qr_codes": []})


if __name__ == "__main__":
    unittest.main()
