"""Common application exceptions and JSON error handlers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.features.schemas import ErrorDetail, ErrorResponse


def error_response(
    error: str,
    message: str,
    status_code: int,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        details=details or [],
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            return error_response(
                error=str(detail.get("error", "bad_request")),
                message=str(detail.get("message", "Request failed.")),
                status_code=exc.status_code,
                request_id=request.headers.get("x-request-id"),
            )
        return error_response(
            error=_error_code_for_status(exc.status_code),
            message=str(detail),
            status_code=exc.status_code,
            request_id=request.headers.get("x-request-id"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            ErrorDetail(field=".".join(str(part) for part in error["loc"]), message=error["msg"])
            for error in exc.errors()
        ]
        return error_response(
            error="validation_error",
            message="The request body is invalid.",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request.headers.get("x-request-id"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return error_response(
            error="internal_error",
            message="An unexpected error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request.headers.get("x-request-id"),
        )


def _error_code_for_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "payload_too_large",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    }.get(status_code, "bad_request")
