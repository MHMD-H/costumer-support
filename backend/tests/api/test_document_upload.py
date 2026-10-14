"""Task 20 upload acceptance and isolation checks."""

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.auth import get_current_dashboard_user
from app.db.models import Document
from app.db.postgres import get_db_session
from app.features import documents as service
from app.features.mock_services import mock_auth_user
from app.main import create_app


@pytest.fixture
def upload_client(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path))
    user = mock_auth_user()
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = lambda: user

    async def session():
        yield None

    app.dependency_overrides[get_db_session] = session
    calls = []

    async def get_user(_session, tenant_id, user_id):
        calls.append((tenant_id, user_id))
        return object() if (tenant_id, user_id) == (user.tenant_id, user.id) else None

    async def create(_session, **kwargs):
        now = datetime.now(timezone.utc)
        return Document(
            id=kwargs["document_id"], tenant_id=kwargs["tenant_id"],
            uploaded_by_user_id=kwargs["uploaded_by_user_id"],
            title=kwargs["title"], type=kwargs["document_type"],
            source=kwargs["source"], visibility=kwargs["visibility"],
            status="uploaded", metadata_={}, created_at=now, updated_at=now,
        )

    monkeypatch.setattr(service.user_repository, "get_user_by_id", get_user)
    monkeypatch.setattr(service.document_repository, "create_document", create)
    return TestClient(app), user, calls, tmp_path


def post(client, name, content, **kwargs):
    return client.post("/documents", files={"file": (name, content, "application/octet-stream")}, **kwargs)


def test_valid_txt_is_retained_with_trusted_ids(upload_client):
    client, user, calls, root = upload_client
    attacker = uuid4()
    response = post(client, "../policy.txt", b"Returns within 30 days.\n", data={"visibility": "public", "tenant_id": str(attacker)}, headers={"X-Tenant-ID": str(attacker)})
    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == str(user.tenant_id)
    assert body["source"] == "policy.txt"
    assert body["status"] == "uploaded"
    assert (root / str(user.tenant_id) / f'{body["id"]}.txt').read_bytes() == b"Returns within 30 days.\n"
    assert calls == [(user.tenant_id, user.id)]
    assert not (root / str(attacker)).exists()


@pytest.mark.parametrize("name,data,expected", [
    ("policy.exe", b"hello", 415),
    ("policy.pdf", b"plain text", 400),
    ("policy.docx", b"PK\x03\x04broken", 400),
    ("policy.txt", b"", 400),
    ("policy.txt", b"\xff\xfe", 400),
    ("policy.txt", b" \n\t", 400),
    ("policy.txt", b"a" * (5 * 1024 * 1024 + 1), 413),
], ids=["unsupported", "pdf-mismatch", "bad-docx", "empty", "bad-utf8", "whitespace", "oversized"])
def test_invalid_upload_creates_nothing(upload_client, name, data, expected):
    client, user, _calls, root = upload_client
    response = post(client, name, data)
    assert response.status_code == expected
    assert not list(root.rglob("*"))


def test_missing_permission_cannot_store_file(upload_client, monkeypatch):
    client, user, _calls, root = upload_client
    client.app.dependency_overrides[get_current_dashboard_user] = lambda: user.model_copy(update={"role": "team_member"})
    async def no_grants(_session, _tenant_id, _user_id):
        return []
    from app.core import permissions
    monkeypatch.setattr(permissions.permission_repository, "list_user_permission_values", no_grants)
    response = post(client, "secret.txt", b"secret")
    assert response.status_code == 403
    assert not list(root.rglob("*"))


def test_cross_tenant_uploader_is_not_found(upload_client, monkeypatch):
    client, user, _calls, root = upload_client

    async def missing(_session, _tenant_id, _user_id):
        return None

    monkeypatch.setattr(service.user_repository, "get_user_by_id", missing)
    response = post(client, "secret.txt", b"secret")
    assert response.status_code == 404
    assert not list(root.rglob("*"))


def test_multipart_body_limit_rejects_before_storage(upload_client):
    client, _user, _calls, root = upload_client
    response = post(client, "large.txt", b"a" * (5 * 1024 * 1024 + 64 * 1024))
    assert response.status_code == 413
    assert not list(root.rglob("*"))


def test_multipart_body_limit_counts_bytes_without_length(upload_client):
    client, _user, _calls, root = upload_client
    response = post(client, "large.txt", b"a" * (5 * 1024 * 1024 + 64 * 1024), headers={"Content-Length": "0"})
    assert response.status_code == 413
    assert not list(root.rglob("*"))


def test_valid_pdf_and_docx_are_retained(upload_client):
    client, user, _calls, root = upload_client
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(pdf)
    docx = BytesIO()
    with ZipFile(docx, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr("word/document.xml", '<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><body><p><r><t>Policy</t></r></p></body></document>')
    for extension, content in (("pdf", pdf.getvalue()), ("docx", docx.getvalue())):
        response = post(client, f"policy.{extension}", content)
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == extension
        assert (root / str(user.tenant_id) / f'{body["id"]}.{extension}').read_bytes() == content


def test_database_failure_removes_staged_content(upload_client, monkeypatch):
    client, user, _calls, root = upload_client

    async def broken_create(_session, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(service.document_repository, "create_document", broken_create)
    with pytest.raises(RuntimeError, match="database unavailable"):
        post(client, "policy.txt", b"Returns within 30 days")
    assert not list((root / str(user.tenant_id)).glob("*"))
