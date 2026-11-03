"""Document API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission
from app.core.rbac import Permission
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import documents as document_service
from app.features.document_uploads import DocumentUploadFormDep
from app.features.schemas import (
    DocumentChunkListResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENT_MULTIPART_REQUEST = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                        "title": {"type": "string"},
                        "visibility": {"type": "string", "enum": ["internal", "public"]},
                    },
                }
            }
        },
    }
}


@router.get("", dependencies=[Depends(require_permission(Permission.VIEW_DOCUMENTS))])
async def list_documents(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    type: Annotated[Literal["pdf", "docx", "txt"] | None, Query()] = None,
    status_filter: Annotated[
        Literal["uploaded", "processing", "ready", "failed"] | None,
        Query(alias="status"),
    ] = None,
    visibility: Annotated[Literal["internal", "public"] | None, Query()] = None,
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
    dependencies=[Depends(require_permission(Permission.UPLOAD_DOCUMENTS))],
    openapi_extra=DOCUMENT_MULTIPART_REQUEST,
)
async def upload_document(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    upload: DocumentUploadFormDep,
) -> DocumentCreateResponse:
    return await document_service.create_document(
        session,
        tenant_id=tenant.tenant_id,
        uploaded_by_user_id=current_user.id,
        file=upload.file,
        title=upload.title,
        visibility=upload.visibility or "internal",
    )


@router.get("/{document_id}", dependencies=[Depends(require_permission(Permission.VIEW_DOCUMENTS))])
async def get_document(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> DocumentResponse:
    return await document_service.get_document(session, tenant.tenant_id, document_id)


@router.patch("/{document_id}", dependencies=[Depends(require_permission(Permission.MANAGE_DOCUMENTS))])
async def update_document(
    document_id: UUID,
    request: DocumentUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> DocumentResponse:
    return await document_service.update_document(session, tenant.tenant_id, document_id, request)


@router.put(
    "/{document_id}",
    dependencies=[Depends(require_permission(Permission.MANAGE_DOCUMENTS))],
    openapi_extra=DOCUMENT_MULTIPART_REQUEST,
)
async def replace_document(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    upload: DocumentUploadFormDep,
) -> DocumentResponse:
    return await document_service.replace_document_content(
        session,
        tenant.tenant_id,
        document_id,
        file=upload.file,
        title=upload.title,
        visibility=upload.visibility,
    )


@router.post("/{document_id}/retry", dependencies=[Depends(require_permission(Permission.MANAGE_DOCUMENTS))])
async def retry_document(
    document_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> DocumentResponse:
    return await document_service.retry_document(session, tenant.tenant_id, document_id)


@router.get("/{document_id}/chunks", dependencies=[Depends(require_permission(Permission.VIEW_DOCUMENTS))])
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
