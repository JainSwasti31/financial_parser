# System Architecture

The application uses a React single-page frontend, a modular FastAPI backend, PostgreSQL, private document storage, and pluggable OCR/AI providers. Parsing runs after the HTTP response through FastAPI background tasks; the browser polls persisted progress.

```mermaid
flowchart TB
    USER([Admin / Analyst])

    subgraph CLIENT[Frontend - React / Vite]
        direction LR
        AUTH_UI[Login and Auth Context]
        DOC_UI[Documents, Search and Filters]
        BATCH_UI[Batch Upload and Queue]
        REVIEW_UI[Review and Confidence Badges]
        DASH_UI[Dashboard and Audit Logs]
        REPORT_UI[Reports and Exports]
        HTTP[Axios Client and JWT Interceptor]

        AUTH_UI --> HTTP
        DOC_UI --> HTTP
        BATCH_UI --> HTTP
        REVIEW_UI --> HTTP
        DASH_UI --> HTTP
        REPORT_UI --> HTTP
    end

    subgraph API[FastAPI Application]
        direction TB
        CORS[CORS and Error Middleware]
        SECURITY[JWT Validation, Roles and Ownership]

        subgraph ROUTERS[API Routers]
            AUTH_API[Auth]
            UPLOAD_API[Single and Batch Upload]
            DOC_API[Documents and Search]
            PARSER_API[Process, Bulk Process and Polling]
            REVIEW_API[Edit, Approve and Reject]
            REPORT_API[Reports and PDF/XLSX/CSV]
            ANALYTICS_API[Dashboard and Audit Logs]
        end

        CORS --> SECURITY
        SECURITY --> AUTH_API
        SECURITY --> UPLOAD_API
        SECURITY --> DOC_API
        SECURITY --> PARSER_API
        SECURITY --> REVIEW_API
        SECURITY --> REPORT_API
        SECURITY --> ANALYTICS_API
    end

    subgraph WORKER[Background Document Pipeline]
        direction LR
        QUEUE[Queued - 0%]
        OCR[OCR - 15%]
        CLASSIFY[Classification - 40%]
        PARSE[Field Parsing - 55%]
        VALIDATE[Validation and Confidence - 75%]
        RICH[Tables, Signatures and QR - 82%]
        SAVE[Persist Report - 85%]
        COMPLETE[Complete / Review - 100%]

        QUEUE --> OCR --> CLASSIFY --> PARSE --> VALIDATE --> RICH --> SAVE --> COMPLETE
    end

    subgraph DATA[Persistence Layer]
        POSTGRES[("PostgreSQL<br/>Users, Documents, Reports, Audit Logs")]
        FILES[("Private File Storage<br/>PDF / JPG / PNG")]
    end

    subgraph EXTERNAL[External and Local Processing]
        GEMINI["Google Gemini<br/>OCR, Classification, Extraction"]
        TESSERACT["Tesseract OCR<br/>Local Fallback"]
        PYMUPDF["PyMuPDF<br/>PDF Rendering and Tables"]
        OPENCV["OpenCV<br/>QR and Signature Regions"]
    end

    subgraph OUTPUT[Generated Outputs]
        PDF[PDF Report]
        XLSX[Excel Report]
        CSV[CSV Report]
    end

    USER --> CLIENT
    HTTP -->|HTTPS + Bearer JWT| CORS

    AUTH_API --> POSTGRES
    UPLOAD_API -->|Metadata and SHA-256 hash| POSTGRES
    UPLOAD_API -->|Private binary| FILES
    DOC_API --> POSTGRES
    REVIEW_API --> POSTGRES
    ANALYTICS_API --> POSTGRES

    PARSER_API -->|Create background task| QUEUE
    PARSER_API -->|Poll stage and percentage| POSTGRES
    BATCH_UI -.->|Poll every 2 seconds| PARSER_API
    DOC_UI -.->|Poll while processing| PARSER_API

    OCR --> FILES
    OCR --> GEMINI
    OCR --> TESSERACT
    CLASSIFY --> GEMINI
    PARSE --> GEMINI
    RICH --> PYMUPDF
    RICH --> OPENCV
    SAVE --> POSTGRES

    REPORT_API -->|Latest approved report| POSTGRES
    REPORT_API --> PDF
    REPORT_API --> XLSX
    REPORT_API --> CSV
    REPORT_UI -->|Authenticated download| REPORT_API

    classDef frontend fill:#312e81,stroke:#818cf8,color:#fff
    classDef backend fill:#0f3d3e,stroke:#2dd4bf,color:#fff
    classDef worker fill:#4c1d95,stroke:#c4b5fd,color:#fff
    classDef data fill:#422006,stroke:#fbbf24,color:#fff
    classDef external fill:#172554,stroke:#60a5fa,color:#fff
    classDef output fill:#052e16,stroke:#4ade80,color:#fff

    class AUTH_UI,DOC_UI,BATCH_UI,REVIEW_UI,DASH_UI,REPORT_UI,HTTP frontend
    class CORS,SECURITY,AUTH_API,UPLOAD_API,DOC_API,PARSER_API,REVIEW_API,REPORT_API,ANALYTICS_API backend
    class QUEUE,OCR,CLASSIFY,PARSE,VALIDATE,RICH,SAVE,COMPLETE worker
    class POSTGRES,FILES data
    class GEMINI,TESSERACT,PYMUPDF,OPENCV external
    class PDF,XLSX,CSV output
```

## Processing sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as React Frontend
    participant API as FastAPI
    participant DB as PostgreSQL
    participant BG as Background Task
    participant FS as Private Storage
    participant AI as OCR / AI Provider

    User->>UI: Select one or multiple files
    UI->>API: POST /upload or /upload/batch
    API->>FS: Store private file
    API->>DB: Create Uploaded document
    API-->>UI: Document IDs

    User->>UI: Process or Bulk parse
    UI->>API: POST /parser/process or /parser/bulk
    API->>DB: Status=Processing, stage=Queued, progress=0
    API-->>UI: 200 Accepted immediately
    API-)BG: Start task with independent DB session

    loop OCR, classify, parse, validate, enrich
        BG->>DB: Persist stage and progress
        BG->>FS: Read document
        BG->>AI: Extract/classify data
        UI->>API: GET /parser/result/{id}
        API->>DB: Read current state
        API-->>UI: Stage, progress and status
    end

    BG->>DB: Save fields, confidence, validation and rich content
    BG->>DB: Status=Parsed/Review Pending, progress=100
    User->>UI: Edit and approve
    UI->>API: PUT fields / POST approve
    API->>DB: Save latest approved values and reviewer
    User->>UI: Export report
    UI->>API: GET PDF/XLSX/CSV export
    API-->>UI: Approved report download
```

## Deployment mapping

```mermaid
flowchart LR
    BROWSER[Browser]
    VERCEL["Vercel or Nginx<br/>React static assets"]
    SERVICE["Render / Railway / Docker<br/>FastAPI service"]
    CLOUD_DB[("Managed PostgreSQL<br/>Neon / Supabase / Railway")]
    VOLUME[("Persistent volume<br/>or future S3 storage")]
    PROVIDER[Gemini API]

    BROWSER -->|HTTPS| VERCEL
    BROWSER -->|HTTPS API + JWT| SERVICE
    SERVICE -->|TLS SQL| CLOUD_DB
    SERVICE --> VOLUME
    SERVICE -->|HTTPS| PROVIDER
```

FastAPI `BackgroundTasks` provides immediate responses without an additional broker, but jobs are tied to the backend process. A production-scale evolution would replace this boundary with Celery/RQ workers and Redis while retaining the same persisted progress and polling contract.
