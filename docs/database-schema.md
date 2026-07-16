# Database Schema

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : uploads
    USERS ||--o{ PARSED_REPORTS : reviews
    DOCUMENTS ||--o| PARSED_REPORTS : produces
    DOCUMENTS ||--o{ AUDIT_LOGS : records

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        enum role
        datetime created_at
        datetime updated_at
    }

    DOCUMENTS {
        int id PK
        string document_name
        string document_type
        string file_path
        int uploaded_by FK
        enum status
        float processing_time
        int processing_progress
        string processing_stage
        int file_size
        string file_hash UK
        datetime created_at
        datetime updated_at
    }

    PARSED_REPORTS {
        int id PK
        int document_id FK
        json parsed_data
        json field_validations
        string validation_status
        string review_status
        text remarks
        int reviewed_by FK
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOGS {
        int id PK
        int document_id FK
        string action
        string status
        string remarks
        float processing_time
        datetime created_at
    }
```

`file_hash` prevents duplicate content at the database level. `parsed_data` stores the classified document type, raw OCR text, and latest extracted fields. `field_validations` stores per-field `valid`, `invalid`, or `missing` results.
