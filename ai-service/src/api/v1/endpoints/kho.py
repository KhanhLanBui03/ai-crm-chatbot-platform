"""Quản lý kho tri thức — UC020 (SCR030–SCR032): duyệt, xem đoạn, sửa, nạp lại, gỡ. [PRODUCTION]

Đường dẫn theo ``docs/openapi/ai-service-to-java-core.yaml`` mục B (bề mặt đọc cho dashboard,
ADR-0014) — dashboard đọc QUA java-core, không gọi thẳng ai-service. ``PATCH /v1/documents/{id}``
chưa có trong hợp đồng: nháp ở ``docs/contracts/uc020-quan-ly-kho.md``.

``document_id`` trên đường dẫn chỉ là định danh tài nguyên, KHÔNG phải nguồn tenant: phiên CSDL gắn
tenant từ ``X-Tenant-Id``, RLS che tài liệu của tenant khác thành 404 — cùng mã với "không tồn tại".
"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from src.ai import service
from src.ai.schemas import (
    ChunkPage,
    DocumentDeleted,
    DocumentDetail,
    DocumentMetadataUpdate,
    DocumentPage,
    ReindexAccepted,
    ReindexTenantAccepted,
)
from src.api.deps import SessionDep, TenantIdDep

router = APIRouter(tags=["kho-tri-thuc"])

TrangThai = Literal["PENDING", "PROCESSING", "READY", "FAILED", "ARCHIVED"]
LoaiNguon = Literal["PDF", "DOCX", "TXT", "MD", "HTML", "URL"]

_404 = {404: {"description": "DOCUMENT_NOT_FOUND — không có, hoặc thuộc tenant khác"}}
_401 = {401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"}}
_409 = {409: {"description": "DOCUMENT_BUSY — đang nạp / đang nạp lại · DOCUMENT_NOT_READY · "
                             "DOCUMENT_ARCHIVED"}}


@router.get("/documents", response_model=DocumentPage, operation_id="listDocuments",
            responses=_401)
async def danh_sach_tai_lieu(
    tenant_id: TenantIdDep,
    session: SessionDep,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=200),
    status: TrangThai | None = None,
    source_type: Annotated[LoaiNguon | None, Query(alias="sourceType")] = None,
) -> DocumentPage:
    """SCR030. ``keyword`` không phân biệt hoa thường và dấu. Không lọc ``status`` thì ẩn
    ARCHIVED."""
    return await service.list_documents(
        session, keyword=keyword, status=status, source_type=source_type, page=page, size=size
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail,
            operation_id="getDocumentDetail", responses={**_401, **_404})
async def chi_tiet_tai_lieu(
    document_id: UUID, tenant_id: TenantIdDep, session: SessionDep
) -> DocumentDetail:
    return await service.get_document(session, document_id)


@router.patch("/documents/{document_id}", response_model=DocumentDetail,
              operation_id="updateDocumentMetadata",
              responses={**_401, **_404, **_409,
                         422: {"description": "INVALID_METADATA — sai định dạng, trùng tiêu đề"}})
async def sua_sieu_du_lieu(
    document_id: UUID, yeu_cau: DocumentMetadataUpdate, tenant_id: TenantIdDep, session: SessionDep
) -> DocumentDetail:
    """Chỉ ``title`` + ``description`` — không đụng chỉ mục vector."""
    return await service.update_document_metadata(session, document_id, yeu_cau)


@router.get("/documents/{document_id}/chunks", response_model=ChunkPage,
            operation_id="listDocumentChunks", responses={**_401, **_404})
async def doan_cua_tai_lieu(
    document_id: UUID,
    tenant_id: TenantIdDep,
    session: SessionDep,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
) -> ChunkPage:
    """SCR031/SCR032. Không bao giờ trả ``embedding``."""
    return await service.list_chunks(session, document_id, page=page, size=size)


@router.post("/documents/{document_id}/reindex", response_model=ReindexAccepted,
             operation_id="reindexSingleDocument", responses={**_401, **_404, **_409})
async def nap_lai_tai_lieu(
    document_id: UUID, tenant_id: TenantIdDep, session: SessionDep
) -> ReindexAccepted:
    """Tạo bản bóng (ADR-0031). Bản cũ vẫn phục vụ tới khi bản mới READY."""
    return await service.reindex_document(session, document_id)


@router.delete("/documents/{document_id}", response_model=DocumentDeleted,
               operation_id="deleteDocumentProxy", responses={**_401, **_404, **_409})
async def go_tai_lieu(
    document_id: UUID, tenant_id: TenantIdDep, session: SessionDep
) -> DocumentDeleted:
    return await service.delete_document(session, document_id)


@router.delete("/ai/kb/documents/{document_id}", response_model=DocumentDeleted,
               operation_id="deleteKnowledgeDocument", responses={**_401, **_404, **_409})
async def go_tai_lieu_noi_bo(
    document_id: UUID, tenant_id: TenantIdDep, session: SessionDep
) -> DocumentDeleted:
    """Cùng xử lý với ``DELETE /v1/documents/{id}`` — hợp đồng khai cả hai đường."""
    return await service.delete_document(session, document_id)


@router.post("/ai/kb/reindex", response_model=ReindexTenantAccepted,
             operation_id="reindexKnowledgeBase", responses=_401)
async def nap_lai_toan_kho(tenant_id: TenantIdDep, session: SessionDep) -> ReindexTenantAccepted:
    """Đổi mô hình nhúng ⇒ nạp lại mọi tài liệu READY (UC020 luồng phụ 6.1). Chạy nền."""
    return await service.reindex_tenant(session, tenant_id)
