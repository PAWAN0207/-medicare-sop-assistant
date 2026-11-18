"""REST API. One endpoint for staff, consistent error envelope, correlation id on every response."""

from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import Settings
from ..container import build_service
from ..errors import AppError
from ..logging_setup import request_id_var, setup_logging

log = logging.getLogger("sopassist.api")


# --------------------------------------------------
# Request / Response Models
# --------------------------------------------------

class AskRequest(BaseModel):
    user_id: str = Field(
        ...,
        examples=["U2001"],
        description="Staff id from staff_users.csv",
    )
    question: str = Field(
        ...,
        examples=["What is the procedure for a needle-stick injury?"],
    )


class CitationOut(BaseModel):
    sop_id: str
    version: str
    title: str
    section: str
    section_title: str
    page: int


class AskResponse(BaseModel):
    answer: str
    refused: bool = Field(
        description="true when the SOPs available to this user do not cover the question"
    )
    reason: str = Field(
        "",
        description="no_relevant_sop | llm_not_covered | ungrounded (only when refused)",
    )
    citations: list[CitationOut]
    cached: bool
    index_generation: int
    request_id: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


# --------------------------------------------------
# Consistent Error Response
# --------------------------------------------------

def _err(
    status: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:

    request_id = request_id_var.get()

    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or {},
            }
        },
        headers={"X-Request-ID": request_id},
    )


# --------------------------------------------------
# Application Factory
# --------------------------------------------------

def create_app(
    settings: Settings | None = None,
    service=None,
) -> FastAPI:

    settings = settings or Settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="MediCare SOP Assistant",
        version="1.0.0",
        description=(
            "Answers clinic staff questions from current SOPs, "
            "with citations and role-based access."
        ),
    )

    # --------------------------------------------------
    # CORS Configuration
    # --------------------------------------------------

    # Local development works with localhost:5173.
    # For deployment, set CORS_ORIGINS in backend environment variables.
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
    )

    # Build backend service
    svc = service or build_service(settings)

    # --------------------------------------------------
    # Correlation ID Middleware
    # --------------------------------------------------

    @app.middleware("http")
    async def correlation(request: Request, call_next):

        request_id = (
            request.headers.get("X-Request-ID")
            or uuid.uuid4().hex[:16]
        )

        request_id_var.set(request_id)

        start_time = time.perf_counter()

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            1,
        )

        log.info(
            "request",
            extra={
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )

        return response

    # --------------------------------------------------
    # Application Error Handler
    # --------------------------------------------------

    @app.exception_handler(AppError)
    async def app_error(
        request: Request,
        error: AppError,
    ):

        if error.status >= 500:
            log.error(
                "app error",
                extra={"code": error.code},
            )

        return _err(
            error.status,
            error.code,
            str(error),
            error.extra,
        )

    # --------------------------------------------------
    # Request Validation Error Handler
    # --------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation(
        request: Request,
        error: RequestValidationError,
    ):

        fields = [
            ".".join(map(str, item["loc"][1:]))
            for item in error.errors()
        ]

        return _err(
            422,
            "INVALID_REQUEST",
            "Request body is invalid",
            {"fields": fields},
        )

    # --------------------------------------------------
    # Unexpected Error Handler
    # --------------------------------------------------

    @app.exception_handler(Exception)
    async def unexpected(
        request: Request,
        error: Exception,
    ):

        log.exception("unhandled error")

        return _err(
            500,
            "INTERNAL",
            "Unexpected error",
        )

    # --------------------------------------------------
    # Ask Endpoint
    # --------------------------------------------------

    @app.post(
        "/v1/ask",
        response_model=AskResponse,
        tags=["qa"],
        responses={
            403: {
                "model": ErrorResponse,
                "description": "UNKNOWN_USER",
            },
            422: {
                "model": ErrorResponse,
                "description": "INVALID_REQUEST | PATIENT_DATA_DETECTED",
            },
            502: {
                "model": ErrorResponse,
                "description": "UPSTREAM_ERROR",
            },
            503: {
                "model": ErrorResponse,
                "description": "INDEX_EMPTY",
            },
            504: {
                "model": ErrorResponse,
                "description": "UPSTREAM_TIMEOUT",
            },
        },
    )
    def ask(body: AskRequest) -> AskResponse:

        answer, cached = svc.ask(
            body.user_id,
            body.question,
        )

        return AskResponse(
            answer=answer.answer,
            refused=answer.refused,
            reason=answer.reason,
            citations=[
                CitationOut(**citation.__dict__)
                for citation in answer.citations
            ],
            cached=cached,
            index_generation=answer.index_generation,
            request_id=request_id_var.get(),
        )

    # --------------------------------------------------
    # Health Check Endpoint
    # --------------------------------------------------

    @app.get(
        "/healthz",
        tags=["ops"],
    )
    def healthz():

        return {
            "status": "ok",
            "index_generation": svc.store.generation(),
            "documents": len(svc.store.documents()),
        }

    return app