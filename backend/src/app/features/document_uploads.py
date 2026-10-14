"""Bounded validation and private local staging for document uploads."""

from io import BytesIO
from os import getenv
from pathlib import Path, PurePosixPath
from uuid import UUID
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_MULTIPART_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
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
            reader = PdfReader(BytesIO(data), strict=True)
            if not reader.pages:
                raise ValueError
        else:
            if not data.startswith(b"PK\x03\x04"):
                raise ValueError
            with ZipFile(BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024:
                    raise ValueError
                if "[Content_Types].xml" not in archive.namelist() or "word/document.xml" not in archive.namelist():
                    raise ValueError
                if archive.testzip() is not None:
                    raise ValueError
                content_types = archive.read("[Content_Types].xml")
                document_xml = archive.read("word/document.xml")
                if b"<!DOCTYPE" in content_types.upper() or b"<!DOCTYPE" in document_xml.upper():
                    raise ValueError
                if ElementTree.fromstring(content_types).tag != "{http://schemas.openxmlformats.org/package/2006/content-types}Types":
                    raise ValueError
                if ElementTree.fromstring(document_xml).tag != "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document":
                    raise ValueError
    except (UnicodeError, ValueError, BadZipFile, PdfReadError, ElementTree.ParseError, EOFError, OSError, KeyError):
        raise _reject(status.HTTP_400_BAD_REQUEST, "File content is invalid or does not match its type.") from None
    return filename, document_type, data


def upload_path(tenant_id: UUID, document_id: UUID, document_type: str) -> Path:
    root = getenv("DOCUMENT_UPLOAD_DIR")
    if not root:
        raise RuntimeError("DOCUMENT_UPLOAD_DIR must be configured for document uploads")
    if document_type not in ALLOWED_TYPES:
        raise ValueError("Unsupported document type")
    return Path(root).resolve() / str(tenant_id) / f"{document_id}.{document_type}"


def save_upload(tenant_id: UUID, document_id: UUID, document_type: str, content: bytes) -> None:
    path = upload_path(tenant_id, document_id, document_type)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as destination:
        destination.write(content)


def remove_upload(tenant_id: UUID, document_id: UUID, document_type: str) -> None:
    upload_path(tenant_id, document_id, document_type).unlink(missing_ok=True)


class UploadBodyLimitMiddleware:
    """Reject oversized upload requests before multipart spooling can grow."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/documents" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        from fastapi.responses import JSONResponse

        response = JSONResponse(
            status_code=413,
            content={"error": "invalid_upload", "message": "Upload request exceeds the size limit."},
        )
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > MAX_MULTIPART_BYTES:
            await response(scope, receive, send)
            return

        total = 0
        messages = []
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return
            total += len(message.get("body", b""))
            if total > MAX_MULTIPART_BYTES:
                await response(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)
