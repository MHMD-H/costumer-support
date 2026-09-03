"""Document API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import documents as document_service
from app.features.schemas import (
    DocumentChunkListResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    type: Literal["pdf", "docx", "txt"] | None = None,
    status_filter: Annotated[
        Literal["uploaded", "processing", "ready", "failed"] | None,
        Query(alias="status"),
    ] = None,
    visibility: Literal["internal", "public"] | None = None,
) -> DocumentListResponse:
    return await document_service.list_documents(
        session,
        tenant.tenant_id,
        document_type=type,
        status=status_filter,
        visibility=visibility,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("upload_documents"))],
)
async def upload_document(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    file: UploadFile = File(),
    title: str | None = Form(default=None),
    visibility: Literal["internal", "public"] = Form(default="internal"),
) -> DocumentCreateResponse:
    return await document_service.create_document(
        session,
        tenant_id=tenant.tenant_id,
        uploaded_by_user_id=current_user.id,
        filename=file.filename or "uploaded.txt",
        title=title,
        visibility=visibility,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> DocumentResponse:
    return await document_service.get_document(session, tenant.tenant_id, document_id)


@router.get("/{document_id}/chunks")
async def list_document_chunks(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentChunkListResponse:
    return await document_service.list_document_chunks(
        session,
        tenant.tenant_id,
        document_id,
        limit=limit,
        offset=offset,
    )
