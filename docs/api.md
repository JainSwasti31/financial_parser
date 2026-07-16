# API Reference

Base path: `/api/v1`. Swagger UI at `/docs`, ReDoc at `/redoc`, and the OpenAPI document at `/api/v1/openapi.json` are generated from these same routes.

All protected endpoints require:

```http
Authorization: Bearer <access-token>
```

Errors use the application envelope `{"error":{"code":<status>,"message":"..."}}`.

## Authentication

| Method | Path | Authentication | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a user |
| POST | `/auth/login` | Public | Obtain a bearer JWT |
| GET | `/auth/profile` | Bearer | Current user profile |

Login body: `{"email":"admin@example.com","password":"password123"}`.

## Uploads and Documents

| Method | Path | Description |
|---|---|---|
| POST | `/upload/` | Upload PDF/JPG/JPEG/PNG as multipart field `file` |
| POST | `/upload/batch` | Upload up to 20 documents as repeated multipart field `files` |
| GET | `/documents/` | Paginated, searchable, filterable document list |
| GET | `/documents/{document_id}` | Document metadata |
| DELETE | `/documents/{document_id}` | Delete document; Admin only |

`GET /documents/` query parameters:

- `page`, `page_size`
- `search`: PAN, GST/GSTIN, invoice/account number, employee/company name, filename, or upload date
- `document_type`: classified type or original file type
- `status`: `Uploaded`, `Processing`, `Parsed`, `Validation Failed`, `Review Pending`, `Approved`, or `Rejected`
- `uploaded_by`: Admin only
- `date_from`, `date_to`: ISO dates
- `processing_time_min`, `processing_time_max`: seconds

## Parsing

| Method | Path | Description |
|---|---|---|
| POST | `/parser/process/{document_id}` | Start OCR, classification, parsing, and validation |
| POST | `/parser/bulk` | Queue up to 20 authorized document IDs for processing |
| POST | `/parser/reprocess/{document_id}` | Reset and run the pipeline again |
| GET | `/parser/result/{document_id}` | Poll document status and parsed result |

Bulk process body: `{"document_ids":[1,2,3]}`. Poll results include `processing_progress` (0–100), `processing_stage`, field confidence scores, and rich extraction results.

## Manual Review

| Method | Path | Description |
|---|---|---|
| GET | `/review/{document_id}` | Parsed fields and per-field validations |
| PUT | `/review/{document_id}/fields` | Merge edited fields and revalidate |
| POST | `/review/{document_id}/approve` | Approve; optional `remarks` body field |
| POST | `/review/{document_id}/reject` | Reject; `remarks` is required |

Admin and Analyst roles may review documents they are authorized to access. Approval records `reviewed_by` and unlocks report exports.

## Reports and Exports

| Method | Path | Description |
|---|---|---|
| GET | `/reports/` | Paginated parsed reports |
| GET | `/reports/{report_id}` | Report detail |
| GET | `/reports/export/pdf/{report_id}` | Download approved PDF report |
| GET | `/reports/export/excel/{report_id}` | Download approved XLSX report |
| GET | `/reports/export/csv/{report_id}` | Download approved CSV report |

Exports return HTTP `409` until parsing and manual approval are complete. Successful exports add a `Report Generated` audit entry.

## Dashboard and Audit Logs

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/` | Live metrics, type counts, upload series, and recent activity |
| GET | `/logs/` | Paginated audit logs |

Dashboard query parameters are `days` (1–365) and `months` (1–36). Log filters are `document_id` and partial `action`.

## Authorization Rules

- Admins can list all documents, reports, and audit activity.
- Analysts are scoped to documents they uploaded.
- Document deletion is Admin-only.
- Exports require a genuinely approved report, approved document status, and reviewer identity.

This file mirrors the routes present in the generated OpenAPI schema at release time. Swagger remains the authoritative request/response schema reference.
