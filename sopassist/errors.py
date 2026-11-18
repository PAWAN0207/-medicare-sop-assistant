"""Domain errors. The API layer maps each to one HTTP status + stable error code."""


class AppError(Exception):
    code = "INTERNAL"
    status = 500

    def __init__(self, message: str = "", **extra):
        super().__init__(message or self.code)
        self.extra = extra


class UnknownUser(AppError):
    code, status = "UNKNOWN_USER", 403


class PatientDataDetected(AppError):
    code, status = "PATIENT_DATA_DETECTED", 422


class InvalidRequest(AppError):
    code, status = "INVALID_REQUEST", 422


class IndexEmpty(AppError):
    code, status = "INDEX_EMPTY", 503


class UpstreamTimeout(AppError):
    code, status = "UPSTREAM_TIMEOUT", 504


class UpstreamError(AppError):
    code, status = "UPSTREAM_ERROR", 502


class IngestError(AppError):
    code, status = "INGEST_FAILED", 500
