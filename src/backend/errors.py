"""Consistent API error envelope. Messages never include transcripts or tokens."""

from __future__ import annotations

import secrets
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def new_request_id() -> str:
    return "req_" + secrets.token_hex(6)


def error_body(
    code: str,
    message: str,
    *,
    field_errors: Optional[list[dict[str, str]]] = None,
    request_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "fieldErrors": field_errors or [],
            "requestId": request_id or new_request_id(),
        }
    }
    if extra:
        payload["error"].update(extra)
    return payload


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field_errors: Optional[list[dict[str, str]]] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field_errors = field_errors or []
        self.extra = extra or {}


def request_id_from(request: Request) -> str:
    existing = request.headers.get("x-request-id")
    if existing and existing.strip():
        return existing.strip()[:64]
    return new_request_id()


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    rid = request_id_from(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, field_errors=exc.field_errors, request_id=rid, extra=exc.extra),
        headers={"X-Request-Id": rid},
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    rid = request_id_from(request)
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    if exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
    message = "Not found." if exc.status_code == 404 else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, message, request_id=rid),
        headers={"X-Request-Id": rid},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = request_id_from(request)
    fields = []
    for err in exc.errors():
        loc = "/".join(str(part) for part in err.get("loc", ()) if part != "body")
        fields.append({"path": "/" + loc if loc else "/", "message": "Invalid request."})
    return JSONResponse(
        status_code=400,
        content=error_body("MALFORMED_JSON", "The request body is not valid JSON.", field_errors=fields, request_id=rid),
        headers={"X-Request-Id": rid},
    )
