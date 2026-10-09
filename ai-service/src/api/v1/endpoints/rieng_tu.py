"""Xoá dữ liệu cá nhân phía Track B — UC041. [PRODUCTION]

``DELETE /v1/ai/privacy/contacts/{contactId}?conversationId=…`` — đặc tả UC041 "REST nội bộ":
đồng bộ, xoá mọi đoạn tri thức và bản ghi gắn với một khách. Nháp hợp đồng:
``docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md``.

CHỈ java-core được gọi, và chỉ SAU khi quy trình xác minh danh tính bên CRM đã xong (đặc tả: "Bên
AI không tự khởi động việc xoá"). Chốt: header ``X-Internal-Token`` phải khớp
``INTERNAL_API_TOKEN``. Gateway đang mở ``/ai/v1/**`` cho MỌI JWT của tenant — không có chốt này
thì một nhân viên bất kỳ xoá vĩnh viễn được dữ liệu của khách mà bỏ qua bước xác minh, đúng chỗ
đặc tả gọi là "dễ bỏ sót nhất của quy trình". So bằng ``hmac.compare_digest`` (thời gian hằng).

``conversationId`` lặp lại được: ``ai_interactions`` không có ``contact_id`` (liên làn, V204), và
chỉ java-core biết khách có những hội thoại nào. ``contactId`` và ``conversationId`` chỉ là định
danh tài nguyên — tenant vẫn từ ``X-Tenant-Id``; RLS làm id của tenant khác khớp 0 dòng.

Không dùng ``SessionDep`` (một transaction cho cả request): phần CSDL phải COMMIT trước khi xoá
tệp S3 và gọi java-core — facade tự mở phiên của nó.
"""

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query

from src.ai import service
from src.ai.exceptions import InternalOnlyError
from src.ai.schemas import ErasureResult
from src.api.deps import SettingsDep, TenantIdDep, TraceIdDep

router = APIRouter(tags=["rieng-tu"])


def _kiem_token_noi_bo(cau_hinh_token: str, x_internal_token: str | None) -> None:
    if not cau_hinh_token:
        raise InternalOnlyError("Endpoint đóng: ai-service chưa cấu hình INTERNAL_API_TOKEN")
    if not x_internal_token or not hmac.compare_digest(
        x_internal_token.encode(), cau_hinh_token.encode()
    ):
        raise InternalOnlyError("Chỉ java-core được gọi endpoint này")


@router.delete(
    "/ai/privacy/contacts/{contact_id}",
    response_model=ErasureResult,
    operation_id="forgetContact",
    responses={
        401: {"description": "TENANT_CONTEXT_MISSING"},
        403: {"description": "INTERNAL_ONLY — thiếu/sai X-Internal-Token"},
    },
)
async def xoa_du_lieu_ca_nhan(
    contact_id: UUID,
    tenant_id: TenantIdDep,
    trace_id: TraceIdDep,
    settings: SettingsDep,
    conversation_ids: Annotated[
        list[UUID], Query(alias="conversationId", max_length=500)
    ] = [],  # noqa: B006 — FastAPI chép giá trị mặc định cho mỗi request
    x_internal_token: Annotated[str | None, Header()] = None,
) -> ErasureResult:
    """200 kèm tiến độ theo từng bảng. ``PARTIALLY_FAILED`` thì gọi lại — luỹ đẳng."""
    _kiem_token_noi_bo(settings.internal_api_token, x_internal_token)
    return await service.forget_contact(tenant_id, contact_id, conversation_ids)
