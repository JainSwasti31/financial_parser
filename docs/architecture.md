# Architecture

```mermaid
flowchart LR
    U[Admin / Analyst Browser]

    subgraph FE[React Frontend]
        UI[Pages and Components]
        API[Axios API Client]
        UI --> API
    end

    subgraph BE[FastAPI Backend]
        AUTH[JWT Authentication and RBAC]
        ROUTES[API Routers]
        PIPE[Background OCR / Classification / Parsing]
        RICH[Tables / Signatures / QR]
        VALID[Validation and Manual Review]
        REPORT[Report and Export Services]
        AUDIT[Audit Logging]
        AUTH --> ROUTES
        ROUTES --> PIPE
        PIPE --> RICH
        ROUTES --> VALID
        ROUTES --> REPORT
        ROUTES --> AUDIT
    end

    DB[(PostgreSQL)]
    FILES[(Private File Storage)]
    AI[Gemini OCR / AI]
    TESS[Tesseract OCR]

    U -->|HTTPS| FE
    API -->|Bearer JWT / JSON| AUTH
    ROUTES --> DB
    ROUTES --> FILES
    PIPE --> FILES
    PIPE --> AI
    PIPE --> TESS
    PIPE --> DB
    VALID --> DB
    REPORT --> DB
    AUDIT --> DB
```

Uploads remain private backend files and are never mounted by the frontend or FastAPI as a public directory. In production, private object storage is recommended in place of local disk.
