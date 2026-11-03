"""Bounded validation and private local staging for document uploads."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from os import getenv
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from rag.parsing.isolated import (
    IsolatedParserInternalError,
    IsolatedParserInvalidError,
    IsolatedParserResourceError,
    validate_docx_bytes,
    validate_pdf_bytes,
)


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_MULTIPART_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
MAX_PDF_PAGES = 500
READ_BYTES = 64 * 1024
ALLOWED_TYPES = {"txt", "pdf", "docx"}


def _reject(code: int, message: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"error": "invalid_upload", "message": message})


async def read_validated_upload(file: UploadFile) -> tuple[str, str, bytes]:
    raw_name = file.filename or ""
    filename = PurePosixPath(raw_name.replace("\\", "/")).name
    if not filename or filename in {".", ".."} or len(filename) > 255 or any(ord(c) < 32 for c in filename):
        raise _reject(status.HTTP_400_BAD_REQUEST, "File name is invalid.")
    document_type = Path(filename).suffix.lower().lstrip(".")
    if document_type not in ALLOWED_TYPES:
        raise _reject(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File type is unsupported.")

    content = bytearray()
    while chunk := await file.read(READ_BYTES):
        if len(content) + len(chunk) > MAX_UPLOAD_BYTES:
            raise _reject(status.HTTP_413_CONTENT_TOO_LARGE, "File exceeds the 5 MB limit.")
        content.extend(chunk)
    if not content:
        raise _reject(status.HTTP_400_BAD_REQUEST, "File is empty.")

    data = bytes(content)
    try:
        if document_type == "txt":
            decoded = data.decode("utf-8-sig")
            if "\x00" in decoded or not decoded.strip():
                raise ValueError
        elif document_type == "pdf":
            if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
                raise ValueError
            await asyncio.to_thread(validate_pdf_bytes, data, max_pages=MAX_PDF_PAGES)
        else:
            if not data.startswith(b"PK\x03\x04"):
                raise ValueError
            await asyncio.to_thread(validate_docx_bytes, data)
    except IsolatedParserInternalError:
        raise
    except (
        UnicodeError, ValueError, EOFError, OSError, KeyError,
        IsolatedParserInvalidError, IsolatedParserResourceError,
    ):
        raise _reject(status.HTTP_400_BAD_REQUEST, "File content is invalid or does not match its type.") from None
    return filename, document_type, data


def upload_path(tenant_id: UUID, document_id: UUID, document_type: str, revision: UUID | None = None) -> Path:
    root = getenv("DOCUMENT_UPLOAD_DIR")
    if not root:
        raise RuntimeError("DOCUMENT_UPLOAD_DIR must be configured for document uploads")
    if document_type not in ALLOWED_TYPES:
        raise ValueError("Unsupported document type")
    suffix = f"-{revision}" if revision else ""
    return Path(root).resolve() / str(tenant_id) / f"{document_id}{suffix}.{document_type}"


def save_upload(tenant_id: UUID, document_id: UUID, document_type: str, content: bytes, revision: UUID | None = None) -> None:
    path = upload_path(tenant_id, document_id, document_type, revision)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as destination:
        destination.write(content)


def remove_upload(tenant_id: UUID, document_id: UUID, document_type: str, revision: UUID | None = None) -> None:
    upload_path(tenant_id, document_id, document_type, revision).unlink(missing_ok=True)


@dataclass(frozen=True)
class DocumentUploadForm:
    file: UploadFile
    title: str | None
    visibility: Literal["internal", "public"] | None


async def get_document_upload_form(request: Request) -> AsyncIterator[DocumentUploadForm]:
    """Parse multipart content only after route authentication dependencies pass."""
    form = await request.form(max_files=1, max_fields=8, max_part_size=MAX_UPLOAD_BYTES)
    try:
        files = form.getlist("file")
        if len(files) != 1 or not isinstance(files[0], StarletteUploadFile):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"error": "validation_error", "message": "Exactly one file is required."},
            )
        title = form.get("title")
        if title is not None and not isinstance(title, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"error": "validation_error", "message": "Title must be text."},
            )
        visibility = form.get("visibility")
        if visibility is not None and visibility not in {"internal", "public"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"error": "validation_error", "message": "Visibility is invalid."},
            )
        yield DocumentUploadForm(
            file=files[0],
            title=title,
            visibility=visibility,
        )
    finally:
        await form.close()


DocumentUploadFormDep = Annotated[DocumentUploadForm, Depends(get_document_upload_form)]


class _UploadBodyTooLarge(Exception):
    pass


class UploadBodyLimitMiddleware:
    """Count upload bytes without reading or retaining the body before authentication."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        document_upload = scope["method"] == "POST" and scope["path"] == "/documents"
        document_replacement = scope["method"] == "PUT" and scope["path"].startswith("/documents/")
        if not (document_upload or document_replacement):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=413,
            content={"error": "invalid_upload", "message": "Upload request exceeds the size limit."},
        )
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        total = 0
        response_started = False

        async def limited_receive():
            nonlocal total
            if declared > MAX_MULTIPART_BYTES:
                raise _UploadBodyTooLarge
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_MULTIPART_BYTES:
                    raise _UploadBodyTooLarge
            return message

        async def tracked_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _UploadBodyTooLarge:
            if response_started:
                raise
            await response(scope, receive, send)
