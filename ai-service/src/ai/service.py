r"""FACADE DUY NHẤT của khối AI — §3.9.2.

Đây là bề mặt duy nhất mà ``src/api/`` và ``src/worker/`` được phép gọi vào. Mọi
năng lực bên dưới (``rag/``, ``orchestrator/``, ``mcp_client/``, ``extraction/``,
``scoring/``, ``clustering/``) đều đi qua đây.

VÌ SAO CÓ FACADE — không phải để cho "gọn"
-------------------------------------------
``api/`` và ``worker/`` **không được import chéo nhau** (§3.9.1: một image, hai vai
trò độc lập). Nhưng cả hai đều cần đúng những năng lực AI giống nhau: một lượt chat
đến từ HTTP và một hội thoại đóng đến từ Kafka chạy qua phần lớn cùng một đường ống.

Facade là chỗ duy nhất giữ được cả hai điều đó cùng lúc. Hệ quả kiểm tra được bằng
máy: ``src/ai/`` **không bao giờ** import ``src.api`` hay ``src.worker``.

Lệnh kiểm phải neo vào ĐẦU DÒNG, nếu không nó tự khớp chính câu lệnh viết trong
docstring này và báo vi phạm giả::

    grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' src/ai/

Nhờ chiều phụ thuộc một hướng này, ``tests/eval/`` chạy lại đúng đường ống RAG mà
không cần dựng máy chủ HTTP.

CHIỀU PHỤ THUỘC
---------------
    api ──┐
          ├──► ai/service.py ──► rag · orchestrator · mcp_client · extraction · scoring
    worker┘                  └──► db · events · telemetry · inference · integrations

Các phương thức của facade — bám theo 10 endpoint §2.5 và hai topic §2.6:
    answer_turn()      UC022/023/025/028   POST /v1/ai/chat     ĐÃ CÓ (UC022; RAG chưa nối)
    extract_signal()   UC029               POST /v1/ai/extract
    score_lead()       UC030               POST /v1/ai/lead-score
    index_document()   UC018/019           POST /v1/ai/kb/documents
    delete_document()  UC020               DELETE /v1/ai/kb/documents/{id}
    reindex_tenant()   UC020               POST /v1/ai/kb/reindex
    record_feedback()  UC027               POST /v1/ai/feedback
    set_mcp_config()   UC021               PUT /v1/ai/mcp/config
    forget_contact()   UC041               DELETE /v1/ai/privacy/contacts/{id}
    usage_summary()    UC006/039           GET /v1/ai/usage
    summarize()        UC026               (bất đồng bộ, từ crm.conversation.closed)
"""

from src.ai.config import get_settings
from src.ai.inference.clients import ClassifyClient, get_classify_client
from src.ai.orchestrator.turn import (
    KnowledgeAnswerer,
    LogTurnRecorder,
    PendingKnowledgeAnswerer,
    TurnRecorder,
    run_turn,
)
from src.ai.schemas import ChatRequest, ChatResponse


async def answer_turn(
    *,
    tenant_id: str,
    request: ChatRequest,
    classifier: ClassifyClient | None = None,
    answerer: KnowledgeAnswerer | None = None,
    recorder: TurnRecorder | None = None,
) -> ChatResponse:
    """Một lượt hội thoại: guardrails -> phân loại -> định tuyến -> trả lời -> ghi (UC022).

    ``tenant_id`` đến từ header đã xác thực (``api/deps.py``), không bao giờ từ ``request``.
    Ba phụ thuộc để trống thì lấy bản mặc định; test truyền bản giả vào.
    """
    settings = get_settings()
    return await run_turn(
        tenant_id=tenant_id,
        request=request,
        classifier=classifier or get_classify_client(),
        answerer=answerer or PendingKnowledgeAnswerer(),
        recorder=recorder or LogTurnRecorder(),
        fast_path_threshold=settings.fast_path_threshold,
        abstention_threshold=settings.router_abstention_threshold,
        classify_timeout_s=settings.classify_timeout_s,
        classify_retries=settings.classify_retries,
    )
