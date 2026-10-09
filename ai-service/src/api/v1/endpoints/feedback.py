"""Đánh giá chất lượng câu trả lời — UC027 · khoảng trống tri thức — UC025. [PRODUCTION]

Hai đường gửi đánh giá, cùng một xử lý (đều có trong docs/openapi/ai-service-to-java-core.yaml):

- ``POST /v1/ai/feedback`` (``recordFeedback``) — java-core gửi, ``interaction_id`` trong body.
- ``POST /v1/ai-interactions/{interaction_id}/feedback`` (``recordInteractionFeedbackProxy``) —
  bề mặt đọc/ghi cho dashboard (ADR-0014), id trên đường dẫn.

Id trên đường dẫn hay trong body chỉ là định danh tài nguyên, KHÔNG phải nguồn tenant: phiên CSDL
gắn tenant từ ``X-Tenant-Id``; lượt của tenant khác thành 404 như lượt không tồn tại.
"""

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query

from src.ai import service
from src.ai.schemas import FeedbackRecorded, FeedbackRequest, KnowledgeGapPage, QualitySummary
from src.api.deps import SessionDep, TenantIdDep

router = APIRouter(tags=["chat-luong"])

_LOI_DANH_GIA = {
    401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"},
    404: {"description": "INTERACTION_NOT_FOUND — lượt không có, hoặc thuộc tenant khác"},
    422: {
        "description": "REASON_REQUIRED (chê thiếu lý do) · INVALID_RATER · INVALID_FEEDBACK"
    },
}


@router.post(
    "/ai/feedback",
    response_model=FeedbackRecorded,
    operation_id="recordFeedback",
    responses=_LOI_DANH_GIA,
)
async def ghi_danh_gia(
    yeu_cau: FeedbackRequest, tenant_id: TenantIdDep, session: SessionDep
) -> FeedbackRecorded:
    """Ghi đánh giá; đánh giá lại từ cùng phía thì CẬP NHẬT (``created=false``), không báo 409."""
    return await service.record_feedback(session, yeu_cau)


@router.post(
    "/ai-interactions/{interaction_id}/feedback",
    response_model=FeedbackRecorded,
    operation_id="recordInteractionFeedbackProxy",
    responses=_LOI_DANH_GIA,
)
async def ghi_danh_gia_theo_luot(
    interaction_id: UUID, yeu_cau: FeedbackRequest, tenant_id: TenantIdDep, session: SessionDep
) -> FeedbackRecorded:
    return await service.record_feedback(session, yeu_cau, interaction_id)


@router.get(
    "/knowledge-gaps",
    response_model=KnowledgeGapPage,
    operation_id="listKnowledgeGaps",
    responses={401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"}},
)
async def khoang_trong_tri_thuc(
    tenant_id: TenantIdDep,
    session: SessionDep,
    gap_type: Literal["NOT_COVERED", "OUT_OF_SCOPE_DATA", "LOW_CONFIDENCE"] | None = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    so_ngay: int = Query(default=30, ge=1, le=365),
) -> KnowledgeGapPage:
    """SCR034 — sắp theo số hội thoại khác nhau, rồi số lần (UC025 luồng phụ 8.1)."""
    return await service.knowledge_gaps(
        session, tenant_id, gap_type=gap_type, page=page, size=size, so_ngay=so_ngay
    )


@router.get(
    "/ai/quality",
    response_model=QualitySummary,
    operation_id="getQualitySummary",
    responses={401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"}},
)
async def tin_hieu_chat_luong(
    tenant_id: TenantIdDep,
    session: SessionDep,
    tu: datetime | None = None,
    den: datetime | None = None,
) -> QualitySummary:
    """UC027 bước 7 — bảy tín hiệu chất lượng. Mặc định 7 ngày gần nhất.

    Chưa có trong hợp đồng — đề xuất ở docs/contracts/uc025-uc027-tu-choi-danh-gia.md.
    """
    den = den or service.bay_gio()
    tu = tu or den - timedelta(days=7)
    return await service.quality_summary(session, tu, den)
