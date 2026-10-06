"""[PRODUCTION] ``POST /v1/ai/chat`` — operationId ``answerChatTurn``.

Hợp đồng: docs/openapi/ai-service-to-java-core.yaml. Endpoint chỉ làm ba việc: lấy tenant
từ header đã xác thực, gọi facade, trả kết quả. Mọi logic nằm ở ``src/ai/``.
"""

from fastapi import APIRouter

from src.ai import service
from src.ai.schemas import ChatRequest, ChatResponse
from src.api.deps import TenantIdDep, TraceIdDep

router = APIRouter(tags=["chat"])


@router.post("/ai/chat", response_model=ChatResponse, operation_id="answerChatTurn")
async def answer_chat_turn(
    body: ChatRequest,
    tenant_id: TenantIdDep,
    _trace_id: TraceIdDep,
) -> ChatResponse:
    return await service.answer_turn(tenant_id=tenant_id, request=body)
