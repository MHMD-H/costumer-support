"""Killable, resource-bounded subprocess boundary for untrusted file parsers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any, Literal

from langchain_core.documents import Document


PARSER_TIMEOUT_SECONDS = 30.0
PARSER_MEMORY_LIMIT_BYTES = 1024 * 1024 * 1024
PARSER_MAX_OUTPUT_BYTES = 16 * 1024 * 1024
PARSER_MAX_INPUT_BYTES = 5 * 1024 * 1024
PARSER_MAX_EXTRACTED_CHARACTERS = 2_000_000


class IsolatedParserError(RuntimeError):
    """Base error for the isolated parser protocol."""


class IsolatedParserInvalidError(IsolatedParserError, ValueError):
    """The parser rejected malformed or unsupported document content."""


class IsolatedParserResourceError(IsolatedParserError):
    """The parser exceeded its time, memory, input, or output budget."""


class IsolatedParserInternalError(IsolatedParserError):
    """The parser boundary could not be established safely."""


def load_isolated_file(
    path: str | Path,
    *,
    source_type: Literal["pdf", "docx"],
    max_bytes: int,
) -> list[Document]:
    payload = _run_parser(
        "extract",
        source_type=source_type,
        path=Path(path),
        max_bytes=max_bytes,
    )
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list):
        raise IsolatedParserInternalError("Document parser returned an invalid response.")
    documents: list[Document] = []
    total = 0
    for item in raw_documents:
        if not isinstance(item, dict):
            raise IsolatedParserInternalError("Document parser returned an invalid response.")
        content = item.get("page_content")
        metadata = item.get("metadata")
        if not isinstance(content, str) or not isinstance(metadata, dict):
            raise IsolatedParserInternalError("Document parser returned an invalid response.")
        total += len(content)
        if total > PARSER_MAX_EXTRACTED_CHARACTERS:
            raise IsolatedParserResourceError("Extracted document content exceeds the parser limit.")
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def validate_pdf_bytes(data: bytes, *, max_pages: int) -> None:
    if len(data) > PARSER_MAX_INPUT_BYTES:
        raise IsolatedParserResourceError("PDF input exceeds the parser limit.")
    _run_parser("validate_pdf", input_bytes=data, max_pages=max_pages)


def validate_docx_bytes(data: bytes) -> None:
    if len(data) > PARSER_MAX_INPUT_BYTES:
        raise IsolatedParserResourceError("DOCX input exceeds the parser limit.")
    _run_parser("validate_docx", input_bytes=data)


def _run_parser(
    operation: Literal["extract", "validate_pdf", "validate_docx"],
    *,
    source_type: Literal["pdf", "docx"] | None = None,
    path: Path | None = None,
    max_bytes: int = PARSER_MAX_INPUT_BYTES,
    max_pages: int = 500,
    input_bytes: bytes | None = None,
) -> dict[str, Any]:
    command = _parser_command(
        operation,
        source_type=source_type,
        path=path,
        max_bytes=max_bytes,
        max_pages=max_pages,
    )
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
    except OSError:
        raise IsolatedParserInternalError(
            "Document parser could not start safely."
        ) from None
    try:
        output, _ = process.communicate(input=input_bytes, timeout=PARSER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _terminate_parser(process)
        raise IsolatedParserResourceError("Document parser exceeded its time limit.") from None

    if len(output) > PARSER_MAX_OUTPUT_BYTES:
        raise IsolatedParserResourceError("Document parser exceeded its output limit.")
    if not output:
        if process.returncode:
            raise IsolatedParserResourceError("Document parser exceeded its resource limit.")
        raise IsolatedParserInternalError("Document parser returned no response.")
    try:
        payload = json.loads(output)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise IsolatedParserInternalError("Document parser returned an invalid response.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        raise IsolatedParserInternalError("Document parser returned an invalid response.")
    if payload["ok"]:
        if process.returncode != 0:
            raise IsolatedParserInternalError("Document parser exited unexpectedly.")
        return payload

    kind = payload.get("error")
    if kind == "invalid_document":
        raise IsolatedParserInvalidError("Document content is invalid.")
    if kind == "resource_limit":
        raise IsolatedParserResourceError("Document parser exceeded its resource limit.")
    raise IsolatedParserInternalError("Document parser could not start safely.")


def _parser_command(
    operation: str,
    *,
    source_type: str | None,
    path: Path | None,
    max_bytes: int,
    max_pages: int,
) -> list[str]:
    worker = Path(__file__).with_name("_worker.py")
    command = [
        sys.executable,
        str(worker),
        operation,
        "--memory-limit-bytes",
        str(PARSER_MEMORY_LIMIT_BYTES),
        "--max-output-bytes",
        str(PARSER_MAX_OUTPUT_BYTES),
        "--max-extracted-characters",
        str(PARSER_MAX_EXTRACTED_CHARACTERS),
    ]
    if operation == "extract":
        if source_type not in {"pdf", "docx"} or path is None:
            raise ValueError("An allowed source type and path are required")
        command.extend([
            "--source-type",
            source_type,
            "--path",
            str(path),
            "--max-input-bytes",
            str(max_bytes),
        ])
    elif operation in {"validate_pdf", "validate_docx"}:
        command.extend([
            "--max-input-bytes",
            str(PARSER_MAX_INPUT_BYTES),
            "--max-pages",
            str(max_pages),
        ])
    else:
        raise ValueError("Unsupported parser operation")
    return command


def _terminate_parser(process: subprocess.Popen[bytes]) -> None:
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        process.kill()
    finally:
        process.communicate()
