# AI Financial Document Parser

## Project Overview

AI Financial Document Parser is a full-stack OCR workflow for uploading financial documents, extracting structured data, validating important fields, manually reviewing results, and exporting approved reports. It supports Bank Statements, Invoices, Salary Slips, GST Returns, ITRs, Balance Sheets, and Profit & Loss statements.

The application includes role-aware Admin/Analyst access, duplicate-file detection, asynchronous polling-based processing progress, batch upload and bulk parsing, OCR and AI classification, per-field confidence and validation, table/signature/QR extraction, approval/rejection workflows, audit logs, dashboard analytics, document search/filtering, and PDF/XLSX/CSV report exports.

## Tech Stack

- Frontend: React 19, Vite, React Router, Axios, Tailwind CSS, Recharts
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, JWT bearer authentication
- Database: PostgreSQL (recommended); SQLite is supported for a basic local demo
- OCR/AI: Google Gemini or local Tesseract; PyMuPDF renders PDF pages
- Rich extraction: PyMuPDF table detection and OpenCV QR/signature-region detection
- Background processing: FastAPI BackgroundTasks with persisted polling progress
- Reports: ReportLab PDF, Open XML XLSX generation, standard-library CSV
- Deployment: Docker, Docker Compose, Vercel, Render, Railway

## Installation Steps

### Local installation

Prerequisites: Python 3.11+, Node.js 20+, PostgreSQL 15+, and optionally Tesseract OCR.

1. Clone the repository and enter it:

   ```bash
   git clone <repository-url>
   cd ocr
   ```

2. Configure and start the backend:

   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   alembic upgrade head
   python seed_users.py
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. In a second terminal, configure and start the frontend:

   ```bash
   cd frontend
   npm ci
   cp .env.example .env
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

4. Open `http://127.0.0.1:5173`. Seed credentials are `admin@example.com` / `password123` and `analyst@example.com` / `password123`. Change these outside local development.

### Processing workflow

1. Upload one document or a batch of up to 20 documents.
2. Start an individual parse or use the **Bulk parse** action.
3. The API returns immediately while FastAPI processes documents in background worker threads with independent database sessions.
4. The frontend polls `/api/v1/parser/result/{document_id}` and displays the persisted processing stage and percentage.
5. Parsing stores extracted fields, 0–100 confidence scores, validation results, tables, candidate signature regions, and decoded QR values.
6. An Admin or owning Analyst reviews the result, edits fields if needed, and approves or rejects it.
7. Approved data can be exported as PDF, XLSX, or CSV.

### Docker installation

1. Copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY` and `GEMINI_API_KEY`.
2. Run:

   ```bash
   docker compose up --build
   docker compose exec backend python seed_users.py
   ```

3. Open the frontend at `http://127.0.0.1:5173` and Swagger at `http://127.0.0.1:8000/docs`.

## Environment Variables

Backend variables are documented in `backend/.env.example`:

| Variable | Required | Description |
|---|---:|---|
| `PROJECT_NAME` | No | FastAPI application name |
| `API_V1_STR` | No | API prefix; default `/api/v1` |
| `DATABASE_URL` | Yes | SQLAlchemy PostgreSQL or SQLite URL |
| `SECRET_KEY` | Yes | Long random JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT lifetime |
| `FRONTEND_ORIGIN` | Yes | Exact browser origin allowed by CORS |
| `UPLOAD_DIR` | No | Private uploaded-file directory |
| `MAX_UPLOAD_SIZE_MB` | No | Upload limit; default 25 MB |
| `MAX_BATCH_SIZE` | No | Maximum files accepted by one batch request; default 20 |
| `OCR_PROVIDER` | Yes | `gemini` or `tesseract` |
| `AI_PROVIDER` | Yes | Classifier provider; currently Gemini is the production path |
| `GEMINI_API_KEY` | For Gemini | Google Gemini API key |

Frontend variables are documented in `frontend/.env.example`:

| Variable | Required | Description |
|---|---:|---|
| `VITE_API_BASE_URL` | Yes | Public backend API base, including `/api/v1` |

Never commit `.env` files. Vite variables are embedded during build and must not contain secrets.

For local development only, configuring either `http://127.0.0.1:5173` or `http://localhost:5173` permits both loopback aliases because browsers treat them as separate origins. Non-local deployments permit only the exact configured origin.

## Folder Structure

```text
ocr/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # Settings, DB and security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── parsers/          # Document-specific parsers
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # OCR, validation, reports and business logic
│   │   └── utils/            # Audit helpers
│   ├── tests/                # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/components/       # Shared React components
│   ├── src/context/          # Authentication context
│   ├── src/pages/            # Application pages
│   ├── src/services/         # Axios API client
│   ├── Dockerfile
│   └── vercel.json
├── docs/                     # Architecture, schema and API reference
└── docker-compose.yml
```

## API Documentation

FastAPI generates interactive documentation from the running application:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`

The checked-in endpoint reference is [docs/api.md](docs/api.md). Except for registration and login, endpoints require `Authorization: Bearer <token>`. Authorization is additionally scoped by role and document ownership.

Bonus endpoints and result fields:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/upload/batch` | Upload up to `MAX_BATCH_SIZE` files using repeated multipart `files` fields |
| `POST` | `/api/v1/parser/bulk` | Queue up to 20 authorized document IDs with `{"document_ids":[...]}` |
| `GET` | `/api/v1/parser/result/{document_id}` | Poll progress, confidences, and rich extraction results |

Confidence data is stored at `parsed_data.field_confidences`. Rich results are stored at `parsed_data.rich_content.tables`, `parsed_data.rich_content.signatures`, and `parsed_data.rich_content.qr_codes`.

## Deployment Guide

### Frontend on Vercel

Import the repository, set the Root Directory to `frontend`, use `npm run build`, and set the output directory to `dist`. Configure `VITE_API_BASE_URL=https://<backend-host>/api/v1`. `frontend/vercel.json` supplies SPA routing.

### Backend on Render

Use `render.yaml`, attach PostgreSQL and a persistent disk for `/app/uploads`, then set `SECRET_KEY`, `GEMINI_API_KEY`, and `FRONTEND_ORIGIN`. The start command runs migrations before Uvicorn.

### Backend on Railway

Deploy with the repository root set to `backend` and the included `railway.json`. Add PostgreSQL, set `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, `FRONTEND_ORIGIN`, and `UPLOAD_DIR=/app/uploads`. Railway ephemeral storage is not suitable for permanent uploads without a volume.

### Managed PostgreSQL

Neon, Supabase, Render, and Railway PostgreSQL are supported through their standard SQLAlchemy URL. Convert `postgres://` to `postgresql://` if necessary, require SSL according to the provider, set `DATABASE_URL`, and run `alembic upgrade head`. MongoDB Atlas is not compatible because the project uses SQLAlchemy relational models and Alembic migrations.

For production, place uploaded files on a persistent disk or migrate storage to S3-compatible object storage. Set `FRONTEND_ORIGIN` to the exact Vercel/custom domain and use HTTPS for both applications.

## Assumptions

- One parsed report represents the latest state of a document.
- Approved exports must have a manually approved report and recorded reviewer.
- Admins can access all documents; Analysts access documents they uploaded.
- PostgreSQL is the production database.
- Uploaded documents are private and are not mounted as public static assets.
- Gemini credentials and internet access are available when Gemini is selected.
- Background jobs run in the same application instance and use independent SQLAlchemy sessions.
- Confidence scores express extraction/validation confidence and are not calibrated financial-risk scores.
- Signature results indicate visual candidate regions only.

## Known Limitations

- OCR and parsing run through FastAPI background tasks rather than a durable distributed queue.
- Background tasks are lost if the backend process restarts, and bulk tasks execute within the application process.
- Most API/database access remains synchronous, although background jobs no longer reuse request-scoped sessions.
- Polling is used instead of WebSockets, producing periodic API traffic while documents process.
- Confidence scores are deterministic heuristics based on validation and OCR evidence, not probabilities from a trained confidence model.
- Signature detection is heuristic and indicates candidate regions, not cryptographic signature authenticity.
- Table extraction quality depends on PDF layout; scanned tables may require a specialized vision model.
- Public self-registration currently permits selecting a role and should be restricted before an untrusted production launch.
- The backend requires `SECRET_KEY` from the environment, but production deployments should additionally use a managed secret store and rotation policy.
- Admin user-management UI/API, account deactivation, global toast notifications, and a global error boundary are not implemented.
- Uploads use local/persistent-disk storage rather than object storage.
- Filename-based type inference is used only as a filter fallback before parsing.
- Search over JSON fields is performed in application code and may not scale to large datasets.
- Automated browser E2E tests are not yet included.

## Future Improvements

- Add Admin-only user management and active-account enforcement.
- Move OCR/parsing to Celery, RQ, or a managed queue with independent DB sessions.
- Add WebSocket or Server-Sent Events progress delivery when moving to distributed workers.
- Add streaming upload limits, MIME-signature validation, atomic concurrent-upload handling, and S3 storage.
- Add document orientation detection and automatic rotation.
- Add specialized scanned-table models, signature classification, and broader barcode support.
- Calibrate confidence scores against a labeled document-validation dataset.
- Move JSON search to indexed PostgreSQL JSONB expressions or a search service.
- Add global error boundaries, toast notifications, standardized skeletons, and full responsive accessibility tests.
- Add Playwright E2E coverage for Admin and Analyst workflows.
- Add observability, rate limiting, token refresh/revocation, and production secret validation.
