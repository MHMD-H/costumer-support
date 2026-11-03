"""Minimal subprocess entry point for bounded document parsing."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from typing import Any


_WINDOWS_JOB_HANDLE: int | None = None


class _InvalidDocumentError(Exception):
    pass


class _ResourceLimitError(Exception):
    pass


def _install_memory_limit(limit: int) -> None:
    if limit <= 0:
        raise RuntimeError("Invalid parser memory limit")
    if os.name == "nt":
        _install_windows_job_limit(limit)
        return
    try:
        import resource
    except ImportError as exc:
        raise RuntimeError("Memory limits are unsupported on this platform") from exc
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _install_windows_job_limit(limit: int) -> None:
    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = 0x00000100 | 0x00002000
    info.ProcessMemoryLimit = limit
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    global _WINDOWS_JOB_HANDLE
    _WINDOWS_JOB_HANDLE = int(job)


def _safe_metadata(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if depth >= 5:
        return str(value)
    if isinstance(value, dict):
        return {str(key): _safe_metadata(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_metadata(item, depth=depth + 1) for item in value]
    return str(value)


def _extract(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path)
    if not path.is_file():
        return {"ok": False, "error": "invalid_document"}
    size = path.stat().st_size
    if size <= 0:
        return {"ok": False, "error": "invalid_document"}
    if size > args.max_input_bytes:
        raise _ResourceLimitError
    if args.source_type == "pdf":
        from langchain_community.document_loaders.pdf import PyPDFLoader
        from pypdf.errors import PdfReadError
        loader = PyPDFLoader(str(path))
        content_errors = (PdfReadError, ValueError, KeyError, EOFError, UnicodeError)
    elif args.source_type == "docx":
        from langchain_community.document_loaders.word_document import Docx2txtLoader
        from xml.etree.ElementTree import ParseError
        from xml.parsers.expat import ExpatError
        from zipfile import BadZipFile
        from zlib import error as ZlibError
        loader = Docx2txtLoader(str(path))
        content_errors = (
            BadZipFile, ParseError, ExpatError, ZlibError, ValueError, KeyError,
            EOFError, UnicodeError,
        )
    else:
        raise RuntimeError("Unsupported parser source type")
    try:
        documents = loader.load()
    except content_errors as exc:
        raise _InvalidDocumentError from exc
    total = 0
    rows = []
    for document in documents:
        total += len(document.page_content)
        if total > args.max_extracted_characters:
            raise _ResourceLimitError
        rows.append({
            "page_content": document.page_content,
            "metadata": _safe_metadata(document.metadata),
        })
    return {"ok": True, "documents": rows}


def _validate_pdf(args: argparse.Namespace) -> dict[str, Any]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    data = _read_input(args)
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted or not reader.pages or len(reader.pages) > args.max_pages:
            raise _InvalidDocumentError
    except (PdfReadError, ValueError, KeyError, EOFError, UnicodeError) as exc:
        raise _InvalidDocumentError from exc
    return {"ok": True}


def _validate_docx(args: argparse.Namespace) -> dict[str, Any]:
    from xml.etree import ElementTree
    from zipfile import BadZipFile, ZipFile
    from zlib import error as ZlibError

    data = _read_input(args)
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024:
                raise _ResourceLimitError
            if "[Content_Types].xml" not in archive.namelist() or "word/document.xml" not in archive.namelist():
                raise _InvalidDocumentError
            if archive.testzip() is not None:
                raise _InvalidDocumentError
            content_types = archive.read("[Content_Types].xml")
            document_xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in content_types.upper() or b"<!DOCTYPE" in document_xml.upper():
                raise _InvalidDocumentError
            if ElementTree.fromstring(content_types).tag != "{http://schemas.openxmlformats.org/package/2006/content-types}Types":
                raise _InvalidDocumentError
            if ElementTree.fromstring(document_xml).tag != "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document":
                raise _InvalidDocumentError
    except _ResourceLimitError:
        raise
    except _InvalidDocumentError:
        raise
    except (
        BadZipFile, ElementTree.ParseError, ZlibError, ValueError, KeyError,
        EOFError, UnicodeError, RuntimeError, NotImplementedError,
    ) as exc:
        raise _InvalidDocumentError from exc
    return {"ok": True}


def _read_input(args: argparse.Namespace) -> bytes:
    data = sys.stdin.buffer.read(args.max_input_bytes + 1)
    if len(data) > args.max_input_bytes:
        raise _ResourceLimitError
    if not data:
        raise _InvalidDocumentError
    return data


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("operation", choices=("extract", "validate_pdf", "validate_docx"))
    parser.add_argument("--memory-limit-bytes", type=int, required=True)
    parser.add_argument("--max-output-bytes", type=int, required=True)
    parser.add_argument("--max-extracted-characters", type=int, required=True)
    parser.add_argument("--max-input-bytes", type=int, required=True)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--source-type", choices=("pdf", "docx"))
    parser.add_argument("--path")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        _install_memory_limit(args.memory_limit_bytes)
    except Exception:
        payload = {"ok": False, "error": "internal"}
    else:
        try:
            if args.operation == "extract":
                payload = _extract(args)
            elif args.operation == "validate_pdf":
                payload = _validate_pdf(args)
            else:
                payload = _validate_docx(args)
        except MemoryError:
            payload = {"ok": False, "error": "resource_limit"}
        except _ResourceLimitError:
            payload = {"ok": False, "error": "resource_limit"}
        except _InvalidDocumentError:
            payload = {"ok": False, "error": "invalid_document"}
        except Exception:
            payload = {"ok": False, "error": "internal"}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > args.max_output_bytes:
        encoded = b'{"ok":false,"error":"resource_limit"}'
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
