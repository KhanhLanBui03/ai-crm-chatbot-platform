"""Kho tri thức — UC018 tải lên tài liệu · UC019 tiến độ nạp. [PRODUCTION]

Chỉ java-core gọi endpoint này, SAU KHI đã kiểm hạn mức gói (409), dung lượng (413), đuôi tệp
và ghi tệp vào kho S3 (ADR-0022). Đặc tả UC018 đặt ranh giới ở URI tệp: java-core không
đọc nội dung tệp, ai-service không ghi vào schema của Track A (ADR-0002).

Tên đường dẫn ``/v1/ai/kb/documents`` theo đặc tả UC018 và ``service.py`` — hợp đồng
``docs/openapi/ai-service-to-java-core.yaml`` còn ghi ``/v1/documents``, ghi nợ ở ADR-0020.
"""

from uuid import UUID

from fastapi import APIRouter

from src.ai import service
from src.ai.schemas import IngestionJobProgress, KbDocumentAccepted, KbDocumentCreate
from src.api.deps import SessionDep, TenantIdDep

router = APIRouter(prefix="/ai/kb", tags=["kb"])


@router.post(
    "/documents",
    status_code=202,
    response_model=KbDocumentAccepted,
    # Mọi thân lỗi có dạng {code, message} — src/api/errors.py.
    responses={
        401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"},
        403: {"description": "FORBIDDEN_FILE_URI — URI ngoài vùng của tenant"},
        413: {"description": "FILE_TOO_LARGE — tệp vượt 20 MiB"},
        415: {"description": "UNSUPPORTED_FORMAT — đuôi hoặc nội dung không hỗ trợ"},
        422: {"description": "INVALID_METADATA hoặc FILE_NOT_FOUND"},
        503: {"description": "STORAGE_UNAVAILABLE — không đọc được kho S3, thử lại sau"},
    },
)
async def tao_tai_lieu(
    yeu_cau: KbDocumentCreate, tenant_id: TenantIdDep, session: SessionDep
) -> KbDocumentAccepted:
    """Nhận tài liệu, ghi ``PENDING``, trả 202 + ``job_id``. Không chờ lập chỉ mục.

    ``tenant_id`` đến DUY NHẤT từ ``TenantIdDep`` (header ``X-Tenant-Id``) — ``KbDocumentCreate``
    không có trường tenant, và ``extra="forbid"`` từ chối nếu phía gọi cố gửi.
    """
    return await service.index_document(session, tenant_id, yeu_cau)


@router.get(
    "/ingestion-jobs/{job_id}",
    response_model=IngestionJobProgress,
    responses={
        401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"},
        404: {"description": "DOCUMENT_NOT_FOUND — không có, hoặc thuộc tenant khác"},
    },
)
async def tien_do_nap(
    job_id: UUID, tenant_id: TenantIdDep, session: SessionDep
) -> IngestionJobProgress:
    """UC019 — sáu bước tiến độ của một job nạp (SCR033). ``job_id`` = ``document_id``.

    ``job_id`` trên đường dẫn chỉ là định danh tài nguyên, KHÔNG phải nguồn tenant: phiên CSDL gắn
    tenant từ ``X-Tenant-Id``, RLS che mọi job của tenant khác thành 404 — cùng mã với job không
    tồn tại, để không dò được id nào có thật ở tenant khác.
    """
    return await service.tien_do_nap(session, job_id)
