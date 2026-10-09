"""Tóm tắt hội thoại, đường đồng bộ — UC026 (nút "tóm tắt lại", trigger ``MANUAL``). [PRODUCTION]

``POST /v1/ai/summarize`` đã có trong ``docs/openapi/ai-service-to-java-core.yaml``. java-core gửi
kèm lịch sử, nhận bốn phần + ảnh chụp phiên bản model và TỰ ghi vào ``engagement.conversations``.
Đường chính của UC026 là bất đồng bộ (worker, ``crm.conversation.closed``) — xem
``src/worker/consumers/tom_tat.py``.

Không dùng ``SessionDep``: lượt tóm tắt gọi LLM vài giây, giữ một transaction mở suốt chừng đó là
giữ một kết nối pool vô ích. Facade tự mở phiên ngắn lúc ghi ``ai_interactions``.
"""

from fastapi import APIRouter

from src.ai import service
from src.ai.schemas import SummarizeRequest, SummarizeResponse
from src.api.deps import TenantIdDep, TraceIdDep

router = APIRouter(tags=["tom-tat"])


@router.post(
    "/ai/summarize",
    response_model=SummarizeResponse,
    operation_id="summarizeConversation",
    responses={
        401: {"description": "TENANT_CONTEXT_MISSING"},
        422: {"description": "CONVERSATION_TOO_SHORT · SUMMARY_SCHEMA_INVALID · INVALID_REQUEST"},
        503: {"description": "LLM_ERROR — nhà cung cấp không phục vụ, thử lại sau"},
    },
)
async def tom_tat_hoi_thoai(
    yeu_cau: SummarizeRequest, tenant_id: TenantIdDep, trace_id: TraceIdDep
) -> SummarizeResponse:
    return await service.summarize_messages(tenant_id, yeu_cau)
