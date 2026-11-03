from __future__ import annotations

from argparse import Namespace
import json
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter
import pytest

from rag.parsing import isolated
from rag.parsing import _worker


def test_isolated_pdf_validation_accepts_a_well_formed_pdf(tmp_path) -> None:
    path = tmp_path / "policy.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as output:
        writer.write(output)

    isolated.validate_pdf_bytes(path.read_bytes(), max_pages=10)


def test_isolated_docx_extraction_returns_content_and_metadata(tmp_path) -> None:
    path = tmp_path / "policy.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body><w:p><w:r><w:t>Returns policy</w:t></w:r></w:p></w:body>
    </w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)

    documents = isolated.load_isolated_file(path, source_type="docx", max_bytes=1024 * 1024)

    assert documents[0].page_content == "Returns policy"
    assert documents[0].metadata["source"] == str(path)


def test_isolated_docx_validation_accepts_expected_package(tmp_path) -> None:
    path = tmp_path / "policy.docx"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
        )

    isolated.validate_docx_bytes(path.read_bytes())


def test_isolated_docx_validation_rejects_malformed_package() -> None:
    with pytest.raises(isolated.IsolatedParserInvalidError):
        isolated.validate_docx_bytes(b"PK\x03\x04broken archive")


def test_isolated_docx_validation_rejects_unsupported_compression(tmp_path) -> None:
    path = tmp_path / "unsupported.docx"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
        )
    data = bytearray(path.read_bytes())
    for signature, offset in ((b"PK\x03\x04", 8), (b"PK\x01\x02", 10)):
        start = 0
        while (index := data.find(signature, start)) != -1:
            data[index + offset:index + offset + 2] = (99).to_bytes(2, "little")
            start = index + 4

    with pytest.raises(isolated.IsolatedParserInvalidError):
        isolated.validate_docx_bytes(bytes(data))


def test_isolated_parser_timeout_kills_the_child(monkeypatch) -> None:
    monkeypatch.setattr(isolated, "PARSER_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(
        isolated,
        "_parser_command",
        lambda *_args, **_kwargs: [sys.executable, "-c", "import time; time.sleep(10)"],
    )

    with pytest.raises(isolated.IsolatedParserResourceError, match="time limit"):
        isolated.validate_pdf_bytes(b"%PDF-1.4\n%%EOF", max_pages=10)


def test_isolated_parser_rejects_malformed_protocol(monkeypatch) -> None:
    monkeypatch.setattr(
        isolated,
        "_parser_command",
        lambda *_args, **_kwargs: [sys.executable, "-c", "print('not-json')"],
    )

    with pytest.raises(isolated.IsolatedParserInternalError, match="invalid response"):
        isolated.validate_pdf_bytes(b"%PDF-1.4\n%%EOF", max_pages=10)


def test_parser_start_failure_is_an_internal_error(monkeypatch) -> None:
    def cannot_start(*_args, **_kwargs):
        raise OSError("process creation denied")

    monkeypatch.setattr(isolated.subprocess, "Popen", cannot_start)

    with pytest.raises(isolated.IsolatedParserInternalError, match="start safely"):
        isolated.validate_pdf_bytes(b"%PDF-1.4\n%%EOF", max_pages=10)


def test_unexpected_worker_failure_is_classified_as_internal(monkeypatch, capsys) -> None:
    args = Namespace(
        operation="extract",
        memory_limit_bytes=1024,
        max_output_bytes=1024,
    )

    def unexpected_failure(_args):
        raise RuntimeError("dependency failure")

    monkeypatch.setattr(_worker, "_arguments", lambda: args)
    monkeypatch.setattr(_worker, "_install_memory_limit", lambda _limit: None)
    monkeypatch.setattr(_worker, "_extract", unexpected_failure)

    assert _worker.main() == 0
    assert json.loads(capsys.readouterr().out) == {"ok": False, "error": "internal"}


def test_parent_rechecks_extracted_text_limit(monkeypatch, tmp_path) -> None:
    path = tmp_path / "policy.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF")
    monkeypatch.setattr(
        isolated,
        "_run_parser",
        lambda *_args, **_kwargs: {
            "ok": True,
            "documents": [{
                "page_content": "x" * (isolated.PARSER_MAX_EXTRACTED_CHARACTERS + 1),
                "metadata": {},
            }],
        },
    )

    with pytest.raises(isolated.IsolatedParserResourceError, match="exceeds"):
        isolated.load_isolated_file(path, source_type="pdf", max_bytes=1024 * 1024)
