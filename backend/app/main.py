import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analyses import router as analyses_router
from app.api.repositories import router as repositories_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="CodeImpact API — Evidence-based codebase intelligence and safe refactoring.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Standard Error Envelope Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        # Strip ValueError prefix if present
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        error_messages.append(f"{loc}: {msg}" if loc else msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(error_messages) if error_messages else "Request validation failed.",
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    error_code = getattr(exc, "code", "HTTP_ERROR")
    if error_code == "HTTP_ERROR":
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "BAD_REQUEST"
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            error_code = "AI_SERVICE_UNAVAILABLE"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "request_id": request_id,
            }
        },
    )


# Health Check Endpoint
@app.get("/health", tags=["health"], summary="Health check probe")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Register API Routers
app.include_router(repositories_router, prefix=settings.api_prefix)
app.include_router(analyses_router, prefix=settings.api_prefix)
