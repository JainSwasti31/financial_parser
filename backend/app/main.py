from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from app.core.config import settings
from app.api.auth import router as auth_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Browsers treat localhost and 127.0.0.1 as different origins. Permit both
# aliases only when the configured frontend is local; production remains exact.
frontend_origin = settings.FRONTEND_ORIGIN.rstrip("/")
allowed_origins = [frontend_origin]
local_origins = {"http://localhost:5173", "http://127.0.0.1:5173"}
if frontend_origin in local_origins:
    allowed_origins = sorted(local_origins)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Consistent error format: { "error": { "code": ..., "message": ... } }
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg") if errors else "Validation Error"
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": msg, "details": errors}},
    )

@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )

@app.get("/")
@app.head("/")
async def root():
    return {"message": "Welcome to the AI Financial Document Parser API"}

from app.api.upload import router as upload_router
from app.api.documents import router as documents_router
from app.api.parser import router as parser_router
from app.api.review import router as review_router
from app.api.reports import router as reports_router
from app.api.dashboard import router as dashboard_router
from app.api.logs import router as logs_router
from app.api.users import router as users_router

# Register Routers
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(upload_router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])
app.include_router(documents_router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"])
app.include_router(parser_router, prefix=f"{settings.API_V1_STR}/parser", tags=["parser"])
app.include_router(review_router, prefix=f"{settings.API_V1_STR}/review", tags=["review"])
app.include_router(reports_router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])
app.include_router(dashboard_router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(logs_router, prefix=f"{settings.API_V1_STR}/logs", tags=["logs"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
