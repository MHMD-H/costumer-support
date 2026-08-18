"""Document API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import (
    DocumentChunkListResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    type: Literal["pdf", "docx", "txt"] | None = None,
    status_filter: Annotated[
        Literal["uploaded", "processing", "ready", "failed"] | None,
        Query(alias="status"),
    ] = None,
    visibility: Literal["internal", "public"] | None = None,
) -> DocumentListResponse:
    return mock_services.list_documents(limit, offset)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("upload_documents"))],
)
def upload_document(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    file: UploadFile = File(),
    title: str | None = Form(default=None),
    visibility: Literal["internal", "public"] = Form(default="internal"),
) -> DocumentCreateResponse:
    return mock_services.create_document(file.filename or "uploaded.txt", title, visibility)


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> DocumentResponse:
    return mock_services.document_response(document_id)


@router.get("/{document_id}/chunks")
def list_document_chunks(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentChunkListResponse:
    return mock_services.list_document_chunks(limit, offset)
