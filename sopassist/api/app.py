"""REST API. One endpoint for staff, consistent error envelope, correlation id on every response."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import Settings
from ..container import build_service
from ..errors import AppError
from ..logging_setup import request_id_var, setup_logging

log = logging.getLogger("sopassist.api")


class AskRequest(BaseModel):
    user_id: str = Field(..., examples=["U2001"], description="Staff id from staff_users.csv")
    question: str = Field(..., examples=["What is the procedure for a needle-stick injury?"])


class CitationOut(BaseModel):
    sop_id: str
    version: str
    title: str
    section: str
    section_title: str
    page: int


class AskResponse(BaseModel):
    answer: str
    refused: bool = Field(description="true when the SOPs available to this user do not cover the question")
    reason: str = Field("", description="no_relevant_sop | llm_not_covered | ungrounded (only when refused)")
    citations: list[CitationOut]
    cached: bool
    index_generation: int
    request_id: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorBody


def _err(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "request_id": request_id_var.get(), "details": details or {}}},
        headers={"X-Request-ID": request_id_var.get()})


def create_app(settings: Settings | None = None, service=None) -> FastAPI:
    settings = settings or Settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="MediCare SOP Assistant", version="1.0.0",
                  description="Answers clinic staff questions from current SOPs, with citations and role-based access.")
    svc = service or build_service(settings)

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request_id_var.set(rid)
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        log.info("request", extra={"path": request.url.path, "status": response.status_code,
                                   "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
        return response

    @app.exception_handler(AppError)
    async def app_error(_: Request, e: AppError):
        if e.status >= 500:
            log.error("app error", extra={"code": e.code})
        return _err(e.status, e.code, str(e), e.extra)

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, e: RequestValidationError):
        return _err(422, "INVALID_REQUEST", "Request body is invalid",
                    {"fields": [".".join(map(str, x["loc"][1:])) for x in e.errors()]})

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("unhandled error")
        return _err(500, "INTERNAL", "Unexpected error")

    @app.post("/v1/ask", response_model=AskResponse, tags=["qa"],
              responses={403: {"model": ErrorResponse, "description": "UNKNOWN_USER"},
                         422: {"model": ErrorResponse, "description": "INVALID_REQUEST | PATIENT_DATA_DETECTED"},
                         502: {"model": ErrorResponse, "description": "UPSTREAM_ERROR"},
                         503: {"model": ErrorResponse, "description": "INDEX_EMPTY"},
                         504: {"model": ErrorResponse, "description": "UPSTREAM_TIMEOUT"}})
    def ask(body: AskRequest) -> AskResponse:
        ans, cached = svc.ask(body.user_id, body.question)
        return AskResponse(answer=ans.answer, refused=ans.refused, reason=ans.reason,
                           citations=[CitationOut(**c.__dict__) for c in ans.citations], cached=cached,
                           index_generation=ans.index_generation, request_id=request_id_var.get())

    @app.get("/healthz", tags=["ops"])
    def healthz():
        return {"status": "ok", "index_generation": svc.store.generation(), "documents": len(svc.store.documents())}

    return app
